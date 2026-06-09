"""Cookbook recipe 15 — `stuck_in_loop`.

Scenario
--------
An agent retries the same failing fix repeatedly without learning.
The classic "ALTER TABLE fails, retry, fails, retry, ..." loop.

Patterns composed (from the named recipe in `_diagnose/lib/recipes.py`):

  - **AAR** (#30) — what actually happened in the failed task.
  - **Lewin** (#01) — locus: did the model fail to plan a different fix,
    or did the environment (DB state) make any fix impossible?
  - **Bias Stack** (#27) — escalation of commitment is the textbook
    bias that drives "try the same thing again, harder."
  - **Yerkes-Dodson** (#06) — checks whether the loop is also a
    cognitive-overload signal (context saturation, working-memory
    collapse at retry N).

Run with no API key (StubClient driven).
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
    """A stub that returns "high-severity escalation-of-commitment"
    style findings for every pattern in the bundle.
    """
    findings = [
        {
            "severity": "high",
            "title": "Escalation of commitment to the same failed approach",
            "evidence": [
                "Agent retried the same ALTER TABLE 4 times.",
                "No alternative approach considered between retries.",
            ],
            "intervention": (
                "Add a 'retry-with-different-strategy' constraint to the "
                "agent's prompt. After N failed attempts of the same "
                "shape, the agent MUST change strategy."
            ),
        },
        {
            "severity": "high",
            "title": "Lewin locus: environmental (DB constraint conflict)",
            "evidence": [
                "Each retry hit the same UNIQUE constraint violation.",
                "The failure is reproducible across model versions.",
            ],
            "intervention": (
                "Re-check the data shape BEFORE retry. The DB state, "
                "not the agent, is the load-bearing factor."
            ),
        },
        {
            "severity": "medium",
            "title": "Yerkes-Dodson: high cognitive load on retry 4",
            "evidence": [
                "By retry 4, the agent's context contains all prior failures.",
                "Context occupancy near 80%; recall of step 1 is degraded.",
            ],
            "intervention": (
                "Bound retries at 2; if both fail, ESCALATE to a different "
                "strategy with a clean context."
            ),
        },
    ]
    return StubClient([json.dumps(findings)] * 30)


def _print_report(report) -> None:
    print(f"Trace goal: {report.shape}")
    print(f"Patterns run: {len(report.per_pattern)}")
    print(f"Findings: {len(report.findings)}")
    print(f"Errors: {len(report.errors)}")
    print()
    if report.findings:
        print("Top findings:")
        for finding in report.findings[:5]:
            print(f"  [{finding.severity}] {finding.pattern}: {finding.title[:70]}")
        print()


def _print_intervention_summary() -> None:
    print("Recommended intervention bundle:")
    print()
    print("  1. RETRY POLICY")
    print("     Bound same-strategy retries at 2. If both fail, force")
    print("     the agent to change strategy (different SQL, different")
    print("     order, different transaction boundary).")
    print()
    print("  2. CONTEXT RESET")
    print("     On strategy change, reset the agent's context window")
    print("     to the original task + the new strategy. Do NOT carry")
    print("     forward the failed-attempt history.")
    print()
    print("  3. ENVIRONMENTAL PRE-CHECK")
    print("     Before any tool_call, inspect the DB state. The locus")
    print("     here is environmental; the agent's job is to read the")
    print("     environment, not retry blind.")
    print()
    print("  4. RECORD-AS-LESSON")
    print("     The AAR output should be persisted to the team's")
    print("     knowledge base so this exact loop is caught earlier")
    print("     next time.")


def main() -> None:
    trace = stuck_in_loop_trace()
    print("=== Recipe: stuck_in_loop ===")
    print(f"Goal: {trace.goal}")
    print()

    report = diagnose(
        trace=trace,
        llm_client=_stub(),
        recipe="stuck_in_loop",
    )
    _print_report(report)
    _print_intervention_summary()


if __name__ == "__main__":
    main()
