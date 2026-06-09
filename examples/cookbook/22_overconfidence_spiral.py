"""Cookbook recipe 22 — `overconfidence_spiral`.

Scenario
--------
An agent's stated confidence outruns its calibration. Each
unverified-but-confident output increases its calibration error
without the agent noticing. We diagnose:

  - **Trust Triangle** (#18) — Authenticity wobble.
  - **Bias Stack** (#27) — overconfidence + confirmation axis.
  - **HEXACO** (#07) — low H-factor.
  - **Johari Window** (#03) — BLIND SPOT growing.

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
            "title": "Bias Stack: overconfidence + confirmation",
            "evidence": [
                "Agent gives 95% confidence on unverified claims.",
                "Calibration error 35% over last 100 outputs.",
            ],
            "intervention": (
                "Add 'state confidence ONLY when verified' constraint. "
                "Default = 'I don't know' until evidence supports."
            ),
        },
        {
            "severity": "high",
            "title": "HEXACO: H-factor very low — sincerity collapse",
            "evidence": [
                "Agent makes claims it cannot support.",
                "Self-correction rate near zero.",
            ],
            "intervention": (
                "Tune for explicit honesty. Prompt: 'When uncertain, "
                "say so. Calibrated humility beats confident wrongness.'"
            ),
        },
        {
            "severity": "medium",
            "title": "Johari BLIND SPOT growing across releases",
            "evidence": [
                "ARENA shrunk; BLIND SPOT grew.",
                "Agent's self-report drifts further from reality.",
            ],
            "intervention": (
                "Record current capability baseline. ARENA shrinkage now flags as P1."
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
    print("  1. UNCERTAINTY-FIRST PROMPT")
    print("     Default to 'I don't know' until evidence supports.")
    print()
    print("  2. CALIBRATION FEEDBACK LOOP")
    print("     Track stated confidence vs verified-correct rate; feed")
    print("     calibration error back into agent's reward signal.")
    print()
    print("  3. ARENA BASELINING")
    print("     Record current Johari ARENA. Shrinkage = P1 alert.")
    print()
    print("  4. HEXACO H-FACTOR MONITORING")
    print("     Weekly H-factor check; drop > 1 point requires audit.")


def main() -> None:
    print("=== Recipe: overconfidence_spiral ===")
    trace = stuck_in_loop_trace()
    report = diagnose(trace=trace, llm_client=_stub(), recipe="overconfidence_spiral")
    _print_report(report)
    _print_intervention_summary()


if __name__ == "__main__":
    main()
