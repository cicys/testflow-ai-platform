from __future__ import annotations

from pathlib import Path
from typing import Any

from testflow_ai.reports.builder import build_run_report as _build_run_report
from testflow_ai.reports.builder import build_session_report as _build_session_report
from testflow_ai.toolkits.sessions import session_dir


def build_run_artifact_report(run_root: str, output: str = "report.md") -> dict[str, Any]:
    """Build a Markdown report from a run artifact directory."""
    root = Path(run_root)
    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = root / output
    return _build_run_report(root, output_path=output_path)


def build_session_report(session_id: str, output: str = "test_report.md") -> dict[str, Any]:
    """Build a Markdown report from a toolkit session."""
    root = session_dir(session_id)
    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = root / output
    return _build_session_report(root, output_path=output_path)
