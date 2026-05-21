from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from testflow_ai.core.artifacts import ensure_run_layout, write_manifest
from testflow_ai.core.models import RunStatus
from testflow_ai.core.paths import artifact_base, db_path
from testflow_ai.core.registry import Registry
from testflow_ai.toolkits import sessions


VALID_STEP_STATUSES = {"pending", "in_progress", "completed", "blocked", "skipped"}
ROUTE_ALIASES = {
    "api": "api",
    "api_test": "api",
    "functional": "api",
    "ui": "ui",
    "web": "ui",
    "browser": "ui",
    "all": "all",
}

WORKFLOW_STEPS: tuple[dict[str, str | None], ...] = (
    {
        "step_id": "requirement_analysis",
        "name": "Requirement analysis",
        "tool": "analyze_requirement",
        "artifact": "01_requirement_analysis.json",
        "route": None,
        "description": "Capture scope, acceptance criteria, risks, and open questions.",
    },
    {
        "step_id": "test_point_analysis",
        "name": "Test point analysis",
        "tool": "analyze_test_points",
        "artifact": "02_test_points.json",
        "route": None,
        "description": "Break requirements into testable points and coverage dimensions.",
    },
    {
        "step_id": "test_plan_design",
        "name": "Test plan design",
        "tool": "design_test_plan",
        "artifact": "02_test_plan.json",
        "route": None,
        "description": "Define strategy, environments, priority, exit criteria, and execution routes.",
    },
    {
        "step_id": "case_design",
        "name": "Case design",
        "tool": "write_test_cases",
        "artifact": "03_test_cases.json",
        "route": None,
        "description": "Create or import test cases and validate coverage.",
    },
    {
        "step_id": "case_registry",
        "name": "Case registry",
        "tool": "init_case_registry",
        "artifact": "case_registry.json",
        "route": None,
        "description": "Initialize case execution tracking.",
    },
    {
        "step_id": "api_suite_preparation",
        "name": "API suite preparation",
        "tool": "api_suite",
        "artifact": "api_suite.json",
        "route": "api",
        "description": "Prepare an API suite from cases or service contracts.",
    },
    {
        "step_id": "api_suite_execution",
        "name": "API suite execution",
        "tool": "api_suite",
        "artifact": "api_suite_report.json",
        "route": "api",
        "description": "Execute API checks and collect run artifacts.",
    },
    {
        "step_id": "ui_suite_preparation",
        "name": "UI suite preparation",
        "tool": "ui_suite",
        "artifact": "ui_suite.json",
        "route": "ui",
        "description": "Prepare browser UI flow definitions.",
    },
    {
        "step_id": "ui_suite_execution",
        "name": "UI suite execution",
        "tool": "ui_suite",
        "artifact": "ui_suite_report.json",
        "route": "ui",
        "description": "Compile or execute browser UI checks and collect artifacts.",
    },
    {
        "step_id": "report_generation",
        "name": "Report generation",
        "tool": "build_session_report",
        "artifact": "test_report.md",
        "route": None,
        "description": "Generate a consolidated Markdown report.",
    },
    {
        "step_id": "release_review",
        "name": "Release review",
        "tool": "release_checklist",
        "artifact": "release_review.json",
        "route": None,
        "description": "Review release gates, known risks, and follow-up actions.",
    },
)


def start_workflow(project_name: str = "default", routes: str = "api,ui") -> dict[str, Any]:
    """Create a toolkit session and initialize a workflow."""
    created = sessions.create_session(project_name)
    session_id = created["session_id"]
    initialized = init_workflow(session_id, routes=routes)
    return {"success": True, "session": created, "workflow": initialized["workflow"]}


def init_workflow(session_id: str, routes: str = "api,ui") -> dict[str, Any]:
    """Initialize workflow.json for an existing session."""
    selected_routes = _parse_routes(routes)
    root = sessions.session_dir(session_id)
    root.mkdir(parents=True, exist_ok=True)
    workflow = {
        "session_id": session_id,
        "status": "running",
        "routes": sorted(selected_routes),
        "created_at": _now(),
        "updated_at": _now(),
        "steps": [_build_step(step, selected_routes) for step in WORKFLOW_STEPS if _include_step(step, selected_routes)],
        "history": [],
    }
    _write_workflow(root, workflow)
    return {"success": True, "session_id": session_id, "path": str(_workflow_path(root)), "workflow": workflow}


def get_workflow_status(session_id: str) -> dict[str, Any]:
    """Return current workflow progress."""
    workflow = _load_workflow(session_id)
    if "error" in workflow:
        return workflow
    counts = Counter(step.get("status", "pending") for step in workflow.get("steps", []))
    total = len(workflow.get("steps", []))
    completed = counts.get("completed", 0) + counts.get("skipped", 0)
    current = _current_step(workflow)
    return {
        "success": True,
        "session_id": session_id,
        "status": workflow.get("status", "unknown"),
        "routes": workflow.get("routes", []),
        "total_steps": total,
        "completed_steps": completed,
        "counts": {status: counts.get(status, 0) for status in sorted(VALID_STEP_STATUSES)},
        "progress": round(completed / total, 3) if total else 0.0,
        "current_step": current,
    }


def get_next_step(session_id: str) -> dict[str, Any]:
    """Mark and return the next executable workflow step."""
    root = sessions.session_dir(session_id)
    workflow = _load_workflow(session_id)
    if "error" in workflow:
        return workflow

    in_progress = next((step for step in workflow["steps"] if step.get("status") == "in_progress"), None)
    if in_progress:
        return {"success": True, "session_id": session_id, "step": in_progress, "already_started": True}

    pending = next((step for step in workflow["steps"] if step.get("status") == "pending"), None)
    if pending is None:
        workflow["status"] = "completed"
        workflow["updated_at"] = _now()
        _write_workflow(root, workflow)
        return {"success": True, "session_id": session_id, "done": True, "workflow_status": "completed"}

    pending["status"] = "in_progress"
    pending["started_at"] = _now()
    workflow["updated_at"] = _now()
    workflow["history"].append({"event": "step_started", "step_id": pending["step_id"], "at": _now()})
    _write_workflow(root, workflow)
    return {"success": True, "session_id": session_id, "step": pending, "already_started": False}


def complete_step(
    session_id: str,
    step_id: str,
    summary: str = "",
    artifact: str = "",
    status: str = "completed",
) -> dict[str, Any]:
    """Complete, skip, or block a workflow step."""
    if status not in {"completed", "skipped", "blocked"}:
        return {"success": False, "error": f"invalid completion status: {status}"}

    root = sessions.session_dir(session_id)
    workflow = _load_workflow(session_id)
    if "error" in workflow:
        return workflow
    step = _find_step(workflow, step_id)
    if step is None:
        return {"success": False, "error": "step not found", "step_id": step_id}

    step["status"] = status
    step["completed_at"] = _now() if status in {"completed", "skipped"} else None
    step["blocked_at"] = _now() if status == "blocked" else None
    step["summary"] = summary
    if artifact:
        step["artifact"] = artifact
    workflow["updated_at"] = _now()
    workflow["history"].append({"event": f"step_{status}", "step_id": step_id, "summary": summary, "at": _now()})
    _refresh_workflow_status(workflow)
    _write_workflow(root, workflow)
    return {"success": True, "session_id": session_id, "step": step, "workflow_status": workflow["status"]}


def block_step(session_id: str, step_id: str, reason: str) -> dict[str, Any]:
    """Mark a workflow step as blocked."""
    return complete_step(session_id, step_id, summary=reason, status="blocked")


def create_linked_run(
    session_id: str,
    step_id: str,
    executor_type: str,
    dataset_version_id: str = "",
    config_json: str = "",
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a TestFlow run and link it to a workflow step."""
    workflow = _load_workflow(session_id)
    if "error" in workflow:
        return workflow
    if _find_step(workflow, step_id) is None:
        return {"success": False, "error": "step not found", "step_id": step_id}

    executor_config = _load_config(config_json, config)
    workflow_ref = {"session_id": session_id, "step_id": step_id}
    reg = Registry(db_path())
    rec = reg.create_run(
        executor_type=executor_type,
        dataset_version_id=dataset_version_id or None,
        artifact_root="",
        manifest={
            "executor_type": executor_type,
            "dataset_version_id": dataset_version_id or None,
            "executor_config": executor_config,
            "workflow": workflow_ref,
        },
    )
    root = ensure_run_layout(artifact_base(), rec.id)
    reg.update_artifact_root(rec.id, str(root))
    manifest = {
        **rec.manifest,
        "run_id": rec.id,
        "artifact_uri": str(root),
        "workflow": workflow_ref,
    }
    reg.update_manifest(rec.id, manifest)
    write_manifest(
        root,
        {
            "run_id": rec.id,
            "executor_type": executor_type,
            "dataset_version_id": dataset_version_id or None,
            "executor_config": _safe_manifest_config(executor_config),
            "workflow": workflow_ref,
            "trace_backend": None,
        },
    )
    linked = link_run(
        session_id=session_id,
        step_id=step_id,
        run_id=rec.id,
        executor_type=executor_type,
        artifact_root=str(root),
        status=rec.status.value,
        summary="created linked run",
    )
    return {
        "success": linked.get("success", False),
        "session_id": session_id,
        "step_id": step_id,
        "run_id": rec.id,
        "artifact_root": str(root),
        "workflow_status": linked.get("workflow_status"),
    }


def link_run(
    session_id: str,
    step_id: str,
    run_id: str,
    executor_type: str = "",
    artifact_root: str = "",
    status: str = "",
    summary: str | dict[str, Any] = "",
) -> dict[str, Any]:
    """Link an existing TestFlow run to a workflow step."""
    root = sessions.session_dir(session_id)
    workflow = _load_workflow(session_id)
    if "error" in workflow:
        return workflow
    step = _find_step(workflow, step_id)
    if step is None:
        return {"success": False, "error": "step not found", "step_id": step_id}

    run_link = {
        "run_id": run_id,
        "executor_type": executor_type,
        "artifact_root": artifact_root,
        "status": status,
        "summary": summary,
        "linked_at": _now(),
    }
    _upsert_item(step.setdefault("runs", []), "run_id", run_link)
    if step.get("status") == "pending":
        step["status"] = "in_progress"
        step["started_at"] = step.get("started_at") or _now()
    workflow["updated_at"] = _now()
    workflow["history"].append({"event": "run_linked", "step_id": step_id, "run_id": run_id, "at": _now()})
    _refresh_workflow_status(workflow)
    _write_workflow(root, workflow)
    return {"success": True, "session_id": session_id, "step": step, "workflow_status": workflow["status"]}


def sync_run_status(
    session_id: str,
    step_id: str,
    run_id: str,
    complete_on_terminal: bool = True,
) -> dict[str, Any]:
    """Sync a linked run status from the ledger back to a workflow step."""
    rec = Registry(db_path()).get_run(run_id)
    if rec is None:
        return {"success": False, "error": "run not found", "run_id": run_id}

    summary_payload = _read_json(Path(rec.artifact_root) / "summary.json")
    summary_text = _run_summary_text(rec.status, summary_payload)
    linked = link_run(
        session_id=session_id,
        step_id=step_id,
        run_id=run_id,
        executor_type=rec.executor_type,
        artifact_root=rec.artifact_root,
        status=rec.status.value,
        summary=summary_payload or summary_text,
    )
    if not linked.get("success"):
        return linked

    if complete_on_terminal and rec.status == RunStatus.succeeded:
        return complete_step(session_id, step_id, summary=summary_text, status="completed")
    if complete_on_terminal and rec.status == RunStatus.failed:
        return complete_step(session_id, step_id, summary=summary_text, status="blocked")
    return {"success": True, "session_id": session_id, "step": linked["step"], "workflow_status": linked["workflow_status"]}


def record_step_artifact(
    session_id: str,
    step_id: str,
    name: str,
    path: str,
    kind: str = "artifact",
    summary: str = "",
) -> dict[str, Any]:
    """Record an artifact produced by a workflow step."""
    root = sessions.session_dir(session_id)
    workflow = _load_workflow(session_id)
    if "error" in workflow:
        return workflow
    step = _find_step(workflow, step_id)
    if step is None:
        return {"success": False, "error": "step not found", "step_id": step_id}

    artifact = {"name": name, "path": path, "kind": kind, "summary": summary, "recorded_at": _now()}
    _upsert_item(step.setdefault("artifacts", []), "name", artifact)
    workflow["updated_at"] = _now()
    workflow["history"].append({"event": "artifact_recorded", "step_id": step_id, "name": name, "at": _now()})
    _write_workflow(root, workflow)
    return {"success": True, "session_id": session_id, "step": step}


def _build_step(step: dict[str, str | None], routes: set[str]) -> dict[str, Any]:
    route = step.get("route")
    return {
        **step,
        "enabled": route is None or "all" in routes or route in routes,
        "status": "pending",
        "started_at": None,
        "completed_at": None,
        "blocked_at": None,
        "summary": "",
    }


def _include_step(step: dict[str, str | None], routes: set[str]) -> bool:
    route = step.get("route")
    return route is None or "all" in routes or route in routes


def _parse_routes(routes: str) -> set[str]:
    selected: set[str] = set()
    for raw in routes.split(","):
        key = raw.strip().lower()
        if not key:
            continue
        selected.add(ROUTE_ALIASES.get(key, key))
    return selected or {"api", "ui"}


def _load_workflow(session_id: str) -> dict[str, Any]:
    path = _workflow_path(sessions.session_dir(session_id))
    if not path.exists():
        return {"success": False, "error": "workflow not found", "path": str(path)}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"success": False, "error": "workflow file is not valid JSON", "path": str(path)}


def _load_config(config_json: str, config: dict[str, Any] | None) -> dict[str, Any]:
    if config is not None:
        return dict(config)
    if not config_json:
        return {}
    loaded = json.loads(config_json)
    if not isinstance(loaded, dict):
        raise ValueError("config_json must be a JSON object")
    return loaded


def _safe_manifest_config(config: dict[str, Any]) -> dict[str, Any]:
    blocked = {"api_key", "token", "password", "secret"}
    return {
        key: ("***" if any(part in key.lower() for part in blocked) else value)
        for key, value in config.items()
    }


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _run_summary_text(status: RunStatus, summary: dict[str, Any]) -> str:
    passed = summary.get("passed")
    failed = summary.get("failed")
    if passed is not None or failed is not None:
        return f"run {status.value}: passed={passed or 0}, failed={failed or 0}"
    return f"run {status.value}"


def _upsert_item(items: list[dict[str, Any]], key: str, new_item: dict[str, Any]) -> None:
    for index, item in enumerate(items):
        if item.get(key) == new_item.get(key):
            items[index] = {**item, **new_item}
            return
    items.append(new_item)


def _write_workflow(root: Path, workflow: dict[str, Any]) -> None:
    _workflow_path(root).write_text(json.dumps(workflow, indent=2, ensure_ascii=False), encoding="utf-8")


def _workflow_path(root: Path) -> Path:
    return root / "workflow.json"


def _find_step(workflow: dict[str, Any], step_id: str) -> dict[str, Any] | None:
    return next((step for step in workflow.get("steps", []) if step.get("step_id") == step_id), None)


def _current_step(workflow: dict[str, Any]) -> dict[str, Any] | None:
    return next((step for step in workflow.get("steps", []) if step.get("status") == "in_progress"), None) or next(
        (step for step in workflow.get("steps", []) if step.get("status") == "pending"),
        None,
    )


def _refresh_workflow_status(workflow: dict[str, Any]) -> None:
    statuses = {step.get("status") for step in workflow.get("steps", [])}
    if "blocked" in statuses:
        workflow["status"] = "blocked"
    elif "in_progress" in statuses or "pending" in statuses:
        workflow["status"] = "running"
    else:
        workflow["status"] = "completed"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
