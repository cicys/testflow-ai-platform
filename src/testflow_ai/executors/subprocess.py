from __future__ import annotations

import json
import os
import shlex
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from testflow_ai.core.artifacts import append_prediction, reset_predictions, write_summary
from testflow_ai.executors.base import ExecutionResult


class SubprocessExecutor:
    """Run Oversee-style checks, pytest suites, or any local command."""

    def execute(
        self,
        run_id: str,
        artifact_root: Path,
        config: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        config = config or {}
        command = _normalize_command(config.get("command"))
        if not command:
            raise ValueError("subprocess/oversee executor requires executor_config.command")

        timeout = int(config.get("timeout_seconds", 300))
        cwd = Path(config["cwd"]).expanduser().resolve() if config.get("cwd") else None
        env = _prepare_env(config.get("env"))

        logs_dir = artifact_root / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        stdout_log = logs_dir / "executor.stdout.log"
        stderr_log = logs_dir / "executor.stderr.log"

        try:
            completed = subprocess.run(
                command,
                cwd=str(cwd) if cwd else None,
                env=env,
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
            returncode = completed.returncode
            stdout = completed.stdout
            stderr = completed.stderr
        except subprocess.TimeoutExpired as exc:
            returncode = 124
            stdout = _to_text(exc.stdout)
            stderr = _to_text(exc.stderr) + f"\nTimeout after {timeout} seconds"

        stdout_log.write_text(stdout, encoding="utf-8")
        stderr_log.write_text(stderr, encoding="utf-8")

        predictions = _predictions_from_junit(config, cwd)
        if not predictions:
            predictions = [
                {
                    "sample_id": "subprocess",
                    "output": {
                        "command": command,
                        "returncode": returncode,
                        "stdout_tail": stdout[-2000:],
                    },
                    "error": stderr[-2000:] if returncode else None,
                }
            ]

        reset_predictions(artifact_root)
        for prediction in predictions:
            append_prediction(artifact_root, prediction)

        failed = sum(1 for item in predictions if item.get("error"))
        total = len(predictions)
        summary = {
            "run_id": run_id,
            "executor_type": config.get("executor_type", "subprocess"),
            "status": "succeeded" if returncode == 0 else "failed",
            "command": command,
            "returncode": returncode,
            "num_predictions": total,
            "failed": failed,
            "passed": total - failed,
            "metrics": {
                "pass_rate": 0.0 if total == 0 else (total - failed) / total,
            },
            "logs": {
                "stdout": str(stdout_log),
                "stderr": str(stderr_log),
            },
        }
        write_summary(artifact_root, summary)
        return ExecutionResult(
            exit_code=returncode,
            summary=summary,
            message="subprocess executed",
            logs=[str(stdout_log), str(stderr_log)],
        )


def _normalize_command(command: Any) -> list[str]:
    if isinstance(command, str):
        return shlex.split(command)
    if isinstance(command, list) and all(isinstance(x, str) for x in command):
        return command
    return []


def _to_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _prepare_env(extra_env: Any) -> dict[str, str] | None:
    if extra_env is None:
        return None
    if not isinstance(extra_env, dict):
        raise ValueError("executor_config.env must be an object")
    env = os.environ.copy()
    env.update({str(k): str(v) for k, v in extra_env.items()})
    return env


def _predictions_from_junit(config: dict[str, Any], cwd: Path | None) -> list[dict[str, Any]]:
    junit_xml = config.get("junit_xml")
    if not junit_xml:
        return []
    path = Path(junit_xml).expanduser()
    if not path.is_absolute() and cwd is not None:
        path = cwd / path
    if not path.exists():
        return []

    root = ET.fromstring(path.read_text(encoding="utf-8"))
    predictions: list[dict[str, Any]] = []
    for testcase in root.iter("testcase"):
        classname = testcase.attrib.get("classname", "")
        name = testcase.attrib.get("name", "unknown")
        sample_id = f"{classname}.{name}".strip(".")
        failure = testcase.find("failure")
        if failure is None:
            failure = testcase.find("error")
        if failure is None:
            failure = testcase.find("skipped")
        predictions.append(
            {
                "sample_id": sample_id,
                "output": {
                    "classname": classname,
                    "name": name,
                    "time": testcase.attrib.get("time"),
                },
                "error": None
                if failure is None
                else json.dumps(
                    {"tag": failure.tag, "message": failure.attrib.get("message", "")},
                    ensure_ascii=False,
                ),
            }
        )
    return predictions
