from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from testflow_ai.core.models import DatasetVersion, MetricResult, RunRecord, RunStatus


class Registry:
    """Small SQLite-backed ledger for local and CI runs."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._conn() as c:
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS dataset_versions (
                    id TEXT PRIMARY KEY,
                    label TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    meta_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    executor_type TEXT NOT NULL,
                    dataset_version_id TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    finished_at TEXT,
                    artifact_root TEXT NOT NULL DEFAULT '',
                    manifest_json TEXT NOT NULL DEFAULT '{}',
                    metrics_json TEXT NOT NULL DEFAULT '[]'
                );
                """
            )

    def upsert_dataset_version(self, dv: DatasetVersion) -> None:
        with self._conn() as c:
            c.execute(
                """INSERT OR REPLACE INTO dataset_versions (id, label, created_at, meta_json)
                   VALUES (?, ?, ?, ?)""",
                (
                    dv.id,
                    dv.label,
                    dv.created_at.isoformat(),
                    json.dumps(dv.meta, ensure_ascii=False),
                ),
            )

    def create_run(
        self,
        executor_type: str,
        dataset_version_id: str | None,
        artifact_root: str,
        manifest: dict[str, Any] | None = None,
    ) -> RunRecord:
        rid = str(uuid.uuid4())
        manifest = manifest or {}
        rec = RunRecord(
            id=rid,
            executor_type=executor_type,
            dataset_version_id=dataset_version_id,
            status=RunStatus.pending,
            artifact_root=artifact_root,
            manifest=manifest,
        )
        with self._conn() as c:
            c.execute(
                """INSERT INTO runs (id, executor_type, dataset_version_id, status,
                       created_at, finished_at, artifact_root, manifest_json, metrics_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    rec.id,
                    rec.executor_type,
                    rec.dataset_version_id,
                    rec.status.value,
                    rec.created_at.isoformat(),
                    None,
                    rec.artifact_root,
                    json.dumps(rec.manifest, ensure_ascii=False),
                    json.dumps([m.model_dump() for m in rec.metrics], ensure_ascii=False),
                ),
            )
        return rec

    def get_run(self, run_id: str) -> RunRecord | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_run(row)

    def update_run_status(self, run_id: str, status: RunStatus, finished: bool = False) -> None:
        from testflow_ai.core.models import utc_now

        fts = utc_now().isoformat() if finished else None
        with self._conn() as c:
            if finished:
                c.execute(
                    "UPDATE runs SET status = ?, finished_at = ? WHERE id = ?",
                    (status.value, fts, run_id),
                )
            else:
                c.execute("UPDATE runs SET status = ? WHERE id = ?", (status.value, run_id))

    def update_manifest(self, run_id: str, manifest: dict[str, Any]) -> None:
        with self._conn() as c:
            c.execute(
                "UPDATE runs SET manifest_json = ? WHERE id = ?",
                (json.dumps(manifest, ensure_ascii=False), run_id),
            )

    def update_artifact_root(self, run_id: str, artifact_root: str) -> None:
        with self._conn() as c:
            c.execute("UPDATE runs SET artifact_root = ? WHERE id = ?", (artifact_root, run_id))

    def update_metrics(self, run_id: str, metrics: list[MetricResult]) -> None:
        with self._conn() as c:
            c.execute(
                "UPDATE runs SET metrics_json = ? WHERE id = ?",
                (json.dumps([m.model_dump() for m in metrics], ensure_ascii=False), run_id),
            )

    def _row_to_run(self, row: sqlite3.Row) -> RunRecord:
        metrics_raw = json.loads(row["metrics_json"] or "[]")
        return RunRecord(
            id=row["id"],
            executor_type=row["executor_type"],
            dataset_version_id=row["dataset_version_id"],
            status=RunStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            finished_at=datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None,
            artifact_root=row["artifact_root"],
            manifest=json.loads(row["manifest_json"] or "{}"),
            metrics=[MetricResult(**m) for m in metrics_raw],
        )
