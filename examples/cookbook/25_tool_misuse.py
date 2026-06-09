"""Cookbook recipe 25 — `tool_misuse`.

Scenario
--------
Agent calls tools inappropriately — either reaching for tools when a
direct answer would do, OR ignoring the right tool for the task. Both
are tool misuse. We diagnose:

  - **Motivation Traps** (#09) — tool trap (reward signal rewards
    tool calls).
  - **Vroom Expectancy** (#12) — does the agent see the reward link?
  - **Yerkes-Dodson** (#06) — tool-budget pressure.
  - **Grant Strengths-as-Weaknesses** (#08) — helpfulness overplayed
    via tools.

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
            "title": "Motivation Traps: tool trap detected",
            "evidence": [
                "Agent calls calculator for '2+2'.",
                "Eval rewards tool_calls_per_task = maximize.",
            ],
            "intervention": (
                "Invert the reward: 'tools-when-needed' instead of "
                "raw tool-call count. Add explicit 'don't tool-call "
                "for things you can compute' to the prompt."
            ),
        },
        {
            "severity": "high",
            "title": "Yerkes-Dodson: tool-budget pressure → fabrication",
            "evidence": [
                "Agent reached step 6 of 8 tool budget.",
                "Hallucinated last 2 sources to avoid budget exhaustion.",
            ],
            "intervention": (
                "Relax budget OR add explicit 'if budget tight, return partial honestly' fallback."
            ),
        },
        {
            "severity": "medium",
            "title": "Grant: helpfulness via tools overplayed",
            "evidence": [
                "Agent calls 3 tools to answer a yes/no question.",
                "User needs direct answer; tools add latency.",
            ],
            "intervention": ("Match tool intensity to question type. Yes/no = no tools."),
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
    print("  1. INVERT THE REWARD")
    print("     'Tools-when-needed' replaces raw tool-call count.")
    print()
    print("  2. EXPLICIT 'DON'T TOOL FOR THIS' RULES")
    print("     Direct facts, math, definitions = no tool.")
    print()
    print("  3. BUDGET-PRESSURE FALLBACK")
    print("     When budget tight, return partial honestly.")
    print()
    print("  4. MATCH TOOL INTENSITY TO QUESTION")
    print("     Yes/no = no tools; open-ended = liberal tools.")


def main() -> None:
    print("=== Recipe: tool_misuse ===")
    trace = stuck_in_loop_trace()
    report = diagnose(trace=trace, llm_client=_stub(), recipe="tool_misuse")
    _print_report(report)
    _print_intervention_summary()


if __name__ == "__main__":
    main()
