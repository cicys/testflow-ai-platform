from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from testflow_ai.core.artifacts import append_prediction, reset_predictions, write_summary
from testflow_ai.executors.base import ExecutionResult


class AgentGatewayExecutor:
    """Call a chat-style agent service and capture the response as a TestFlow run."""

    def execute(
        self,
        run_id: str,
        artifact_root: Path,
        config: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        config = config or {}
        base_url = str(config.get("base_url", "")).rstrip("/")
        endpoint = str(config.get("endpoint", "/chat/sync"))
        message = str(config.get("message", "Run TestFlow smoke check"))
        timeout = int(config.get("timeout_seconds", 120))
        conversation_id = config.get("conversation_id")
        if not base_url:
            raise ValueError("agent_gateway executor requires executor_config.base_url")

        url = f"{base_url}{endpoint}"
        payload = {
            "message": message,
            "conversation_id": conversation_id,
            "system_prompt": config.get("system_prompt"),
        }
        request_body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=request_body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        logs_dir = artifact_root / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        response_log = logs_dir / "agent_gateway.response.json"
        error_log = logs_dir / "agent_gateway.error.log"

        status = "succeeded"
        response_payload: dict[str, Any] = {}
        error = None
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
                response_payload = json.loads(raw) if raw.strip().startswith("{") else {"message": raw}
                response_log.write_text(json.dumps(response_payload, indent=2, ensure_ascii=False), encoding="utf-8")
        except urllib.error.HTTPError as exc:
            status = "failed"
            raw = exc.read().decode("utf-8", errors="replace")
            error = f"HTTP {exc.code}: {raw}"
            error_log.write_text(error, encoding="utf-8")
        except Exception as exc:
            status = "failed"
            error = str(exc)
            error_log.write_text(error, encoding="utf-8")

        reset_predictions(artifact_root)
        append_prediction(
            artifact_root,
            {
                "sample_id": "agent_gateway",
                "input": {"message": message},
                "output": response_payload,
                "error": error,
            },
        )

        summary = {
            "run_id": run_id,
            "executor_type": config.get("executor_type", "agent_gateway"),
            "status": status,
            "base_url": base_url,
            "endpoint": endpoint,
            "num_predictions": 1,
            "failed": 1 if error else 0,
            "passed": 0 if error else 1,
            "metrics": {"pass_rate": 0.0 if error else 1.0},
            "logs": {
                "response": str(response_log) if response_log.exists() else None,
                "error": str(error_log) if error_log.exists() else None,
            },
        }
        write_summary(artifact_root, summary)
        return ExecutionResult(
            exit_code=1 if error else 0,
            summary=summary,
            message="agent gateway executed",
            logs=[path for path in summary["logs"].values() if path],
        )
