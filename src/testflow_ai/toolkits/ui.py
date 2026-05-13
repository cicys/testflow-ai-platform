from __future__ import annotations

from pathlib import Path
from typing import Any

from testflow_ai.ui_testing.compiler import compile_playwright_spec, load_suite, summarize_suite


def validate_ui_suite(suite_file: str) -> dict[str, Any]:
    """Validate a UI suite JSON file and return a compact summary."""
    return {"success": True, **summarize_suite(load_suite(Path(suite_file)))}


def compile_ui_suite(suite_file: str, output: str) -> dict[str, Any]:
    """Compile a UI suite JSON file into a Playwright spec."""
    suite = load_suite(Path(suite_file))
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(compile_playwright_spec(suite), encoding="utf-8")
    return {"success": True, "suite_id": suite.suite_id, "path": str(target)}
