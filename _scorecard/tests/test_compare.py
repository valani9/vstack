"""Tests for scorecard comparison."""

from __future__ import annotations

from vstack.scorecard import (
    compare_scorecards,
    compute_scorecard,
)
from vstack.scorecard._compare import is_blocking_regression


def _make_finding(pattern: str, severity: str):
    return {
        "pattern": pattern,
        "severity": severity,
        "title": "test",
        "intervention": "fix it",
    }


def _make_report(findings: list[dict]) -> dict:
    return {"findings": findings}


class TestCompareScorecards:
    def test_no_change(self):
        sc1 = compute_scorecard(reports=[])
        sc2 = compute_scorecard(reports=[])
        comp = compare_scorecards(sc1, sc2)
        assert comp.overall_delta == 0.0
        assert not comp.has_regression
        assert not comp.has_improvement

    def test_clear_regression(self):
        sc1 = compute_scorecard(reports=[])  # perfect
        sc2 = compute_scorecard(
            reports=[
                _make_report([_make_finding("lewin", "high")]),
            ]
        )
        comp = compare_scorecards(sc1, sc2)
        assert comp.overall_delta < 0
        assert comp.has_regression

    def test_clear_improvement(self):
        sc1 = compute_scorecard(
            reports=[
                _make_report([_make_finding("lewin", "high")]),
            ]
        )
        sc2 = compute_scorecard(reports=[])
        comp = compare_scorecards(sc1, sc2)
        assert comp.overall_delta > 0
        assert comp.has_improvement

    def test_dimension_delta_score_correct(self):
        sc1 = compute_scorecard(reports=[])
        sc2 = compute_scorecard(
            reports=[
                _make_report([_make_finding("lewin", "high")]),
            ]
        )
        comp = compare_scorecards(sc1, sc2)
        reasoning = comp.dimension_deltas["reasoning"]
        assert reasoning.score_before == 100.0
        assert reasoning.score_after == 75.0
        assert reasoning.delta == -25.0
        assert reasoning.is_regression

    def test_grade_changed_flag(self):
        sc1 = compute_scorecard(reports=[])  # A+
        sc2 = compute_scorecard(
            reports=[
                _make_report([_make_finding("lewin", "high")]),
            ]
        )  # C+ for reasoning
        comp = compare_scorecards(sc1, sc2)
        assert comp.dimension_deltas["reasoning"].grade_changed

    def test_regressed_dimensions_filter(self):
        sc1 = compute_scorecard(reports=[])
        sc2 = compute_scorecard(
            reports=[
                _make_report([_make_finding("lewin", "high")]),
                _make_report([_make_finding("grpi", "high")]),
            ]
        )
        comp = compare_scorecards(sc1, sc2)
        regressed = comp.regressed_dimensions
        regressed_names = {d.name for d in regressed}
        assert "reasoning" in regressed_names
        assert "coordination" in regressed_names

    def test_to_markdown_runs(self):
        sc1 = compute_scorecard(reports=[])
        sc2 = compute_scorecard(
            reports=[
                _make_report([_make_finding("lewin", "high")]),
            ]
        )
        comp = compare_scorecards(sc1, sc2)
        md = comp.to_markdown()
        assert "Scorecard Comparison" in md

    def test_to_dict_serializes(self):
        sc1 = compute_scorecard(reports=[])
        sc2 = compute_scorecard(
            reports=[
                _make_report([_make_finding("lewin", "high")]),
            ]
        )
        comp = compare_scorecards(sc1, sc2)
        data = comp.to_dict()
        assert "overall_before" in data
        assert "overall_after" in data
        assert "dimension_deltas" in data
        assert "reasoning" in data["dimension_deltas"]


class TestNewAndRemovedPatterns:
    def test_new_pattern_detected(self):
        sc1 = compute_scorecard(
            reports=[
                _make_report([_make_finding("lewin", "high")]),
            ]
        )
        sc2 = compute_scorecard(
            reports=[
                _make_report([_make_finding("lewin", "high")]),
                _make_report([_make_finding("aar", "medium")]),
            ]
        )
        comp = compare_scorecards(sc1, sc2)
        assert "aar" in comp.new_patterns
        assert "lewin" not in comp.new_patterns

    def test_removed_pattern_detected(self):
        sc1 = compute_scorecard(
            reports=[
                _make_report([_make_finding("lewin", "high")]),
                _make_report([_make_finding("aar", "medium")]),
            ]
        )
        sc2 = compute_scorecard(
            reports=[
                _make_report([_make_finding("lewin", "high")]),
            ]
        )
        comp = compare_scorecards(sc1, sc2)
        assert "aar" in comp.removed_patterns


class TestIsBlockingRegression:
    def test_no_change_not_blocking(self):
        sc1 = compute_scorecard(reports=[])
        sc2 = compute_scorecard(reports=[])
        comp = compare_scorecards(sc1, sc2)
        assert not is_blocking_regression(comp)

    def test_huge_overall_drop_is_blocking(self):
        sc1 = compute_scorecard(reports=[])
        # Drop ALL dimensions to C+/C/F.
        sc2 = compute_scorecard(
            reports=[
                _make_report([_make_finding("lewin", "high")]),
                _make_report([_make_finding("grpi", "high")]),
                _make_report([_make_finding("trust_triangle", "high")]),
                _make_report([_make_finding("yerkes_dodson", "high")]),
                _make_report([_make_finding("schein_culture", "high")]),
            ]
        )
        comp = compare_scorecards(sc1, sc2)
        # Overall dropped 25 points; default score_threshold = 10.
        assert is_blocking_regression(comp)

    def test_dimension_drop_below_threshold_is_blocking(self):
        # Start with reasoning at A (above C threshold).
        sc1 = compute_scorecard(
            reports=[
                _make_report([_make_finding("lewin", "medium")]),
            ]
        )  # reasoning = 90 (A)

        # Drop reasoning below C.
        sc2 = compute_scorecard(
            reports=[
                _make_report(
                    [
                        _make_finding("lewin", "high"),
                        _make_finding("lewin", "high"),
                        _make_finding("lewin", "high"),
                    ]
                ),
            ]
        )  # reasoning = 25 (F)

        comp = compare_scorecards(sc1, sc2)
        # Should be blocking — reasoning crossed from A to F.
        assert is_blocking_regression(comp)
