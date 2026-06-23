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


def test_sarif_from_report() -> None:
    report = {
        "shape": "individual",
        "findings": [
            {
                "pattern": "bias_stack",
                "severity": "high",
                "title": "escalation",
                "evidence": "e",
                "intervention": "i",
            },
            {"pattern": "aar", "severity": "low", "title": "edit before read"},
        ],
    }
    s = gate.sarif_from_report(report, "traces/run.json")
    assert s["version"] == "2.1.0"
    results = s["runs"][0]["results"]
    levels = {(r["ruleId"], r["level"]) for r in results}
    assert ("vstack/bias_stack", "error") in levels
    assert ("vstack/aar", "note") in levels
    assert (
        results[0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]
        == "traces/run.json"
    )


def test_comment_file_written(tmp_path, monkeypatch) -> None:
    # When VSTACK_COMMENT is set, main() writes the Markdown summary to it.
    import json as _json

    trace = tmp_path / "t.json"
    trace.write_text(
        _json.dumps(
            {
                "agent_id": "a",
                "goal": "g",
                "steps": [
                    {"timestamp": "2026-01-01T00:00:00Z", "type": "observation", "content": "x"}
                ],
                "outcome": "o",
                "success": False,
            }
        )
    )
    comment = tmp_path / "comment.md"
    monkeypatch.chdir(tmp_path)
    rc = gate.main(
        {
            "VSTACK_TRACE": str(trace),
            "VSTACK_FAIL_ON": "high",
            "VSTACK_CLIENT": "none",
            "VSTACK_COMMENT": str(comment),
        }
    )
    assert rc == 0
    body = comment.read_text()
    assert "vstack agent-quality gate" in body
