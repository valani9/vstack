"""Tests for ``vstack.dashboard.render``.

Covers the single-report renderer + the overview renderer with both
dict and attribute-style inputs (so the renderer works equally well
on real :class:`DiagnoseReport` instances and on JSON-parsed payloads).
"""

from __future__ import annotations

from types import SimpleNamespace


from vstack.dashboard import (
    DashboardConfig,
    render_report,
    render_reports_overview,
)


# --- helpers ---------------------------------------------------------


def _sample_report(report_id: str = "run-1") -> dict:
    return {
        "report_id": report_id,
        "shape": "individual",
        "findings": [
            {
                "pattern": "lewin",
                "severity": "high",
                "title": "environmental locus drives failure",
                "evidence": "stale RAG returned 2003 revision",
                "intervention": "refresh RAG index nightly",
            },
            {
                "pattern": "aar",
                "severity": "medium",
                "title": "premature scope reduction",
                "evidence": "spec said full module; agent did helpers",
                "intervention": "add explicit acceptance criteria",
            },
            {
                "pattern": "bias_stack",
                "severity": "low",
                "title": "mild anchoring",
                "evidence": "",
                "intervention": "",
            },
        ],
        "per_pattern": [
            {
                "pattern": "lewin",
                "n_findings": 1,
                "elapsed_seconds": 4.2,
                "error": None,
            },
            {
                "pattern": "aar",
                "n_findings": 1,
                "elapsed_seconds": 2.1,
                "error": None,
            },
            {
                "pattern": "bias_stack",
                "n_findings": 1,
                "elapsed_seconds": 1.7,
                "error": None,
            },
        ],
        "errors": {},
        "cost": {
            "llm_calls": 8,
            "input_tokens": 4500,
            "output_tokens": 1100,
            "total_tokens": 5600,
            "elapsed_ms": 8000,
            "by_pattern": {
                "lewin": {
                    "llm_calls": 4,
                    "total_tokens": 2400,
                    "elapsed_ms": 4200,
                },
                "aar": {
                    "llm_calls": 3,
                    "total_tokens": 2100,
                    "elapsed_ms": 2100,
                },
                "bias_stack": {
                    "llm_calls": 1,
                    "total_tokens": 1100,
                    "elapsed_ms": 1700,
                },
            },
            "by_model": {},
        },
        "cache_stats": None,
    }


# --- single report ---------------------------------------------------


def test_render_report_emits_html() -> None:
    html = render_report(_sample_report(), report_id="run-1")
    assert html.startswith("<!doctype html>")
    assert html.endswith("</html>")
    assert "Chart" in html  # Chart.js loaded
    assert "tailwindcss" in html


def test_render_report_contains_findings() -> None:
    html = render_report(_sample_report(), report_id="run-1")
    assert "environmental locus drives failure" in html
    assert "premature scope reduction" in html
    assert "mild anchoring" in html
    # Pattern slugs appear
    assert "lewin" in html
    assert "aar" in html


def test_render_report_severity_badges_render() -> None:
    html = render_report(_sample_report(), report_id="run-1")
    # Severity name appears in a badge span (whitespace tolerant).
    assert "badge" in html
    assert "high" in html
    assert "medium" in html
    assert "low" in html


def test_render_report_works_with_simple_namespace() -> None:
    """The renderer must handle real DiagnoseReport-shaped attribute
    objects, not just dicts."""
    payload = _sample_report()
    ns_report = SimpleNamespace(
        shape=payload["shape"],
        findings=[SimpleNamespace(**f) for f in payload["findings"]],
        per_pattern=[SimpleNamespace(**p) for p in payload["per_pattern"]],
        errors=payload["errors"],
        cost=SimpleNamespace(**payload["cost"]),
        cache_stats=None,
    )
    html = render_report(ns_report, report_id="run-ns")
    assert "environmental locus" in html
    assert "run-ns" in html


def test_render_report_handles_empty_findings() -> None:
    report = _sample_report()
    report["findings"] = []
    report["per_pattern"] = []
    html = render_report(report)
    assert "0" in html  # the stats strip should show 0 findings
    assert "No findings surfaced" in html


def test_render_report_handles_errors() -> None:
    report = _sample_report()
    report["errors"] = {"broken_pattern": "simulated crash"}
    report["per_pattern"].append(
        {
            "pattern": "broken_pattern",
            "n_findings": 0,
            "elapsed_seconds": 0.1,
            "error": "simulated crash",
        }
    )
    html = render_report(report)
    assert "Pattern errors" in html
    assert "broken_pattern" in html
    assert "simulated crash" in html


def test_render_report_respects_config_title() -> None:
    cfg = DashboardConfig(title="My Custom Dashboard")
    html = render_report(_sample_report(), config=cfg)
    assert "My Custom Dashboard" in html


def test_render_report_truncates_top_n_findings() -> None:
    report = _sample_report()
    # Add many findings
    for i in range(20):
        report["findings"].append(
            {
                "pattern": f"pat_{i}",
                "severity": "low",
                "title": f"low-severity finding {i}",
                "evidence": "",
                "intervention": "",
            }
        )
    cfg = DashboardConfig(show_top_n_findings=5)
    html = render_report(report, config=cfg)
    # Top 5 should appear, rest should be summarized
    assert "Showing top 5 of" in html


# --- overview --------------------------------------------------------


def test_render_overview_lists_runs() -> None:
    reports = [_sample_report("run-1"), _sample_report("run-2")]
    html = render_reports_overview(reports)
    assert "run-1" in html
    assert "run-2" in html
    assert "All runs" in html


def test_render_overview_empty_state() -> None:
    html = render_reports_overview([])
    assert "No reports yet" in html


def test_render_overview_shows_top_severity_per_run() -> None:
    reports = [_sample_report("run-1")]
    html = render_reports_overview(reports)
    # The top severity (high) for the sample report appears
    assert "high" in html


# --- config ----------------------------------------------------------


def test_config_badge_falls_back_for_unknown_severity() -> None:
    cfg = DashboardConfig()
    badge = cfg.badge_for("nonexistent-severity")
    assert badge.background  # not None / empty
    assert badge.foreground


def test_config_badge_uses_override_when_provided() -> None:
    from vstack.dashboard import BadgeStyle

    cfg = DashboardConfig(
        badge_styles={"critical": BadgeStyle(background="#ff0000", foreground="#000")}
    )
    badge = cfg.badge_for("critical")
    assert badge.background == "#ff0000"
    assert badge.foreground == "#000"
