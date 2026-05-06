from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer

from testflow_ai.core.artifacts import ensure_run_layout, write_manifest
from testflow_ai.core.diff import diff_runs as diff_run_artifacts
from testflow_ai.core.models import DatasetVersion, MetricResult, RunStatus
from testflow_ai.core.paths import artifact_base, db_path, eval_home
from testflow_ai.core.registry import Registry
from testflow_ai.executors.mock import MockExecutor
from testflow_ai.executors.subprocess import SubprocessExecutor

app = typer.Typer(no_args_is_help=True, help="TestFlow AI local test orchestration toolkit")
run_app = typer.Typer(no_args_is_help=True, help="Create, execute, and compare runs")
dataset_app = typer.Typer(no_args_is_help=True, help="Manage dataset versions")
app.add_typer(run_app, name="run")
app.add_typer(dataset_app, name="dataset")


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
    if executor_type in {"subprocess", "oversee", "pytest"}:
        return SubprocessExecutor()
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
