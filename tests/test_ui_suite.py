from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from testflow_ai.executors.ui_suite import UISuiteExecutor
from testflow_ai.toolkits.catalog import get_tool, list_tools
from testflow_ai.ui_testing.compiler import compile_playwright_spec, plan_suite, summarize_suite
from testflow_ai.ui_testing.models import UISuite


def test_ui_suite_compiles_playwright_spec() -> None:
    suite = UISuite.model_validate(_suite_payload())

    spec = compile_playwright_spec(suite)
    plan = plan_suite(suite)
    summary = summarize_suite(suite)

    assert "test.describe" in spec
    assert "await page.goto(\"http://app.local/login\"" in spec
    assert "await page.locator(\"[data-testid=email]\").fill(\"tester@example.com\"" in spec
    assert "await expect(page.locator(\"h1\")).toContainText(\"Dashboard\"" in spec
    assert plan["status"] == "planned"
    assert plan["total_steps"] == 6
    assert summary["actions"]["fill"] == 2


def test_ui_suite_executor_writes_plan_and_spec(tmp_path: Path) -> None:
    root = tmp_path / "run"
    (root / "logs").mkdir(parents=True)

    result = UISuiteExecutor().execute(
        "ui-run",
        root,
        {"executor_type": "ui_suite", "suite_json": _suite_payload()},
    )

    assert result.exit_code == 0
    assert result.summary["executor_type"] == "ui_suite"
    assert result.summary["mode"] == "plan"
    assert result.summary["num_predictions"] == 1
    assert root.joinpath("logs/ui_suite.plan.json").exists()
    assert root.joinpath("logs/ui_suite.playwright.spec.ts").exists()
    prediction = json.loads(root.joinpath("predictions.jsonl").read_text(encoding="utf-8"))
    assert prediction["sample_id"] == "case-ui-001"
    assert prediction["output"]["status"] == "planned"


def test_tool_catalog_contains_ui_tools() -> None:
    names = {tool["name"] for tool in list_tools(domain="ui")}
    assert "validate_ui_suite" in names
    assert get_tool("compile_ui_suite") is not None


def _suite_payload() -> dict[str, Any]:
    return {
        "suite_id": "browser-smoke",
        "name": "Browser smoke suite",
        "base_url": "http://app.local",
        "browser": "chromium",
        "variables": {
            "email": "tester@example.com",
            "password": "password-value",
        },
        "cases": [
            {
                "case_id": "case-ui-001",
                "name": "login dashboard",
                "tags": ["smoke"],
                "steps": [
                    {
                        "step_id": "open-login",
                        "name": "open login page",
                        "action": "goto",
                        "url": "/login",
                    },
                    {
                        "step_id": "fill-email",
                        "name": "fill email",
                        "action": "fill",
                        "target": "[data-testid=email]",
                        "value": "{{email}}",
                    },
                    {
                        "step_id": "fill-password",
                        "name": "fill password",
                        "action": "fill",
                        "target": "[data-testid=password]",
                        "value": "{{password}}",
                    },
                    {
                        "step_id": "submit",
                        "name": "submit login",
                        "action": "click",
                        "target": "[data-testid=submit]",
                    },
                    {
                        "step_id": "assert-dashboard",
                        "name": "dashboard is visible",
                        "action": "assert_text",
                        "target": "h1",
                        "value": "Dashboard",
                    },
                    {
                        "step_id": "capture",
                        "name": "capture dashboard",
                        "action": "screenshot",
                    },
                ],
            }
        ],
    }
