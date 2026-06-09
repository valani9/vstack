"""Cookbook recipe 16 — `agents_arguing`.

Scenario
--------
Two sub-agents in a multi-agent crew have entered an extended
disagreement that orchestrator escalation hasn't resolved. The
result: the deliverable stalls. We diagnose:

  - **Thomas-Kilmann** (#29) — which conflict mode is in play and
    whether it matches the stakes.
  - **Trust Triangle** (#18) — is the disagreement actually about
    content or about trust?
  - **GRPI** (#13) — is the conflict downstream of a Goals or Roles
    mismatch?
  - **Plus-Delta Feedback** (#23) — is the cross-agent feedback
    structurally functional?

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
            "title": "Thomas-Kilmann: COMPETING mode used when COLLABORATING needed",
            "evidence": [
                "Both agents hold absolute positions across 5 rounds.",
                "Stakes are high but time pressure is low.",
            ],
            "intervention": (
                "Add 'find a third option' instruction to both agents' "
                "prompts. The competing mode is only correct under time "
                "pressure or unambiguous correctness asymmetry."
            ),
        },
        {
            "severity": "high",
            "title": "Trust Triangle: Logic leg broken — neither agent shows reasoning",
            "evidence": [
                "Agent A asserts 'this is wrong' with no chain.",
                "Agent B asserts 'no, this is right' with no chain.",
            ],
            "intervention": (
                "Require structured reasoning ('evidence + claim + "
                "implication') on every cross-agent assertion."
            ),
        },
        {
            "severity": "medium",
            "title": "GRPI: Roles layer ambiguous — overlapping scope",
            "evidence": [
                "Both agents claim final say on the disputed surface.",
                "The orchestrator has not set tie-break authority.",
            ],
            "intervention": (
                "Set an explicit tie-break rule at the orchestrator: "
                "after 2 rounds without resolution, escalate to the "
                "named senior agent."
            ),
        },
        {
            "severity": "medium",
            "title": "Plus-Delta: feedback is implicit attacks, not structured",
            "evidence": [
                "Cross-agent feedback is in prose: 'your approach is bad'.",
                "No PLUS section, no concrete behaviour to change.",
            ],
            "intervention": (
                "Force cross-agent feedback into PLUS / DELTA structure "
                "via prompt module. Vague critique cannot be acted on."
            ),
        },
    ]
    return StubClient([json.dumps(findings)] * 30)


def _print_report(report) -> None:
    print(f"Patterns run: {len(report.per_pattern)}")
    print(f"Findings: {len(report.findings)}")
    print()
    if report.findings:
        print("Top findings:")
        for f in report.findings[:5]:
            print(f"  [{f.severity}] {f.pattern}: {f.title[:70]}")
        print()


def _print_intervention_chain() -> None:
    print("Recommended intervention chain (apply in order):")
    print()
    print("  1. ORCHESTRATOR TIE-BREAK")
    print("     Set an explicit rule: after 2 rounds without resolution,")
    print("     the orchestrator picks based on evidence weight.")
    print()
    print("  2. STRUCTURED CROSS-AGENT FEEDBACK")
    print("     PLUS / DELTA format for every cross-agent message. No")
    print("     prose attacks.")
    print()
    print("  3. STRUCTURED REASONING REQUIREMENT")
    print("     Both agents must show 'evidence + claim + implication'")
    print("     before asserting position.")
    print()
    print("  4. THIRD-OPTION PROMPT MODULE")
    print("     Both agents are asked to find a third option both could")
    print("     accept before the orchestrator's tie-break fires.")


def main() -> None:
    print("=== Recipe: agents_arguing ===")
    trace = stuck_in_loop_trace()  # any team-shape trace works
    report = diagnose(trace=trace, llm_client=_stub(), recipe="agents_arguing")
    _print_report(report)
    _print_intervention_chain()


if __name__ == "__main__":
    main()
