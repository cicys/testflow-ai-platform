from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from testflow_ai.toolkits import cases as cases
from testflow_ai.toolkits import sessions as sessions


ToolHandler = Callable[..., dict]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    domain: str
    summary: str
    handler: ToolHandler


BUILTIN_TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="create_session",
        domain="session",
        summary="Create a toolkit session artifact directory.",
        handler=sessions.create_session,
    ),
    ToolSpec(
        name="list_sessions",
        domain="session",
        summary="List recent toolkit sessions.",
        handler=sessions.list_sessions,
    ),
    ToolSpec(
        name="write_artifact",
        domain="session",
        summary="Write a JSON or text artifact to a session.",
        handler=sessions.write_artifact,
    ),
    ToolSpec(
        name="read_artifact",
        domain="session",
        summary="Read a JSON or text artifact from a session.",
        handler=sessions.read_artifact,
    ),
    ToolSpec(
        name="merge_case_batches",
        domain="cases",
        summary="Merge 03_test_cases_batch_N.json files into one case set.",
        handler=cases.merge_case_batches,
    ),
    ToolSpec(
        name="validate_case_coverage",
        domain="cases",
        summary="Validate case coverage, field completeness, and scenario balance.",
        handler=cases.validate_case_coverage,
    ),
    ToolSpec(
        name="init_case_registry",
        domain="tracking",
        summary="Create case_registry.json from a test case set.",
        handler=cases.init_case_registry,
    ),
    ToolSpec(
        name="update_case_status",
        domain="tracking",
        summary="Update a single case status in case_registry.json.",
        handler=cases.update_case_status,
    ),
    ToolSpec(
        name="get_execution_progress",
        domain="tracking",
        summary="Return execution and pass-rate progress from case_registry.json.",
        handler=cases.get_execution_progress,
    ),
)


def list_tools(domain: str | None = None) -> list[dict]:
    specs = BUILTIN_TOOLS
    if domain:
        specs = tuple(spec for spec in specs if spec.domain == domain)
    return [
        {"name": spec.name, "domain": spec.domain, "summary": spec.summary}
        for spec in specs
    ]


def get_tool(name: str) -> ToolSpec | None:
    return next((spec for spec in BUILTIN_TOOLS if spec.name == name), None)
