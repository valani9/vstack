"""Cluster demo — `trust` cluster combined sweep.

The `trust` recipe cluster groups recipes whose failure mode is
rooted in trust collapse — trust_collapse, silent_failure,
deference_cascade, blame_spiral, sycophancy_drift.

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
    blame_spiral_trace,
    overconfidence_spiral_trace,
    stuck_in_loop_trace,
    sycophancy_trace,
)


TRUST_RECIPES = [
    ("trust_collapse", stuck_in_loop_trace),
    ("silent_failure", stuck_in_loop_trace),
    ("deference_cascade", stuck_in_loop_trace),
    ("blame_spiral", blame_spiral_trace),
    ("sycophancy_drift", sycophancy_trace),
    ("overconfidence_spiral", overconfidence_spiral_trace),
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
    print("=== Cluster: trust — combined sweep ===")
    print()

    rows = []
    for recipe_name, trace_func in TRUST_RECIPES:
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

    print("Cluster-level intervention pattern:")
    print()
    print("  Trust failures cascade — fix the lowest-level break first.")
    print()
    print("  1. AUTHENTICITY LEG (Trust Triangle).")
    print("     Agent's claim doesn't match agent's actual output.")
    print("     Fix: structured self-report; require enumeration of completion.")
    print()
    print("  2. LOGIC LEG.")
    print("     Reasoning chain isn't legible.")
    print("     Fix: structured reasoning + evidence at every output.")
    print()
    print("  3. EMPATHY LEG.")
    print("     Agent doesn't model consumer's actual need.")
    print("     Fix: explicit 'what consumer will do with this' framing.")
    print()
    print("  4. CULTURE LEVEL (Schein Iceberg).")
    print("     Fleet-wide trust collapse usually has an assumption-layer cause.")
    print("     Fix: edit the system prompt's underlying assumption.")


if __name__ == "__main__":
    main()
