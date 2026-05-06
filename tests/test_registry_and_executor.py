from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from testflow_ai.core.artifacts import run_dir
from testflow_ai.core.paths import artifact_base, db_path
from testflow_ai.core.registry import Registry
from testflow_ai.executors.mock import MockExecutor
from testflow_ai.executors.subprocess import SubprocessExecutor


@pytest.fixture()
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("TESTFLOW_HOME", str(tmp_path))
    return tmp_path


def test_create_run_mock_flow(isolated_home: Path) -> None:
    Registry(db_path())
    art = artifact_base()
    reg = Registry(db_path())
    rec = reg.create_run(
        executor_type="mock",
        dataset_version_id="dv1",
        artifact_root="",
        manifest={},
    )
    root = run_dir(art, rec.id)
    root.mkdir(parents=True)
    (root / "logs").mkdir(exist_ok=True)
    reg.update_artifact_root(rec.id, str(root))
    man = {"run_id": rec.id, "executor_type": "mock"}
    root.joinpath("manifest.json").write_text(json.dumps(man), encoding="utf-8")

    result = MockExecutor().execute(rec.id, root)
    summary = result.summary
    assert result.exit_code == 0
    assert summary["executor_type"] == "mock"
    assert (root / "predictions.jsonl").exists()
    loaded = reg.get_run(rec.id)
    assert loaded is not None
    assert loaded.executor_type == "mock"


def test_diff_summaries(isolated_home: Path) -> None:
    from testflow_ai.core.diff import diff_run_summaries

    a = isolated_home / "a"
    b = isolated_home / "b"
    a.mkdir()
    b.mkdir()
    a.joinpath("summary.json").write_text(json.dumps({"run_id": "1", "x": 1}), encoding="utf-8")
    b.joinpath("summary.json").write_text(json.dumps({"run_id": "2", "x": 2}), encoding="utf-8")
    out = diff_run_summaries(a, b)
    assert out["all_equal"] is False
    assert out["fields"]["x"]["equal"] is False


def test_subprocess_executor_writes_summary_and_logs(isolated_home: Path) -> None:
    root = isolated_home / "run"
    (root / "logs").mkdir(parents=True)

    result = SubprocessExecutor().execute(
        "run-subprocess",
        root,
        {
            "executor_type": "oversee",
            "command": [sys.executable, "-c", "print('ok from subprocess')"],
        },
    )

    assert result.exit_code == 0
    assert result.summary["executor_type"] == "oversee"
    assert result.summary["metrics"]["pass_rate"] == 1.0
    assert "ok from subprocess" in root.joinpath("logs/executor.stdout.log").read_text(encoding="utf-8")
    assert root.joinpath("predictions.jsonl").exists()
