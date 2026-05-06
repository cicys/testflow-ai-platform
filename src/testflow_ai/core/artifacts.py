from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def run_dir(base: Path, run_id: str) -> Path:
    return base / "runs" / run_id


def ensure_run_layout(artifact_base: Path, run_id: str) -> Path:
    root = run_dir(artifact_base, run_id)
    (root / "logs").mkdir(parents=True, exist_ok=True)
    return root


def write_manifest(root: Path, payload: dict[str, Any]) -> Path:
    path = root / "manifest.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return path


def write_summary(root: Path, payload: dict[str, Any]) -> Path:
    path = root / "summary.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return path


def append_prediction(root: Path, line: dict[str, Any]) -> None:
    path = root / "predictions.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False, default=str) + "\n")


def reset_predictions(root: Path) -> None:
    path = root / "predictions.jsonl"
    path.write_text("", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
