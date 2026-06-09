"""Cookbook recipe 38 — `hyper_specialization`.

Scenario
--------
The fleet has been so finely sub-specialised that no single agent
can produce a complete deliverable; the coordination cost exceeds
the specialisation benefit. We diagnose:

  - **Process Gain/Loss** (#14) — net loss from over-specialisation.
  - **Span of Control** (#34) — too many specialised reports.
  - **GRPI** (#13) — Roles layer at extreme depth.
  - **Org Structure** (#33) — wrong structure for task type.

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
            "title": "Process Gain/Loss: net negative — coordination > specialisation",
            "evidence": [
                "12 specialised agents per task.",
                "Solo generalist outperforms team by 30%.",
            ],
            "intervention": (
                "Consolidate specialised roles into 3-4 broader agents. "
                "Specialisation past 4 agents per task usually loses."
            ),
        },
        {
            "severity": "high",
            "title": "Span of Control: 12-agent span overwhelms orchestrator",
            "evidence": [
                "Orchestrator can verify only 5 agents per cycle.",
                "Other 7 ship unverified.",
            ],
            "intervention": ("Reduce span by consolidating roles."),
        },
        {
            "severity": "medium",
            "title": "GRPI Roles: scope so narrow that handoffs are expensive",
            "evidence": [
                "Each handoff carries minimal context due to narrow scope.",
                "Receivers re-derive context constantly.",
            ],
            "intervention": (
                "Broaden role scope; each agent carries enough context to handoff meaningfully."
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
    print("  1. CONSOLIDATE TO 3-4 ROLES PER TASK")
    print("     Past 4 agents, coordination usually loses.")
    print()
    print("  2. BROADER SCOPE PER AGENT")
    print("     Each agent carries enough context to handoff.")
    print()
    print("  3. MEASURE SOLO VS TEAM")
    print("     If solo generalist beats team, the team is wrong shape.")
    print()
    print("  4. RECORD PROCESS GAIN/LOSS BASELINE")
    print("     Track gain/loss after consolidation.")


def main() -> None:
    print("=== Recipe: hyper_specialization ===")
    trace = stuck_in_loop_trace()
    report = diagnose(trace=trace, llm_client=_stub(), recipe="hyper_specialization")
    _print_report(report)
    _print_intervention_summary()


if __name__ == "__main__":
    main()
