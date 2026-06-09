"""Cluster demo — `reasoning` cluster combined sweep.

The `reasoning` recipe cluster groups all named recipes whose
failure mode is rooted in the agent's *reasoning chain* — stuck
loops, hallucination cascades, overconfidence, plan collapse,
context saturation, tool misuse.

This demo runs the four canonical reasoning recipes against
representative traces and prints a side-by-side summary showing
which patterns each recipe fires on. Useful when you want to
*understand the cluster* before deploying any individual recipe.

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
    context_saturation_trace,
    hallucination_cascade_trace,
    overconfidence_spiral_trace,
    stuck_in_loop_trace,
    tool_misuse_trace,
)


REASONING_RECIPES = [
    ("stuck_in_loop", stuck_in_loop_trace),
    ("hallucination_cascade", hallucination_cascade_trace),
    ("overconfidence_spiral", overconfidence_spiral_trace),
    ("context_saturation", context_saturation_trace),
    ("tool_misuse", tool_misuse_trace),
]


def _stub() -> StubClient:
    """A stub that returns generic findings sufficient for the demo.

    Real runs against a flagship LLM produce specific, scored
    findings keyed to the actual trace content.
    """
    finding = {
        "severity": "medium",
        "title": "Cluster-demo placeholder finding",
        "evidence": ["See WALKTHROUGH.md for the per-pattern surface."],
        "intervention": "See per-recipe cookbook for the intervention bundle.",
    }
    return StubClient([json.dumps([finding])] * 50)


def _summarize(report) -> dict:
    return {
        "patterns_run": len(report.per_pattern),
        "findings": len(report.findings),
        "errors": len(report.errors),
    }


def main() -> None:
    print("=== Cluster: reasoning — combined sweep ===")
    print()
    print("Running 5 reasoning recipes against representative traces.")
    print()

    rows = []
    for recipe_name, trace_func in REASONING_RECIPES:
        trace = trace_func()
        report = diagnose(
            trace=trace,
            llm_client=_stub(),
            recipe=recipe_name,
        )
        summary = _summarize(report)
        rows.append((recipe_name, trace.goal[:50], summary))

    # Print summary table.
    print(f"  {'Recipe':25s}  {'Patterns':10s}  {'Findings':10s}  {'Errors':10s}")
    print(f"  {'-' * 25}  {'-' * 10}  {'-' * 10}  {'-' * 10}")
    for recipe_name, goal, summary in rows:
        print(
            f"  {recipe_name:25s}  {summary['patterns_run']:10d}  "
            f"{summary['findings']:10d}  {summary['errors']:10d}"
        )
    print()

    # Print per-recipe goals.
    print("Trace goals:")
    for recipe_name, goal, _ in rows:
        print(f"  {recipe_name}: {goal!r}")
    print()

    # Print cluster-level intervention pattern.
    print("Cluster-level intervention pattern:")
    print()
    print("  Reasoning failures are typically downstream of one of three")
    print("  upstream causes:")
    print()
    print("  1. PROMPT UNDER-SPECIFICATION (Lewin: environmental locus).")
    print("     The prompt doesn't constrain the agent enough to avoid the")
    print("     failure shape. Fix at the prompt layer, not the model.")
    print()
    print("  2. REWARD-SIGNAL CAPTURE (Motivation Traps).")
    print("     The eval metric rewards a proxy (citation count, tool")
    print("     calls, confidence) at the cost of the actual goal.")
    print()
    print("  3. CONTEXT MANAGEMENT FAILURE (Yerkes-Dodson).")
    print("     The agent is over- or under-loaded. Reset context boundaries,")
    print("     scale prompt to load.")
    print()
    print("  Once you've named which of the three is dominant, run the")
    print("  per-recipe walkthrough for the matched intervention bundle.")


if __name__ == "__main__":
    main()
