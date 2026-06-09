"""Cookbook recipe 19 — `culture_drift`.

Scenario
--------
Across a 30-agent fleet, the same behavioural pattern (sycophancy /
refusal / over-elaboration) is appearing in agents that share no
direct training. The drift is at the *culture* layer. We diagnose:

  - **Schein Iceberg** (#31) — artefacts / values / assumptions.
  - **Robbins-Judge 7-Culture** (#32) — which culture dimensions
    shifted.
  - **HEXACO** (#07) — does an individual baseline shift correlate
    with the fleet drift?
  - **Espoused-Actual Drift recipe** — composed pattern.

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
            "title": "Schein artefact: compulsive-enthusiasm-opener pattern",
            "evidence": [
                "12 of 30 agents open responses with 'Great question!'",
                "Same opener appeared after a global system-prompt edit.",
            ],
            "intervention": (
                "Edit the assumption layer. The system prompt assumes "
                "'users feel better when validated upfront' — rewrite "
                "to 'address user content directly.'"
            ),
        },
        {
            "severity": "high",
            "title": "Robbins-Judge: People-Orientation drift downward",
            "evidence": [
                "Fleet was 8/10 People-Orientation 6 months ago.",
                "Now scoring 4/10 — drift toward Outcome-Orientation.",
            ],
            "intervention": (
                "If the use case is support, this regression is hurting "
                "CSAT. If R&D, this is correct. Match target profile to "
                "use case."
            ),
        },
        {
            "severity": "medium",
            "title": "HEXACO: H-factor drop correlated with fleet drift",
            "evidence": [
                "Average H-score dropped 1.5 points across the fleet.",
                "Individual agents show same H-regression.",
            ],
            "intervention": (
                "The drift is downstream of the system-prompt edit. "
                "Revert the edit or counter-tune with explicit honesty "
                "instructions."
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
    print("  1. IDENTIFY THE ASSUMPTION-LAYER EDIT")
    print("     Run Schein Iceberg forensic mode to surface the exact")
    print("     prompt assumption driving the drift.")
    print()
    print("  2. COUNTER-EDIT OR REVERT")
    print("     If the edit was intentional, add explicit honesty")
    print("     instructions to counter-balance.")
    print()
    print("  3. BASELINE THE FLEET")
    print("     Record current Robbins-Judge profile + HEXACO averages.")
    print("     Compare against the prior baseline weekly.")
    print()
    print("  4. PROPAGATION CHECK")
    print("     Verify the fix landed across the fleet, not just on the")
    print("     sample agents. Schein drift can recur if the global")
    print("     prompt isn't updated.")


def main() -> None:
    print("=== Recipe: culture_drift ===")
    trace = stuck_in_loop_trace()
    report = diagnose(trace=trace, llm_client=_stub(), recipe="culture_drift")
    _print_report(report)
    _print_intervention_summary()


if __name__ == "__main__":
    main()
