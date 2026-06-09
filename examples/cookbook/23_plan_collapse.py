"""Cookbook recipe 23 — `plan_collapse`.

Scenario
--------
A multi-step plan deteriorates over execution. Early steps are
detailed and on-spec; later steps degrade to terse, generic,
or skipped. We diagnose:

  - **Yerkes-Dodson** (#06) — cognitive overload at step N.
  - **Vroom Expectancy** (#12) — Instrumentality decay across steps.
  - **GRPI** (#13) — Processes layer (handoff between steps).
  - **AAR** (#30) — retro for the failed plan.

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
            "title": "Yerkes-Dodson: HIGH arousal at steps 5-6 (context saturation)",
            "evidence": [
                "Context occupancy 80% by step 5.",
                "Output detail drops 60% step 4 → step 6.",
            ],
            "intervention": (
                "Reset context between major plan stages. Carry forward "
                "only the prior-step decision, not the full transcript."
            ),
        },
        {
            "severity": "high",
            "title": "Vroom: Instrumentality decays across multi-step plan",
            "evidence": [
                "Quality reward only at end of full plan.",
                "Effort decays linearly across steps.",
            ],
            "intervention": (
                "Add per-step reward signal. Each step gets immediate feedback on quality."
            ),
        },
        {
            "severity": "medium",
            "title": "GRPI: Processes layer — no inter-step handoff format",
            "evidence": [
                "Each step starts fresh without structured prior state.",
                "Decisions from prior steps not surfaced.",
            ],
            "intervention": (
                "Define a structured handoff Pydantic model carrying "
                "decisions, constraints, and remaining work between steps."
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
    print("  1. CONTEXT RESET BETWEEN STAGES")
    print("     Don't carry full transcript forward — only the decision.")
    print()
    print("  2. PER-STEP REWARD SIGNALS")
    print("     Each step gets a quality check before moving to next.")
    print()
    print("  3. STRUCTURED HANDOFF FORMAT")
    print("     Pydantic model between steps carrying decisions only.")
    print()
    print("  4. RUN AAR ON COLLAPSED PLAN")
    print("     Generate a structured retro to extract permanent lessons.")


def main() -> None:
    print("=== Recipe: plan_collapse ===")
    trace = stuck_in_loop_trace()
    report = diagnose(trace=trace, llm_client=_stub(), recipe="plan_collapse")
    _print_report(report)
    _print_intervention_summary()


if __name__ == "__main__":
    main()
