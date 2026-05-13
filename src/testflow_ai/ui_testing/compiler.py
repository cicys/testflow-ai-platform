from __future__ import annotations

import json
import re
import urllib.parse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from testflow_ai.ui_testing.models import UIAction, UICase, UIStep, UISuite

_VARIABLE_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_.-]*)\s*\}\}")


def load_suite(path: Path) -> UISuite:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return UISuite.model_validate(payload)


def summarize_suite(suite: UISuite) -> dict[str, Any]:
    actions = Counter(step.action.value for case in suite.cases for step in case.steps)
    return {
        "suite_id": suite.suite_id,
        "name": suite.name,
        "base_url": suite.base_url,
        "browser": suite.browser.value,
        "cases": len(suite.cases),
        "steps": sum(len(case.steps) for case in suite.cases),
        "actions": dict(sorted(actions.items())),
    }


def plan_suite(suite: UISuite) -> dict[str, Any]:
    """Create a deterministic plan report without launching a browser."""
    planned_cases: list[dict[str, Any]] = []
    for case in suite.cases:
        variables = {**suite.variables, **case.variables}
        planned_steps = [_planned_step(suite, case, step, variables) for step in case.steps]
        planned_cases.append(
            {
                "case_id": case.case_id,
                "name": case.name,
                "tags": case.tags,
                "status": "planned",
                "steps": planned_steps,
                "total_steps": len(planned_steps),
            }
        )

    total_steps = sum(case["total_steps"] for case in planned_cases)
    return {
        "suite_id": suite.suite_id,
        "suite_name": suite.name,
        "status": "planned",
        "mode": "plan",
        "browser": suite.browser.value,
        "total_cases": len(planned_cases),
        "planned_cases": len(planned_cases),
        "total_steps": total_steps,
        "planned_steps": total_steps,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metrics": {
            "planned_case_rate": 1.0 if planned_cases else 0.0,
            "planned_step_rate": 1.0 if total_steps else 0.0,
        },
        "cases": planned_cases,
    }


def compile_playwright_spec(suite: UISuite) -> str:
    """Compile a UI suite into a Playwright test specification."""
    lines = [
        "import { test, expect } from '@playwright/test';",
        "",
        f"test.describe({_js(suite.name)}, () => {{",
        f"  test.use({{ browserName: {_js(suite.browser.value)} }});",
        "",
    ]
    for case in suite.cases:
        lines.extend(_compile_case(suite, case))
        lines.append("")
    lines.append("});")
    lines.append("")
    return "\n".join(lines)


def _compile_case(suite: UISuite, case: UICase) -> list[str]:
    variables = {**suite.variables, **case.variables}
    width = int(suite.viewport.get("width", 1280))
    height = int(suite.viewport.get("height", 720))
    lines = [
        f"  test({_js(f'{case.case_id} {case.name}')}, async ({{ page }}) => {{",
        f"    await page.setViewportSize({{ width: {width}, height: {height} }});",
    ]
    if case.start_url:
        lines.append(f"    await page.goto({_js(_absolute_url(suite.base_url, _render_str(case.start_url, variables)))}, {{ waitUntil: 'networkidle', timeout: {suite.timeout_ms} }});")
    for step in case.steps:
        lines.append(f"    // {step.step_id}: {_safe_comment(step.name)}")
        lines.extend(f"    {line}" for line in _compile_step(suite, case, step, variables))
    lines.append("  });")
    return lines


def _compile_step(suite: UISuite, case: UICase, step: UIStep, variables: dict[str, Any]) -> list[str]:
    action = step.action
    timeout = step.timeout_ms or suite.timeout_ms
    target = _render_optional_str(step.target, variables)
    value = _render_value(step.value, variables)
    url_value = _render_optional_str(step.url, variables)

    if action == UIAction.GOTO:
        url = _absolute_url(suite.base_url, url_value or str(value or target or ""))
        return [f"await page.goto({_js(url)}, {{ waitUntil: 'networkidle', timeout: {timeout} }});"]
    if action == UIAction.CLICK:
        return [f"await page.locator({_js(_required(target, step, 'target'))}).click({{ timeout: {timeout} }});"]
    if action == UIAction.FILL:
        return [f"await page.locator({_js(_required(target, step, 'target'))}).fill({_js(str(value or ''))}, {{ timeout: {timeout} }});"]
    if action == UIAction.SELECT:
        return [f"await page.locator({_js(_required(target, step, 'target'))}).selectOption({_js(value)}, {{ timeout: {timeout} }});"]
    if action == UIAction.CHECK:
        return [f"await page.locator({_js(_required(target, step, 'target'))}).check({{ timeout: {timeout} }});"]
    if action == UIAction.UNCHECK:
        return [f"await page.locator({_js(_required(target, step, 'target'))}).uncheck({{ timeout: {timeout} }});"]
    if action == UIAction.PRESS:
        return [f"await page.locator({_js(_required(target, step, 'target'))}).press({_js(str(value or 'Enter'))}, {{ timeout: {timeout} }});"]
    if action == UIAction.HOVER:
        return [f"await page.locator({_js(_required(target, step, 'target'))}).hover({{ timeout: {timeout} }});"]
    if action == UIAction.WAIT_FOR_SELECTOR:
        return [f"await page.locator({_js(_required(target, step, 'target'))}).waitFor({{ state: 'visible', timeout: {timeout} }});"]
    if action in {UIAction.WAIT_FOR_URL, UIAction.ASSERT_URL}:
        expected = _absolute_url(suite.base_url, url_value or str(value or target or ""))
        return [f"await expect(page).toHaveURL({_js(expected)}, {{ timeout: {timeout} }});"]
    if action == UIAction.ASSERT_TEXT:
        return [f"await expect(page.locator({_js(_required(target, step, 'target'))})).toContainText({_js(str(value or ''))}, {{ timeout: {timeout} }});"]
    if action == UIAction.ASSERT_VISIBLE:
        return [f"await expect(page.locator({_js(_required(target, step, 'target'))})).toBeVisible({{ timeout: {timeout} }});"]
    if action == UIAction.ASSERT_HIDDEN:
        return [f"await expect(page.locator({_js(_required(target, step, 'target'))})).toBeHidden({{ timeout: {timeout} }});"]
    if action == UIAction.SCREENSHOT:
        path = _screenshot_path(case.case_id, step.step_id, value)
        return [f"await page.screenshot({{ path: {_js(path)}, fullPage: true }});"]
    raise ValueError(f"unsupported UI action: {action.value}")


def _planned_step(suite: UISuite, case: UICase, step: UIStep, variables: dict[str, Any]) -> dict[str, Any]:
    rendered_target = _render_optional_str(step.target, variables)
    rendered_value = _render_value(step.value, variables)
    rendered_url = _render_optional_str(step.url, variables)
    if step.action in {UIAction.GOTO, UIAction.WAIT_FOR_URL, UIAction.ASSERT_URL}:
        rendered_url = _absolute_url(suite.base_url, rendered_url or str(rendered_value or rendered_target or ""))
    return {
        "step_id": step.step_id,
        "name": step.name,
        "action": step.action.value,
        "target": rendered_target,
        "value": rendered_value,
        "url": rendered_url,
        "timeout_ms": step.timeout_ms or suite.timeout_ms,
    }


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


def _render_optional_str(value: str | None, variables: dict[str, Any]) -> str | None:
    if value is None:
        return None
    return str(_render_value(value, variables))


def _render_str(value: str, variables: dict[str, Any]) -> str:
    return str(_render_value(value, variables))


def _absolute_url(base_url: str, value: str) -> str:
    if value.startswith(("http://", "https://")):
        return value
    if not base_url:
        return value
    return urllib.parse.urljoin(f"{base_url.rstrip('/')}/", value.lstrip("/"))


def _required(value: str | None, step: UIStep, field_name: str) -> str:
    if value:
        return value
    raise ValueError(f"ui step {step.step_id} requires {field_name}")


def _screenshot_path(case_id: str, step_id: str, value: Any) -> str:
    if value:
        return str(value)
    safe_case = re.sub(r"[^A-Za-z0-9_.-]+", "_", case_id).strip("._-") or "case"
    safe_step = re.sub(r"[^A-Za-z0-9_.-]+", "_", step_id).strip("._-") or "step"
    return f"test-results/screenshots/{safe_case}_{safe_step}.png"


def _safe_comment(value: str) -> str:
    return value.replace("\n", " ").replace("\r", " ")[:120]


def _js(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)
