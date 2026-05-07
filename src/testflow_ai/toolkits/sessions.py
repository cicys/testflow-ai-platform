from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from testflow_ai.core.paths import eval_home


def toolkit_home() -> Path:
    return eval_home() / "toolkit_sessions"


def session_dir(session_id: str) -> Path:
    return toolkit_home() / _safe_name(session_id)


def create_session(project_name: str = "default") -> dict:
    safe_project = _safe_name(project_name)[:60] or "default"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    sid = f"{safe_project}_{timestamp}"
    root = session_dir(sid)
    root.mkdir(parents=True, exist_ok=True)
    metadata = {
        "session_id": sid,
        "project_name": project_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "created",
    }
    (root / "session.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return {"session_id": sid, "path": str(root), "metadata": metadata}


def list_sessions(limit: int = 20) -> dict:
    root = toolkit_home()
    if not root.exists():
        return {"sessions": []}
    sessions: list[dict] = []
    for entry in sorted(root.iterdir(), reverse=True):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        metadata_path = entry / "session.json"
        metadata: dict[str, Any] = {"session_id": entry.name}
        if metadata_path.exists():
            metadata.update(json.loads(metadata_path.read_text(encoding="utf-8")))
        artifacts = [p.name for p in entry.iterdir() if p.is_file() and p.name != "session.json"]
        metadata["path"] = str(entry)
        metadata["artifact_count"] = len(artifacts)
        metadata["artifacts"] = artifacts[:20]
        sessions.append(metadata)
        if len(sessions) >= limit:
            break
    return {"sessions": sessions}


def write_artifact(session_id: str, artifact_name: str, content: dict | list | str) -> dict:
    root = session_dir(session_id)
    root.mkdir(parents=True, exist_ok=True)
    target = root / _safe_artifact_name(artifact_name)
    if isinstance(content, (dict, list)):
        target.write_text(json.dumps(content, indent=2, ensure_ascii=False), encoding="utf-8")
    else:
        target.write_text(str(content), encoding="utf-8")
    return {"success": True, "session_id": session_id, "path": str(target)}


def read_artifact(session_id: str, artifact_name: str) -> dict:
    target = session_dir(session_id) / _safe_artifact_name(artifact_name)
    if not target.exists():
        return {"success": False, "error": "artifact not found", "path": str(target)}
    if target.suffix == ".json":
        return {"success": True, "path": str(target), "content": json.loads(target.read_text(encoding="utf-8"))}
    return {"success": True, "path": str(target), "content": target.read_text(encoding="utf-8")}


def _safe_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return value.strip("._-") or "default"


def _safe_artifact_name(value: str) -> str:
    name = value.replace("\\", "/").split("/")[-1].strip()
    if not name or name in {".", ".."}:
        raise ValueError("artifact_name must resolve to a file name")
    return name
