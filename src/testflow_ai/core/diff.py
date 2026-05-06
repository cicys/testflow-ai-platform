from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from testflow_ai.core.artifacts import read_json


def diff_runs(a_root: Path, b_root: Path, sample_key: str = "sample_id") -> dict[str, Any]:
    """Compare summaries and sample-level prediction JSONL files."""
    sa = read_json(a_root / "summary.json") if (a_root / "summary.json").exists() else {}
    sb = read_json(b_root / "summary.json") if (b_root / "summary.json").exists() else {}
    keys = sorted(set(sa) | set(sb))
    per_key: dict[str, dict[str, Any]] = {}
    for k in keys:
        va, vb = sa.get(k), sb.get(k)
        per_key[k] = {"a": va, "b": vb, "equal": va == vb}
    prediction_diff = diff_predictions(a_root, b_root, sample_key=sample_key)
    return {
        "summary_a": sa.get("run_id"),
        "summary_b": sb.get("run_id"),
        "fields": per_key,
        "all_equal": sa == sb,
        "predictions": prediction_diff,
    }


def diff_run_summaries(a_root: Path, b_root: Path) -> dict[str, Any]:
    """Backward-compatible summary diff with default sample_id prediction diff."""
    return diff_runs(a_root, b_root)


def diff_predictions(a_root: Path, b_root: Path, sample_key: str = "sample_id") -> dict[str, Any]:
    pa = _load_predictions(a_root / "predictions.jsonl", sample_key)
    pb = _load_predictions(b_root / "predictions.jsonl", sample_key)
    keys = sorted(set(pa) | set(pb))
    changed: list[dict[str, Any]] = []
    only_a: list[str] = []
    only_b: list[str] = []
    for key in keys:
        if key not in pa:
            only_b.append(key)
            continue
        if key not in pb:
            only_a.append(key)
            continue
        if pa[key] != pb[key]:
            changed.append({"sample_id": key, "a": pa[key], "b": pb[key]})
    return {
        "sample_key": sample_key,
        "count_a": len(pa),
        "count_b": len(pb),
        "only_a": only_a,
        "only_b": only_b,
        "changed": changed,
        "all_equal": not only_a and not only_b and not changed,
    }


def _load_predictions(path: Path, sample_key: str) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    out: dict[str, dict[str, Any]] = {}
    for idx, raw in enumerate(path.read_text(encoding="utf-8").splitlines()):
        if not raw.strip():
            continue
        item = json.loads(raw)
        key = str(item.get(sample_key) or item.get("id") or idx)
        out[key] = item
    return out


def count_predictions(root: Path) -> int:
    p = root / "predictions.jsonl"
    if not p.exists():
        return 0
    return sum(1 for _ in p.open(encoding="utf-8"))
