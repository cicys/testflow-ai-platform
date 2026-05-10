from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from testflow_ai.api_testing.models import APISuite
from testflow_ai.api_testing.runner import load_suite, run_suite
from testflow_ai.core.artifacts import append_prediction, reset_predictions, write_summary
from testflow_ai.executors.base import ExecutionResult


class APISuiteExecutor:
    """Execute a vendor-neutral API suite and store case-level artifacts."""

    def execute(
        self,
        run_id: str,
        artifact_root: Path,
        config: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        config = config or {}
        suite = _load_configured_suite(config)
        report = run_suite(suite, timeout_seconds=config.get("timeout_seconds"))

        logs_dir = artifact_root / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        report_path = logs_dir / "api_suite.report.json"
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

        reset_predictions(artifact_root)
        for case in report["cases"]:
            append_prediction(
                artifact_root,
                {
                    "sample_id": case["case_id"],
                    "input": {
                        "suite_id": report["suite_id"],
                        "case_name": case["name"],
                        "tags": case["tags"],
                    },
                    "output": {
                        "status": case["status"],
                        "passed_steps": case["passed_steps"],
                        "failed_steps": case["failed_steps"],
                    },
                    "error": None if case["status"] == "passed" else "one or more API steps failed",
                },
            )

        summary = {
            "run_id": run_id,
            "executor_type": config.get("executor_type", "api_suite"),
            "status": "succeeded" if report["status"] == "passed" else "failed",
            "suite_id": report["suite_id"],
            "suite_name": report["suite_name"],
            "num_predictions": report["total_cases"],
            "passed": report["passed_cases"],
            "failed": report["failed_cases"],
            "total_steps": report["total_steps"],
            "failed_steps": report["failed_steps"],
            "duration_ms": report["duration_ms"],
            "metrics": {
                "pass_rate": report["metrics"]["case_pass_rate"],
                "step_pass_rate": report["metrics"]["step_pass_rate"],
            },
            "logs": {"report": str(report_path)},
        }
        write_summary(artifact_root, summary)
        return ExecutionResult(
            exit_code=0 if report["status"] == "passed" else 1,
            summary=summary,
            message="api suite executed",
            logs=[str(report_path)],
        )


def _load_configured_suite(config: dict[str, Any]) -> APISuite:
    suite_file = config.get("suite_file")
    suite_json = config.get("suite_json")
    if suite_file:
        return load_suite(Path(str(suite_file)))
    if suite_json:
        payload = json.loads(suite_json) if isinstance(suite_json, str) else suite_json
        return APISuite.model_validate(payload)
    raise ValueError("api_suite executor requires executor_config.suite_file or executor_config.suite_json")
