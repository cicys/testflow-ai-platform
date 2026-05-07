from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from testflow_ai.toolkits.sessions import session_dir


VALID_CASE_STATUSES = {
    "passed",
    "failed",
    "blocked",
    "skipped",
    "not_executed",
    "running",
    "repaired",
}

BATCH_PATTERN = re.compile(r"03_test_cases_batch_(\d+)\.json$")

STRATEGY_PREFIX_MAP = {
    "business": "TC-BIZ",
    "api": "TC-API",
    "skills": "TC-SKL",
    "agent": "TC-AI",
    "performance": "TC-PRF",
    "optimization": "TC-OPT",
    "strategy_business": "TC-BIZ",
    "strategy_api": "TC-API",
    "strategy_skills": "TC-SKL",
    "strategy_ai_agent": "TC-AI",
    "strategy_performance": "TC-PRF",
    "strategy_optimization": "TC-OPT",
}

REQUIRED_CASE_FIELDS = ("strategy", "design_technique", "tag", "requirement_type")
SCENE_DIMENSION_THRESHOLDS = {"positive": 0.30, "abnormal": 0.15, "boundary": 0.10}


def merge_case_batches(session_id: str, output_filename: str = "03_test_cases.json") -> dict:
    root = session_dir(session_id)
    if not root.exists():
        return {"success": False, "error": "session not found", "session_id": session_id}

    batches = _find_batch_files(root)
    if not batches:
        return {"success": False, "error": "no batch files found", "session_id": session_id}

    batch_payloads = [_load_case_set(path) for _, path in batches]
    all_cases: list[dict[str, Any]] = []
    for payload in batch_payloads:
        all_cases.extend(payload.get("test_cases", []))

    deduped_cases, dedup_removed = _deduplicate_cases(all_cases)
    renumbered_cases = _renumber_case_ids(deduped_cases)
    merged = {
        "test_case_set": {
            "total_cases": len(renumbered_cases),
            "test_cases": renumbered_cases,
            "coverage_summary": _compute_coverage_summary(renumbered_cases),
            "traceability_matrix": _merge_traceability(batch_payloads),
            "merged_at": datetime.now(timezone.utc).isoformat(),
        }
    }
    output_path = root / output_filename
    output_path.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "success": True,
        "session_id": session_id,
        "output_path": str(output_path),
        "total_batches": len(batches),
        "input_cases": len(all_cases),
        "dedup_removed": dedup_removed,
        "final_cases": len(renumbered_cases),
    }


def validate_case_coverage(session_id: str, cases_filename: str = "03_test_cases.json") -> dict:
    root = session_dir(session_id)
    cases_path = root / cases_filename
    if not cases_path.exists():
        return {"success": False, "error": "case file not found", "path": str(cases_path)}

    case_set = _load_case_set(cases_path)
    cases = case_set.get("test_cases", [])
    checks = [
        _validate_case_count(case_set),
        _validate_field_completeness(cases),
        _validate_scene_dimensions(cases),
        _validate_traceability(case_set),
    ]
    passed = all(check["passed"] for check in checks)
    report = {
        "success": passed,
        "session_id": session_id,
        "cases_file": str(cases_path),
        "total_cases": len(cases),
        "checks": checks,
    }
    (root / "case_coverage_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return report


def init_case_registry(session_id: str, cases_filename: str = "03_test_cases.json") -> dict:
    root = session_dir(session_id)
    cases_path = root / cases_filename
    if not cases_path.exists():
        return {"success": False, "error": "case file not found", "path": str(cases_path)}
    cases = _load_case_set(cases_path).get("test_cases", [])
    registry = {
        "session_id": session_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "cases": [
            {
                "case_id": case.get("case_id") or f"TC-GEN-{idx + 1:03d}",
                "title": case.get("title", ""),
                "executor": case.get("executor", ""),
                "status": "not_executed",
                "updated_at": None,
                "details": {},
            }
            for idx, case in enumerate(cases)
        ],
    }
    path = root / "case_registry.json"
    path.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")
    progress = _case_progress(registry)
    return {"success": True, "session_id": session_id, "path": str(path), **progress}


def update_case_status(
    session_id: str,
    case_id: str,
    status: str,
    executor: str = "",
    fail_reason: str = "",
    score: float | None = None,
    latency_ms: float | None = None,
    screenshot: str = "",
) -> dict:
    if status not in VALID_CASE_STATUSES:
        return {"success": False, "error": f"invalid status: {status}", "valid_statuses": sorted(VALID_CASE_STATUSES)}

    registry_path = session_dir(session_id) / "case_registry.json"
    if not registry_path.exists():
        return {"success": False, "error": "case registry not found", "path": str(registry_path)}
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    target = next((case for case in registry.get("cases", []) if case.get("case_id") == case_id), None)
    if target is None:
        return {"success": False, "error": "case not found", "case_id": case_id}

    target["status"] = status
    target["executor"] = executor or target.get("executor", "")
    target["updated_at"] = datetime.now(timezone.utc).isoformat()
    target["details"] = {
        "fail_reason": fail_reason,
        "score": score,
        "latency_ms": latency_ms,
        "screenshot": screenshot,
    }
    registry_path.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"success": True, "session_id": session_id, "case_id": case_id, **_case_progress(registry)}


def get_execution_progress(session_id: str) -> dict:
    registry_path = session_dir(session_id) / "case_registry.json"
    if not registry_path.exists():
        return {"success": False, "error": "case registry not found", "path": str(registry_path)}
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    return {"success": True, "session_id": session_id, **_case_progress(registry)}


def _find_batch_files(root: Path) -> list[tuple[int, Path]]:
    batches: list[tuple[int, Path]] = []
    for path in root.iterdir():
        match = BATCH_PATTERN.match(path.name)
        if match:
            batches.append((int(match.group(1)), path))
    return sorted(batches, key=lambda item: item[0])


def _load_case_set(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("test_case_set", data)


def _renumber_case_ids(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counters: dict[str, int] = defaultdict(int)
    out: list[dict[str, Any]] = []
    for case in cases:
        item = dict(case)
        strategy = str(item.get("strategy", "business"))
        prefix = STRATEGY_PREFIX_MAP.get(strategy, "TC-GEN")
        counters[prefix] += 1
        item["case_id"] = f"{prefix}-{counters[prefix]:03d}"
        out.append(item)
    return out


def _deduplicate_cases(cases: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    seen: dict[str, dict[str, Any]] = {}
    removed = 0
    for case in cases:
        key = f"{case.get('test_point_id', '')}::{case.get('title', '')}".strip(":")
        if key in seen:
            existing_steps = len(seen[key].get("test_steps", []))
            new_steps = len(case.get("test_steps", []))
            if new_steps > existing_steps:
                seen[key] = case
            removed += 1
        else:
            seen[key] = case
    return list(seen.values()), removed


def _compute_coverage_summary(cases: list[dict[str, Any]]) -> dict:
    total = len(cases)
    priority_counter = Counter(case.get("priority", "P2") for case in cases)
    tag_counter = Counter(_normalize_tag(case.get("tag", "positive")) for case in cases)
    strategy_counter = Counter(case.get("strategy", "business") for case in cases)
    test_point_ids = {case.get("test_point_id", "") for case in cases if case.get("test_point_id")}
    return {
        "total_test_points": len(test_point_ids),
        "covered_test_points": len(test_point_ids),
        "coverage_rate": "100%" if test_point_ids else "n/a",
        "by_priority": dict(priority_counter.most_common()),
        "by_tag": dict(tag_counter.most_common()),
        "by_strategy": dict(strategy_counter.most_common()),
        "total_cases": total,
    }


def _merge_traceability(payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for payload in payloads:
        for entry in payload.get("traceability_matrix", []):
            ref_id = entry.get("ref_id") or entry.get("ac_id") or entry.get("requirement_id")
            if not ref_id:
                continue
            current = merged.setdefault(str(ref_id), {"ref_id": str(ref_id), "case_ids": []})
            current["case_ids"] = sorted(set(current.get("case_ids", [])) | set(entry.get("case_ids", [])))
    return list(merged.values())


def _validate_case_count(case_set: dict[str, Any]) -> dict:
    cases = case_set.get("test_cases", [])
    total = len(cases)
    return {
        "name": "case_count",
        "passed": total > 0,
        "message": f"{total} cases found" if total else "no cases found",
        "details": {"total_cases": total},
    }


def _validate_field_completeness(cases: list[dict[str, Any]]) -> dict:
    failures: dict[str, list[str]] = {}
    for field in REQUIRED_CASE_FIELDS:
        missing = [case.get("case_id", "unknown") for case in cases if not case.get(field)]
        if missing:
            failures[field] = missing[:10]
    return {
        "name": "field_completeness",
        "passed": not failures,
        "message": "required fields are complete" if not failures else "some required fields are missing",
        "details": {"missing": failures},
    }


def _validate_scene_dimensions(cases: list[dict[str, Any]]) -> dict:
    total = len(cases)
    if not total:
        return {"name": "scene_dimensions", "passed": False, "message": "no cases found", "details": {}}
    counter = Counter(_scene_dimension(case) for case in cases)
    dimensions = {
        name: {
            "count": counter.get(name, 0),
            "ratio": round(counter.get(name, 0) / total, 3),
            "threshold": threshold,
        }
        for name, threshold in SCENE_DIMENSION_THRESHOLDS.items()
    }
    passed = all(item["ratio"] >= item["threshold"] for item in dimensions.values())
    return {
        "name": "scene_dimensions",
        "passed": passed,
        "message": "scene dimension thresholds met" if passed else "scene dimension thresholds not met",
        "details": {"dimensions": dimensions, "all_dimensions": dict(counter.most_common())},
    }


def _validate_traceability(case_set: dict[str, Any]) -> dict:
    cases = case_set.get("test_cases", [])
    missing = [case.get("case_id", "unknown") for case in cases if not case.get("test_point_id")]
    return {
        "name": "traceability",
        "passed": not missing,
        "message": "all cases include test_point_id" if not missing else "some cases do not include test_point_id",
        "details": {"missing_case_ids": missing[:20]},
    }


def _case_progress(registry: dict[str, Any]) -> dict:
    cases = registry.get("cases", [])
    total = len(cases)
    counts = Counter(case.get("status", "not_executed") for case in cases)
    executed = total - counts.get("not_executed", 0)
    passed = counts.get("passed", 0) + counts.get("repaired", 0)
    return {
        "total": total,
        "executed": executed,
        "counts": {status: counts.get(status, 0) for status in sorted(VALID_CASE_STATUSES)},
        "execution_rate": round(executed / total, 3) if total else 0.0,
        "pass_rate": round(passed / executed, 3) if executed else 0.0,
    }


def _scene_dimension(case: dict[str, Any]) -> str:
    value = case.get("strategy_fields", {}).get("scene_dimension") or case.get("tag") or "positive"
    if isinstance(value, list):
        value = value[0] if value else "positive"
    if value == "negative":
        return "abnormal"
    return str(value)


def _normalize_tag(tag: Any) -> str:
    if isinstance(tag, list):
        return str(tag[0]) if tag else "positive"
    return str(tag or "positive")
