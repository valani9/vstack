"""Tests for the findings_db module."""

from __future__ import annotations

from pathlib import Path

import pytest

from vstack.findings_db import FindingRecord, FindingsDB


def _f(pattern="lewin", severity="high", confidence=0.8, title=None, intervention=None):
    return {
        "pattern": pattern,
        "severity": severity,
        "confidence": confidence,
        "title": title or f"{pattern} finding",
        "intervention": intervention or f"fix {pattern}",
    }


def _r(findings):
    return {"findings": findings}


class TestStorage:
    def test_in_memory_db(self):
        db = FindingsDB()
        assert db.total_count() == 0

    def test_store_single_finding(self):
        db = FindingsDB()
        fid = db.store_finding(finding=_f(), run_id="r1", agent_id="a1")
        assert fid > 0
        assert db.total_count() == 1

    def test_store_report(self):
        db = FindingsDB()
        ids = db.store_report(
            report=_r([_f("lewin", "high"), _f("aar", "medium")]),
            run_id="r1",
            agent_id="a1",
        )
        assert len(ids) == 2
        assert db.total_count() == 2

    def test_persistent_db(self, tmp_path: Path):
        db_path = tmp_path / "findings.db"
        db1 = FindingsDB(db_path)
        db1.store_finding(finding=_f(), run_id="r1")
        db1.close()

        db2 = FindingsDB(db_path)
        assert db2.total_count() == 1
        db2.close()


class TestFind:
    def test_find_all(self):
        db = FindingsDB()
        db.store_finding(finding=_f("lewin", "high"))
        db.store_finding(finding=_f("aar", "medium"))
        results = db.find()
        assert len(results) == 2

    def test_find_by_pattern(self):
        db = FindingsDB()
        db.store_finding(finding=_f("lewin", "high"))
        db.store_finding(finding=_f("aar", "medium"))
        results = db.find(pattern="lewin")
        assert len(results) == 1
        assert results[0].pattern == "lewin"

    def test_find_by_multiple_patterns(self):
        db = FindingsDB()
        db.store_finding(finding=_f("lewin", "high"))
        db.store_finding(finding=_f("aar", "medium"))
        db.store_finding(finding=_f("grpi", "low"))
        results = db.find(pattern=["lewin", "aar"])
        assert len(results) == 2

    def test_find_by_severity(self):
        db = FindingsDB()
        db.store_finding(finding=_f("a", "high"))
        db.store_finding(finding=_f("b", "low"))
        results = db.find(severity="high")
        assert len(results) == 1

    def test_find_by_multiple_severities(self):
        db = FindingsDB()
        db.store_finding(finding=_f("a", "high"))
        db.store_finding(finding=_f("b", "medium"))
        db.store_finding(finding=_f("c", "low"))
        results = db.find(severity=["high", "medium"])
        assert len(results) == 2

    def test_find_by_agent(self):
        db = FindingsDB()
        db.store_finding(finding=_f(), agent_id="a1")
        db.store_finding(finding=_f(), agent_id="a2")
        results = db.find(agent_id="a1")
        assert len(results) == 1

    def test_find_by_run(self):
        db = FindingsDB()
        db.store_finding(finding=_f(), run_id="r1")
        db.store_finding(finding=_f(), run_id="r2")
        results = db.find(run_id="r1")
        assert len(results) == 1

    def test_find_by_timestamp_range(self):
        db = FindingsDB()
        db.store_finding(finding=_f(), timestamp=100.0)
        db.store_finding(finding=_f(), timestamp=200.0)
        db.store_finding(finding=_f(), timestamp=300.0)

        results = db.find(since_ts=150, until_ts=250)
        assert len(results) == 1

    def test_combined_filters(self):
        db = FindingsDB()
        db.store_finding(finding=_f("lewin", "high"), agent_id="a1")
        db.store_finding(finding=_f("lewin", "low"), agent_id="a1")
        db.store_finding(finding=_f("lewin", "high"), agent_id="a2")

        results = db.find(pattern="lewin", severity="high", agent_id="a1")
        assert len(results) == 1

    def test_limit(self):
        db = FindingsDB()
        for i in range(10):
            db.store_finding(finding=_f(), timestamp=float(i))
        results = db.find(limit=5)
        assert len(results) == 5

    def test_results_sorted_by_timestamp_desc(self):
        db = FindingsDB()
        db.store_finding(finding=_f(), timestamp=100.0)
        db.store_finding(finding=_f(), timestamp=300.0)
        db.store_finding(finding=_f(), timestamp=200.0)

        results = db.find()
        assert results[0].timestamp == 300.0
        assert results[1].timestamp == 200.0
        assert results[2].timestamp == 100.0


class TestCountBy:
    def test_count_by_pattern(self):
        db = FindingsDB()
        db.store_finding(finding=_f("lewin"))
        db.store_finding(finding=_f("lewin"))
        db.store_finding(finding=_f("aar"))

        counts = db.count_by(group_by="pattern")
        assert counts["lewin"] == 2
        assert counts["aar"] == 1

    def test_count_by_severity(self):
        db = FindingsDB()
        db.store_finding(finding=_f(severity="high"))
        db.store_finding(finding=_f(severity="high"))
        db.store_finding(finding=_f(severity="low"))

        counts = db.count_by(group_by="severity")
        assert counts["high"] == 2
        assert counts["low"] == 1

    def test_count_by_with_since_filter(self):
        db = FindingsDB()
        db.store_finding(finding=_f("a"), timestamp=100.0)
        db.store_finding(finding=_f("a"), timestamp=300.0)

        counts = db.count_by(group_by="pattern", since_ts=200.0)
        assert counts["a"] == 1

    def test_invalid_group_by_raises(self):
        db = FindingsDB()
        with pytest.raises(ValueError):
            db.count_by(group_by="invalid_field")


class TestDeleteAll:
    def test_delete_all(self):
        db = FindingsDB()
        db.store_finding(finding=_f())
        db.store_finding(finding=_f())
        assert db.total_count() == 2

        count = db.delete_all()
        assert count == 2
        assert db.total_count() == 0


class TestFindingRecord:
    def test_to_dict(self):
        rec = FindingRecord(
            id=1,
            run_id="r1",
            agent_id="a1",
            pattern="lewin",
            severity="high",
            confidence=0.9,
            title="x",
            intervention="fix",
            timestamp=100.0,
        )
        data = rec.to_dict()
        assert data["id"] == 1
        assert data["pattern"] == "lewin"


class TestContextManager:
    def test_context_manager_closes(self, tmp_path: Path):
        db_path = tmp_path / "findings.db"
        with FindingsDB(db_path) as db:
            db.store_finding(finding=_f())
        # After context exit, conn should be closed.
        # Re-open should still work.
        with FindingsDB(db_path) as db2:
            assert db2.total_count() == 1


class TestExtras:
    def test_extras_stored_and_retrieved(self):
        db = FindingsDB()
        finding = {
            "pattern": "lewin",
            "severity": "high",
            "title": "x",
            "intervention": "fix",
            "confidence": 0.8,
            "custom_field": "custom_value",
            "another": 42,
        }
        db.store_finding(finding=finding)
        results = db.find()
        assert results[0].extras["custom_field"] == "custom_value"
        assert results[0].extras["another"] == 42
