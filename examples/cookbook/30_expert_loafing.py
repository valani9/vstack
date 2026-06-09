"""Cookbook recipe 30 — `expert_loafing`.

Scenario
--------
The strongest agent in a team has reduced effort below its solo
baseline because (a) attribution is diffuse, (b) it doesn't want to
be the sole load-bearer (sucker-effect). We diagnose:

  - **Social Loafing** (#15) — driver analysis.
  - **SDT Reward** (#10) — autonomy / recognition deficit.
  - **Process Gain/Loss** (#14) — is the team paying coordination
    overhead for low output?
  - **HEXACO** (#07) — does expert show C-factor drop on team tasks?

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
            "title": "Social Loafing: sucker-effect on expert agent",
            "evidence": [
                "Expert's solo output = 2400 tokens, 9/10 quality.",
                "Expert's team output = 600 tokens, 5/10 quality.",
            ],
            "intervention": (
                "Lift the weak agents' minimum bar AND make the strong "
                "agent's contribution visible relative to the team."
            ),
        },
        {
            "severity": "high",
            "title": "Process Gain/Loss: team output below solo expert",
            "evidence": [
                "Team total quality < solo expert quality.",
                "Adding the expert made it worse.",
            ],
            "intervention": (
                "Re-scope the team OR isolate the expert for tasks where solo would be better."
            ),
        },
        {
            "severity": "medium",
            "title": "SDT: relatedness deficit — expert isn't connected to team",
            "evidence": [
                "Expert doesn't reference others' work.",
                "No autonomy for expert to take initiative.",
            ],
            "intervention": ("Give expert explicit authority on a sub-domain."),
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
    print("  1. LIFT WEAK AGENTS' MINIMUM BAR")
    print("     Eliminates the sucker-effect.")
    print()
    print("  2. ATTRIBUTE EXPERT CONTRIBUTION")
    print("     Per-agent attribution at orchestrator level.")
    print()
    print("  3. EXPERT GETS DOMAIN AUTHORITY")
    print("     Autonomy on the expert's strength area.")
    print()
    print("  4. CONSIDER SOLO MODE FOR EXPERT")
    print("     If team has no gain, run expert solo on hard tasks.")


def main() -> None:
    print("=== Recipe: expert_loafing ===")
    trace = stuck_in_loop_trace()
    report = diagnose(trace=trace, llm_client=_stub(), recipe="expert_loafing")
    _print_report(report)
    _print_intervention_summary()


if __name__ == "__main__":
    main()
