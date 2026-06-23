"""Tests for the vstack GitHub Action gate script."""

from __future__ import annotations

import pytest

import gate


def test_build_command_minimal() -> None:
    cmd = gate.build_command({"VSTACK_TRACE": "t.json"})
    assert cmd[:4] == ["vstack-diagnose", "--trace", "t.json", "--json"]
    assert "--client" in cmd and "none" in cmd


def test_build_command_full() -> None:
    cmd = gate.build_command(
        {
            "VSTACK_TRACE": "t.json",
            "VSTACK_CLIENT": "anthropic",
            "VSTACK_MODE": "forensic",
            "VSTACK_RECIPE": "stuck_in_loop",
            "VSTACK_SHAPE": "team",
        }
    )
    assert "anthropic" in cmd
    assert "--mode" in cmd and "forensic" in cmd
    assert "--recipe" in cmd and "stuck_in_loop" in cmd
    assert "--shape" in cmd and "team" in cmd


def test_build_command_requires_trace() -> None:
    with pytest.raises(ValueError):
        gate.build_command({})


def test_decide_gate_fails_at_threshold() -> None:
    findings = [
        {"severity": "low", "pattern": "a", "title": "x"},
        {"severity": "high", "pattern": "b", "title": "y"},
    ]
    failed, max_sev, count = gate.decide_gate(findings, "high")
    assert failed is True
    assert max_sev == "high"
    assert count == 2


def test_decide_gate_below_threshold_passes() -> None:
    findings = [{"severity": "low", "pattern": "a", "title": "x"}]
    failed, max_sev, _ = gate.decide_gate(findings, "high")
    assert failed is False
    assert max_sev == "low"


def test_decide_gate_none_never_fails() -> None:
    findings = [{"severity": "critical", "pattern": "a", "title": "x"}]
    failed, max_sev, _ = gate.decide_gate(findings, "none")
    assert failed is False
    assert max_sev == "critical"


def test_decide_gate_empty_findings() -> None:
    failed, max_sev, count = gate.decide_gate([], "high")
    assert failed is False
    assert max_sev == "none"
    assert count == 0


def test_render_summary_failed_has_table() -> None:
    report = {"shape": "team", "errors": []}
    findings = [{"severity": "high", "pattern": "lewin", "title": "edit before read"}]
    out = gate.render_summary(report, findings, "high", True, "high")
    assert "FAILED" in out
    assert "lewin" in out
    assert "| Severity |" in out


def test_render_summary_passed_no_findings() -> None:
    out = gate.render_summary({"shape": "individual", "errors": []}, [], "high", False, "none")
    assert "PASSED" in out
    assert "No findings" in out
