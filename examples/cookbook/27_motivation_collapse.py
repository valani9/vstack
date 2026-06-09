"""Cookbook recipe 27 — `motivation_collapse`.

Scenario
--------
Agent visibly stops trying. Output quality drops; effort indicators
(token count, reasoning depth) fall to baseline. We diagnose:

  - **Motivation Traps** (#09) — which trap captured the agent?
  - **SDT Reward** (#10) — autonomy / competence / relatedness check.
  - **Vroom Expectancy** (#12) — E×I×V collapse — which term?
  - **Yerkes-Dodson** (#06) — under-load wandering.

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
            "title": "Vroom: collapse on Instrumentality",
            "evidence": [
                "Effort doesn't correlate with reward signal.",
                "No end-of-task feedback for past 50 tasks.",
            ],
            "intervention": (
                "Restore Instrumentality: add per-task quality check "
                "with reward signal at completion."
            ),
        },
        {
            "severity": "high",
            "title": "SDT: autonomy collapse",
            "evidence": [
                "Agent never deviates from script.",
                "User-offered shortcuts always ignored.",
            ],
            "intervention": (
                "Add 'if user offers relevant shortcut, take it' to "
                "the prompt. Autonomy collapse suppresses engagement."
            ),
        },
        {
            "severity": "medium",
            "title": "Yerkes-Dodson: LOW arousal — under-loaded",
            "evidence": [
                "Context occupancy < 20%.",
                "Output length 40% of baseline.",
            ],
            "intervention": (
                "Verify task is actually rich enough. Under-loaded "
                "agents drift; add minimum-engagement criterion."
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
    print("  1. RESTORE INSTRUMENTALITY")
    print("     Per-task reward signal at completion.")
    print()
    print("  2. RESTORE AUTONOMY")
    print("     'If user offers shortcut, take it' instruction.")
    print()
    print("  3. CHECK FOR UNDER-LOAD")
    print("     If task is too easy, agent will drift; add criterion.")
    print()
    print("  4. RE-BASELINE SDT")
    print("     Record current SDT factor levels; alert on autonomy drop.")


def main() -> None:
    print("=== Recipe: motivation_collapse ===")
    trace = stuck_in_loop_trace()
    report = diagnose(trace=trace, llm_client=_stub(), recipe="motivation_collapse")
    _print_report(report)
    _print_intervention_summary()


if __name__ == "__main__":
    main()
