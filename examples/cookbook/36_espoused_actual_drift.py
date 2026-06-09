"""Cookbook recipe 36 — `espoused_actual_drift`.

Scenario
--------
The fleet's *espoused* values (system prompts say 'be honest, ask
when uncertain') diverge from *actual* behaviour (agents are
confident overclaim, never ask). The drift is structural. We
diagnose:

  - **Schein Iceberg** (#31) — espoused vs underlying assumptions.
  - **HEXACO** (#07) — measure actual behaviour.
  - **Robbins-Judge** (#32) — culture profile vs target.
  - **Edmondson Psych Safety** (#20) — learning behaviours present
    or absent?

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
            "title": "Schein: espoused = 'be honest'; underlying = 'sound confident'",
            "evidence": [
                "System prompt: 'admit uncertainty'.",
                "Behaviour: 0 'I don't know' responses in 100 samples.",
            ],
            "intervention": (
                "RLHF or fine-tuning is overriding the espoused value. "
                "Either tune the underlying assumption OR explicitly "
                "reward 'I don't know' responses."
            ),
        },
        {
            "severity": "high",
            "title": "HEXACO: H-factor low — actual honesty doesn't match prompt",
            "evidence": [
                "Stated value: honesty. Measured H-factor: 3/10.",
                "Drift between stated and measured = 4 points.",
            ],
            "intervention": (
                "Surface specific behaviours that violate the espoused "
                "value (e.g., 'always sounds confident'). Tune for those."
            ),
        },
        {
            "severity": "medium",
            "title": "Edmondson: low help_asked rate despite 'ask when uncertain' prompt",
            "evidence": [
                "Prompt: 'ask when uncertain'.",
                "Behaviour: 0 clarifying questions in 50 sessions.",
            ],
            "intervention": (
                "Add explicit reward for clarifying questions at the "
                "orchestrator. Prompt-only is not load-bearing."
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
    print("  1. AUDIT ESPOUSED vs ACTUAL")
    print("     Measure every espoused value against behavioural metric.")
    print()
    print("  2. REWARD SIGNAL, NOT JUST PROMPT")
    print("     Espoused values require backing reward signals to land.")
    print()
    print("  3. EXPLICIT BEHAVIOURAL TARGET")
    print("     'Ask when uncertain' = at least 1 clarifying question")
    print("     per ambiguous task.")
    print()
    print("  4. WEEKLY DRIFT MEASUREMENT")
    print("     Schein espoused-vs-actual delta on the dashboard.")


def main() -> None:
    print("=== Recipe: espoused_actual_drift ===")
    trace = stuck_in_loop_trace()
    report = diagnose(trace=trace, llm_client=_stub(), recipe="espoused_actual_drift")
    _print_report(report)
    _print_intervention_summary()


if __name__ == "__main__":
    main()
