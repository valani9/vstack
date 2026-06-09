"""Tests for the aggregate module."""

from __future__ import annotations


from vstack.aggregate import (
    AggregateSummary,
    PatternStats,
    aggregate_reports,
    cooccurrence_matrix,
    severity_distribution,
    top_n_agents,
    top_n_patterns,
)


def _r(findings, agent_id="bot-1"):
    return {"findings": findings, "agent_id": agent_id}


def _f(pattern="lewin", severity="high"):
    return {"pattern": pattern, "severity": severity, "title": "x"}


class TestPatternStats:
    def test_severity_score(self):
        s = PatternStats(pattern="x", high=2, medium=3, low=4)
        # 2*3 + 3*2 + 4 = 6+6+4 = 16.
        assert s.severity_score == 16

    def test_to_dict(self):
        s = PatternStats(pattern="x", total=10)
        data = s.to_dict()
        assert data["pattern"] == "x"
        assert "severity_score" in data


class TestAggregateReports:
    def test_empty_input(self):
        summary = aggregate_reports([])
        assert summary.total_reports == 0
        assert summary.total_findings == 0
        assert summary.unique_patterns == 0

    def test_single_report(self):
        summary = aggregate_reports([_r([_f("lewin", "high")])])
        assert summary.total_reports == 1
        assert summary.total_findings == 1
        assert summary.unique_patterns == 1

    def test_pattern_stats_aggregated(self):
        reports = [
            _r([_f("lewin", "high"), _f("lewin", "low")]),
            _r([_f("lewin", "high")]),
        ]
        summary = aggregate_reports(reports)
        lewin = summary.pattern_stats["lewin"]
        assert lewin.total == 3
        assert lewin.high == 2
        assert lewin.low == 1

    def test_severity_counts(self):
        reports = [
            _r([_f(severity="high"), _f(severity="medium")]),
            _r([_f(severity="high")]),
        ]
        summary = aggregate_reports(reports)
        assert summary.severity_counts["high"] == 2
        assert summary.severity_counts["medium"] == 1

    def test_agent_counts(self):
        reports = [
            _r([_f(), _f()], agent_id="a"),
            _r([_f()], agent_id="b"),
        ]
        summary = aggregate_reports(reports)
        assert summary.agent_counts["a"] == 2
        assert summary.agent_counts["b"] == 1

    def test_top_patterns(self):
        reports = [_r([_f("lewin"), _f("lewin"), _f("aar")])]
        summary = aggregate_reports(reports)
        top = summary.top_patterns(n=2)
        assert top[0].pattern == "lewin"
        assert top[0].total == 2

    def test_to_dict(self):
        summary = aggregate_reports([_r([_f()])])
        data = summary.to_dict()
        assert "total_findings" in data
        assert "pattern_stats" in data


class TestTopNPatterns:
    def test_empty(self):
        assert top_n_patterns([]) == []

    def test_orders_by_frequency(self):
        reports = [
            _r([_f("a"), _f("b"), _f("a"), _f("a")]),
            _r([_f("b"), _f("c")]),
        ]
        top = top_n_patterns(reports, n=3)
        # a: 3, b: 2, c: 1
        assert top[0] == ("a", 3)
        assert top[1] == ("b", 2)

    def test_limit_respected(self):
        reports = [_r([_f("a"), _f("b"), _f("c"), _f("d")])]
        top = top_n_patterns(reports, n=2)
        assert len(top) == 2


class TestTopNAgents:
    def test_orders_by_finding_count(self):
        reports = [
            _r([_f(), _f(), _f()], agent_id="noisy"),
            _r([_f()], agent_id="quiet"),
        ]
        top = top_n_agents(reports)
        assert top[0][0] == "noisy"
        assert top[0][1] == 3

    def test_severity_filter(self):
        reports = [
            _r([_f(severity="high"), _f(severity="low")], agent_id="a"),
            _r([_f(severity="high")], agent_id="b"),
        ]
        top = top_n_agents(reports, severity="high")
        # Both have 1 high.
        assert dict(top)["a"] == 1
        assert dict(top)["b"] == 1


class TestSeverityDistribution:
    def test_empty(self):
        dist = severity_distribution([])
        assert dist["high"] == 0

    def test_counts(self):
        reports = [
            _r([_f(severity="high"), _f(severity="high"), _f(severity="medium")]),
            _r([_f(severity="low")]),
        ]
        dist = severity_distribution(reports)
        assert dist["high"] == 2
        assert dist["medium"] == 1
        assert dist["low"] == 1


class TestCooccurrenceMatrix:
    def test_no_cooccurrence(self):
        reports = [_r([_f("a")]), _r([_f("b")])]
        matrix = cooccurrence_matrix(reports)
        assert matrix == {}

    def test_pair_in_same_report(self):
        reports = [_r([_f("a"), _f("b")])]
        matrix = cooccurrence_matrix(reports)
        assert matrix[("a", "b")] == 1

    def test_repeated_pair_counts(self):
        reports = [
            _r([_f("a"), _f("b")]),
            _r([_f("a"), _f("b")]),
            _r([_f("c"), _f("d")]),
        ]
        matrix = cooccurrence_matrix(reports)
        assert matrix[("a", "b")] == 2

    def test_dedupes_within_report(self):
        # Multiple findings of same pattern in one report only count once.
        reports = [_r([_f("a"), _f("a"), _f("b")])]
        matrix = cooccurrence_matrix(reports)
        assert matrix[("a", "b")] == 1

    def test_triple_creates_pairs(self):
        reports = [_r([_f("a"), _f("b"), _f("c")])]
        matrix = cooccurrence_matrix(reports)
        assert matrix[("a", "b")] == 1
        assert matrix[("a", "c")] == 1
        assert matrix[("b", "c")] == 1


class TestAggregateSummary:
    def test_top_patterns_with_n_limit(self):
        summary = AggregateSummary(
            pattern_stats={
                "a": PatternStats(pattern="a", total=5),
                "b": PatternStats(pattern="b", total=3),
                "c": PatternStats(pattern="c", total=10),
            }
        )
        top = summary.top_patterns(n=2)
        assert len(top) == 2
        assert top[0].pattern == "c"
