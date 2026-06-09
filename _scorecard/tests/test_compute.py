"""Tests for scorecard computation."""

from __future__ import annotations

from vstack.scorecard import (
    ScoreCardConfig,
    compute_scorecard,
)
from vstack.scorecard._compute import PATTERN_DIMENSIONS


def _make_finding(pattern: str, severity: str, title: str = "test finding"):
    """Build a dict-shaped finding (since compute_scorecard accepts dicts)."""
    return {
        "pattern": pattern,
        "severity": severity,
        "title": title,
        "intervention": f"Fix {pattern}",
    }


def _make_report(findings: list[dict]) -> dict:
    return {"findings": findings}


class TestComputeScorecard:
    def test_empty_reports_full_score(self):
        scorecard = compute_scorecard(reports=[])
        for dim in scorecard.dimensions.values():
            assert dim.score == 100.0
            assert dim.grade.letter == "A+"
        assert scorecard.overall_score == 100.0

    def test_single_high_finding_deducts_25(self):
        reports = [_make_report([_make_finding("lewin", "high")])]
        scorecard = compute_scorecard(reports=reports)
        reasoning = scorecard.dimensions["reasoning"]
        assert reasoning.score == 75.0  # 100 - 25
        assert reasoning.grade.letter == "C+"

    def test_single_medium_finding_deducts_10(self):
        reports = [_make_report([_make_finding("lewin", "medium")])]
        scorecard = compute_scorecard(reports=reports)
        reasoning = scorecard.dimensions["reasoning"]
        assert reasoning.score == 90.0
        assert reasoning.grade.letter == "A"

    def test_single_low_finding_deducts_3(self):
        reports = [_make_report([_make_finding("lewin", "low")])]
        scorecard = compute_scorecard(reports=reports)
        reasoning = scorecard.dimensions["reasoning"]
        assert reasoning.score == 97.0
        assert reasoning.grade.letter == "A+"

    def test_findings_capped_per_dimension(self):
        """Default cap is 5 findings per dimension."""
        # 10 high findings = capped at 5 * 25 = 125, clamped to 0.
        findings = [_make_finding("lewin", "high") for _ in range(10)]
        reports = [_make_report(findings)]
        scorecard = compute_scorecard(reports=reports)
        reasoning = scorecard.dimensions["reasoning"]
        # 100 - 5 * 25 = -25, clamped to 0.
        assert reasoning.score == 0.0
        assert reasoning.grade.letter == "F"

    def test_pattern_with_split_dimension_weights(self):
        """goleman_ei contributes 0.7 to trust + 0.3 to culture."""
        reports = [_make_report([_make_finding("goleman_ei", "high")])]
        scorecard = compute_scorecard(reports=reports)
        trust = scorecard.dimensions["trust"]
        culture = scorecard.dimensions["culture"]
        # 100 - 25 * 0.7 = 82.5 for trust.
        assert abs(trust.score - 82.5) < 0.1
        # 100 - 25 * 0.3 = 92.5 for culture.
        assert abs(culture.score - 92.5) < 0.1

    def test_multiple_patterns_same_dimension(self):
        reports = [
            _make_report([_make_finding("lewin", "high")]),
            _make_report([_make_finding("bias_stack", "high")]),
        ]
        scorecard = compute_scorecard(reports=reports)
        reasoning = scorecard.dimensions["reasoning"]
        # 100 - 25 - 25 = 50 (both patterns contribute fully to reasoning).
        assert reasoning.score == 50.0
        assert reasoning.grade.letter == "F"

    def test_overall_score_is_mean_of_dimensions(self):
        # Make exactly one high finding in each dimension's exclusive
        # pattern.
        reports = [
            _make_report([_make_finding("lewin", "high")]),  # reasoning
            _make_report([_make_finding("grpi", "high")]),  # coordination
            _make_report([_make_finding("trust_triangle", "high")]),  # trust
            _make_report([_make_finding("yerkes_dodson", "high")]),  # workload
            _make_report([_make_finding("schein_culture", "high")]),  # culture
        ]
        scorecard = compute_scorecard(reports=reports)
        # All five dimensions lose 25 = 75 each.
        # Overall = mean = 75.
        assert scorecard.overall_score == 75.0


class TestPatternContributions:
    def test_each_pattern_contributes(self):
        reports = [
            _make_report(
                [
                    _make_finding("lewin", "high"),
                    _make_finding("lewin", "medium"),
                    _make_finding("lewin", "low"),
                ]
            ),
        ]
        scorecard = compute_scorecard(reports=reports)
        # Find the lewin contribution.
        lewin = next(c for c in scorecard.pattern_contributions if c.pattern == "lewin")
        assert lewin.findings_high == 1
        assert lewin.findings_medium == 1
        assert lewin.findings_low == 1
        # Score delta = -(25 + 10 + 3) = -38.
        assert lewin.score_delta == -38

    def test_total_findings_count(self):
        reports = [
            _make_report([_make_finding("lewin", "high")]),
            _make_report([_make_finding("aar", "medium")]),
            _make_report([_make_finding("bias_stack", "low")]),
        ]
        scorecard = compute_scorecard(reports=reports)
        assert scorecard.total_findings == 3


class TestTopInterventions:
    def test_returns_worst_dimensions_first(self):
        # lewin → reasoning (high severity), bias_stack also → reasoning,
        # trust_triangle → trust (high)
        reports = [
            _make_report(
                [
                    _make_finding("lewin", "high", title="lewin issue"),
                    _make_finding("bias_stack", "high", title="bias issue"),
                    _make_finding("trust_triangle", "medium", title="trust issue"),
                ]
            ),
        ]
        scorecard = compute_scorecard(reports=reports)
        interventions = scorecard.top_interventions(n=2)
        assert len(interventions) >= 1
        # Worst dimension (reasoning, lowest score) should come first.
        first_dim, _first_intervention = interventions[0]
        assert first_dim == "reasoning"

    def test_returns_at_most_n(self):
        reports = [_make_report([_make_finding("lewin", "high")])]
        scorecard = compute_scorecard(reports=reports)
        assert len(scorecard.top_interventions(n=3)) <= 3


class TestScoreCardConfig:
    def test_custom_starting_score(self):
        cfg = ScoreCardConfig(starting_score=80.0)
        scorecard = compute_scorecard(reports=[], config=cfg)
        for d in scorecard.dimensions.values():
            assert d.score == 80.0

    def test_custom_severity_penalty(self):
        cfg = ScoreCardConfig(severity_penalty={"high": 50, "medium": 25, "low": 5})
        reports = [_make_report([_make_finding("lewin", "high")])]
        scorecard = compute_scorecard(reports=reports, config=cfg)
        assert scorecard.dimensions["reasoning"].score == 50.0  # 100 - 50

    def test_custom_cap(self):
        cfg = ScoreCardConfig(cap_findings_per_dimension=2)
        # 4 high findings, capped at 2 = -50 points.
        findings = [_make_finding("lewin", "high") for _ in range(4)]
        reports = [_make_report(findings)]
        scorecard = compute_scorecard(reports=reports, config=cfg)
        assert scorecard.dimensions["reasoning"].score == 50.0  # 100 - 50


class TestScoreCardSerialization:
    def test_to_dict_roundtrip(self):
        reports = [_make_report([_make_finding("lewin", "high")])]
        scorecard = compute_scorecard(reports=reports)
        data = scorecard.to_dict()
        assert data["overall_score"] > 0
        assert "reasoning" in data["dimensions"]
        assert data["dimensions"]["reasoning"]["grade"] in (
            "A+",
            "A",
            "A-",
            "B+",
            "B",
            "B-",
            "C+",
            "C",
            "C-",
            "D+",
            "D",
            "D-",
            "F",
        )
        assert "pattern_contributions" in data
        assert "total_cost_usd" in data
        assert "total_findings" in data

    def test_to_markdown_runs(self):
        reports = [_make_report([_make_finding("lewin", "high")])]
        scorecard = compute_scorecard(reports=reports)
        md = scorecard.to_markdown()
        assert "Scorecard" in md
        assert "reasoning" in md

    def test_to_html_runs(self):
        reports = [_make_report([_make_finding("lewin", "high")])]
        scorecard = compute_scorecard(reports=reports)
        html = scorecard.to_html()
        assert "<html" in html
        assert "reasoning" in html


class TestDimensionMapping:
    def test_every_shipped_pattern_has_a_mapping(self):
        """Sanity check: every pattern in PATTERN_DIMENSIONS maps to
        at least one valid dimension."""
        valid_dims = {"reasoning", "coordination", "trust", "workload", "culture"}
        for pattern, dims in PATTERN_DIMENSIONS.items():
            assert dims, f"pattern {pattern} has empty dimension mapping"
            for dim_name, weight in dims:
                assert dim_name in valid_dims, f"pattern {pattern} maps to invalid dim {dim_name}"
                assert 0 < weight <= 1, (
                    f"pattern {pattern} → {dim_name} has invalid weight {weight}"
                )

    def test_weights_sum_to_at_most_one(self):
        """Weights per pattern should sum to ≤ 1 (a pattern can't
        contribute >100% across dimensions)."""
        for pattern, dims in PATTERN_DIMENSIONS.items():
            total = sum(w for _, w in dims)
            assert total <= 1.001, f"pattern {pattern} weights sum to {total}, expected ≤ 1"
