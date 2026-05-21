from __future__ import annotations

from pathlib import Path

import pytest

from testflow_ai.core.models import RunStatus
from testflow_ai.core.paths import db_path
from testflow_ai.core.registry import Registry
from testflow_ai.executors.mock import MockExecutor
from testflow_ai.toolkits import sessions, workflows
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


def test_workflow_can_create_and_sync_linked_run(isolated_home: Path) -> None:
    started = workflows.start_workflow("linked-run-demo", routes="api")
    session_id = started["session"]["session_id"]

    created = workflows.create_linked_run(
        session_id=session_id,
        step_id="api_suite_execution",
        executor_type="mock",
        dataset_version_id="smoke-v1",
        config={"api_key": "secret", "mode": "smoke"},
    )

    assert created["success"] is True
    run_id = created["run_id"]
    artifact_root = Path(created["artifact_root"])
    assert artifact_root.exists()

    rec = Registry(db_path()).get_run(run_id)
    assert rec is not None
    assert rec.executor_type == "mock"
    assert rec.dataset_version_id == "smoke-v1"
    assert rec.manifest["workflow"] == {
        "session_id": session_id,
        "step_id": "api_suite_execution",
    }

    manifest = sessions.read_artifact(session_id, "workflow.json")["content"]
    step = _step_by_id(manifest, "api_suite_execution")
    assert step["status"] == "in_progress"
    assert step["runs"][0]["run_id"] == run_id
    assert step["runs"][0]["status"] == "pending"

    MockExecutor().execute(run_id, artifact_root, {})
    Registry(db_path()).update_run_status(run_id, RunStatus.succeeded, finished=True)

    synced = workflows.sync_run_status(session_id, "api_suite_execution", run_id)
    assert synced["success"] is True
    assert synced["step"]["status"] == "completed"
    assert synced["step"]["runs"][0]["status"] == "succeeded"
    assert synced["step"]["summary"] == "run succeeded"


def test_workflow_can_record_step_artifact(isolated_home: Path) -> None:
    started = workflows.start_workflow("artifact-demo", routes="ui")
    session_id = started["session"]["session_id"]

    recorded = workflows.record_step_artifact(
        session_id=session_id,
        step_id="ui_suite_preparation",
        name="ui-suite",
        path="ui_suite.json",
        kind="suite",
        summary="compiled UI suite definition",
    )

    assert recorded["success"] is True
    artifact = recorded["step"]["artifacts"][0]
    assert artifact["name"] == "ui-suite"
    assert artifact["path"] == "ui_suite.json"
    assert artifact["kind"] == "suite"


def test_tool_catalog_contains_workflow_tools(isolated_home: Path) -> None:
    names = {tool["name"] for tool in list_tools(domain="workflow")}
    assert "start_workflow" in names
    assert "get_next_step" in names
    assert "create_linked_run" in names
    assert "sync_run_status" in names
    assert get_tool("complete_step") is not None
    assert get_tool("record_step_artifact") is not None


def _step_by_id(workflow: dict, step_id: str) -> dict:
    return next(step for step in workflow["steps"] if step["step_id"] == step_id)
