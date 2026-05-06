from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, Field


class ExecutionResult(BaseModel):
    """Shared return contract for all executors."""

    exit_code: int
    summary: dict[str, Any]
    message: str = ""
    logs: list[str] = Field(default_factory=list)


class Executor(Protocol):
    """Executor protocol: receive run context and write only under artifact_root."""

    def execute(
        self,
        run_id: str,
        artifact_root: Path,
        config: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        ...
