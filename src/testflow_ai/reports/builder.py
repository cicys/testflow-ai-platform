from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def summarize_run_artifacts(run_root: Path) -> dict[str, Any]:
    """Read a TestFlow run directory and return report-ready summary data."""
    if not run_root.exists():
        return {"success": False, "error": "run artifact root not found", "path": str(run_root)}

    summary = _read_json(run_root / "summary.json")
    manifest = _read_json(run_root / "manifest.json")
    predictions = _read_jsonl(run_root / "predictions.jsonl")
    failed_predictions = [item for item in predictions if _prediction_failed(item)]
    computed_total = len(predictions)
    total = _int_or(summary.get("num_predictions"), computed_total)
    failed = _int_or(summary.get("failed"), len(failed_predictions))
    passed = _int_or(summary.get("passed"), max(total - failed, 0))
    metrics = summary.get("metrics") if isinstance(summary.get("metrics"), dict) else {}

    return {
        "success": True,
        "kind": "run",
        "path": str(run_root),
        "run_id": summary.get("run_id") or manifest.get("run_id") or run_root.name,
        "executor_type": summary.get("executor_type") or manifest.get("executor_type", ""),
        "dataset_version_id": manifest.get("dataset_version_id"),
        "status": summary.get("status", "unknown"),
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": _rate(passed, total),
        "metrics": metrics,
        "duration_ms": summary.get("duration_ms"),
        "logs": _relative_logs(run_root),
        "failed_samples": [_sample_failure(item) for item in failed_predictions[:20]],
        "summary": summary,
    }


def render_run_markdown(run_root: Path, title: str | None = None) -> str:
    report = summarize_run_artifacts(run_root)
    if not report.get("success"):
        return f"# TestFlow Run Report\n\nFailed to load run artifacts: {report.get('error')}\n"

    title = title or f"TestFlow Run Report: {report['run_id']}"
    lines = [
        f"# {title}",
        "",
        f"- Generated at: {_now_iso()}",
        f"- Run ID: `{report['run_id']}`",
        f"- Executor: `{report['executor_type']}`",
        f"- Status: `{report['status']}`",
        f"- Total samples: {report['total']}",
        f"- Passed: {report['passed']}",
        f"- Failed: {report['failed']}",
        f"- Pass rate: {_pct(report['pass_rate'])}",
    ]
    if report.get("dataset_version_id"):
        lines.append(f"- Dataset version: `{report['dataset_version_id']}`")
    if report.get("duration_ms") is not None:
        lines.append(f"- Duration: {report['duration_ms']} ms")

    lines.extend(["", "## Metrics", ""])
    metrics = report.get("metrics") or {}
    if metrics:
        lines.extend(["| Metric | Value |", "|---|---|"])
        for name, value in sorted(metrics.items()):
            lines.append(f"| `{name}` | {_md_value(value)} |")
    else:
        lines.append("No metrics were recorded.")

    lines.extend(["", "## Failed Samples", ""])
    failed_samples = report.get("failed_samples") or []
    if failed_samples:
        lines.extend(["| Sample | Status | Error |", "|---|---|---|"])
        for sample in failed_samples:
            lines.append(
                f"| `{_escape_pipe(sample['sample_id'])}` | "
                f"`{_escape_pipe(sample['status'])}` | "
                f"{_escape_pipe(sample['error'])} |"
            )
    else:
        lines.append("No failed samples were found.")

    lines.extend(["", "## Artifacts", ""])
    logs = report.get("logs") or []
    if logs:
        for log in logs:
            lines.append(f"- `{log}`")
    else:
        lines.append("No log files were found.")
    lines.append("")
    return "\n".join(lines)


def build_run_report(run_root: Path, output_path: Path | None = None, title: str | None = None) -> dict[str, Any]:
    """Build and write a Markdown report for a run artifact directory."""
    markdown = render_run_markdown(run_root, title=title)
    output = output_path or run_root / "report.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown, encoding="utf-8")
    summary = summarize_run_artifacts(run_root)
    return {
        "success": summary.get("success", False),
        "kind": "run",
        "path": str(output),
        "summary": _public_summary(summary),
        "report_preview": markdown[:3000],
    }


def summarize_session_artifacts(session_root: Path) -> dict[str, Any]:
    """Summarize a toolkit session directory and its case registry."""
    if not session_root.exists():
        return {"success": False, "error": "session not found", "path": str(session_root)}
    metadata = _read_json(session_root / "session.json")
    registry = _read_json(session_root / "case_registry.json")
    cases = registry.get("cases", []) if isinstance(registry.get("cases"), list) else []
    counts = Counter(str(case.get("status", "not_executed")) for case in cases)
    total = len(cases)
    executed = total - counts.get("not_executed", 0)
    passed = counts.get("passed", 0) + counts.get("repaired", 0)
    failed = counts.get("failed", 0)
    blocked = counts.get("blocked", 0)
    skipped = counts.get("skipped", 0)

    return {
        "success": True,
        "kind": "session",
        "path": str(session_root),
        "session_id": metadata.get("session_id") or session_root.name,
        "project_name": metadata.get("project_name", ""),
        "status": metadata.get("status", "unknown"),
        "total": total,
        "executed": executed,
        "passed": passed,
        "failed": failed,
        "blocked": blocked,
        "skipped": skipped,
        "execution_rate": _rate(executed, total),
        "pass_rate": _rate(passed, executed),
        "counts": dict(sorted(counts.items())),
        "failed_cases": [_case_failure(case) for case in cases if str(case.get("status")) in {"failed", "blocked"}][:30],
        "artifacts": sorted(path.name for path in session_root.iterdir() if path.is_file()),
    }


def render_session_markdown(session_root: Path, title: str | None = None) -> str:
    report = summarize_session_artifacts(session_root)
    if not report.get("success"):
        return f"# TestFlow Session Report\n\nFailed to load session: {report.get('error')}\n"

    title = title or f"TestFlow Session Report: {report['session_id']}"
    lines = [
        f"# {title}",
        "",
        f"- Generated at: {_now_iso()}",
        f"- Session ID: `{report['session_id']}`",
        f"- Project: `{report['project_name']}`",
        f"- Status: `{report['status']}`",
        f"- Total cases: {report['total']}",
        f"- Executed cases: {report['executed']}",
        f"- Passed cases: {report['passed']}",
        f"- Failed cases: {report['failed']}",
        f"- Blocked cases: {report['blocked']}",
        f"- Skipped cases: {report['skipped']}",
        f"- Execution rate: {_pct(report['execution_rate'])}",
        f"- Pass rate: {_pct(report['pass_rate'])}",
        "",
        "## Status Distribution",
        "",
        "| Status | Count |",
        "|---|---:|",
    ]
    for status, count in report.get("counts", {}).items():
        lines.append(f"| `{status}` | {count} |")

    lines.extend(["", "## Failed Or Blocked Cases", ""])
    failed_cases = report.get("failed_cases") or []
    if failed_cases:
        lines.extend(["| Case | Status | Executor | Reason |", "|---|---|---|---|"])
        for case in failed_cases:
            lines.append(
                f"| `{_escape_pipe(case['case_id'])}` | "
                f"`{_escape_pipe(case['status'])}` | "
                f"`{_escape_pipe(case['executor'])}` | "
                f"{_escape_pipe(case['reason'])} |"
            )
    else:
        lines.append("No failed or blocked cases were found.")

    lines.extend(["", "## Session Artifacts", ""])
    for artifact in report.get("artifacts", []):
        lines.append(f"- `{artifact}`")
    lines.append("")
    return "\n".join(lines)


def build_session_report(session_root: Path, output_path: Path | None = None, title: str | None = None) -> dict[str, Any]:
    """Build and write a Markdown report for a toolkit session."""
    markdown = render_session_markdown(session_root, title=title)
    output = output_path or session_root / "test_report.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown, encoding="utf-8")
    summary = summarize_session_artifacts(session_root)
    return {
        "success": summary.get("success", False),
        "kind": "session",
        "path": str(output),
        "summary": _public_summary(summary),
        "report_preview": markdown[:3000],
    }


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            rows.append(data)
    return rows


def _prediction_failed(item: dict[str, Any]) -> bool:
    if item.get("error"):
        return True
    output = item.get("output")
    if isinstance(output, dict):
        status = str(output.get("status", "")).lower()
        return status in {"failed", "error", "blocked"}
    return False


def _sample_failure(item: dict[str, Any]) -> dict[str, str]:
    output = item.get("output") if isinstance(item.get("output"), dict) else {}
    return {
        "sample_id": str(item.get("sample_id", "")),
        "status": str(output.get("status", "failed")),
        "error": str(item.get("error") or output.get("error") or "failed assertion"),
    }


def _case_failure(case: dict[str, Any]) -> dict[str, str]:
    details = case.get("details") if isinstance(case.get("details"), dict) else {}
    return {
        "case_id": str(case.get("case_id", "")),
        "status": str(case.get("status", "")),
        "executor": str(case.get("executor", "")),
        "reason": str(details.get("fail_reason") or case.get("fail_reason") or ""),
    }


def _relative_logs(run_root: Path) -> list[str]:
    logs_root = run_root / "logs"
    if not logs_root.exists():
        return []
    return sorted(str(path.relative_to(run_root)) for path in logs_root.rglob("*") if path.is_file())


def _public_summary(summary: dict[str, Any]) -> dict[str, Any]:
    keep = (
        "kind",
        "run_id",
        "session_id",
        "executor_type",
        "status",
        "total",
        "executed",
        "passed",
        "failed",
        "blocked",
        "skipped",
        "pass_rate",
        "execution_rate",
    )
    return {key: summary[key] for key in keep if key in summary}


def _int_or(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 6)


def _pct(value: Any) -> str:
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return "n/a"


def _md_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return f"`{_escape_pipe(json.dumps(value, ensure_ascii=False, default=str))}`"
    return f"`{_escape_pipe(str(value))}`"


def _escape_pipe(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")[:500]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
