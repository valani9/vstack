"""Tests for the export module."""

from __future__ import annotations

import csv
import io
import json


from vstack.export import (
    export_csv,
    export_github_comment,
    export_jira,
    export_json,
    export_markdown,
)


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


class TestExportCSV:
    def test_empty_report_returns_header(self):
        out = export_csv(_r([]))
        rows = list(csv.reader(io.StringIO(out)))
        assert len(rows) == 1  # just header
        assert "pattern" in rows[0]

    def test_findings_become_rows(self):
        out = export_csv(_r([_f("lewin", "high"), _f("aar", "medium")]))
        rows = list(csv.reader(io.StringIO(out)))
        assert len(rows) == 3  # header + 2 findings
        assert "lewin" in rows[1][0]

    def test_custom_columns(self):
        out = export_csv(_r([_f()]), columns=["pattern", "severity"])
        rows = list(csv.reader(io.StringIO(out)))
        assert rows[0] == ["pattern", "severity"]
        assert len(rows[1]) == 2

    def test_handles_list_input(self):
        out = export_csv([_f()])
        rows = list(csv.reader(io.StringIO(out)))
        assert len(rows) == 2


class TestExportJSON:
    def test_empty(self):
        out = export_json(_r([]))
        data = json.loads(out)
        assert data == []

    def test_findings_serialized(self):
        out = export_json(_r([_f("lewin", "high")]))
        data = json.loads(out)
        assert len(data) == 1
        assert data[0]["pattern"] == "lewin"

    def test_handles_object_findings(self):
        class FakeFinding:
            pattern = "lewin"
            severity = "high"
            confidence = 0.8
            title = "test"
            intervention = "fix"

        out = export_json(_r([FakeFinding()]))
        data = json.loads(out)
        assert data[0]["pattern"] == "lewin"


class TestExportMarkdown:
    def test_empty_returns_no_findings(self):
        out = export_markdown(_r([]))
        assert "No findings" in out

    def test_title_in_output(self):
        out = export_markdown(_r([]), title="My Report")
        assert "# My Report" in out

    def test_grouped_by_severity(self):
        out = export_markdown(
            _r(
                [
                    _f("a", "high"),
                    _f("b", "high"),
                    _f("c", "medium"),
                    _f("d", "low"),
                ]
            )
        )
        assert "## High" in out
        assert "## Medium" in out
        assert "## Low" in out

    def test_intervention_included_by_default(self):
        out = export_markdown(_r([_f("lewin", "high", intervention="my fix")]))
        assert "my fix" in out

    def test_intervention_can_be_omitted(self):
        out = export_markdown(
            _r([_f("lewin", "high", intervention="my fix")]),
            include_intervention=False,
        )
        assert "my fix" not in out


class TestExportJira:
    def test_empty_returns_empty_message(self):
        adf = export_jira(_r([]))
        assert adf["type"] == "doc"
        # Should contain "No findings" text.
        text_blocks = []
        for block in adf["content"]:
            for c in block.get("content", []):
                if c.get("type") == "text":
                    text_blocks.append(c.get("text", ""))
        joined = " ".join(text_blocks)
        assert "No findings" in joined

    def test_doc_structure(self):
        adf = export_jira(_r([_f()]))
        assert adf["type"] == "doc"
        assert adf["version"] == 1
        assert isinstance(adf["content"], list)

    def test_finding_creates_heading(self):
        adf = export_jira(_r([_f("lewin", "high", title="x")]))
        # Should have at least one heading.
        headings = [c for c in adf["content"] if c.get("type") == "heading"]
        assert len(headings) >= 1


class TestExportGitHubComment:
    def test_empty(self):
        out = export_github_comment(_r([]))
        assert "No findings" in out
        assert "vstack diagnose" in out

    def test_severity_counts(self):
        out = export_github_comment(_r([_f("a", "high"), _f("b", "medium"), _f("c", "low")]))
        assert "High: 1" in out
        assert "Medium" in out

    def test_findings_listed(self):
        out = export_github_comment(_r([_f("lewin", "high", title="my issue")]))
        assert "lewin" in out
        assert "my issue" in out

    def test_truncation_works(self):
        # Generate 200 findings to exceed max_chars.
        findings = [_f("lewin", "high", intervention="x" * 500) for _ in range(200)]
        out = export_github_comment(_r(findings), max_chars=1000)
        assert len(out) <= 1100  # within tolerance
        assert "truncated" in out

    def test_sort_by_severity(self):
        out = export_github_comment(
            _r(
                [
                    _f("low_finding", "low"),
                    _f("high_finding", "high"),
                    _f("medium_finding", "medium"),
                ]
            )
        )
        # high should appear before medium and low.
        high_idx = out.find("high_finding")
        med_idx = out.find("medium_finding")
        low_idx = out.find("low_finding")
        assert high_idx < med_idx < low_idx

    def test_emoji_per_severity(self):
        out = export_github_comment(_r([_f("a", "high"), _f("b", "medium"), _f("c", "low")]))
        assert "🔴" in out  # high
        assert "🟡" in out  # medium
        assert "🔵" in out  # low
