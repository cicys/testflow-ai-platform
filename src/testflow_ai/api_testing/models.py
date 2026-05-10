from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class AssertionKind(str, Enum):
    STATUS_CODE = "status_code"
    JSON_PATH = "json_path"
    HEADER = "header"
    BODY_CONTAINS = "body_contains"
    RESPONSE_TIME_MS = "response_time_ms"


class AssertionOperator(str, Enum):
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    EXISTS = "exists"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"


class APIAssertion(BaseModel):
    """A single assertion against an HTTP response."""

    model_config = ConfigDict(extra="forbid")

    kind: AssertionKind
    expected: Any | None = None
    path: str | None = None
    operator: AssertionOperator = AssertionOperator.EQUALS
    message: str = ""


class APIStep(BaseModel):
    """One HTTP call inside an API case."""

    model_config = ConfigDict(extra="forbid")

    step_id: str
    name: str
    method: HttpMethod = HttpMethod.GET
    endpoint: str
    headers: dict[str, Any] = Field(default_factory=dict)
    query_params: dict[str, Any] = Field(default_factory=dict)
    body: Any | None = None
    assertions: list[APIAssertion] = Field(default_factory=list)
    extract: dict[str, str] = Field(default_factory=dict)
    timeout_seconds: float | None = None


class APICase(BaseModel):
    """A group of ordered API steps that share case-scoped variables."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    name: str
    variables: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    steps: list[APIStep]


class APISuite(BaseModel):
    """Public, vendor-neutral API automation suite definition."""

    model_config = ConfigDict(extra="forbid")

    suite_id: str
    name: str
    base_url: str
    headers: dict[str, Any] = Field(default_factory=dict)
    variables: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: float = 30
    cases: list[APICase]
