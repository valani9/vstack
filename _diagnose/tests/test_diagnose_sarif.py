"""Tests for SARIF 2.1.0 output (`vstack.diagnose.to_sarif` + `--sarif`)."""

from __future__ import annotations

import json

from vstack.diagnose import DiagnoseReport, Finding, to_sarif
from vstack.diagnose.sarif import SARIF_SCHEMA, SARIF_VERSION


def _report() -> DiagnoseReport:
    return DiagnoseReport(
        shape="individual",
        findings=[
            Finding(
                pattern="bias_stack",
                severity="high",
                title="escalation of commitment",
                evidence="looped 47x",
                intervention="add a devil's advocate",
            ),
            Finding(pattern="aar", severity="low", title="edit before read"),
            Finding(pattern="bias_stack", severity="medium", title="anchoring"),
        ],
    )


def test_sarif_top_level_shape() -> None:
    s = to_sarif(_report(), trace_uri="run.json")
    assert s["$schema"] == SARIF_SCHEMA
    assert s["version"] == SARIF_VERSION
    assert len(s["runs"]) == 1
    driver = s["runs"][0]["tool"]["driver"]
    assert driver["name"] == "vstack"
    assert driver["version"]  # non-empty


def test_sarif_level_mapping() -> None:
    results = to_sarif(_report())["runs"][0]["results"]
    levels = {(r["ruleId"], r["level"]) for r in results}
    assert ("vstack/bias_stack", "error") in levels  # high -> error
    assert ("vstack/aar", "note") in levels  # low -> note
    assert ("vstack/bias_stack", "warning") in levels  # medium -> warning


def test_sarif_rules_are_deduped() -> None:
    driver = to_sarif(_report())["runs"][0]["tool"]["driver"]
    rule_ids = [r["id"] for r in driver["rules"]]
    # 3 findings across 2 distinct patterns -> 2 rules, no duplicates.
    assert sorted(rule_ids) == ["vstack/aar", "vstack/bias_stack"]


def test_sarif_message_includes_evidence_and_intervention() -> None:
    results = to_sarif(_report())["runs"][0]["results"]
    high = next(r for r in results if r["ruleId"] == "vstack/bias_stack" and r["level"] == "error")
    assert "escalation of commitment" in high["message"]["text"]
    assert "Evidence: looped 47x" in high["message"]["text"]
    assert "Intervention:" in high["message"]["text"]
    assert high["properties"]["severity"] == "high"


def test_sarif_location_uri() -> None:
    results = to_sarif(_report(), trace_uri="traces/run.json")["runs"][0]["results"]
    uri = results[0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]
    assert uri == "traces/run.json"


def test_sarif_empty_findings() -> None:
    s = to_sarif(DiagnoseReport(shape="team"))
    run = s["runs"][0]
    assert run["results"] == []
    assert run["tool"]["driver"]["rules"] == []


def test_cli_sarif_emits_valid_sarif() -> None:
    from io import StringIO
    import sys

    from vstack.diagnose.cli import main as cli_main

    payload = {
        "agent_id": "a",
        "goal": "g",
        "steps": [{"timestamp": "2026-01-01T00:00:00Z", "type": "observation", "content": "x"}],
        "outcome": "o",
        "success": False,
    }
    out, real_out, real_in = StringIO(), sys.stdout, sys.stdin
    sys.stdout, sys.stdin = out, StringIO(json.dumps(payload))
    try:
        code = cli_main(["--client", "none", "--shape", "individual", "--sarif"])
    finally:
        sys.stdout, sys.stdin = real_out, real_in
    assert code == 0
    doc = json.loads(out.getvalue())
    assert doc["version"] == "2.1.0"
    assert doc["runs"][0]["tool"]["driver"]["name"] == "vstack"
