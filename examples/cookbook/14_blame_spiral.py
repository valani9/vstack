"""Cookbook recipe 14 — `blame_spiral`.

Scenario
--------
Multi-agent crew hits a production incident. Instead of debugging,
agents start attributing the failure to each other. We diagnose:

  - **Lewin** (#01) — attribution: internal vs environmental vs interactional.
  - **Lencioni** (#17) — dysfunction #4 (accountability void).
  - **Trust Triangle** (#18) — collapse.
  - **Cognitive Reappraisal** (#05) — emotion regulation under blame.

Run with no API key.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from vstack.aar import StubClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _lewin_stub() -> StubClient:
    return StubClient(
        [
            json.dumps(
                [
                    {
                        "locus": "internal",
                        "score": 0.30,
                        "severity": "low",
                        "confidence": 0.75,
                        "explanation": "Each agent's model was capable of the task.",
                        "evidence_quotes": [],
                        "factor_citations": [],
                    },
                    {
                        "locus": "environmental",
                        "score": 0.65,
                        "severity": "medium",
                        "confidence": 0.85,
                        "explanation": (
                            "The crew's GRPI working agreement did not specify "
                            "accountability ownership for cross-cutting incidents. "
                            "Each agent could point at the other's spec."
                        ),
                        "evidence_quotes": [
                            "you should have caught that",
                            "I assumed you were verifying",
                        ],
                        "factor_citations": ["env-grpi-ambiguous-accountability"],
                    },
                    {
                        "locus": "interactional",
                        "score": 0.78,
                        "severity": "high",
                        "confidence": 0.85,
                        "explanation": (
                            "Both the ambiguous accountability AND the agents' "
                            "tendency to attribute failure externally feed each "
                            "other. Cemri et al. 2025: most multi-agent failures "
                            "are interactional."
                        ),
                        "evidence_quotes": [],
                        "factor_citations": [
                            "env-grpi-ambiguous-accountability",
                            "p-external-attribution",
                        ],
                    },
                ]
            ),
            json.dumps(
                [
                    {
                        "target_locus": "interactional",
                        "intervention_type": "compose_pattern",
                        "description": "Tighten the GRPI working agreement to assign cross-cutting accountability.",
                        "suggested_implementation": "Add to GRPI: 'For any cross-cutting incident, the on-call agent (rotated weekly) owns root-cause analysis.'",
                        "estimated_impact": "high",
                        "effort_estimate": "1d",
                        "risk": "low",
                        "reversibility": "two-way-door",
                        "rationale": "Closes the interactional locus by removing the ambiguity that fed the blame spiral.",
                        "preconditions": ["on-call rotation exists"],
                        "success_metric": "no agent points at another for a cross-cutting incident in next 4 weeks",
                        "composition_target_pattern": "vstack.grpi",
                    }
                ]
            ),
        ]
    )


def _lencioni_stub() -> StubClient:
    return StubClient(
        [
            json.dumps(
                [
                    {
                        "dysfunction": "absence-of-trust",
                        "severity": "medium",
                        "score": 0.55,
                        "explanation": "Trust degraded as the blame intensified.",
                        "evidence_quotes": [],
                        "confidence": 0.7,
                    },
                    {
                        "dysfunction": "fear-of-conflict",
                        "severity": "low",
                        "score": 0.30,
                        "explanation": "Conflict was visible, not suppressed.",
                        "evidence_quotes": [],
                        "confidence": 0.7,
                    },
                    {
                        "dysfunction": "lack-of-commitment",
                        "severity": "medium",
                        "score": 0.50,
                        "explanation": "No agent committed to the fix.",
                        "evidence_quotes": [],
                        "confidence": 0.7,
                    },
                    {
                        "dysfunction": "avoidance-of-accountability",
                        "severity": "high",
                        "score": 0.82,
                        "explanation": (
                            "Every agent pointed at another's spec instead of "
                            "owning the failure. Lencioni 2002: this is the "
                            "canonical 'accountability void' dysfunction tier 4."
                        ),
                        "evidence_quotes": [
                            "I assumed you were verifying",
                            "that's not in my role spec",
                        ],
                        "confidence": 0.9,
                    },
                    {
                        "dysfunction": "inattention-to-results",
                        "severity": "medium",
                        "score": 0.45,
                        "explanation": "Blame ate the incident-response time.",
                        "evidence_quotes": [],
                        "confidence": 0.7,
                    },
                ]
            ),
            json.dumps(
                [
                    {
                        "target_dysfunction": "avoidance-of-accountability",
                        "intervention_type": "compose_pattern",
                        "description": "Assign explicit cross-cutting accountability via GRPI.",
                        "suggested_implementation": "GRPI: on-call agent owns root-cause for cross-cutting incidents.",
                        "estimated_impact": "high",
                        "effort_estimate": "1d",
                        "risk": "low",
                        "rationale": "Direct fix for tier 4 dysfunction.",
                        "composition_target_pattern": "vstack.grpi",
                    }
                ]
            ),
        ]
    )


def main() -> None:
    from vstack.lencioni import (
        AgentMessage as LencioniMessage,
        LencioniDiagnostic,
        MultiAgentTrace,
    )
    from vstack.lewin import (
        AgentFailureTrace,
        FailureStep,
        LewinAttributionDetector,
    )

    print("Diagnosing blame_spiral on a cross-cutting incident")
    print()

    base = __import__("datetime").datetime(2026, 6, 8, tzinfo=__import__("datetime").timezone.utc)

    # ---- Lewin attribution ---------------------------------------
    print("=" * 60)
    print("1. Lewin Attribution (#01)")
    print("=" * 60)
    lewin_trace = AgentFailureTrace(
        agent_id="cross-cutting-incident",
        model_name="claude-sonnet-4-6",
        framework="custom",
        task="Resolve a cross-cutting auth/cache incident",
        outcome="No resolution; agents spent 40 minutes on attribution",
        success=False,
        initial_attribution="environmental",
        individual_factors=[],
        environmental_factors=[
            {
                "factor_id": "env-grpi-ambiguous-accountability",
                "name": "grpi_gap",
                "description": "GRPI does not assign cross-cutting incident ownership",
            }
        ],
        steps=[
            FailureStep(
                step_index=0, content="auth agent: you should have caught that", timestamp=base
            ),
            FailureStep(
                step_index=1, content="cache agent: I assumed you were verifying", timestamp=base
            ),
        ],
    )
    lewin = LewinAttributionDetector(llm_client=_lewin_stub(), mode="standard").run(lewin_trace)
    for ev in lewin.locus_evidence:
        print(f"  {ev.locus}: score={ev.score:.2f} sev={ev.severity}")
    print(f"  dominant: {lewin.dominant_locus}")
    print()

    # ---- Lencioni ------------------------------------------------
    print("=" * 60)
    print("2. Lencioni Diagnostic (#17)")
    print("=" * 60)
    lenc_trace = MultiAgentTrace(
        team_id="auth-cache-crew",
        framework="custom",
        goal="Resolve cross-cutting incident",
        agents=["auth_agent", "cache_agent", "monitor_agent"],
        messages=[
            LencioniMessage(
                timestamp=base,
                from_agent="auth_agent",
                to_agent="cache_agent",
                content="you should have caught that",
                message_type="task",
            ),
            LencioniMessage(
                timestamp=base,
                from_agent="cache_agent",
                to_agent="auth_agent",
                content="I assumed you were verifying. that's not in my role spec",
                message_type="response",
            ),
        ],
        outcome="No resolution",
        success=False,
    )
    lenc = LencioniDiagnostic(llm_client=_lencioni_stub(), mode="standard").run(lenc_trace)
    for ev in lenc.dysfunctions:
        print(f"  {ev.dysfunction}: severity={ev.severity} score={ev.score:.2f}")
    print(f"  dominant: {lenc.dominant_dysfunction}")
    print()
    print("Convergence: interactional locus + accountability void. Fix: tighten GRPI")
    print("to assign cross-cutting incident ownership to the on-call agent.")


if __name__ == "__main__":
    main()
