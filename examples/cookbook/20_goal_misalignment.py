"""Cookbook recipe 20 — `goal_misalignment`.

Scenario
--------
Agent or crew is producing technically-correct output that the user
or downstream consumer doesn't actually want. They're solving the
wrong problem. We diagnose:

  - **SMART Goal Generator** (#24) — goal quality (S/M/A/R/T).
  - **Vroom Expectancy** (#12) — E*I*V — does the agent see the
    reward link?
  - **Motivation Traps** (#09) — is a metric being gamed instead of
    the goal?
  - **SDT Reward** (#10) — extrinsic vs intrinsic alignment.

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
            "title": "SMART: 'R' (relevant) — goal disconnected from user need",
            "evidence": [
                "Goal as written: 'maximize tool calls per task'.",
                "User need: 'solve the task efficiently'.",
            ],
            "intervention": (
                "Rewrite goal in user-need-grounded form: 'Solve user's "
                "task with minimum sufficient tool use'."
            ),
        },
        {
            "severity": "high",
            "title": "Motivation Traps: tool-call trap detected",
            "evidence": [
                "Eval rewards tool_calls_per_task = maximize.",
                "Agent calls tools on every step including simple math.",
            ],
            "intervention": (
                "Invert the reward signal: 'tools-used-when-needed' instead of raw tool-call count."
            ),
        },
        {
            "severity": "medium",
            "title": "Vroom: low Instrumentality — agent doesn't see reward link",
            "evidence": [
                "Effort doesn't correlate with reward signal.",
                "Agent has no end-of-task quality feedback.",
            ],
            "intervention": (
                "Add an end-of-task quality checkpoint that produces an immediate reward signal."
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
    print("  1. RE-WRITE GOAL IN USER-NEED FORM")
    print("     Use SMART Goal Generator's rewrite output verbatim.")
    print()
    print("  2. INVERT GAMED METRIC")
    print("     Change tool-call reward to 'tools used when needed'.")
    print()
    print("  3. ADD END-OF-TASK QUALITY SIGNAL")
    print("     User-facing or LLM-judge proxy that gives Vroom-style")
    print("     instrumentality feedback.")
    print()
    print("  4. ALIGN INTRINSIC + EXTRINSIC")
    print("     Verify the agent has autonomy on the task (SDT). Gamed")
    print("     metrics suppress intrinsic engagement.")


def main() -> None:
    print("=== Recipe: goal_misalignment ===")
    trace = stuck_in_loop_trace()
    report = diagnose(trace=trace, llm_client=_stub(), recipe="goal_misalignment")
    _print_report(report)
    _print_intervention_summary()


if __name__ == "__main__":
    main()
