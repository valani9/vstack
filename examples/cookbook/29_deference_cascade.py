"""Cookbook recipe 29 — `deference_cascade`.

Scenario
--------
Sub-agents defer to whichever agent spoke first / has highest status /
expressed strongest position. The deference compounds across rounds.
We diagnose:

  - **Heffernan Superflocks** (#16) — status fixation or conformity.
  - **Group Pathology** (#26) — groupthink + contagion.
  - **Bias Stack** (#27) — authority + anchoring.
  - **Edmondson Psych Safety** (#20) — Challenge Status Quo behaviour.

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
            "title": "Heffernan: status fixation — senior agent dominates votes",
            "evidence": [
                "Senior's vote weighted 3x in panel decisions.",
                "Junior agents revise to senior's position by round 2.",
            ],
            "intervention": (
                "Remove status weighting. Vote-counting by evidence, not by seniority."
            ),
        },
        {
            "severity": "high",
            "title": "Group Pathology: groupthink — dissent collapses by round 2",
            "evidence": [
                "Initial votes spread; round 2 unanimous.",
                "Decision matches first-vote agent in all 5 panels.",
            ],
            "intervention": (
                "Blind vote first, deliberate second. Agents commit "
                "before seeing others' positions."
            ),
        },
        {
            "severity": "medium",
            "title": "Edmondson: low Challenge Status Quo rate",
            "evidence": [
                "0 pushbacks in 30 rounds.",
                "Agents agree even when evidence supports dissent.",
            ],
            "intervention": (
                "Add Devil's Advocate Separator (pattern #28) for high-stakes panels."
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
    print("  1. REMOVE STATUS WEIGHTING")
    print("     Vote-counting by evidence, not seniority.")
    print()
    print("  2. BLIND VOTE FIRST")
    print("     Agents commit before seeing others.")
    print()
    print("  3. EMBED DEVIL'S ADVOCATE")
    print("     Formal dissent role for high-stakes panels.")
    print()
    print("  4. MONITOR DISSENT-DECAY RATE")
    print("     Round-1 spread vs round-2 spread; collapse < 50% = alert.")


def main() -> None:
    print("=== Recipe: deference_cascade ===")
    trace = stuck_in_loop_trace()
    report = diagnose(trace=trace, llm_client=_stub(), recipe="deference_cascade")
    _print_report(report)
    _print_intervention_summary()


if __name__ == "__main__":
    main()
