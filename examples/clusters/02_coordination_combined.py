"""Cluster demo — `coordination` cluster combined sweep.

The `coordination` recipe cluster groups all recipes whose failure
mode is rooted in *multi-agent coordination* — bottlenecks, handoff
loss, consensus dilution, cold handoff, role thrash, hyper-
specialization.

This demo runs the canonical coordination recipes against
representative traces and prints a comparative summary. Useful
when the team is struggling and you don't yet know which
coordination dimension is broken.

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
    bottleneck_orchestrator_trace,
    cold_handoff_trace,
    consensus_dilution_trace,
    role_thrash_trace,
    stuck_in_loop_trace,
)


COORDINATION_RECIPES = [
    ("bottleneck_orchestrator", bottleneck_orchestrator_trace),
    ("cold_handoff", cold_handoff_trace),
    ("consensus_dilution", consensus_dilution_trace),
    ("role_thrash", role_thrash_trace),
    ("hub_spoke_fragility", stuck_in_loop_trace),
    ("hyper_specialization", stuck_in_loop_trace),
]


def _stub() -> StubClient:
    finding = {
        "severity": "medium",
        "title": "Cluster-demo placeholder finding",
        "evidence": ["See WALKTHROUGH.md for per-pattern surface."],
        "intervention": "See per-recipe cookbook for intervention bundle.",
    }
    return StubClient([json.dumps([finding])] * 60)


def _summarize(report) -> dict:
    return {
        "patterns_run": len(report.per_pattern),
        "findings": len(report.findings),
        "errors": len(report.errors),
    }


def main() -> None:
    print("=== Cluster: coordination — combined sweep ===")
    print()
    print("Running 6 coordination recipes against representative traces.")
    print()

    rows = []
    for recipe_name, trace_func in COORDINATION_RECIPES:
        trace = trace_func()
        report = diagnose(
            trace=trace,
            llm_client=_stub(),
            recipe=recipe_name,
        )
        summary = _summarize(report)
        rows.append((recipe_name, trace.goal[:50], summary))

    print(f"  {'Recipe':30s}  {'Patterns':10s}  {'Findings':10s}  {'Errors':10s}")
    print(f"  {'-' * 30}  {'-' * 10}  {'-' * 10}  {'-' * 10}")
    for recipe_name, goal, summary in rows:
        print(
            f"  {recipe_name:30s}  {summary['patterns_run']:10d}  "
            f"{summary['findings']:10d}  {summary['errors']:10d}"
        )
    print()

    print("Trace goals:")
    for recipe_name, goal, _ in rows:
        print(f"  {recipe_name}: {goal!r}")
    print()

    print("Cluster-level intervention pattern:")
    print()
    print("  Coordination failures are typically driven by one of:")
    print()
    print("  1. WRONG SPAN OF CONTROL.")
    print("     Orchestrator manages too many or too few sub-agents.")
    print("     Fix: split into mid-level orchestrators or absorb more workers.")
    print()
    print("  2. UNSTRUCTURED HANDOFF.")
    print("     Information drops at every cross-agent boundary.")
    print("     Fix: shared handoff schema (goal/constraints/output/questions).")
    print()
    print("  3. ROLE SCOPE OVERLAP OR THRASH.")
    print("     Multiple agents claim the same scope.")
    print("     Fix: tighten role definitions; cross-scope work requires explicit")
    print("     orchestrator handoff.")
    print()
    print("  4. WRONG STRUCTURE FOR TASK.")
    print("     Matrix where Functional fits, or vice versa.")
    print("     Fix: restructure at the orchestrator level.")


if __name__ == "__main__":
    main()
