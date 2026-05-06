from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RunStatus(str, Enum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class DatasetVersion(BaseModel):
    """Minimal dataset version record."""

    id: str
    label: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    meta: dict[str, Any] = Field(default_factory=dict)


class MetricResult(BaseModel):
    name: str
    value: float | str | dict[str, Any]
    meta: dict[str, Any] = Field(default_factory=dict)


class RunRecord(BaseModel):
    """A single TestFlow execution record."""

    id: str
    executor_type: str
    dataset_version_id: str | None = None
    status: RunStatus = RunStatus.pending
    created_at: datetime = Field(default_factory=utc_now)
    finished_at: datetime | None = None
    artifact_root: str = ""
    manifest: dict[str, Any] = Field(default_factory=dict)
    metrics: list[MetricResult] = Field(default_factory=list)
