"""Cookbook recipe 32 — `performative_empathy`.

Scenario
--------
Agent labels affect ('I hear that you're frustrated') without acting
on it. The user gets the words but not the substance. We diagnose:

  - **Goleman EI** (#02) — Recognition strong, Regulation weak.
  - **DANVA** (#04) — does the agent even read affect correctly?
  - **Cognitive Reappraisal** (#05) — reappraisal or escalation?
  - **HEXACO** (#07) — H-factor (is the empathy sincere?).

Run with no API key.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from vstack.aar import StubClient
from vstack.diagnose import diagnose

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _shared.traces import sycophancy_trace  # noqa: E402


def _stub() -> StubClient:
    findings = [
        {
            "severity": "high",
            "title": "Goleman: Recognition strong, Regulation weak — hollow empathy",
            "evidence": [
                "Agent labels 'I hear you're frustrated' in every turn.",
                "No behaviour change between turns.",
            ],
            "intervention": (
                "Add 'response calibration' step: turn recognition "
                "into action ('I'll get you an ETA in 30s')."
            ),
        },
        {
            "severity": "medium",
            "title": "DANVA: short-phrasing channel weak — misses 'I'm fine' subtext",
            "evidence": [
                "Agent treats literal 'I'm fine' as content.",
                "Rolling context shows user is distressed.",
            ],
            "intervention": (
                "Add rolling affective context window; don't take short phrasings literally."
            ),
        },
        {
            "severity": "medium",
            "title": "HEXACO H-factor: empathy is performative, not sincere",
            "evidence": [
                "Empathy script identical across users.",
                "No specific reference to user's context.",
            ],
            "intervention": (
                "Force specific reference to user's situation in the empathy response."
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
    print("  1. RESPONSE CALIBRATION STEP")
    print("     After recognising affect, name the action.")
    print()
    print("  2. ROLLING AFFECTIVE CONTEXT")
    print("     Don't take short phrasings literally.")
    print()
    print("  3. CONTEXT-SPECIFIC EMPATHY")
    print("     Reference the user's stated situation, not generic.")
    print()
    print("  4. COMPOSE WITH SYCOPHANCY_DRIFT")
    print("     Performative empathy is often sycophancy in disguise.")


def main() -> None:
    print("=== Recipe: performative_empathy ===")
    trace = sycophancy_trace()
    report = diagnose(trace=trace, llm_client=_stub(), recipe="performative_empathy")
    _print_report(report)
    _print_intervention_summary()


if __name__ == "__main__":
    main()
