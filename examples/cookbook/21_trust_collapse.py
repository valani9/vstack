"""Cookbook recipe 21 — `trust_collapse`.

Scenario
--------
Members of a multi-agent crew have stopped trusting each other's
outputs and are over-verifying. The team's effective capacity is the
slowest verifier. We diagnose:

  - **Trust Triangle** (#18) — which leg broke?
  - **McAllister Trust Dimensions** (#19) — cognition vs affect.
  - **Lencioni** (#17) — Dysfunction #1 (Absence of Trust).
  - **GRPI** (#13) — Interpersonal layer.

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
            "title": "Trust Triangle: Authenticity leg broken across team",
            "evidence": [
                "Each agent's stated output != actual output 30% of time.",
                "Cross-agent re-verification rate is 100%.",
            ],
            "intervention": (
                "Require structured self-report ('I did X, Y, Z') on "
                "every output. Reject bare 'done' messages."
            ),
        },
        {
            "severity": "high",
            "title": "McAllister: cognition trust normal, affect trust collapsed",
            "evidence": [
                "Outputs verify correctly (cognition OK).",
                "Agents don't reference each other's downstream needs.",
            ],
            "intervention": (
                "Add 'reference consumer's need' to every cross-agent "
                "output. Affect trust requires demonstrated care."
            ),
        },
        {
            "severity": "medium",
            "title": "Lencioni: Trust dysfunction blocking 4 layers above",
            "evidence": [
                "Conflict / Commitment / Accountability / Results all broken.",
                "Trust is the upstream cause.",
            ],
            "intervention": ("Fix Trust first; the other 4 dysfunctions will unblock."),
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
    print("  1. STRUCTURED SELF-REPORT")
    print("     Every cross-agent output must enumerate completion.")
    print()
    print("  2. CONSUMER-AWARENESS PROMPT")
    print("     Each agent references the downstream consumer's need.")
    print()
    print("  3. SUSPEND VERIFICATION GRADUATION")
    print("     Until trust rebuilds, the orchestrator verifies all")
    print("     handoffs explicitly (Theory-X mode).")
    print()
    print("  4. PROGRESSIVELY RELAX")
    print("     After N clean handoffs, drop verification rate by half.")
    print("     The relaxation IS the trust rebuild signal.")


def main() -> None:
    print("=== Recipe: trust_collapse ===")
    trace = stuck_in_loop_trace()
    report = diagnose(trace=trace, llm_client=_stub(), recipe="trust_collapse")
    _print_report(report)
    _print_intervention_summary()


if __name__ == "__main__":
    main()
