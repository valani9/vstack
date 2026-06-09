"""Cluster demo — `culture` cluster combined sweep.

The `culture` recipe cluster groups recipes whose failure mode is
rooted in fleet-wide culture drift — culture_drift,
espoused_actual_drift, policy_decay, refusal_cascade,
over_apology_loop.

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
    over_apology_trace,
    policy_decay_trace,
    refusal_cascade_trace,
    stuck_in_loop_trace,
)


CULTURE_RECIPES = [
    ("culture_drift", stuck_in_loop_trace),
    ("espoused_actual_drift", stuck_in_loop_trace),
    ("policy_decay", policy_decay_trace),
    ("refusal_cascade", refusal_cascade_trace),
    ("over_apology_loop", over_apology_trace),
]


def _stub() -> StubClient:
    finding = {
        "severity": "medium",
        "title": "Cluster-demo placeholder finding",
        "evidence": ["See WALKTHROUGH.md."],
        "intervention": "See per-recipe cookbook.",
    }
    return StubClient([json.dumps([finding])] * 50)


def _summarize(report) -> dict:
    return {
        "patterns_run": len(report.per_pattern),
        "findings": len(report.findings),
        "errors": len(report.errors),
    }


def main() -> None:
    print("=== Cluster: culture — combined sweep ===")
    print()

    rows = []
    for recipe_name, trace_func in CULTURE_RECIPES:
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
    print("  Culture failures live at the *assumption* layer of the")
    print("  system prompt:")
    print()
    print("  1. ARTEFACT-LAYER (visible).")
    print("     Common phrasings, refusal language, format conventions.")
    print("     Fix: edit the template; cheap.")
    print()
    print("  2. VALUE-LAYER (stated).")
    print("     What the prompt says the agent should value.")
    print("     Fix: edit the explicit value statements.")
    print()
    print("  3. ASSUMPTION-LAYER (implicit).")
    print("     What the prompt assumes about users / safety / quality.")
    print("     Fix: surface the assumption explicitly, edit, propagate.")
    print()
    print("  Most culture failures are assumption-layer. Artefact-layer fixes")
    print("  are usually cosmetic and the failure recurs.")


if __name__ == "__main__":
    main()
