from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from testflow_ai.tool_server import handle_request, serve_jsonl


@pytest.fixture()
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("TESTFLOW_HOME", str(tmp_path))
    return tmp_path


def test_tool_server_lists_tools() -> None:
    response = handle_request({"id": 1, "method": "tools.list", "params": {"domain": "workflow"}})

    assert response["ok"] is True
    names = {tool["name"] for tool in response["result"]["tools"]}
    assert "start_workflow" in names
    assert any(param["name"] == "project_name" for tool in response["result"]["tools"] for param in tool["parameters"])


def test_tool_server_calls_tool(isolated_home: Path) -> None:
    response = handle_request(
        {
            "id": "call-1",
            "method": "tools.call",
            "params": {
                "name": "start_workflow",
                "arguments": {"project_name": "server-demo", "routes": "api"},
            },
        }
    )

    assert response["ok"] is True
    result = response["result"]["result"]
    assert result["success"] is True
    assert result["workflow"]["routes"] == ["api"]


def test_tool_server_jsonl_loop(isolated_home: Path) -> None:
    input_stream = io.StringIO(
        "\n".join(
            [
                json.dumps({"id": 1, "method": "server.info"}),
                json.dumps({"id": 2, "method": "tools.list", "params": {"domain": "ui"}}),
                json.dumps({"id": 3, "method": "server.shutdown"}),
            ]
        )
    )
    output_stream = io.StringIO()

    serve_jsonl(input_stream, output_stream)

    responses = [json.loads(line) for line in output_stream.getvalue().splitlines()]
    assert responses[0]["result"]["protocol"] == "testflow-jsonl-v1"
    assert responses[1]["result"]["tools"][0]["domain"] == "ui"
    assert responses[2]["result"]["shutdown"] is True
