"""Cookbook recipe 28 — `handoff_loss`.

Scenario
--------
Information drops at every cross-agent handoff. By the time the
work reaches the third agent, half the original context is gone.
We diagnose:

  - **Process Gain/Loss** (#14) — handoff_overhead + information_retained_pct.
  - **GRPI** (#13) — Processes layer (handoff protocol).
  - **Trust Triangle** (#18) — does information loss mean the
    receiver re-verifies everything?
  - **Cold Handoff recipe** — composed pattern.

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
            "title": "Process Loss: information_retained_pct = 45% per handoff",
            "evidence": [
                "Handoff 1 retains 65% of original context.",
                "Handoff 2 retains 45%; handoff 3 retains 25%.",
            ],
            "intervention": (
                "Structured handoff payload (Pydantic model) covering "
                "goal / constraints / decisions / open questions."
            ),
        },
        {
            "severity": "high",
            "title": "GRPI Processes layer: no formal handoff protocol",
            "evidence": [
                "Each agent re-asks for context.",
                "Handoff format varies per pair.",
            ],
            "intervention": ("Adopt a single shared handoff schema across all agents."),
        },
        {
            "severity": "medium",
            "title": "Trust Triangle: Logic leg eroded by handoff loss",
            "evidence": [
                "Receivers re-verify every claim because reasoning is lost.",
                "Re-verification cost = 30% of total task cost.",
            ],
            "intervention": ("Carry forward reasoning chain in handoff payload."),
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
    print("  1. SHARED HANDOFF SCHEMA")
    print("     Single Pydantic model used by every agent.")
    print()
    print("  2. STRUCTURED PAYLOAD: GOAL/CONSTRAINTS/DECISIONS/QUESTIONS")
    print("     Each section is mandatory; none can be empty unless N/A.")
    print()
    print("  3. CARRY REASONING CHAIN")
    print("     Receiver gets the why, not just the what.")
    print()
    print("  4. MEASURE INFORMATION_RETAINED_PCT")
    print("     Bake into the orchestrator dashboard; alert if < 80%.")


def main() -> None:
    print("=== Recipe: handoff_loss ===")
    trace = stuck_in_loop_trace()
    report = diagnose(trace=trace, llm_client=_stub(), recipe="handoff_loss")
    _print_report(report)
    _print_intervention_summary()


if __name__ == "__main__":
    main()
