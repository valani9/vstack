"""Tests for the priority_queue module."""

from __future__ import annotations


from vstack.priority_queue import FindingPriorityQueue, QueueEntry


def _f(pattern="lewin", severity="high", confidence=0.9):
    return {"pattern": pattern, "severity": severity, "confidence": confidence, "title": "x"}


class TestEmpty:
    def test_new_queue_empty(self):
        q = FindingPriorityQueue()
        assert q.is_empty()
        assert len(q) == 0

    def test_pop_empty_returns_none(self):
        q = FindingPriorityQueue()
        assert q.pop() is None

    def test_peek_empty_returns_none(self):
        q = FindingPriorityQueue()
        assert q.peek() is None


class TestBasicPushPop:
    def test_push_increases_length(self):
        q = FindingPriorityQueue()
        q.push(_f())
        assert len(q) == 1

    def test_pop_returns_finding(self):
        q = FindingPriorityQueue()
        q.push(_f())
        result = q.pop()
        assert result["pattern"] == "lewin"
        assert q.is_empty()

    def test_single_item_pop(self):
        q = FindingPriorityQueue()
        q.push(_f(pattern="solo"))
        assert q.pop()["pattern"] == "solo"


class TestSeverityOrdering:
    def test_high_pops_before_low(self):
        q = FindingPriorityQueue()
        q.push(_f(pattern="low", severity="low"))
        q.push(_f(pattern="high", severity="high"))
        # High pops first.
        assert q.pop()["pattern"] == "high"
        assert q.pop()["pattern"] == "low"

    def test_medium_pops_before_low(self):
        q = FindingPriorityQueue()
        q.push(_f(pattern="low", severity="low"))
        q.push(_f(pattern="medium", severity="medium"))
        assert q.pop()["pattern"] == "medium"

    def test_three_severities(self):
        q = FindingPriorityQueue()
        q.push(_f(pattern="lo", severity="low"))
        q.push(_f(pattern="me", severity="medium"))
        q.push(_f(pattern="hi", severity="high"))
        # High, medium, low.
        assert q.pop()["pattern"] == "hi"
        assert q.pop()["pattern"] == "me"
        assert q.pop()["pattern"] == "lo"


class TestConfidenceWeighting:
    def test_high_confidence_wins_within_severity(self):
        q = FindingPriorityQueue()
        q.push(_f(pattern="lowconf", severity="medium", confidence=0.1))
        q.push(_f(pattern="highconf", severity="medium", confidence=1.0))
        assert q.pop()["pattern"] == "highconf"


class TestAging:
    def test_old_low_severity_can_beat_new_low_severity(self):
        q = FindingPriorityQueue(aging_multiplier=10.0)
        # Push old low item.
        q.push(_f(pattern="old"), inserted_at=0.0)
        # Push new low item.
        q.push(_f(pattern="new"), inserted_at=100.0)
        # At now=100, old has 100s of aging = 100/3600 * 10 = ~0.28 boost.
        # Not enough to overtake within same severity, but verify aging applies.
        # Use a stronger differential.
        snapshot = q.snapshot(now=100.0)
        old_score = next(s for f, s in snapshot if f["pattern"] == "old")
        new_score = next(s for f, s in snapshot if f["pattern"] == "new")
        assert old_score > new_score

    def test_aging_boost_grows_with_time(self):
        q = FindingPriorityQueue(aging_multiplier=1.0)
        q.push(_f(pattern="x"), inserted_at=0.0)
        snap1 = q.snapshot(now=3600.0)  # +1 hour
        snap2 = q.snapshot(now=7200.0)  # +2 hours
        score1 = snap1[0][1]
        score2 = snap2[0][1]
        assert score2 > score1


class TestManualBoost:
    def test_manual_boost_overrides_severity(self):
        q = FindingPriorityQueue()
        q.push(_f(pattern="low", severity="low"), manual_boost=1000.0)
        q.push(_f(pattern="high", severity="high"))
        # Low + 1000 boost should beat high.
        assert q.pop()["pattern"] == "low"

    def test_boost_method(self):
        q = FindingPriorityQueue()
        q.push(_f(pattern="lewin", severity="low"))
        q.push(_f(pattern="aar", severity="medium"))
        n = q.boost("lewin", 100.0)
        assert n == 1
        # After boost, lewin should pop first.
        assert q.pop()["pattern"] == "lewin"

    def test_boost_multiple(self):
        q = FindingPriorityQueue()
        q.push(_f(pattern="lewin"))
        q.push(_f(pattern="lewin"))
        q.push(_f(pattern="aar"))
        n = q.boost("lewin", 1.0)
        assert n == 2


class TestPeek:
    def test_peek_does_not_remove(self):
        q = FindingPriorityQueue()
        q.push(_f(pattern="x"))
        q.peek()
        assert len(q) == 1

    def test_peek_matches_pop(self):
        q = FindingPriorityQueue()
        q.push(_f(pattern="low", severity="low"))
        q.push(_f(pattern="high", severity="high"))
        peek_result = q.peek()
        pop_result = q.pop()
        assert peek_result["pattern"] == pop_result["pattern"]


class TestRemove:
    def test_remove_pattern(self):
        q = FindingPriorityQueue()
        q.push(_f(pattern="x"))
        q.push(_f(pattern="x"))
        q.push(_f(pattern="y"))
        n = q.remove_pattern("x")
        assert n == 2
        assert len(q) == 1

    def test_remove_nonexistent(self):
        q = FindingPriorityQueue()
        q.push(_f(pattern="x"))
        n = q.remove_pattern("nonexistent")
        assert n == 0
        assert len(q) == 1


class TestClear:
    def test_clear_empties_queue(self):
        q = FindingPriorityQueue()
        for _ in range(5):
            q.push(_f())
        q.clear()
        assert q.is_empty()


class TestSnapshot:
    def test_snapshot_returns_all_entries(self):
        q = FindingPriorityQueue()
        q.push(_f(pattern="a"))
        q.push(_f(pattern="b"))
        q.push(_f(pattern="c"))
        snap = q.snapshot()
        assert len(snap) == 3

    def test_snapshot_ordered_by_score(self):
        q = FindingPriorityQueue()
        q.push(_f(pattern="low", severity="low"))
        q.push(_f(pattern="high", severity="high"))
        q.push(_f(pattern="medium", severity="medium"))
        snap = q.snapshot()
        # First should be high.
        assert snap[0][0]["pattern"] == "high"
        assert snap[-1][0]["pattern"] == "low"


class TestQueueEntry:
    def test_base_score_high(self):
        entry = QueueEntry(
            finding={"severity": "high", "confidence": 1.0},
            inserted_at=0.0,
        )
        # high * 1.0 (mult) = 100.
        assert entry.base_score() == 100.0

    def test_base_score_low_confidence(self):
        entry = QueueEntry(
            finding={"severity": "high", "confidence": 0.0},
            inserted_at=0.0,
        )
        # high * 0.5 = 50.
        assert entry.base_score() == 50.0

    def test_invalid_severity_defaults_to_low_weight(self):
        entry = QueueEntry(
            finding={"severity": "nonsense", "confidence": 1.0},
            inserted_at=0.0,
        )
        # Defaults to low (1.0) * 1.0 = 1.0.
        assert entry.base_score() == 1.0
