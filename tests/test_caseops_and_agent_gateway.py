from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from testflow_ai.executors.agent_gateway import AgentGatewayExecutor
from testflow_ai.integrations.caseops import CaseOpsClient


def test_caseops_build_payload_is_generic() -> None:
    payload = CaseOpsClient().build_payload(
        owner="tester",
        project_id="sprint-1",
        description="UI smoke result",
        status="passed",
        node_id="node-123",
        execution_method="ui_automation",
    )

    assert payload["owner"] == "tester"
    assert payload["project_id"] == "sprint-1"
    assert payload["records"][0]["status"] == 1
    assert payload["records"][0]["node_id"] == "node-123"
    assert payload["records"][0]["execution_method"] == "ui_automation"
    assert "CaseOps" not in json.dumps(payload)


def test_agent_gateway_executor_calls_chat_sync(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)
    root = tmp_path / "run"
    (root / "logs").mkdir(parents=True)

    result = AgentGatewayExecutor().execute(
        "agent-run",
        root,
        {
            "executor_type": "agent_gateway",
            "base_url": "http://agent.local",
            "endpoint": "/chat/sync",
            "message": "generate a smoke test",
        },
    )

    assert result.exit_code == 0
    assert result.summary["status"] == "succeeded"
    predictions = root.joinpath("predictions.jsonl").read_text(encoding="utf-8")
    assert "agent response" in predictions
    assert root.joinpath("summary.json").exists()


class _FakeResponse:
    status = 200

    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def _fake_urlopen(request: Any, timeout: int = 0) -> _FakeResponse:
    payload = json.loads(request.data.decode("utf-8"))
    return _FakeResponse(
        json.dumps(
            {
                "message": f"agent response: {payload['message']}",
                "conversation_id": "conv-test",
                "tools_used": ["planner"],
            }
        ).encode("utf-8")
    )
