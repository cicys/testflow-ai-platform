from __future__ import annotations

import os
from pathlib import Path


def eval_home() -> Path:
    return Path(os.environ.get("TESTFLOW_HOME", Path.home() / ".testflow")).resolve()


def db_path() -> Path:
    return eval_home() / "registry.sqlite3"


def artifact_base() -> Path:
    return eval_home() / "artifacts"
