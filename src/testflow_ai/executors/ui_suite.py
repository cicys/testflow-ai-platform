from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from testflow_ai.core.artifacts import append_prediction, reset_predictions, write_summary
from testflow_ai.executors.base import ExecutionResult
from testflow_ai.ui_testing.compiler import compile_playwright_spec, load_suite, plan_suite
from testflow_ai.ui_testing.models import UISuite


class UISuiteExecutor:
    """Compile a vendor-neutral UI suite and store case-level plan artifacts."""

    def execute(
        self,
        run_id: str,
        artifact_root: Path,
        config: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        config = config or {}
        suite = _load_configured_suite(config)
        plan = plan_suite(suite)
        spec = compile_playwright_spec(suite)

        logs_dir = artifact_root / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        plan_path = logs_dir / "ui_suite.plan.json"
        spec_path = logs_dir / "ui_suite.playwright.spec.ts"
        plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
        spec_path.write_text(spec, encoding="utf-8")

        reset_predictions(artifact_root)
        for case in plan["cases"]:
            append_prediction(
                artifact_root,
                {
                    "sample_id": case["case_id"],
                    "input": {
                        "suite_id": plan["suite_id"],
                        "case_name": case["name"],
                        "tags": case["tags"],
                    },
                    "output": {
                        "status": case["status"],
                        "total_steps": case["total_steps"],
                        "mode": plan["mode"],
                    },
                    "error": None,
                },
            )

        summary = {
            "run_id": run_id,
            "executor_type": config.get("executor_type", "ui_suite"),
            "status": "succeeded",
            "mode": plan["mode"],
            "suite_id": plan["suite_id"],
            "suite_name": plan["suite_name"],
            "browser": plan["browser"],
            "num_predictions": plan["total_cases"],
            "passed": plan["planned_cases"],
            "failed": 0,
            "total_steps": plan["total_steps"],
            "metrics": {
                "planned_case_rate": plan["metrics"]["planned_case_rate"],
                "planned_step_rate": plan["metrics"]["planned_step_rate"],
            },
            "logs": {
                "plan": str(plan_path),
                "playwright_spec": str(spec_path),
            },
        }
        write_summary(artifact_root, summary)
        return ExecutionResult(
            exit_code=0,
            summary=summary,
            message="ui suite planned",
            logs=[str(plan_path), str(spec_path)],
        )


def _load_configured_suite(config: dict[str, Any]) -> UISuite:
    suite_file = config.get("suite_file")
    suite_json = config.get("suite_json")
    if suite_file:
        return load_suite(Path(str(suite_file)))
    if suite_json:
        payload = json.loads(suite_json) if isinstance(suite_json, str) else suite_json
        return UISuite.model_validate(payload)
    raise ValueError("ui_suite executor requires executor_config.suite_file or executor_config.suite_json")
