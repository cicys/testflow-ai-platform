from __future__ import annotations

import json
from pathlib import Path

import pytest

from testflow_ai.toolkits import cases, sessions
from testflow_ai.toolkits.catalog import get_tool, list_tools


@pytest.fixture()
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("TESTFLOW_HOME", str(tmp_path))
    return tmp_path


def test_tool_catalog_contains_case_tools(isolated_home: Path) -> None:
    names = {tool["name"] for tool in list_tools()}
    assert "merge_case_batches" in names
    assert "validate_case_coverage" in names
    assert get_tool("init_case_registry") is not None


def test_merge_validate_and_track_cases(isolated_home: Path) -> None:
    session = sessions.create_session("toolkit smoke")
    sid = session["session_id"]
    root = Path(session["path"])

    batch_1 = {
        "test_case_set": {
            "test_cases": [
                _case("old-1", "Login happy path", "positive"),
                _case("old-2", "Login invalid password", "abnormal"),
            ],
            "traceability_matrix": [{"ref_id": "REQ-1", "case_ids": ["old-1", "old-2"]}],
        }
    }
    batch_2 = {
        "test_case_set": {
            "test_cases": [
                _case("old-3", "Login locked user boundary", "boundary"),
            ],
            "traceability_matrix": [{"ref_id": "REQ-2", "case_ids": ["old-3"]}],
        }
    }
    root.joinpath("03_test_cases_batch_1.json").write_text(json.dumps(batch_1), encoding="utf-8")
    root.joinpath("03_test_cases_batch_2.json").write_text(json.dumps(batch_2), encoding="utf-8")

    merged = cases.merge_case_batches(sid)
    assert merged["success"] is True
    assert merged["final_cases"] == 3

    validation = cases.validate_case_coverage(sid)
    assert validation["success"] is True

    registry = cases.init_case_registry(sid)
    assert registry["success"] is True
    assert registry["total"] == 3
    assert registry["execution_rate"] == 0.0

    updated = cases.update_case_status(sid, "TC-BIZ-001", "passed", executor="oversee")
    assert updated["success"] is True
    assert updated["executed"] == 1
    assert updated["pass_rate"] == 1.0


def _case(case_id: str, title: str, tag: str) -> dict:
    return {
        "case_id": case_id,
        "title": title,
        "test_point_id": "TP-1",
        "strategy": "business",
        "design_technique": "scenario",
        "tag": tag,
        "requirement_type": "functional",
        "priority": "P1",
        "test_steps": [{"step": "do it", "expected": "works"}],
    }
