"""Cookbook recipe 24 — `premature_completion`.

Scenario
--------
An agent claims a task is complete before the actual completion
criteria are met. This is the failure mode adjacent to silent-failure
— but caught at the orchestrator boundary, not by the user. We
diagnose:

  - **Johari Window** (#03) — BLIND SPOT about completion criteria.
  - **SMART Goal Generator** (#24) — was the goal measurable?
  - **Yerkes-Dodson** (#06) — LOW arousal (under-loaded → drift).
  - **HEXACO** (#07) — C-factor for completion discipline.

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
            "title": "SMART: 'M' (measurable) missing — completion criteria not defined",
            "evidence": [
                "Goal: 'help user plan their week'.",
                "No verification: what is 'planned'?",
            ],
            "intervention": (
                "Rewrite goal with explicit completion criteria. SMART "
                "Goal Generator's rewrite output gives you the form."
            ),
        },
        {
            "severity": "high",
            "title": "Johari: BLIND SPOT about completion definition",
            "evidence": [
                "Agent claims 'done' but missed 3 criteria.",
                "Agent's self-report doesn't enumerate completion.",
            ],
            "intervention": (
                "Require structured enumeration: 'I completed X (criterion), "
                "Y (criterion), Z (criterion).'"
            ),
        },
        {
            "severity": "medium",
            "title": "Yerkes-Dodson: LOW arousal — under-loaded agent drifts to completion",
            "evidence": [
                "Context occupancy 15%; agent has no load signal.",
                "Drift to 'good enough' completion is common at low load.",
            ],
            "intervention": (
                "Add a minimum-effort floor instruction. At low load, "
                "the agent needs explicit minimum criteria."
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
    print("  1. SMART GOAL REWRITE")
    print("     Explicit completion criteria for every task.")
    print()
    print("  2. STRUCTURED COMPLETION CLAIM")
    print("     Agent must enumerate satisfied criteria.")
    print()
    print("  3. MINIMUM-EFFORT FLOOR")
    print("     For low-load tasks, define minimum acceptable output.")
    print()
    print("  4. ORCHESTRATOR REJECTION RULE")
    print("     Bare 'done' messages are rejected; require enumeration.")


def main() -> None:
    print("=== Recipe: premature_completion ===")
    trace = stuck_in_loop_trace()
    report = diagnose(trace=trace, llm_client=_stub(), recipe="premature_completion")
    _print_report(report)
    _print_intervention_summary()


if __name__ == "__main__":
    main()
