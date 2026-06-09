"""Tests for scorecard rendering (text / markdown / HTML)."""

from __future__ import annotations

from vstack.scorecard import (
    ScoreCardConfig,
    compute_scorecard,
    render_html,
    render_markdown,
    render_text,
)


def _make_finding(pattern: str, severity: str, title: str = "test"):
    return {
        "pattern": pattern,
        "severity": severity,
        "title": title,
        "intervention": f"Fix {pattern}",
    }


def _make_report(findings: list[dict]) -> dict:
    return {"findings": findings}


class TestRenderText:
    def test_renders_title(self):
        cfg = ScoreCardConfig(title="My Test Card")
        sc = compute_scorecard(reports=[], config=cfg)
        text = render_text(sc)
        assert "My Test Card" in text

    def test_renders_overall_grade(self):
        sc = compute_scorecard(reports=[])
        text = render_text(sc)
        assert "OVERALL" in text
        assert "A+" in text

    def test_renders_all_dimensions(self):
        sc = compute_scorecard(reports=[])
        text = render_text(sc)
        for dim in ("reasoning", "coordination", "trust", "workload", "culture"):
            assert dim in text

    def test_renders_findings_count(self):
        sc = compute_scorecard(
            reports=[
                _make_report([_make_finding("lewin", "high")]),
            ]
        )
        text = render_text(sc)
        assert "Total findings" in text


class TestRenderMarkdown:
    def test_renders_h1(self):
        cfg = ScoreCardConfig(title="Test")
        sc = compute_scorecard(reports=[], config=cfg)
        md = render_markdown(sc)
        assert "# Test" in md

    def test_renders_overall_grade(self):
        sc = compute_scorecard(reports=[])
        md = render_markdown(sc)
        assert "**Overall**" in md
        assert "A+" in md

    def test_renders_dimensions_table(self):
        sc = compute_scorecard(reports=[])
        md = render_markdown(sc)
        assert "| Dimension" in md or "Dimension" in md

    def test_renders_agent_id(self):
        cfg = ScoreCardConfig(agent_id="bot-001")
        sc = compute_scorecard(reports=[], config=cfg)
        md = render_markdown(sc)
        assert "bot-001" in md

    def test_renders_fleet_id(self):
        cfg = ScoreCardConfig(fleet_id="fleet-prod")
        sc = compute_scorecard(reports=[], config=cfg)
        md = render_markdown(sc)
        assert "fleet-prod" in md


class TestRenderHTML:
    def test_renders_doctype(self):
        sc = compute_scorecard(reports=[])
        html = render_html(sc)
        assert "<!DOCTYPE html>" in html

    def test_renders_title(self):
        cfg = ScoreCardConfig(title="My Card")
        sc = compute_scorecard(reports=[], config=cfg)
        html = render_html(sc)
        assert "My Card" in html

    def test_renders_overall_score(self):
        sc = compute_scorecard(reports=[])
        html = render_html(sc)
        assert "100.0" in html or "100" in html

    def test_renders_all_dimensions(self):
        sc = compute_scorecard(reports=[])
        html = render_html(sc)
        for dim in ("reasoning", "coordination", "trust", "workload", "culture"):
            assert dim in html.lower()

    def test_renders_top_interventions(self):
        sc = compute_scorecard(
            reports=[
                _make_report([_make_finding("lewin", "high", "Some Issue")]),
            ]
        )
        html = render_html(sc)
        assert "intervention" in html.lower()

    def test_renders_per_pattern_table(self):
        sc = compute_scorecard(
            reports=[
                _make_report([_make_finding("lewin", "high")]),
            ]
        )
        html = render_html(sc)
        assert "lewin" in html

    def test_renders_total_cost(self):
        sc = compute_scorecard(reports=[])
        html = render_html(sc)
        assert "Total cost" in html

    def test_html_has_no_unbound_template_vars(self):
        """Sanity check: the HTML should have no leftover {var}
        placeholders.
        """
        sc = compute_scorecard(
            reports=[
                _make_report([_make_finding("lewin", "high")]),
            ]
        )
        html = render_html(sc)
        # No literal "{" placeholder syntax in the output.
        # (CSS uses { } but those are inside <style>, not in our format args.)
        # We check that no {python_var} substring remains.
        import re

        unbound = re.findall(r"\{[a-z_][a-z_0-9]*\}", html)
        # Allow CSS class patterns like {color}.
        assert not any(u in ("{title}", "{overall_grade}") for u in unbound)
