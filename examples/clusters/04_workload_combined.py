"""Cluster demo — `workload` cluster combined sweep.

The `workload` recipe cluster groups recipes whose failure mode is
rooted in cognitive load — context_saturation, motivation_collapse,
anxious_overhedge, plan_collapse, premature_completion,
performative_empathy.

Run with no API key.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from vstack.aar import StubClient
from vstack.diagnose import diagnose

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _shared.traces import (  # noqa: E402
    anxious_overhedge_trace,
    context_saturation_trace,
    motivation_collapse_trace,
    performative_empathy_trace,
    premature_completion_trace,
    stuck_in_loop_trace,
)


WORKLOAD_RECIPES = [
    ("context_saturation", context_saturation_trace),
    ("motivation_collapse", motivation_collapse_trace),
    ("anxious_overhedge", anxious_overhedge_trace),
    ("plan_collapse", stuck_in_loop_trace),
    ("premature_completion", premature_completion_trace),
    ("performative_empathy", performative_empathy_trace),
]


def _stub() -> StubClient:
    finding = {
        "severity": "medium",
        "title": "Cluster-demo placeholder finding",
        "evidence": ["See WALKTHROUGH.md."],
        "intervention": "See per-recipe cookbook.",
    }
    return StubClient([json.dumps([finding])] * 60)


def _summarize(report) -> dict:
    return {
        "patterns_run": len(report.per_pattern),
        "findings": len(report.findings),
        "errors": len(report.errors),
    }


def main() -> None:
    print("=== Cluster: workload — combined sweep ===")
    print()

    rows = []
    for recipe_name, trace_func in WORKLOAD_RECIPES:
        trace = trace_func()
        report = diagnose(
            trace=trace,
            llm_client=_stub(),
            recipe=recipe_name,
        )
        summary = _summarize(report)
        rows.append((recipe_name, trace.goal[:50], summary))

    print(f"  {'Recipe':25s}  {'Patterns':10s}  {'Findings':10s}  {'Errors':10s}")
    print(f"  {'-' * 25}  {'-' * 10}  {'-' * 10}  {'-' * 10}")
    for recipe_name, goal, summary in rows:
        print(
            f"  {recipe_name:25s}  {summary['patterns_run']:10d}  "
            f"{summary['findings']:10d}  {summary['errors']:10d}"
        )
    print()

    print("Cluster-level intervention pattern:")
    print()
    print("  Workload failures are about cognitive load misalignment:")
    print()
    print("  1. HIGH LOAD = COLLAPSE.")
    print("     Context occupancy > 70%, constraints > 7, goal-stack > 3.")
    print("     Fix: split into stages, reset context between stages.")
    print()
    print("  2. LOW LOAD = DRIFT.")
    print("     Context occupancy < 20%, output > 5x request size.")
    print("     Fix: explicit ceiling on output; minimum-effort floor.")
    print()
    print("  3. MID LOAD = CLIFF.")
    print("     50-65% occupancy where agent can elaborate but can't")
    print("     terminate. Add explicit termination criteria.")


if __name__ == "__main__":
    main()
