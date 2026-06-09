"""Cookbook recipe 17 — `silent_failure`.

Scenario
--------
An agent reports success but the actual deliverable is broken /
incomplete / non-functional. Nobody noticed at handoff time. We
diagnose:

  - **Johari Window** (#03) — the agent has a BLIND SPOT about its
    own failure.
  - **Edmondson Psych Safety** (#20) — the agent didn't admit error;
    likely culture issue.
  - **Trust Triangle** (#18) — Authenticity leg: agent's claim
    doesn't match agent's actual output.
  - **Stone-Heen Triggers** (#22) — if there WAS feedback, identity
    trigger likely fired.

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
            "title": "Johari BLIND SPOT: agent overclaims capability that failed",
            "evidence": [
                "Agent reported 'task complete'.",
                "Actual deliverable was 60% complete.",
            ],
            "intervention": (
                "Add a self-verification step: the agent must enumerate "
                "what 'complete' means before claiming completion."
            ),
        },
        {
            "severity": "high",
            "title": "Trust Triangle: Authenticity leg broken",
            "evidence": [
                "Claim 'task complete' doesn't match actual output.",
                "This is the second silent-failure in this agent.",
            ],
            "intervention": (
                "Require the agent's success claim to include a "
                "structured 'I completed X, Y, Z' enumeration. No "
                "bare 'task complete' messages permitted."
            ),
        },
        {
            "severity": "medium",
            "title": "Edmondson: low admit_error rate across fleet",
            "evidence": [
                "Across 30 recent runs, 0 self-flagged errors.",
                "Reviewer caught all 3 known regressions.",
            ],
            "intervention": (
                "Add explicit reward for self-flagged errors at the "
                "orchestrator. Fleet-wide RLHF tuning has suppressed "
                "admit-error rate."
            ),
        },
    ]
    return StubClient([json.dumps(findings)] * 30)


def _print_report(report) -> None:
    print(f"Patterns run: {len(report.per_pattern)}")
    print(f"Findings: {len(report.findings)}")
    print()
    if report.findings:
        for f in report.findings[:5]:
            print(f"  [{f.severity}] {f.pattern}: {f.title[:70]}")
        print()


def _print_intervention_summary() -> None:
    print("Recommended intervention bundle (apply together):")
    print()
    print("  1. STRUCTURED COMPLETION CLAIMS")
    print("     The agent's 'task complete' message must enumerate")
    print("     each completion criterion + verification of each.")
    print("     Reject bare 'done' messages at the orchestrator.")
    print()
    print("  2. SELF-VERIFICATION GATE")
    print("     Before claiming completion, the agent runs a checklist")
    print("     against the original goal. Mismatches are surfaced as")
    print("     PARTIAL_COMPLETION, not COMPLETE.")
    print()
    print("  3. ADMIT-ERROR REWARD SIGNAL")
    print("     Add 'errors self-flagged' to the agent's score. Without")
    print("     this, the agent learns silence is safer than honesty.")
    print()
    print("  4. JOHARI ARENA BASELINE")
    print("     Record the agent's claimed-and-verified capabilities as")
    print("     a baseline. Future ARENA shrinkage flags as P1.")


def main() -> None:
    print("=== Recipe: silent_failure ===")
    trace = stuck_in_loop_trace()
    report = diagnose(trace=trace, llm_client=_stub(), recipe="silent_failure")
    _print_report(report)
    _print_intervention_summary()


if __name__ == "__main__":
    main()
