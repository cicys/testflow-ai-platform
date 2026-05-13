from __future__ import annotations

from pathlib import Path

import pytest

from testflow_ai.toolkits import workflows
from testflow_ai.toolkits.catalog import get_tool, list_tools


@pytest.fixture()
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("TESTFLOW_HOME", str(tmp_path))
    return tmp_path


def test_workflow_can_start_advance_and_complete(isolated_home: Path) -> None:
    started = workflows.start_workflow("workflow-demo", routes="api")
    session_id = started["session"]["session_id"]

    status = workflows.get_workflow_status(session_id)
    assert status["success"] is True
    assert status["routes"] == ["api"]
    assert status["current_step"]["step_id"] == "requirement_analysis"

    first = workflows.get_next_step(session_id)
    assert first["step"]["status"] == "in_progress"
    assert first["step"]["step_id"] == "requirement_analysis"

    completed = workflows.complete_step(
        session_id,
        "requirement_analysis",
        summary="scope captured",
        artifact="01_requirement_analysis.json",
    )
    assert completed["success"] is True
    assert completed["step"]["status"] == "completed"

    next_step = workflows.get_next_step(session_id)
    assert next_step["step"]["step_id"] == "test_point_analysis"

    progress = workflows.get_workflow_status(session_id)
    assert progress["completed_steps"] == 1
    assert progress["counts"]["in_progress"] == 1


def test_workflow_routes_filter_ui_steps(isolated_home: Path) -> None:
    started = workflows.start_workflow("api-only", routes="api")
    steps = started["workflow"]["steps"]
    step_ids = {step["step_id"] for step in steps}

    assert "api_suite_execution" in step_ids
    assert "ui_suite_execution" not in step_ids


def test_tool_catalog_contains_workflow_tools(isolated_home: Path) -> None:
    names = {tool["name"] for tool in list_tools(domain="workflow")}
    assert "start_workflow" in names
    assert "get_next_step" in names
    assert get_tool("complete_step") is not None
