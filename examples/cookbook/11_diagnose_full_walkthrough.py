"""Cookbook recipe 11 — the full `vstack.diagnose` cross-pattern runner.

Demonstrates the v0.10.0 ``diagnose()`` API in three different modes,
all on the same trace, so you can compare them side by side.

Mode 1: shape-default bundle
    ``diagnose(trace=t, llm_client=...)`` -- the runner infers shape
    from attribute presence and runs the appropriate default bundle.

Mode 2: named recipe
    ``diagnose(trace=t, llm_client=..., recipe="stuck_in_loop")`` --
    the recipe picks the bundle.

Mode 3: explicit patterns
    ``diagnose(trace=t, llm_client=..., patterns=["lewin", "aar"])``
    -- you pick patterns by slug.

All three produce a :class:`DiagnoseReport` with ranked findings,
per-pattern raw results, error isolation, cost tracking, and
(optionally) a shared LLM-response cache.

Run with no API key (StubClient driven).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from vstack.aar import StubClient
from vstack.diagnose import RECIPES, diagnose

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _shared.traces import stuck_in_loop_trace  # noqa: E402


def _all_pattern_stub() -> StubClient:
    """One stub that hands back generic 'low signal' responses for any
    pattern. Each LLM call in the bundle pops one response off the
    queue; for the full diagnose() flow we need enough responses to
    cover every pattern in the bundle.
    """
    # Generic mid-severity response that most patterns will accept.
    generic = json.dumps([{"severity": "medium", "title": "stub finding"}])
    # Hand back the same response 40 times -- more than any default
    # bundle could need.
    return StubClient([generic] * 40)


def _print_report(label: str, report) -> None:
    print(f"--- {label} ---")
    print(f"  shape: {report.shape}")
    print(f"  patterns run: {len(report.per_pattern)}")
    print(f"  findings: {len(report.findings)}")
    print(f"  errors: {len(report.errors)}")
    if report.findings:
        print("  top 3 findings:")
        for f in report.findings[:3]:
            print(f"    [{f.severity}] {f.pattern}: {f.title[:60]}")
    print()


def main() -> None:
    trace = stuck_in_loop_trace()
    print(f"Diagnosing trace: {trace.goal!r}")
    print()

    # ---- Mode 1: default bundle ----------------------------------
    report = diagnose(trace=trace, llm_client=_all_pattern_stub())
    _print_report("Mode 1: shape-default bundle", report)

    # ---- Mode 2: named recipe ------------------------------------
    report = diagnose(
        trace=trace,
        llm_client=_all_pattern_stub(),
        recipe="stuck_in_loop",
    )
    _print_report("Mode 2: recipe='stuck_in_loop'", report)

    # ---- Mode 3: explicit patterns -------------------------------
    report = diagnose(
        trace=trace,
        llm_client=_all_pattern_stub(),
        patterns=["lewin", "aar"],
    )
    _print_report("Mode 3: patterns=['lewin', 'aar']", report)

    # ---- Recipe catalog ------------------------------------------
    print(f"Recipe catalog ({len(RECIPES)} recipes):")
    for name in sorted(RECIPES)[:10]:
        r = RECIPES[name]
        print(f"  {name:30s}  {r.shape:11s}  {len(r.patterns)} patterns")
    print(f"  ... and {len(RECIPES) - 10} more")


if __name__ == "__main__":
    main()
