from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from testflow_ai.api_testing.models import APISuite
from testflow_ai.api_testing.runner import run_suite
from testflow_ai.executors.api_suite import APISuiteExecutor


def test_api_suite_runner_supports_assertions_and_extraction(monkeypatch: Any) -> None:
    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)

    report = run_suite(APISuite.model_validate(_suite_payload()))

    assert report["status"] == "passed"
    assert report["total_cases"] == 1
    assert report["passed_steps"] == 2
    second_step = report["cases"][0]["steps"][1]
    assert second_step["request"]["headers"]["Authorization"] == "***"
    assert second_step["assertions"][1]["actual"] == "ready"


def test_api_suite_executor_writes_case_predictions(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)
    root = tmp_path / "run"
    (root / "logs").mkdir(parents=True)

    result = APISuiteExecutor().execute(
        "api-run",
        root,
        {"executor_type": "api_suite", "suite_json": _suite_payload()},
    )

    assert result.exit_code == 0
    assert result.summary["executor_type"] == "api_suite"
    assert result.summary["metrics"]["pass_rate"] == 1.0
    assert root.joinpath("summary.json").exists()
    assert root.joinpath("logs/api_suite.report.json").exists()
    prediction = json.loads(root.joinpath("predictions.jsonl").read_text(encoding="utf-8"))
    assert prediction["sample_id"] == "case-api-001"
    assert prediction["output"]["status"] == "passed"


def _suite_payload() -> dict[str, Any]:
    return {
        "suite_id": "api-smoke",
        "name": "API smoke suite",
        "base_url": "http://api.local",
        "headers": {"User-Agent": "TestFlow"},
        "variables": {"project_id": "p1"},
        "cases": [
            {
                "case_id": "case-api-001",
                "name": "login and read project",
                "steps": [
                    {
                        "step_id": "login",
                        "name": "create token",
                        "method": "POST",
                        "endpoint": "/login",
                        "body": {"user": "tester"},
                        "assertions": [
                            {"kind": "status_code", "expected": 200},
                            {"kind": "json_path", "path": "$.token", "operator": "exists"},
                        ],
                        "extract": {"auth_token": "$.token"},
                    },
                    {
                        "step_id": "read-project",
                        "name": "read project",
                        "method": "GET",
                        "endpoint": "/projects/{{project_id}}",
                        "headers": {"Authorization": "Bearer {{auth_token}}"},
                        "query_params": {"verbose": "true"},
                        "assertions": [
                            {"kind": "status_code", "expected": 200},
                            {"kind": "json_path", "path": "$.project.status", "expected": "ready"},
                            {
                                "kind": "body_contains",
                                "operator": "contains",
                                "expected": "project",
                            },
                        ],
                    },
                ],
            }
        ],
    }


class _FakeResponse:
    def __init__(self, status: int, body: dict[str, Any], headers: dict[str, str] | None = None) -> None:
        self.status = status
        self.body = json.dumps(body).encode("utf-8")
        self.headers = headers or {"Content-Type": "application/json"}

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def _fake_urlopen(request: Any, timeout: float = 0) -> _FakeResponse:
    if request.full_url == "http://api.local/login":
        payload = json.loads(request.data.decode("utf-8"))
        assert payload["user"] == "tester"
        return _FakeResponse(200, {"token": "token-123"})
    if request.full_url == "http://api.local/projects/p1?verbose=true":
        assert request.headers["Authorization"] == "Bearer token-123"
        return _FakeResponse(200, {"project": {"id": "p1", "status": "ready"}})
    return _FakeResponse(404, {"error": "not found"})
