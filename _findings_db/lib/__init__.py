"""vstack.findings_db — SQLite-backed finding store.

A lightweight persistent store for findings emitted across many
diagnose() runs. Useful for:

  - **Historical analysis** — query findings over time.
  - **Drift detection** — compare today's findings to last week's.
  - **Filtering** — fetch findings by pattern / severity / agent.
  - **Aggregation** — count by pattern, severity, agent.

Backend: SQLite (built-in to Python). No external dependencies.

Quick start
-----------

    from vstack.findings_db import FindingsDB

    db = FindingsDB(path="findings.db")

    # Store findings from a report:
    db.store_report(
        report=report,
        agent_id="prod-bot-001",
        run_id="run-2026-06-09-01",
    )

    # Query:
    recent = db.find(
        pattern="lewin",
        severity=["high", "medium"],
        since_ts=1717891200,
    )

    # Aggregate:
    counts = db.count_by(group_by="pattern")
"""

from __future__ import annotations

from ._db import (
    FindingRecord,
    FindingsDB,
)

__all__ = [
    "FindingRecord",
    "FindingsDB",
]
