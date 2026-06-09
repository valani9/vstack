"""Tests for intervention_tracker module."""

from __future__ import annotations

import pytest

from vstack.intervention_tracker import (
    Intervention,
    InterventionOutcome,
    InterventionTracker,
    OutcomeStats,
)


def _finding(pattern="yerkes_dodson", severity="high"):
    return {"pattern": pattern, "severity": severity, "title": "test"}


class TestInterventionRecording:
    def test_record_returns_intervention(self):
        t = InterventionTracker()
        iv = t.record(title="test", finding=_finding(), applied_by="alice")
        assert isinstance(iv, Intervention)
        assert iv.title == "test"
        assert iv.applied_by == "alice"

    def test_id_auto_assigned(self):
        t = InterventionTracker()
        iv1 = t.record(title="a")
        iv2 = t.record(title="b")
        assert iv1.id != iv2.id

    def test_pattern_extracted_from_finding(self):
        t = InterventionTracker()
        iv = t.record(title="test", finding=_finding(pattern="lewin"))
        assert iv.pattern == "lewin"

    def test_severity_extracted(self):
        t = InterventionTracker()
        iv = t.record(title="test", finding=_finding(severity="medium"))
        assert iv.severity_at_apply == "medium"

    def test_initial_outcome_pending(self):
        t = InterventionTracker()
        iv = t.record(title="test")
        assert iv.outcome == InterventionOutcome.PENDING

    def test_applied_at_set(self):
        t = InterventionTracker()
        iv = t.record(title="test", applied_at=12345.0)
        assert iv.applied_at == 12345.0

    def test_metadata_propagated(self):
        t = InterventionTracker()
        iv = t.record(title="test", metadata={"jira": "PLAT-123"})
        assert iv.metadata["jira"] == "PLAT-123"


class TestSetOutcome:
    def test_set_to_resolved(self):
        t = InterventionTracker()
        iv = t.record(title="x")
        t.set_outcome(iv.id, InterventionOutcome.RESOLVED, notes="great")
        assert iv.outcome == InterventionOutcome.RESOLVED
        assert iv.outcome_notes == "great"
        assert iv.outcome_set_at is not None

    def test_set_to_rolled_back_captures_reason(self):
        t = InterventionTracker()
        iv = t.record(title="x")
        t.set_outcome(
            iv.id,
            InterventionOutcome.ROLLED_BACK,
            rollback_reason="broke prod",
        )
        assert iv.rollback_reason == "broke prod"

    def test_set_outcome_unknown_id_raises(self):
        t = InterventionTracker()
        with pytest.raises(KeyError):
            t.set_outcome("unknown", InterventionOutcome.RESOLVED)


class TestQuery:
    def test_all(self):
        t = InterventionTracker()
        t.record(title="a")
        t.record(title="b")
        assert len(t.all()) == 2

    def test_by_pattern(self):
        t = InterventionTracker()
        t.record(title="a", finding=_finding(pattern="lewin"))
        t.record(title="b", finding=_finding(pattern="aar"))
        lewin = t.by_pattern("lewin")
        assert len(lewin) == 1
        assert lewin[0].title == "a"

    def test_by_applied_by(self):
        t = InterventionTracker()
        t.record(title="a", applied_by="alice")
        t.record(title="b", applied_by="bob")
        alice = t.by_applied_by("alice")
        assert len(alice) == 1

    def test_pending(self):
        t = InterventionTracker()
        iv1 = t.record(title="a")
        iv2 = t.record(title="b")
        t.set_outcome(iv1.id, InterventionOutcome.RESOLVED)
        pending = t.pending()
        assert len(pending) == 1
        assert pending[0].id == iv2.id

    def test_closed(self):
        t = InterventionTracker()
        iv1 = t.record(title="a")
        t.record(title="b")
        t.set_outcome(iv1.id, InterventionOutcome.RESOLVED)
        closed = t.closed()
        assert len(closed) == 1


class TestStats:
    def test_empty_stats(self):
        t = InterventionTracker()
        s = t.stats()
        assert s.total == 0
        assert s.effectiveness == 0.0

    def test_stats_count_outcomes(self):
        t = InterventionTracker()
        for _ in range(3):
            iv = t.record(title="a")
            t.set_outcome(iv.id, InterventionOutcome.RESOLVED)
        for _ in range(2):
            iv = t.record(title="a")
            t.set_outcome(iv.id, InterventionOutcome.NO_EFFECT)
        s = t.stats()
        assert s.resolved == 3
        assert s.no_effect == 2

    def test_stats_by_pattern(self):
        t = InterventionTracker()
        iv1 = t.record(title="a", finding=_finding(pattern="lewin"))
        iv2 = t.record(title="b", finding=_finding(pattern="aar"))
        t.set_outcome(iv1.id, InterventionOutcome.RESOLVED)
        t.set_outcome(iv2.id, InterventionOutcome.NO_EFFECT)
        s_lewin = t.stats(pattern="lewin")
        assert s_lewin.resolved == 1
        s_aar = t.stats(pattern="aar")
        assert s_aar.no_effect == 1

    def test_effectiveness_perfect(self):
        t = InterventionTracker()
        iv = t.record(title="x", finding=_finding(pattern="lewin"))
        t.set_outcome(iv.id, InterventionOutcome.RESOLVED)
        score = t.effectiveness_score("lewin")
        assert score == 1.0

    def test_effectiveness_partial_counts_half(self):
        t = InterventionTracker()
        iv1 = t.record(title="a", finding=_finding(pattern="lewin"))
        iv2 = t.record(title="b", finding=_finding(pattern="lewin"))
        t.set_outcome(iv1.id, InterventionOutcome.PARTIAL)
        t.set_outcome(iv2.id, InterventionOutcome.PARTIAL)
        # 2 closed, 2 partials = (0 + 0.5*2)/2 = 0.5.
        score = t.effectiveness_score("lewin")
        assert score == 0.5

    def test_effectiveness_excludes_pending(self):
        t = InterventionTracker()
        t.record(title="x", finding=_finding(pattern="lewin"))
        # Pending intervention; closed=0; effectiveness should be 0.
        score = t.effectiveness_score("lewin")
        assert score == 0.0


class TestRankPatterns:
    def test_rank_by_effectiveness(self):
        t = InterventionTracker()
        iv1 = t.record(title="a", finding=_finding(pattern="lewin"))
        iv2 = t.record(title="b", finding=_finding(pattern="aar"))
        iv3 = t.record(title="c", finding=_finding(pattern="aar"))
        t.set_outcome(iv1.id, InterventionOutcome.RESOLVED)
        t.set_outcome(iv2.id, InterventionOutcome.NO_EFFECT)
        t.set_outcome(iv3.id, InterventionOutcome.NO_EFFECT)
        ranked = t.rank_patterns_by_effectiveness()
        assert ranked[0][0] == "lewin"
        assert ranked[0][1] == 1.0


class TestTerminalProperty:
    def test_pending_not_terminal(self):
        t = InterventionTracker()
        iv = t.record(title="x")
        assert not iv.is_terminal

    def test_resolved_terminal(self):
        t = InterventionTracker()
        iv = t.record(title="x")
        t.set_outcome(iv.id, InterventionOutcome.RESOLVED)
        assert iv.is_terminal

    def test_rolled_back_terminal(self):
        t = InterventionTracker()
        iv = t.record(title="x")
        t.set_outcome(iv.id, InterventionOutcome.ROLLED_BACK)
        assert iv.is_terminal


class TestSerialization:
    def test_to_dict(self):
        t = InterventionTracker()
        t.record(title="a")
        t.record(title="b")
        data = t.to_dict()
        assert "interventions" in data
        assert len(data["interventions"]) == 2
        assert "stats_overall" in data

    def test_intervention_to_dict(self):
        t = InterventionTracker()
        iv = t.record(title="x")
        data = iv.to_dict()
        assert data["title"] == "x"
        assert data["outcome"] == "pending"

    def test_outcome_stats_to_dict(self):
        s = OutcomeStats(total=10, resolved=5, no_effect=3, partial=2)
        data = s.to_dict()
        assert data["total"] == 10
        assert "effectiveness" in data
