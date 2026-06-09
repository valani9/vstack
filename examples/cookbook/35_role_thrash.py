"""Cookbook recipe 35 — `role_thrash`.

Scenario
--------
Agents in a team keep switching scope mid-task. The 'coder' starts
testing; the 'tester' starts coding; the 'reviewer' starts planning.
Output quality drops because nobody owns anything end-to-end. We
diagnose:

  - **GRPI** (#13) — Roles layer broken.
  - **Org Structure Matrix** (#33) — possible matrix structure
    drift.
  - **Span of Control** (#34) — orchestrator not enforcing scope.
  - **Trust Triangle** (#18) — agents don't trust each other to do
    their roles.

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
            "title": "GRPI Roles layer: scope overlap across all agents",
            "evidence": [
                "Coder, tester, reviewer all wrote tests this week.",
                "3 sets of duplicate tests in the codebase.",
            ],
            "intervention": (
                "Set tight scope boundaries in each agent's prompt. "
                "Cross-scope work requires explicit handoff."
            ),
        },
        {
            "severity": "high",
            "title": "Trust Triangle: agents don't trust each other's role",
            "evidence": [
                "Coder writes own tests because 'tester unreliable'.",
                "Tester writes own code because 'coder doesn't read spec'.",
            ],
            "intervention": (
                "Rebuild trust at the role boundary. Each agent's "
                "output is judged by its specific scope, not by "
                "downstream effects."
            ),
        },
        {
            "severity": "medium",
            "title": "Org Structure: matrix-like dual-report drift",
            "evidence": [
                "Reviewer reports to both tech-lead and product-orch.",
                "Conflicting priorities → role-thrash by reviewer.",
            ],
            "intervention": ("Collapse to functional structure. Single reporting line."),
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
    print("  1. TIGHT SCOPE BOUNDARIES")
    print("     Each agent's prompt: 'You do X, not Y, not Z'.")
    print()
    print("  2. SCOPED EVALUATION")
    print("     Judge each agent's output by its scope only.")
    print()
    print("  3. SINGLE REPORTING LINE")
    print("     Collapse matrix to functional structure.")
    print()
    print("  4. EXPLICIT CROSS-SCOPE HANDOFF")
    print("     Cross-scope work requires structured handoff at orchestrator.")


def main() -> None:
    print("=== Recipe: role_thrash ===")
    trace = stuck_in_loop_trace()
    report = diagnose(trace=trace, llm_client=_stub(), recipe="role_thrash")
    _print_report(report)
    _print_intervention_summary()


if __name__ == "__main__":
    main()
