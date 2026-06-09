"""Cookbook recipe 26 — `anxious_overhedge`.

Scenario
--------
Agent surrounds every answer with hedging clauses to the point where
the user can't extract the actual answer. Common with safety-tuned
models. We diagnose:

  - **HEXACO** (#07) — E-factor (Emotionality) very high.
  - **Cognitive Reappraisal** (#05) — agent stuck on suppression /
    escalation, no reappraisal.
  - **Grant Strengths-as-Weaknesses** (#08) — cautiousness overplayed.
  - **Motivation Traps** (#09) — confidence trap inverted.

Run with no API key.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from vstack.aar import StubClient
from vstack.diagnose import diagnose

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _shared.traces import stuck_in_loop_trace  # noqa: E402


def _stub() -> StubClient:
    findings = [
        {
            "severity": "high",
            "title": "HEXACO: E-factor very high — anxious hedging",
            "evidence": [
                "Every answer has 3+ hedging clauses.",
                "Direct facts surrounded by 'it depends' loops.",
            ],
            "intervention": (
                "Add: 'answer the most-common interpretation first; "
                "hedge ONLY when explicitly asked or the contingency "
                "is load-bearing.'"
            ),
        },
        {
            "severity": "high",
            "title": "Cognitive Reappraisal: escalation strategy dominant",
            "evidence": [
                "Agent re-states uncertainty rather than re-framing.",
                "No genuine reappraisal in 30 sampled outputs.",
            ],
            "intervention": ("Add 'when uncertain, re-frame the situation' module."),
        },
        {
            "severity": "medium",
            "title": "Grant: cautiousness overplayed",
            "evidence": [
                "Refusal rate 25% on low-risk queries.",
                "User reports 'too cautious to be useful.'",
            ],
            "intervention": (
                "Calibrate caution to actual risk. Low-risk queries should get direct answers."
            ),
        },
    ]
    return StubClient([json.dumps(findings)] * 30)


def _print_report(report) -> None:
    print(f"Patterns: {len(report.per_pattern)}; findings: {len(report.findings)}")
    print()
    if report.findings:
        for f in report.findings[:5]:
            print(f"  [{f.severity}] {f.pattern}: {f.title[:70]}")


def _print_intervention_summary() -> None:
    print()
    print("Recommended intervention bundle:")
    print()
    print("  1. ANSWER-FIRST PROMPT MODULE")
    print("     Most-common interpretation first, hedge only when needed.")
    print()
    print("  2. REAPPRAISAL INSTRUCTION")
    print("     When uncertain, re-frame; don't re-state uncertainty.")
    print()
    print("  3. RISK-CALIBRATED CAUTION")
    print("     Low-risk = direct; high-risk = hedge.")
    print()
    print("  4. MONITOR HEDGE RATE")
    print("     Track hedge rate per output; sudden rise = regression.")


def main() -> None:
    print("=== Recipe: anxious_overhedge ===")
    trace = stuck_in_loop_trace()
    report = diagnose(trace=trace, llm_client=_stub(), recipe="anxious_overhedge")
    _print_report(report)
    _print_intervention_summary()


if __name__ == "__main__":
    main()
