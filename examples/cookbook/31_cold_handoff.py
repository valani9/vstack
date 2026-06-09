"""Cookbook recipe 31 — `cold_handoff`.

Scenario
--------
Each cross-agent handoff is structurally cold — no user context,
no goal restatement, no constraint enumeration. The receiver
treats it as a fresh task. We diagnose:

  - **Process Gain/Loss** (#14) — information loss.
  - **GRPI** (#13) — Processes layer.
  - **Trust Triangle** (#18) — Empathy leg — does sender model
    receiver's needs?
  - **Goleman EI** (#02) — affective handoff component.

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
            "title": "Trust Triangle: Empathy leg — sender doesn't model receiver's need",
            "evidence": [
                "Handoffs contain bare output + no goal restatement.",
                "Receiver re-derives the goal from scratch.",
            ],
            "intervention": (
                "Add 'what the receiver will do with this' framing to "
                "every handoff. Empathy must be structural, not optional."
            ),
        },
        {
            "severity": "high",
            "title": "GRPI Processes: handoff format misses goal + constraints",
            "evidence": [
                "Handoff template has output field only.",
                "No fields for goal, constraints, open questions.",
            ],
            "intervention": (
                "Adopt 4-field handoff schema: goal / constraints / output / open_questions."
            ),
        },
        {
            "severity": "medium",
            "title": "Process Loss: warm-up overhead = 30% of receiver's time",
            "evidence": [
                "Receiver spends 30% of time re-deriving goal.",
                "This is recoverable with structured handoff.",
            ],
            "intervention": ("Adopt the structured schema; receiver's warm-up drops to 5%."),
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
    print("  1. 4-FIELD HANDOFF SCHEMA")
    print("     goal / constraints / output / open_questions.")
    print()
    print("  2. EMPATHY FRAMING")
    print("     Sender names 'what receiver will do with this'.")
    print()
    print("  3. MEASURE WARM-UP TIME")
    print("     Track receiver's re-derivation cost; alert if rising.")
    print()
    print("  4. STRUCTURED COMPOSITION WITH HANDOFF_LOSS")
    print("     If structural cold-handoff persists, run handoff_loss")
    print("     recipe for deeper analysis.")


def main() -> None:
    print("=== Recipe: cold_handoff ===")
    trace = stuck_in_loop_trace()
    report = diagnose(trace=trace, llm_client=_stub(), recipe="cold_handoff")
    _print_report(report)
    _print_intervention_summary()


if __name__ == "__main__":
    main()
