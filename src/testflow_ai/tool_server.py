from __future__ import annotations

import inspect
import json
import sys
from typing import Any, TextIO

from testflow_ai.toolkits.catalog import get_tool, list_tools

PROTOCOL_VERSION = "testflow-jsonl-v1"


def handle_request(request: dict[str, Any]) -> dict[str, Any]:
    """Handle one dependency-free JSONL tool server request."""
    request_id = request.get("id")
    method = str(request.get("method", ""))
    params = request.get("params") if isinstance(request.get("params"), dict) else {}

    try:
        if method == "server.info":
            return _ok(
                request_id,
                {
                    "name": "testflow-tool-server",
                    "protocol": PROTOCOL_VERSION,
                    "methods": ["server.info", "tools.list", "tools.call", "server.shutdown"],
                },
            )
        if method == "tools.list":
            return _ok(request_id, {"tools": [_tool_descriptor(tool) for tool in list_tools(params.get("domain"))]})
        if method == "tools.call":
            return _ok(request_id, {"result": call_tool(params)})
        if method == "server.shutdown":
            return _ok(request_id, {"shutdown": True})
    except Exception as exc:
        return _error(request_id, "tool_error", str(exc))

    return _error(request_id, "method_not_found", f"unsupported method: {method}")


def call_tool(params: dict[str, Any]) -> Any:
    """Call a registered toolkit function."""
    name = str(params.get("name", ""))
    arguments = params.get("arguments") or {}
    if not isinstance(arguments, dict):
        raise ValueError("tools.call params.arguments must be an object")

    spec = get_tool(name)
    if spec is None:
        raise ValueError(f"unknown tool: {name}")
    return spec.handler(**arguments)


def serve_jsonl(input_stream: TextIO | None = None, output_stream: TextIO | None = None) -> None:
    """Run a line-delimited JSON request loop over stdio-style streams."""
    input_stream = input_stream or sys.stdin
    output_stream = output_stream or sys.stdout
    for raw in input_stream:
        line = raw.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            if not isinstance(request, dict):
                raise ValueError("request must be a JSON object")
            response = handle_request(request)
        except Exception as exc:
            response = _error(None, "invalid_request", str(exc))
        output_stream.write(json.dumps(response, ensure_ascii=False, default=str) + "\n")
        output_stream.flush()
        if response.get("result", {}).get("shutdown") is True:
            break


def _tool_descriptor(tool: dict[str, Any]) -> dict[str, Any]:
    spec = get_tool(str(tool["name"]))
    parameters: list[dict[str, Any]] = []
    if spec is not None:
        signature = inspect.signature(spec.handler)
        for name, param in signature.parameters.items():
            parameters.append(
                {
                    "name": name,
                    "required": param.default is inspect.Parameter.empty,
                    "default": None if param.default is inspect.Parameter.empty else param.default,
                }
            )
    return {**tool, "parameters": parameters}


def _ok(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"id": request_id, "ok": True, "result": result}


def _error(request_id: Any, code: str, message: str) -> dict[str, Any]:
    return {"id": request_id, "ok": False, "error": {"code": code, "message": message}}
