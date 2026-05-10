from __future__ import annotations

import json
from pathlib import Path

import pytest

from testflow_ai.reports.builder import build_run_report, build_session_report
from testflow_ai.toolkits import cases, sessions
from testflow_ai.toolkits.catalog import get_tool, list_tools


@pytest.fixture()
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("TESTFLOW_HOME", str(tmp_path))
    return tmp_path


def test_build_run_report_from_artifacts(tmp_path: Path) -> None:
    root = tmp_path / "run"
    (root / "logs").mkdir(parents=True)
    root.joinpath("manifest.json").write_text(
        json.dumps({"run_id": "run-1", "executor_type": "api_suite", "dataset_version_id": "dv1"}),
        encoding="utf-8",
    )
    root.joinpath("summary.json").write_text(
        json.dumps(
            {
                "run_id": "run-1",
                "executor_type": "api_suite",
                "status": "failed",
                "num_predictions": 2,
                "passed": 1,
                "failed": 1,
                "metrics": {"pass_rate": 0.5},
            }
        ),
        encoding="utf-8",
    )
    root.joinpath("predictions.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"sample_id": "case-1", "output": {"status": "passed"}, "error": None}),
                json.dumps({"sample_id": "case-2", "output": {"status": "failed"}, "error": "assertion failed"}),
            ]
        ),
        encoding="utf-8",
    )
    root.joinpath("logs/executor.log").write_text("details", encoding="utf-8")

    result = build_run_report(root)

    assert result["success"] is True
    assert result["summary"]["run_id"] == "run-1"
    assert result["summary"]["failed"] == 1
    report = root.joinpath("report.md").read_text(encoding="utf-8")
    assert "TestFlow Run Report" in report
    assert "case-2" in report
    assert "logs/executor.log" in report


def test_build_session_report_from_case_registry(isolated_home: Path) -> None:
    created = sessions.create_session("report-demo")
    sid = created["session_id"]
    root = Path(created["path"])
    case_set = {
        "test_case_set": {
            "test_cases": [
                _case("legacy-1", "Happy path"),
                _case("legacy-2", "Failure path"),
            ],
            "traceability_matrix": [{"ref_id": "REQ-1", "case_ids": ["legacy-1", "legacy-2"]}],
        }
    }
    root.joinpath("03_test_cases.json").write_text(json.dumps(case_set), encoding="utf-8")
    cases.init_case_registry(sid)
    cases.update_case_status(sid, "legacy-1", "passed", executor="api_suite")
    cases.update_case_status(sid, "legacy-2", "failed", executor="api_suite", fail_reason="response mismatch")

    result = build_session_report(root)

    assert result["success"] is True
    assert result["summary"]["session_id"] == sid
    assert result["summary"]["failed"] == 1
    report = root.joinpath("test_report.md").read_text(encoding="utf-8")
    assert "TestFlow Session Report" in report
    assert "response mismatch" in report


def test_tool_catalog_contains_reporting_tools(isolated_home: Path) -> None:
    names = {tool["name"] for tool in list_tools(domain="reporting")}
    assert "build_session_report" in names
    assert get_tool("build_run_artifact_report") is not None


def _case(case_id: str, title: str) -> dict:
    return {
        "case_id": case_id,
        "title": title,
        "test_point_id": "TP-1",
        "strategy": "business",
        "design_technique": "scenario",
        "tag": "positive",
        "requirement_type": "functional",
        "priority": "P1",
        "test_steps": [{"step": "do it", "expected": "works"}],
    }
