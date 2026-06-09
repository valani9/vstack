"""Starter demo for pattern #28 — Devil's Advocate Separator.

Configure or audit a dedicated dissenting agent role.

This is the smallest possible per-pattern demo. It runs without an
API key by using the StubClient. For the deeper per-pattern
walkthrough see ``WALKTHROUGH.md`` in this pattern's module
directory, and for end-to-end multi-pattern recipes see
``examples/cookbook/``.

Usage:

    python examples/patterns/28_devils_advocate.py
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
    """A stub LLM client that returns generic findings.

    The findings shape is intentionally minimal — the goal of this
    demo is to show the call surface, not to produce realistic
    output. For richer output, swap in ``AnthropicClient`` /
    ``OpenAIClient`` / ``OllamaClient`` from ``vstack.aar.clients``.
    """
    finding = {
        "severity": "medium",
        "title": "Starter-demo stub finding for devils_advocate",
        "evidence": [
            "This is a placeholder evidence line.",
            "Real runs against a live LLM will produce specific findings.",
        ],
        "intervention": ("See WALKTHROUGH.md for the real interventions this pattern recommends."),
    }
    return StubClient([json.dumps([finding])] * 10)


def _print_report(report) -> None:
    """Print a one-screen summary of the diagnose() result."""
    print("Pattern: devils_advocate")
    print(f"Trace shape: {report.shape}")
    print(f"Patterns run: {len(report.per_pattern)}")
    print(f"Findings: {len(report.findings)}")
    print(f"Errors: {len(report.errors)}")
    print()
    if report.findings:
        print("Top findings:")
        for finding in report.findings[:5]:
            title = finding.title[:70]
            print(f"  [{finding.severity}] {finding.pattern}: {title}")
    else:
        print("(no findings emitted by the stub — try a real LLM client)")


def _print_next_steps() -> None:
    """Print pointers to deeper resources for this pattern."""
    print()
    print("Next steps:")
    print()
    print("  1. WALKTHROUGH.md — the 5-scenario recipe pack for this")
    print("     pattern. Find it under:")
    print("     module-*-*/NN-devils_advocate*/WALKTHROUGH.md")
    print()
    print("  2. Cookbook — end-to-end recipes that compose this pattern")
    print("     with others. Browse examples/cookbook/.")
    print()
    print("  3. Live LLM — swap StubClient for AnthropicClient /")
    print("     OpenAIClient / OllamaClient from vstack.aar.clients.")
    print()
    print("  4. CLI — every pattern ships a console script. Try:")
    print("       vstack-devils-advocate --help")


def main() -> None:
    """Build the trace, run diagnose() with this single pattern, print."""
    trace = stuck_in_loop_trace()
    print("=== Pattern starter demo: devils_advocate ===")
    print(f"Trace goal: {trace.goal!r}")
    print()

    report = diagnose(
        trace=trace,
        llm_client=_stub(),
        patterns=["devils_advocate"],
    )

    _print_report(report)
    _print_next_steps()


if __name__ == "__main__":
    main()
