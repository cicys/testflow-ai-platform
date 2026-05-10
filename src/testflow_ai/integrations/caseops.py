from __future__ import annotations

import json
import os
import random
import string
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


STATUS_CODE = {
    "not_executed": 0,
    "passed": 1,
    "failed": 2,
    "blocked": 3,
    "skipped": 4,
    "running": 5,
    "repaired": 1,
}


@dataclass(frozen=True)
class CaseOpsResult:
    success: bool
    payload: dict[str, Any]
    response: dict[str, Any] | None = None
    error: str = ""


class CaseOpsClient:
    """Generic adapter for test-case and CI/CD platforms."""

    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        self.base_url = (base_url or os.environ.get("TESTFLOW_CASEOPS_URL", "")).rstrip("/")
        self.token = token or os.environ.get("TESTFLOW_CASEOPS_TOKEN", "")
        self.timeout_seconds = timeout_seconds

    def build_payload(
        self,
        owner: str,
        project_id: str,
        description: str,
        status: str | int,
        priority: int = 1,
        node_id: str | None = None,
        execution_method: str = "automation",
        history: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        code = _status_code(status)
        node = node_id or _random_node_id()
        now = datetime.now(timezone.utc).isoformat()
        return {
            "owner": owner,
            "project_id": project_id,
            "category": "automation",
            "records": [
                {
                    "node_id": node,
                    "description": description,
                    "execution_method": execution_method,
                    "priority": priority,
                    "status": code,
                    "status_name": _status_name(code),
                    "history": history
                    or [{"name": "TestFlow", "time": now, "status": code}],
                    "metadata": metadata or {},
                }
            ],
        }

    def submit_result(
        self,
        owner: str,
        project_id: str,
        description: str,
        status: str | int,
        priority: int = 1,
        node_id: str | None = None,
        execution_method: str = "automation",
        history: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
        endpoint: str = "/api/cases/automation",
    ) -> CaseOpsResult:
        payload = self.build_payload(
            owner=owner,
            project_id=project_id,
            description=description,
            status=status,
            priority=priority,
            node_id=node_id,
            execution_method=execution_method,
            history=history,
            metadata=metadata,
        )
        if not self.base_url:
            return CaseOpsResult(
                success=False,
                payload=payload,
                error="TESTFLOW_CASEOPS_URL or base_url is required to submit",
            )

        url = f"{self.base_url}{endpoint}"
        body = urllib.parse.urlencode({"payload": json.dumps(payload, ensure_ascii=False)}).encode("utf-8")
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
                parsed = json.loads(raw) if raw.strip().startswith(("{", "[")) else {"raw": raw}
                return CaseOpsResult(success=200 <= response.status < 300, payload=payload, response=parsed)
        except Exception as exc:
            return CaseOpsResult(success=False, payload=payload, error=str(exc))


def _status_code(status: str | int) -> int:
    if isinstance(status, int):
        return status
    return STATUS_CODE.get(status, STATUS_CODE.get(status.lower(), 0))


def _status_name(code: int) -> str:
    for name, value in STATUS_CODE.items():
        if value == code and name != "repaired":
            return name
    return "unknown"


def _random_node_id() -> str:
    length = random.randint(8, 12)
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))
