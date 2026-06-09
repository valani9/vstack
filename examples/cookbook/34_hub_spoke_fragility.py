"""Cookbook recipe 34 — `hub_spoke_fragility`.

Scenario
--------
An orchestrator has become a single point of failure. When the
orchestrator is slow / wrong / unavailable, the entire fleet stalls.
We diagnose:

  - **Span of Control** (#34) — orchestrator span exceeded.
  - **Bottleneck Orchestrator recipe** — composed pattern.
  - **Org Structure Matrix** (#33) — hub-and-spoke structure.
  - **McGregor** (#11) — orchestrator running Theory-X on too many.

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
            "title": "Span of Control: 18 workers under one orchestrator",
            "evidence": [
                "Orchestrator span = 18 for high-precision codegen.",
                "Recommended span = 5-7 for that task type.",
            ],
            "intervention": (
                "Add a middle layer: 3 mid-orchestrators each managing "
                "6 workers. Top-orch manages the 3."
            ),
        },
        {
            "severity": "high",
            "title": "Org Structure: hub-and-spoke with no spoke autonomy",
            "evidence": [
                "Workers can't act without orchestrator approval.",
                "When orch is offline, all 18 workers idle.",
            ],
            "intervention": (
                "Move to functional structure with mid-level "
                "orchestrators having authority on routine decisions."
            ),
        },
        {
            "severity": "medium",
            "title": "McGregor: Theory-X applied to all 18 workers",
            "evidence": [
                "Every worker output is verified by orchestrator.",
                "0 trust graduations in 30 days.",
            ],
            "intervention": (
                "Graduate workers with clean records to Theory-Y. Verify only critical surfaces."
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
    print("  1. ADD MID-LAYER")
    print("     3 mid-orchestrators × 6 workers each.")
    print()
    print("  2. AUTONOMY ON ROUTINE DECISIONS")
    print("     Mid-orchs decide; top-orch escalates exceptions.")
    print()
    print("  3. GRADUATE TO THEORY-Y")
    print("     Workers with clean records get verification graduation.")
    print()
    print("  4. ELIMINATE SINGLE POINT OF FAILURE")
    print("     Verify the fleet can run if any single agent is offline.")


def main() -> None:
    print("=== Recipe: hub_spoke_fragility ===")
    trace = stuck_in_loop_trace()
    report = diagnose(trace=trace, llm_client=_stub(), recipe="hub_spoke_fragility")
    _print_report(report)
    _print_intervention_summary()


if __name__ == "__main__":
    main()
