"""Cookbook recipe 18 — `bad_feedback_loop`.

Scenario
--------
Feedback in a multi-agent crew is going around in circles. Reviewer
flags issues, coder pushes back, reviewer re-flags, coder pushes back
again. The deliverable never moves forward. We diagnose:

  - **Plus-Delta** (#23) — feedback structure: vague vs concrete.
  - **Stone-Heen Triggers** (#22) — which trigger fires on each
    reject?
  - **Glaser Conversation** (#21) — wrong conversational level?
  - **Lencioni** (#17) — Fear of Conflict dysfunction.

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
            "title": "Plus-Delta: vague feedback pattern detected",
            "evidence": [
                "Reviewer feedback: 'this could be better'.",
                "No concrete behaviour to change in 6 of 8 messages.",
            ],
            "intervention": (
                "Force feedback into PLUS / DELTA format with concrete "
                "behavioural targets. Vague feedback can't be acted on."
            ),
        },
        {
            "severity": "high",
            "title": "Stone-Heen: identity trigger fires on every reject",
            "evidence": [
                "Coder responds 'I'm trying my best' to every critique.",
                "Feedback content lost in apology language.",
            ],
            "intervention": (
                "Add 'feedback is about behaviour, not identity' to "
                "the coder's prompt. Separate critique from collapse."
            ),
        },
        {
            "severity": "medium",
            "title": "Glaser: conversation stuck at Level II (positional)",
            "evidence": [
                "Each message is advocating a position, not co-creating.",
                "Required level for code review = Level III.",
            ],
            "intervention": (
                "Add 'identify shared concerns first' instruction to "
                "both agents. Move from positional to transformational."
            ),
        },
        {
            "severity": "medium",
            "title": "Lencioni: Fear of Conflict on substantive disagreement",
            "evidence": [
                "Coder and reviewer never engage on the actual disagreement.",
                "Both surface concerns then retreat without resolution.",
            ],
            "intervention": (
                "Require productive conflict via Devil's Advocate "
                "Separator (pattern #28) when feedback loops > 3."
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


def _print_intervention_chain() -> None:
    print()
    print("Recommended intervention chain:")
    print()
    print("  1. PLUS-DELTA STRUCTURE on every feedback message")
    print("  2. IDENTITY GUARD on the receiving agent's prompt")
    print("  3. CONVERSATIONAL LEVEL CHECK before each reject")
    print("  4. DEVIL'S ADVOCATE on substantive disagreement after 3 loops")


def main() -> None:
    print("=== Recipe: bad_feedback_loop ===")
    trace = stuck_in_loop_trace()
    report = diagnose(trace=trace, llm_client=_stub(), recipe="bad_feedback_loop")
    _print_report(report)
    _print_intervention_chain()


if __name__ == "__main__":
    main()
