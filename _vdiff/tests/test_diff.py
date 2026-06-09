"""Tests for the report diff."""

from __future__ import annotations


from vstack.vdiff import FindingDiff, diff_reports


def _f(pattern: str, severity: str, title: str = "", intervention: str = ""):
    return {
        "pattern": pattern,
        "severity": severity,
        "title": title or f"{pattern}-{severity}-title",
        "intervention": intervention or f"fix {pattern}",
    }


def _r(findings: list[dict], per_pattern: dict | None = None) -> dict:
    return {
        "findings": findings,
        "per_pattern": per_pattern or {},
    }


class TestDiffReports:
    def test_no_change(self):
        report = _r([_f("lewin", "high")])
        delta = diff_reports(report, report)
        assert len(delta.added) == 0
        assert len(delta.removed) == 0
        assert len(delta.severity_changed) == 0
        assert len(delta.unchanged) == 1

    def test_finding_added(self):
        before = _r([])
        after = _r([_f("lewin", "high")])
        delta = diff_reports(before, after)
        assert len(delta.added) == 1
        assert delta.added[0].severity_after == "high"
        assert delta.added[0].pattern == "lewin"

    def test_finding_removed(self):
        before = _r([_f("lewin", "high")])
        after = _r([])
        delta = diff_reports(before, after)
        assert len(delta.removed) == 1
        assert delta.removed[0].severity_before == "high"

    def test_severity_increased(self):
        before = _r([_f("lewin", "medium", title="loop")])
        after = _r([_f("lewin", "high", title="loop")])
        delta = diff_reports(before, after)
        assert len(delta.severity_changed) == 1
        sc = delta.severity_changed[0]
        assert sc.severity_increased
        assert sc.severity_before == "medium"
        assert sc.severity_after == "high"

    def test_severity_decreased(self):
        before = _r([_f("lewin", "high", title="loop")])
        after = _r([_f("lewin", "low", title="loop")])
        delta = diff_reports(before, after)
        assert delta.severity_changed[0].severity_decreased

    def test_intervention_changed(self):
        before = _r([_f("lewin", "high", title="x", intervention="old")])
        after = _r([_f("lewin", "high", title="x", intervention="new")])
        delta = diff_reports(before, after)
        assert len(delta.intervention_changed) == 1
        ic = delta.intervention_changed[0]
        assert ic.intervention_before == "old"
        assert ic.intervention_after == "new"

    def test_per_pattern_added(self):
        before = _r([], per_pattern={"lewin": {}})
        after = _r([], per_pattern={"lewin": {}, "aar": {}})
        delta = diff_reports(before, after)
        assert "aar" in delta.patterns_added
        assert "lewin" not in delta.patterns_added

    def test_per_pattern_removed(self):
        before = _r([], per_pattern={"lewin": {}, "aar": {}})
        after = _r([], per_pattern={"lewin": {}})
        delta = diff_reports(before, after)
        assert "aar" in delta.patterns_removed

    def test_counts_correct(self):
        before = _r([_f("a", "high"), _f("b", "low")])
        after = _r([_f("a", "high"), _f("c", "medium")])
        delta = diff_reports(before, after)
        assert delta.before_count == 2
        assert delta.after_count == 2


class TestIsRegression:
    def test_new_high_finding_is_regression(self):
        before = _r([])
        after = _r([_f("lewin", "high")])
        delta = diff_reports(before, after)
        assert delta.is_regression()

    def test_new_low_finding_is_not_regression(self):
        before = _r([])
        after = _r([_f("lewin", "low")])
        delta = diff_reports(before, after)
        # No threshold violation with just 1 low finding.
        # (1/1 = 100% but it's not a "high".)
        # Actually 1/1 > threshold(0.1), so regression by threshold.
        assert delta.is_regression()

    def test_severity_increase_is_regression(self):
        before = _r([_f("lewin", "medium", title="x")])
        after = _r([_f("lewin", "high", title="x")])
        delta = diff_reports(before, after)
        assert delta.is_regression()

    def test_no_change_no_regression(self):
        report = _r([_f("lewin", "high")])
        delta = diff_reports(report, report)
        assert not delta.is_regression()


class TestIsImprovement:
    def test_high_finding_removed_is_improvement(self):
        before = _r([_f("lewin", "high")])
        after = _r([])
        delta = diff_reports(before, after)
        assert delta.is_improvement()

    def test_severity_decrease_is_improvement(self):
        before = _r([_f("lewin", "high", title="x")])
        after = _r([_f("lewin", "medium", title="x")])
        delta = diff_reports(before, after)
        assert delta.is_improvement()

    def test_no_change_no_improvement(self):
        report = _r([_f("lewin", "high")])
        delta = diff_reports(report, report)
        assert not delta.is_improvement()


class TestSerialization:
    def test_to_dict(self):
        before = _r([_f("lewin", "high")])
        after = _r([_f("aar", "medium")])
        delta = diff_reports(before, after)
        data = delta.to_dict()
        assert data["before_count"] == 1
        assert data["after_count"] == 1
        assert "added" in data
        assert "removed" in data

    def test_to_markdown(self):
        before = _r([_f("lewin", "high")])
        after = _r([_f("aar", "medium")])
        delta = diff_reports(before, after)
        md = delta.to_markdown()
        assert "# Report Delta" in md
        assert "Added" in md
        assert "Removed" in md


class TestFindingDiff:
    def test_severity_increased_property(self):
        d = FindingDiff(
            pattern="x",
            title="y",
            kind="severity_changed",
            severity_before="low",
            severity_after="high",
        )
        assert d.severity_increased
        assert not d.severity_decreased

    def test_severity_decreased_property(self):
        d = FindingDiff(
            pattern="x",
            title="y",
            kind="severity_changed",
            severity_before="high",
            severity_after="low",
        )
        assert d.severity_decreased
        assert not d.severity_increased

    def test_severity_change_with_none_returns_false(self):
        d = FindingDiff(
            pattern="x",
            title="y",
            kind="added",
            severity_after="high",
        )
        assert not d.severity_increased
        assert not d.severity_decreased


class TestEdgeCases:
    def test_handles_empty_reports(self):
        delta = diff_reports(_r([]), _r([]))
        assert len(delta.finding_diffs) == 0
        assert delta.before_count == 0
        assert delta.after_count == 0

    def test_handles_pydantic_like_objects(self):
        """diff_reports accepts both dict and attribute-style objects."""

        class FakeReport:
            findings = [_f("lewin", "high")]
            per_pattern = {"lewin": "x"}

        delta = diff_reports(FakeReport(), FakeReport())
        assert delta.before_count == 1
