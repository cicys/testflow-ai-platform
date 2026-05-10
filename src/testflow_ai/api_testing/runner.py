from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from testflow_ai.api_testing.models import APIAssertion, APIStep, APISuite, AssertionKind, AssertionOperator

_MISSING = object()
_VARIABLE_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_.-]*)\s*\}\}")
_SENSITIVE_HEADER_PARTS = ("authorization", "token", "api-key", "apikey", "secret", "password", "cookie")


def load_suite(path: Path) -> APISuite:
    """Load a suite from a JSON file."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return APISuite.model_validate(payload)


def run_suite(suite: APISuite, timeout_seconds: float | None = None) -> dict[str, Any]:
    """Execute a suite and return a serializable report."""
    started = time.perf_counter()
    case_results: list[dict[str, Any]] = []

    for case in suite.cases:
        variables = {**suite.variables, **case.variables}
        step_results: list[dict[str, Any]] = []
        for step in case.steps:
            result = _run_step(
                suite=suite,
                step=step,
                variables=variables,
                timeout_seconds=timeout_seconds or step.timeout_seconds or suite.timeout_seconds,
            )
            variables.update(result.get("extracted") or {})
            step_results.append(result)

        passed_steps = sum(1 for item in step_results if item["status"] == "passed")
        failed_steps = len(step_results) - passed_steps
        case_results.append(
            {
                "case_id": case.case_id,
                "name": case.name,
                "tags": case.tags,
                "status": "passed" if failed_steps == 0 else "failed",
                "passed_steps": passed_steps,
                "failed_steps": failed_steps,
                "steps": step_results,
            }
        )

    total_cases = len(case_results)
    passed_cases = sum(1 for item in case_results if item["status"] == "passed")
    failed_cases = total_cases - passed_cases
    total_steps = sum(len(item["steps"]) for item in case_results)
    passed_steps = sum(item["passed_steps"] for item in case_results)
    failed_steps = total_steps - passed_steps
    duration_ms = round((time.perf_counter() - started) * 1000, 3)

    return {
        "suite_id": suite.suite_id,
        "suite_name": suite.name,
        "status": "passed" if failed_cases == 0 else "failed",
        "total_cases": total_cases,
        "passed_cases": passed_cases,
        "failed_cases": failed_cases,
        "total_steps": total_steps,
        "passed_steps": passed_steps,
        "failed_steps": failed_steps,
        "duration_ms": duration_ms,
        "metrics": {
            "case_pass_rate": _rate(passed_cases, total_cases),
            "step_pass_rate": _rate(passed_steps, total_steps),
        },
        "cases": case_results,
    }


def _run_step(
    suite: APISuite,
    step: APIStep,
    variables: dict[str, Any],
    timeout_seconds: float,
) -> dict[str, Any]:
    method = step.method.value
    headers = _string_map({**suite.headers, **_render_value(step.headers, variables)})
    query_params = _render_value(step.query_params, variables)
    body = _render_value(step.body, variables)
    url = _build_url(suite.base_url, str(_render_value(step.endpoint, variables)), query_params)
    request_body: bytes | None = None

    if body is not None:
        request_body = json.dumps(body).encode("utf-8")
        _set_default_header(headers, "Content-Type", "application/json")

    request = urllib.request.Request(url, data=request_body, headers=headers, method=method)
    started = time.perf_counter()
    status_code: int | None = None
    response_headers: dict[str, str] = {}
    response_text = ""
    response_json: Any = None
    transport_error: str | None = None

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            status_code, response_headers, response_text, response_json = _read_response(response)
    except urllib.error.HTTPError as exc:
        status_code, response_headers, response_text, response_json = _read_response(exc)
    except Exception as exc:
        transport_error = str(exc)

    duration_ms = round((time.perf_counter() - started) * 1000, 3)
    assertion_results = [
        _evaluate_assertion(assertion, status_code, response_headers, response_text, response_json, duration_ms)
        for assertion in step.assertions
    ]
    if transport_error is not None:
        assertion_results.append(
            {
                "kind": "transport",
                "path": None,
                "operator": "connect",
                "expected": None,
                "actual": transport_error,
                "passed": False,
                "message": "request failed before a response was received",
            }
        )

    passed = all(item["passed"] for item in assertion_results)
    extracted = _extract_variables(step.extract, response_json)
    return {
        "step_id": step.step_id,
        "name": step.name,
        "status": "passed" if passed else "failed",
        "request": {
            "method": method,
            "url": _redact_url(url),
            "headers": _redact_headers(headers),
            "has_body": body is not None,
        },
        "response": {
            "status_code": status_code,
            "duration_ms": duration_ms,
            "headers": _redact_headers(response_headers),
        },
        "assertions": assertion_results,
        "extracted": extracted,
        "error": transport_error,
    }


def _read_response(response: Any) -> tuple[int | None, dict[str, str], str, Any]:
    raw = response.read()
    text = raw.decode("utf-8", errors="replace")
    status_code = getattr(response, "status", None) or getattr(response, "code", None)
    headers = _headers_to_dict(getattr(response, "headers", None))
    try:
        payload = json.loads(text) if text else None
    except json.JSONDecodeError:
        payload = None
    return status_code, headers, text, payload


def _evaluate_assertion(
    assertion: APIAssertion,
    status_code: int | None,
    headers: dict[str, str],
    text: str,
    payload: Any,
    duration_ms: float,
) -> dict[str, Any]:
    actual = _actual_value(assertion.kind, assertion.path, status_code, headers, text, payload, duration_ms)
    passed = _compare(actual, assertion.expected, assertion.operator)
    return {
        "kind": assertion.kind.value,
        "path": assertion.path,
        "operator": assertion.operator.value,
        "expected": assertion.expected,
        "actual": None if actual is _MISSING else actual,
        "passed": passed,
        "message": assertion.message,
    }


def _actual_value(
    kind: AssertionKind,
    path: str | None,
    status_code: int | None,
    headers: dict[str, str],
    text: str,
    payload: Any,
    duration_ms: float,
) -> Any:
    if kind == AssertionKind.STATUS_CODE:
        return status_code
    if kind == AssertionKind.JSON_PATH:
        return _lookup_path(payload, path)
    if kind == AssertionKind.HEADER:
        return _header_value(headers, path or "")
    if kind == AssertionKind.BODY_CONTAINS:
        return text
    if kind == AssertionKind.RESPONSE_TIME_MS:
        return duration_ms
    return _MISSING


def _compare(actual: Any, expected: Any, operator: AssertionOperator) -> bool:
    if operator == AssertionOperator.EXISTS:
        return actual is not _MISSING and actual is not None
    if actual is _MISSING:
        return False
    if operator == AssertionOperator.EQUALS:
        return actual == expected
    if operator == AssertionOperator.NOT_EQUALS:
        return actual != expected
    if operator == AssertionOperator.CONTAINS:
        if isinstance(actual, str):
            return str(expected) in actual
        try:
            return expected in actual
        except TypeError:
            return str(expected) in str(actual)
    if operator == AssertionOperator.GREATER_THAN:
        return _as_float(actual) > _as_float(expected)
    if operator == AssertionOperator.LESS_THAN:
        return _as_float(actual) < _as_float(expected)
    return False


def _build_url(base_url: str, endpoint: str, query_params: dict[str, Any]) -> str:
    if endpoint.startswith(("http://", "https://")):
        url = endpoint
    else:
        url = urllib.parse.urljoin(f"{base_url.rstrip('/')}/", endpoint.lstrip("/"))
    if query_params:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}{urllib.parse.urlencode(query_params, doseq=True)}"
    return url


def _render_value(value: Any, variables: dict[str, Any]) -> Any:
    if isinstance(value, str):
        full_match = _VARIABLE_RE.fullmatch(value)
        if full_match:
            return variables.get(full_match.group(1), value)
        return _VARIABLE_RE.sub(lambda match: str(variables.get(match.group(1), match.group(0))), value)
    if isinstance(value, list):
        return [_render_value(item, variables) for item in value]
    if isinstance(value, dict):
        return {key: _render_value(item, variables) for key, item in value.items()}
    return value


def _extract_variables(extractors: dict[str, str], payload: Any) -> dict[str, Any]:
    extracted: dict[str, Any] = {}
    for name, path in extractors.items():
        value = _lookup_path(payload, path)
        if value is not _MISSING:
            extracted[name] = value
    return extracted


def _lookup_path(payload: Any, path: str | None) -> Any:
    if path in (None, "", "$"):
        return payload
    current = payload
    tokens = _path_tokens(str(path))
    for token in tokens:
        if isinstance(current, dict) and isinstance(token, str) and token in current:
            current = current[token]
        elif isinstance(current, list) and isinstance(token, int) and 0 <= token < len(current):
            current = current[token]
        else:
            return _MISSING
    return current


def _path_tokens(path: str) -> list[str | int]:
    normalized = path[2:] if path.startswith("$.") else path[1:] if path.startswith("$") else path
    tokens: list[str | int] = []
    for part in normalized.split("."):
        if not part:
            continue
        cursor = 0
        for match in re.finditer(r"([^\[\]]+)|\[(\d+)\]", part):
            if match.start() != cursor:
                return []
            if match.group(1) is not None:
                tokens.append(match.group(1))
            else:
                tokens.append(int(match.group(2)))
            cursor = match.end()
    return tokens


def _headers_to_dict(headers: Any) -> dict[str, str]:
    if headers is None:
        return {}
    if isinstance(headers, dict):
        return {str(key): str(value) for key, value in headers.items()}
    if hasattr(headers, "items"):
        return {str(key): str(value) for key, value in headers.items()}
    return {}


def _header_value(headers: dict[str, str], name: str) -> str | None:
    requested = name.lower()
    for key, value in headers.items():
        if key.lower() == requested:
            return value
    return None


def _string_map(values: dict[str, Any]) -> dict[str, str]:
    return {str(key): str(value) for key, value in values.items()}


def _set_default_header(headers: dict[str, str], name: str, value: str) -> None:
    if not any(key.lower() == name.lower() for key in headers):
        headers[name] = value


def _redact_headers(headers: dict[str, str]) -> dict[str, str]:
    redacted: dict[str, str] = {}
    for key, value in headers.items():
        if any(part in key.lower() for part in _SENSITIVE_HEADER_PARTS):
            redacted[key] = "***"
        else:
            redacted[key] = value
    return redacted


def _redact_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    safe_query = [
        (key, "***" if any(part in key.lower() for part in _SENSITIVE_HEADER_PARTS) else value)
        for key, value in query
    ]
    return urllib.parse.urlunsplit(parsed._replace(query=urllib.parse.urlencode(safe_query)))


def _rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 6)


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")
