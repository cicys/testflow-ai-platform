from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer

from testflow_ai.api_testing.runner import load_suite, run_suite as run_api_suite
from testflow_ai.core.artifacts import ensure_run_layout, write_manifest
from testflow_ai.core.diff import diff_runs as diff_run_artifacts
from testflow_ai.core.models import DatasetVersion, MetricResult, RunStatus
from testflow_ai.core.paths import artifact_base, db_path, eval_home
from testflow_ai.core.registry import Registry
from testflow_ai.executors.agent_gateway import AgentGatewayExecutor
from testflow_ai.executors.api_suite import APISuiteExecutor
from testflow_ai.executors.mock import MockExecutor
from testflow_ai.executors.subprocess import SubprocessExecutor
from testflow_ai.executors.ui_suite import UISuiteExecutor
from testflow_ai.integrations.caseops import CaseOpsClient
from testflow_ai.reports.builder import build_run_report, build_session_report
from testflow_ai.tool_server import serve_jsonl
from testflow_ai.toolkits import cases, sessions, workflows
from testflow_ai.toolkits.catalog import list_tools
from testflow_ai.ui_testing.compiler import compile_playwright_spec, load_suite as load_ui_suite, plan_suite, summarize_suite

app = typer.Typer(no_args_is_help=True, help="TestFlow AI local test orchestration toolkit")
run_app = typer.Typer(no_args_is_help=True, help="Create, execute, and compare runs")
dataset_app = typer.Typer(no_args_is_help=True, help="Manage dataset versions")
api_app = typer.Typer(no_args_is_help=True, help="Validate and run API automation suites")
ui_app = typer.Typer(no_args_is_help=True, help="Validate and compile UI automation suites")
report_app = typer.Typer(no_args_is_help=True, help="Build Markdown reports from run and session artifacts")
server_app = typer.Typer(no_args_is_help=True, help="Run local tool server adapters")
toolkit_app = typer.Typer(no_args_is_help=True, help="Run built-in testing toolkit utilities")
session_app = typer.Typer(no_args_is_help=True, help="Manage toolkit sessions")
case_app = typer.Typer(no_args_is_help=True, help="Manage test case assets and execution progress")
caseops_app = typer.Typer(no_args_is_help=True, help="Build and submit CaseOps payloads")
workflow_app = typer.Typer(no_args_is_help=True, help="Manage testing workflow progress")
app.add_typer(run_app, name="run")
app.add_typer(dataset_app, name="dataset")
app.add_typer(api_app, name="api")
app.add_typer(ui_app, name="ui")
app.add_typer(report_app, name="report")
app.add_typer(server_app, name="server")
app.add_typer(toolkit_app, name="toolkit")
toolkit_app.add_typer(session_app, name="session")
toolkit_app.add_typer(case_app, name="case")
toolkit_app.add_typer(caseops_app, name="caseops")
toolkit_app.add_typer(workflow_app, name="workflow")


@app.command()
def init() -> None:
    """Initialize TESTFLOW_HOME and the local SQLite ledger."""
    home = eval_home()
    home.mkdir(parents=True, exist_ok=True)
    artifact_base().mkdir(parents=True, exist_ok=True)
    Registry(db_path())
    typer.echo(f"OK: testflow_home={home}")


@run_app.command()
def create(
    executor: str = typer.Option("mock", "--executor", "-e"),
    dataset_version: str | None = typer.Option(None, "--dataset-version", "-d"),
    config_json: str | None = typer.Option(None, "--config-json"),
    config_file: Path | None = typer.Option(None, "--config-file", readable=True),
) -> None:
    """Create a run and write its artifact layout."""
    executor_config = _load_config(config_json, config_file)
    reg = Registry(db_path())
    rec = reg.create_run(
        executor_type=executor,
        dataset_version_id=dataset_version,
        artifact_root="",
        manifest={
            "executor_type": executor,
            "dataset_version_id": dataset_version,
            "executor_config": executor_config,
        },
    )
    root = ensure_run_layout(artifact_base(), rec.id)
    reg.update_artifact_root(rec.id, str(root))
    manifest = {
        **rec.manifest,
        "run_id": rec.id,
        "artifact_uri": str(root),
    }
    reg.update_manifest(rec.id, manifest)
    write_manifest(
        root,
        {
            "run_id": rec.id,
            "executor_type": executor,
            "dataset_version_id": dataset_version,
            "executor_config": _safe_manifest_config(executor_config),
            "trace_backend": None,
        },
    )
    typer.echo(rec.id)


@run_app.command()
def execute(run_id: str = typer.Argument(...)) -> None:
    """Execute a run with the executor stored in its manifest."""
    reg = Registry(db_path())
    rec = reg.get_run(run_id)
    if rec is None:
        raise typer.BadParameter("unknown run_id")
    reg.update_run_status(run_id, RunStatus.running)
    try:
        result = _select_executor(rec.executor_type).execute(
            run_id,
            Path(rec.artifact_root),
            _executor_config(rec.manifest, rec.executor_type),
        )
    except Exception:
        reg.update_run_status(run_id, RunStatus.failed, finished=True)
        raise

    status = RunStatus.succeeded if result.exit_code == 0 else RunStatus.failed
    _persist_metrics(reg, run_id, result.summary)
    reg.update_run_status(run_id, status, finished=True)
    typer.echo(json.dumps(result.summary, indent=2, ensure_ascii=False))


@run_app.command()
def finalize(
    run_id: str = typer.Argument(...),
    status: str = typer.Option("succeeded", "--status"),
) -> None:
    """Manually finalize a run."""
    reg = Registry(db_path())
    st = RunStatus(status)
    reg.update_run_status(run_id, st, finished=st in (RunStatus.succeeded, RunStatus.failed, RunStatus.cancelled))
    typer.echo("OK")


@run_app.command()
def diff(
    run_a: str = typer.Argument(...),
    run_b: str = typer.Argument(...),
    sample_key: str = typer.Option("sample_id", "--sample-key"),
) -> None:
    """Compare run summaries and sample-level predictions."""
    reg = Registry(db_path())
    ra = reg.get_run(run_a)
    rb = reg.get_run(run_b)
    if ra is None or rb is None:
        raise typer.BadParameter("run not found")
    out = diff_run_artifacts(Path(ra.artifact_root), Path(rb.artifact_root), sample_key=sample_key)
    typer.echo(json.dumps(out, indent=2, ensure_ascii=False))


@dataset_app.command("register-version")
def register_dataset_version(
    version_id: str = typer.Argument(...),
    label: str = typer.Option("", "--label"),
) -> None:
    """Register a lightweight dataset version reference."""
    Registry(db_path()).upsert_dataset_version(DatasetVersion(id=version_id, label=label))
    typer.echo("OK")


@api_app.command("validate-suite")
def api_validate_suite(suite_file: Path = typer.Argument(..., readable=True)) -> None:
    """Validate and summarize an API suite JSON file."""
    suite = load_suite(suite_file)
    typer.echo(
        json.dumps(
            {
                "suite_id": suite.suite_id,
                "name": suite.name,
                "base_url": suite.base_url,
                "cases": len(suite.cases),
                "steps": sum(len(case.steps) for case in suite.cases),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


@api_app.command("run-suite")
def api_run_suite(
    suite_file: Path = typer.Argument(..., readable=True),
    timeout_seconds: float | None = typer.Option(None, "--timeout-seconds"),
) -> None:
    """Run an API suite JSON file without creating a ledger run."""
    suite = load_suite(suite_file)
    report = run_api_suite(suite, timeout_seconds=timeout_seconds)
    typer.echo(json.dumps(report, indent=2, ensure_ascii=False))


@ui_app.command("validate-suite")
def ui_validate_suite(suite_file: Path = typer.Argument(..., readable=True)) -> None:
    """Validate and summarize a UI suite JSON file."""
    suite = load_ui_suite(suite_file)
    typer.echo(json.dumps(summarize_suite(suite), indent=2, ensure_ascii=False))


@ui_app.command("plan-suite")
def ui_plan_suite(suite_file: Path = typer.Argument(..., readable=True)) -> None:
    """Render a UI suite execution plan without launching a browser."""
    suite = load_ui_suite(suite_file)
    typer.echo(json.dumps(plan_suite(suite), indent=2, ensure_ascii=False))


@ui_app.command("compile-suite")
def ui_compile_suite(
    suite_file: Path = typer.Argument(..., readable=True),
    output: Path | None = typer.Option(None, "--output", "-o"),
) -> None:
    """Compile a UI suite JSON file into a Playwright test specification."""
    suite = load_ui_suite(suite_file)
    spec = compile_playwright_spec(suite)
    if output is None:
        typer.echo(spec)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(spec, encoding="utf-8")
    typer.echo(json.dumps({"success": True, "suite_id": suite.suite_id, "path": str(output)}, indent=2))


@report_app.command("run")
def report_run(
    run_id: str = typer.Argument(...),
    output: Path | None = typer.Option(None, "--output", "-o"),
) -> None:
    """Build a Markdown report for a ledger run."""
    reg = Registry(db_path())
    rec = reg.get_run(run_id)
    if rec is None:
        raise typer.BadParameter("unknown run_id")
    root = Path(rec.artifact_root)
    result = build_run_report(root, output_path=output)
    typer.echo(json.dumps(result, indent=2, ensure_ascii=False))


@report_app.command("artifacts")
def report_artifacts(
    run_root: Path = typer.Argument(..., exists=True, file_okay=False),
    output: Path | None = typer.Option(None, "--output", "-o"),
) -> None:
    """Build a Markdown report from a run artifact directory."""
    result = build_run_report(run_root, output_path=output)
    typer.echo(json.dumps(result, indent=2, ensure_ascii=False))


@report_app.command("session")
def report_session(
    session_id: str = typer.Argument(...),
    output: Path | None = typer.Option(None, "--output", "-o"),
) -> None:
    """Build a Markdown report for a toolkit session."""
    result = build_session_report(sessions.session_dir(session_id), output_path=output)
    typer.echo(json.dumps(result, indent=2, ensure_ascii=False))


@server_app.command("stdio")
def server_stdio() -> None:
    """Run a dependency-free JSONL tool server over stdin/stdout."""
    serve_jsonl()


@toolkit_app.command("list")
def toolkit_list(domain: str | None = typer.Option(None, "--domain")) -> None:
    """List built-in toolkit utilities."""
    typer.echo(json.dumps(list_tools(domain=domain), indent=2, ensure_ascii=False))


@session_app.command("create")
def toolkit_session_create(project_name: str = typer.Argument("default")) -> None:
    """Create a toolkit session directory."""
    typer.echo(json.dumps(sessions.create_session(project_name), indent=2, ensure_ascii=False))


@session_app.command("list")
def toolkit_session_list(limit: int = typer.Option(20, "--limit")) -> None:
    """List recent toolkit sessions."""
    typer.echo(json.dumps(sessions.list_sessions(limit=limit), indent=2, ensure_ascii=False))


@session_app.command("write")
def toolkit_session_write(
    session_id: str = typer.Argument(...),
    artifact_name: str = typer.Argument(...),
    content_json: str | None = typer.Option(None, "--content-json"),
    content_file: Path | None = typer.Option(None, "--content-file", readable=True),
) -> None:
    """Write a JSON or text artifact to a toolkit session."""
    content: dict | list | str
    if content_file is not None:
        raw = content_file.read_text(encoding="utf-8")
        content = _try_json(raw)
    elif content_json is not None:
        content = _try_json(content_json)
    else:
        raise typer.BadParameter("provide --content-json or --content-file")
    typer.echo(json.dumps(sessions.write_artifact(session_id, artifact_name, content), indent=2, ensure_ascii=False))


@session_app.command("read")
def toolkit_session_read(
    session_id: str = typer.Argument(...),
    artifact_name: str = typer.Argument(...),
) -> None:
    """Read an artifact from a toolkit session."""
    typer.echo(json.dumps(sessions.read_artifact(session_id, artifact_name), indent=2, ensure_ascii=False))


@case_app.command("merge-batches")
def toolkit_case_merge(
    session_id: str = typer.Argument(...),
    output: str = typer.Option("03_test_cases.json", "--output"),
) -> None:
    """Merge 03_test_cases_batch_N.json files."""
    typer.echo(json.dumps(cases.merge_case_batches(session_id, output_filename=output), indent=2, ensure_ascii=False))


@case_app.command("validate")
def toolkit_case_validate(
    session_id: str = typer.Argument(...),
    cases_file: str = typer.Option("03_test_cases.json", "--cases-file"),
) -> None:
    """Validate test case coverage and quality."""
    typer.echo(json.dumps(cases.validate_case_coverage(session_id, cases_filename=cases_file), indent=2, ensure_ascii=False))


@case_app.command("init-registry")
def toolkit_case_init_registry(
    session_id: str = typer.Argument(...),
    cases_file: str = typer.Option("03_test_cases.json", "--cases-file"),
) -> None:
    """Create case_registry.json from a case set."""
    typer.echo(json.dumps(cases.init_case_registry(session_id, cases_filename=cases_file), indent=2, ensure_ascii=False))


@case_app.command("update-status")
def toolkit_case_update_status(
    session_id: str = typer.Argument(...),
    case_id: str = typer.Argument(...),
    status: str = typer.Argument(...),
    executor: str = typer.Option("", "--executor"),
    fail_reason: str = typer.Option("", "--fail-reason"),
    score: float | None = typer.Option(None, "--score"),
    latency_ms: float | None = typer.Option(None, "--latency-ms"),
    screenshot: str = typer.Option("", "--screenshot"),
) -> None:
    """Update one case status."""
    typer.echo(
        json.dumps(
            cases.update_case_status(
                session_id=session_id,
                case_id=case_id,
                status=status,
                executor=executor,
                fail_reason=fail_reason,
                score=score,
                latency_ms=latency_ms,
                screenshot=screenshot,
            ),
            indent=2,
            ensure_ascii=False,
        )
    )


@case_app.command("progress")
def toolkit_case_progress(session_id: str = typer.Argument(...)) -> None:
    """Show case execution progress."""
    typer.echo(json.dumps(cases.get_execution_progress(session_id), indent=2, ensure_ascii=False))


@caseops_app.command("payload")
def toolkit_caseops_payload(
    owner: str = typer.Option(..., "--owner"),
    project_id: str = typer.Option(..., "--project-id"),
    description: str = typer.Option(..., "--description"),
    status: str = typer.Option("passed", "--status"),
    priority: int = typer.Option(1, "--priority"),
    node_id: str | None = typer.Option(None, "--node-id"),
    execution_method: str = typer.Option("automation", "--execution-method"),
) -> None:
    """Build a sanitized CaseOps payload without submitting it."""
    payload = CaseOpsClient().build_payload(
        owner=owner,
        project_id=project_id,
        description=description,
        status=status,
        priority=priority,
        node_id=node_id,
        execution_method=execution_method,
    )
    typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))


@caseops_app.command("submit")
def toolkit_caseops_submit(
    owner: str = typer.Option(..., "--owner"),
    project_id: str = typer.Option(..., "--project-id"),
    description: str = typer.Option(..., "--description"),
    status: str = typer.Option("passed", "--status"),
    priority: int = typer.Option(1, "--priority"),
    node_id: str | None = typer.Option(None, "--node-id"),
    execution_method: str = typer.Option("automation", "--execution-method"),
    base_url: str | None = typer.Option(None, "--base-url"),
    endpoint: str = typer.Option("/api/cases/automation", "--endpoint"),
) -> None:
    """Submit a result to a CaseOps-compatible platform."""
    result = CaseOpsClient(base_url=base_url).submit_result(
        owner=owner,
        project_id=project_id,
        description=description,
        status=status,
        priority=priority,
        node_id=node_id,
        execution_method=execution_method,
        endpoint=endpoint,
    )
    typer.echo(json.dumps(result.__dict__, indent=2, ensure_ascii=False))


@workflow_app.command("start")
def toolkit_workflow_start(
    project_name: str = typer.Argument("default"),
    routes: str = typer.Option("api,ui", "--routes"),
) -> None:
    """Create a session and initialize a workflow."""
    typer.echo(json.dumps(workflows.start_workflow(project_name=project_name, routes=routes), indent=2, ensure_ascii=False))


@workflow_app.command("init")
def toolkit_workflow_init(
    session_id: str = typer.Argument(...),
    routes: str = typer.Option("api,ui", "--routes"),
) -> None:
    """Initialize workflow.json for an existing session."""
    typer.echo(json.dumps(workflows.init_workflow(session_id=session_id, routes=routes), indent=2, ensure_ascii=False))


@workflow_app.command("status")
def toolkit_workflow_status(session_id: str = typer.Argument(...)) -> None:
    """Show workflow progress."""
    typer.echo(json.dumps(workflows.get_workflow_status(session_id), indent=2, ensure_ascii=False))


@workflow_app.command("next")
def toolkit_workflow_next(session_id: str = typer.Argument(...)) -> None:
    """Start and return the next workflow step."""
    typer.echo(json.dumps(workflows.get_next_step(session_id), indent=2, ensure_ascii=False))


@workflow_app.command("complete")
def toolkit_workflow_complete(
    session_id: str = typer.Argument(...),
    step_id: str = typer.Argument(...),
    summary: str = typer.Option("", "--summary"),
    artifact: str = typer.Option("", "--artifact"),
    status: str = typer.Option("completed", "--status"),
) -> None:
    """Complete, skip, or block a workflow step."""
    typer.echo(
        json.dumps(
            workflows.complete_step(
                session_id=session_id,
                step_id=step_id,
                summary=summary,
                artifact=artifact,
                status=status,
            ),
            indent=2,
            ensure_ascii=False,
        )
    )


@workflow_app.command("block")
def toolkit_workflow_block(
    session_id: str = typer.Argument(...),
    step_id: str = typer.Argument(...),
    reason: str = typer.Option(..., "--reason"),
) -> None:
    """Mark a workflow step as blocked."""
    typer.echo(json.dumps(workflows.block_step(session_id, step_id, reason), indent=2, ensure_ascii=False))


def main() -> None:
    app()


def _load_config(config_json: str | None, config_file: Path | None) -> dict[str, Any]:
    config: dict[str, Any] = {}
    if config_file is not None:
        loaded = json.loads(config_file.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise typer.BadParameter("config file must contain a JSON object")
        config.update(loaded)
    if config_json:
        loaded = json.loads(config_json)
        if not isinstance(loaded, dict):
            raise typer.BadParameter("--config-json must be a JSON object")
        config.update(loaded)
    return config


def _try_json(raw: str) -> dict | list | str:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _safe_manifest_config(config: dict[str, Any]) -> dict[str, Any]:
    blocked = {"api_key", "token", "password", "secret"}
    return {
        key: ("***" if any(x in key.lower() for x in blocked) else value)
        for key, value in config.items()
    }


def _executor_config(manifest: dict[str, Any], executor_type: str) -> dict[str, Any]:
    config = dict(manifest.get("executor_config") or {})
    config.setdefault("executor_type", executor_type)
    return config


def _select_executor(executor_type: str):
    if executor_type == "mock":
        return MockExecutor()
    if executor_type == "api_suite":
        return APISuiteExecutor()
    if executor_type in {"ui_suite", "browser_suite"}:
        return UISuiteExecutor()
    if executor_type in {"subprocess", "oversee", "pytest"}:
        return SubprocessExecutor()
    if executor_type in {"agent_gateway", "qa_gateway", "chat_gateway"}:
        return AgentGatewayExecutor()
    raise typer.BadParameter(f"unsupported executor_type: {executor_type}")


def _persist_metrics(reg: Registry, run_id: str, summary: dict[str, Any]) -> None:
    metrics = summary.get("metrics") or {}
    if isinstance(metrics, dict):
        reg.update_metrics(
            run_id,
            [MetricResult(name=str(name), value=value) for name, value in metrics.items()],
        )


if __name__ == "__main__":
    main()
