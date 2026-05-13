from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BrowserName(str, Enum):
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"


class UIAction(str, Enum):
    GOTO = "goto"
    CLICK = "click"
    FILL = "fill"
    SELECT = "select"
    CHECK = "check"
    UNCHECK = "uncheck"
    PRESS = "press"
    HOVER = "hover"
    WAIT_FOR_SELECTOR = "wait_for_selector"
    WAIT_FOR_URL = "wait_for_url"
    ASSERT_URL = "assert_url"
    ASSERT_TEXT = "assert_text"
    ASSERT_VISIBLE = "assert_visible"
    ASSERT_HIDDEN = "assert_hidden"
    SCREENSHOT = "screenshot"


class UIStep(BaseModel):
    """One browser automation step in a UI suite."""

    model_config = ConfigDict(extra="forbid")

    step_id: str
    name: str
    action: UIAction
    target: str | None = None
    value: Any | None = None
    url: str | None = None
    timeout_ms: int | None = None


class UICase(BaseModel):
    """A browser test case with ordered UI steps."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    name: str
    start_url: str | None = None
    variables: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    steps: list[UIStep]


class UISuite(BaseModel):
    """Public, vendor-neutral browser automation suite definition."""

    model_config = ConfigDict(extra="forbid")

    suite_id: str
    name: str
    base_url: str = ""
    browser: BrowserName = BrowserName.CHROMIUM
    viewport: dict[str, int] = Field(default_factory=lambda: {"width": 1280, "height": 720})
    variables: dict[str, Any] = Field(default_factory=dict)
    timeout_ms: int = 30000
    cases: list[UICase]
