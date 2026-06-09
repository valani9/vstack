"""SQLite-backed findings store."""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence


@dataclass
class FindingRecord:
    """One stored finding."""

    id: int | None = None
    run_id: str = ""
    agent_id: str = ""
    pattern: str = ""
    severity: str = "low"
    confidence: float = 0.0
    title: str = ""
    intervention: str = ""
    timestamp: float = 0.0
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "agent_id": self.agent_id,
            "pattern": self.pattern,
            "severity": self.severity,
            "confidence": self.confidence,
            "title": self.title,
            "intervention": self.intervention,
            "timestamp": self.timestamp,
            "extras": dict(self.extras),
        }


_SCHEMA = """
CREATE TABLE IF NOT EXISTS findings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      TEXT,
    agent_id    TEXT,
    pattern     TEXT,
    severity    TEXT,
    confidence  REAL,
    title       TEXT,
    intervention TEXT,
    timestamp   REAL,
    extras_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_findings_pattern    ON findings (pattern);
CREATE INDEX IF NOT EXISTS idx_findings_severity   ON findings (severity);
CREATE INDEX IF NOT EXISTS idx_findings_agent      ON findings (agent_id);
CREATE INDEX IF NOT EXISTS idx_findings_timestamp  ON findings (timestamp);
CREATE INDEX IF NOT EXISTS idx_findings_run        ON findings (run_id);
"""


def _get_findings(report: Any) -> list[Any]:
    if isinstance(report, dict):
        return list(report.get("findings", []))
    if hasattr(report, "findings"):
        return list(report.findings)
    if isinstance(report, list):
        return list(report)
    return []


def _f(finding: Any, field: str, default: Any = "") -> Any:
    if isinstance(finding, dict):
        return finding.get(field, default)
    return getattr(finding, field, default)


class FindingsDB:
    """SQLite-backed finding store."""

    def __init__(self, path: str | Path = ":memory:"):
        self.path = str(path)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        for stmt in _SCHEMA.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                self._conn.execute(stmt)
        self._conn.commit()

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except sqlite3.Error:
                pass
            self._conn = None  # type: ignore[assignment]

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    def __enter__(self) -> FindingsDB:
        return self

    def __exit__(self, *_args) -> None:
        self.close()

    def store_finding(
        self,
        *,
        finding: Any,
        run_id: str = "",
        agent_id: str = "",
        timestamp: float | None = None,
    ) -> int:
        ts = timestamp if timestamp is not None else time.time()
        pattern = _f(finding, "pattern", "")
        severity = _f(finding, "severity", "low")
        confidence = float(_f(finding, "confidence", 0.0) or 0.0)
        title = _f(finding, "title", "")
        intervention = _f(finding, "intervention", "")

        extras = {}
        if isinstance(finding, dict):
            extras = {
                k: v
                for k, v in finding.items()
                if k not in {"pattern", "severity", "confidence", "title", "intervention"}
            }

        cursor = self._conn.execute(
            """INSERT INTO findings
            (run_id, agent_id, pattern, severity, confidence, title,
             intervention, timestamp, extras_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id,
                agent_id,
                pattern,
                severity,
                confidence,
                title,
                intervention,
                ts,
                json.dumps(extras, default=str),
            ),
        )
        self._conn.commit()
        return int(cursor.lastrowid or 0)

    def store_report(
        self,
        *,
        report: Any,
        run_id: str = "",
        agent_id: str = "",
        timestamp: float | None = None,
    ) -> list[int]:
        """Store all findings from a report; return their IDs."""
        ids = []
        for finding in _get_findings(report):
            ids.append(
                self.store_finding(
                    finding=finding,
                    run_id=run_id,
                    agent_id=agent_id,
                    timestamp=timestamp,
                )
            )
        return ids

    def find(
        self,
        *,
        pattern: str | Sequence[str] | None = None,
        severity: str | Sequence[str] | None = None,
        agent_id: str | None = None,
        run_id: str | None = None,
        since_ts: float | None = None,
        until_ts: float | None = None,
        limit: int = 1000,
    ) -> list[FindingRecord]:
        """Query findings with optional filters."""
        conditions = []
        params: list[Any] = []

        if pattern is not None:
            if isinstance(pattern, str):
                conditions.append("pattern = ?")
                params.append(pattern)
            else:
                placeholders = ",".join("?" * len(pattern))
                conditions.append(f"pattern IN ({placeholders})")
                params.extend(pattern)

        if severity is not None:
            if isinstance(severity, str):
                conditions.append("severity = ?")
                params.append(severity)
            else:
                placeholders = ",".join("?" * len(severity))
                conditions.append(f"severity IN ({placeholders})")
                params.extend(severity)

        if agent_id is not None:
            conditions.append("agent_id = ?")
            params.append(agent_id)

        if run_id is not None:
            conditions.append("run_id = ?")
            params.append(run_id)

        if since_ts is not None:
            conditions.append("timestamp >= ?")
            params.append(since_ts)

        if until_ts is not None:
            conditions.append("timestamp <= ?")
            params.append(until_ts)

        where = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT * FROM findings WHERE {where} ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        records = []
        for row in self._conn.execute(sql, params).fetchall():
            extras = {}
            if row["extras_json"]:
                try:
                    extras = json.loads(row["extras_json"])
                except json.JSONDecodeError:
                    extras = {}
            records.append(
                FindingRecord(
                    id=row["id"],
                    run_id=row["run_id"] or "",
                    agent_id=row["agent_id"] or "",
                    pattern=row["pattern"] or "",
                    severity=row["severity"] or "low",
                    confidence=row["confidence"] or 0.0,
                    title=row["title"] or "",
                    intervention=row["intervention"] or "",
                    timestamp=row["timestamp"] or 0.0,
                    extras=extras,
                )
            )
        return records

    def count_by(
        self,
        *,
        group_by: str = "pattern",
        since_ts: float | None = None,
    ) -> dict[str, int]:
        """Count findings grouped by a column."""
        if group_by not in {"pattern", "severity", "agent_id", "run_id"}:
            raise ValueError(
                f"group_by must be one of pattern/severity/agent_id/run_id, got {group_by}"
            )

        params: list[Any] = []
        where = "1=1"
        if since_ts is not None:
            where = "timestamp >= ?"
            params.append(since_ts)

        sql = f"SELECT {group_by} AS key, COUNT(*) AS n FROM findings WHERE {where} GROUP BY {group_by}"
        result = {}
        for row in self._conn.execute(sql, params).fetchall():
            result[row["key"] or ""] = int(row["n"])
        return result

    def delete_all(self) -> int:
        """Delete all findings. Returns count deleted."""
        cursor = self._conn.execute("DELETE FROM findings")
        self._conn.commit()
        return cursor.rowcount

    def total_count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS n FROM findings").fetchone()
        return int(row["n"])

    def vacuum(self) -> None:
        """Reclaim space."""
        self._conn.execute("VACUUM")
