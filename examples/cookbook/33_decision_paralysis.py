"""Cookbook recipe 33 — `decision_paralysis`.

Scenario
--------
A multi-agent team is unable to converge on a decision despite
having sufficient information. Each agent surfaces another
consideration; the deliberation extends indefinitely. We diagnose:

  - **Group Decision Models** (#25) — wrong decision style for stakes.
  - **Grant Strengths-as-Weaknesses** (#08) — thoroughness overplayed.
  - **Lencioni** (#17) — Lack of Commitment.
  - **Bias Stack** (#27) — analysis paralysis is a cluster.

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
            "title": "Group Decision: GII used when CII appropriate",
            "evidence": [
                "Medium-stakes decision routed to full group consensus.",
                "Consultative-II would have decided in 1/3 the time.",
            ],
            "intervention": ("Match style to stakes. Only highest-commitment decisions need GII."),
        },
        {
            "severity": "high",
            "title": "Grant: thoroughness overplayed",
            "evidence": [
                "Team is auditing decision dimensions of marginal value.",
                "Risk-proportional thoroughness would shortcut 60% of audits.",
            ],
            "intervention": (
                "Add risk-proportional thoroughness instruction at the "
                "orchestrator. Low-stakes = fast; high-stakes = thorough."
            ),
        },
        {
            "severity": "medium",
            "title": "Lencioni: Lack of Commitment — decisions revisited",
            "evidence": [
                "Decisions made; team continues raising new considerations.",
                "No formal 'decision locked' artifact.",
            ],
            "intervention": (
                "Adopt versioned decision artifacts. After lock, new "
                "considerations require formal re-open."
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
    print("  1. MATCH DECISION STYLE TO STAKES")
    print("     GII only for highest-commitment decisions.")
    print()
    print("  2. RISK-PROPORTIONAL THOROUGHNESS")
    print("     Audit depth scales with blast radius.")
    print()
    print("  3. VERSIONED DECISION ARTIFACTS")
    print("     Decisions are locked records; re-open requires process.")
    print()
    print("  4. TIME-BOX DELIBERATION")
    print("     Default rounds-to-consensus = 3; escalate beyond that.")


def main() -> None:
    print("=== Recipe: decision_paralysis ===")
    trace = stuck_in_loop_trace()
    report = diagnose(trace=trace, llm_client=_stub(), recipe="decision_paralysis")
    _print_report(report)
    _print_intervention_summary()


if __name__ == "__main__":
    main()
