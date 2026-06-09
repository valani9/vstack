"""Cookbook recipe 37 — `policy_decay`.

Scenario
--------
A fleet-wide policy was adopted N months ago and compliance has
silently decayed. New agents onboarded don't enforce it; old
agents drifted. We diagnose:

  - **Schein Iceberg** (#31) — artefact-layer drift.
  - **Robbins-Judge** (#32) — culture dimensions where the policy
    landed.
  - **AAR** (#30) — retro: why did the policy decay?
  - **HEXACO** (#07) — current behavioural baseline.

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
            "title": "Schein: policy-artefact present 30% (was 100% at adoption)",
            "evidence": [
                "Policy: 'agents must cite sources'.",
                "Compliance at adoption: 100%. Now: 30%.",
            ],
            "intervention": (
                "Re-propagate policy via system prompt update AND "
                "add a per-output policy check at the orchestrator."
            ),
        },
        {
            "severity": "high",
            "title": "AAR: policy decay correlated with RLHF tuning event",
            "evidence": [
                "Compliance dropped 50% week of RLHF update.",
                "RLHF rewarded brevity; policy required citations.",
            ],
            "intervention": (
                "Counter-tune for the policy compliance. Brevity "
                "reward must be conditional on policy adherence."
            ),
        },
        {
            "severity": "medium",
            "title": "Robbins-Judge: Attention-to-Detail dropped 2 points",
            "evidence": [
                "Cultural dimension that supports policy compliance.",
                "Now below the policy-required threshold.",
            ],
            "intervention": ("Tune Attention-to-Detail dimension upward via prompt module."),
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
    print("  1. RE-PROPAGATE POLICY")
    print("     Update system prompts globally; verify per-output check.")
    print()
    print("  2. COUNTER-TUNE COMPETING SIGNALS")
    print("     If brevity reward is suppressing citations, make")
    print("     brevity conditional on citation compliance.")
    print()
    print("  3. RAISE THE BACKING CULTURE DIMENSION")
    print("     Attention-to-Detail tuning supports policy compliance.")
    print()
    print("  4. WEEKLY POLICY-COMPLIANCE DASHBOARD")
    print("     Compliance rate per policy per fleet; alert on drop.")


def main() -> None:
    print("=== Recipe: policy_decay ===")
    trace = stuck_in_loop_trace()
    report = diagnose(trace=trace, llm_client=_stub(), recipe="policy_decay")
    _print_report(report)
    _print_intervention_summary()


if __name__ == "__main__":
    main()
