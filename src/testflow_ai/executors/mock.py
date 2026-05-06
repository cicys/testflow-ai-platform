from __future__ import annotations

from pathlib import Path
from typing import Any

from testflow_ai.core.artifacts import append_prediction, reset_predictions, write_manifest, write_summary
from testflow_ai.executors.base import ExecutionResult


class MockExecutor:
    """Dependency-free executor that emits deterministic predictions."""

    def execute(
        self,
        run_id: str,
        artifact_root: Path,
        config: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        manifest_path = artifact_root / "manifest.json"
        manifest: dict[str, Any] = {}
        if manifest_path.exists():
            import json

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest.setdefault("run_id", run_id)
        manifest["executor_type"] = "mock"
        write_manifest(artifact_root, manifest)
        reset_predictions(artifact_root)

        for i in range(3):
            append_prediction(
                artifact_root,
                {
                    "sample_id": f"s{i}",
                    "output": {"label": "ok", "score": 0.9 - i * 0.01},
                    "error": None,
                },
            )

        summary = {
            "run_id": run_id,
            "executor_type": "mock",
            "num_predictions": 3,
            "status": "succeeded",
            "metrics": {"mock_pass_rate": 1.0},
        }
        write_summary(artifact_root, summary)
        return ExecutionResult(exit_code=0, summary=summary, message="mock executed")
