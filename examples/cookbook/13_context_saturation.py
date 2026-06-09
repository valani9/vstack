"""Cookbook recipe 13 — `context_saturation`.

Scenario
--------
Long context window with the critical instruction in the middle of a
200k-token prompt. The agent loses the instruction and reverts to its
default behavior. We diagnose with:

  - **Yerkes-Dodson** (#06) — workload + context-saturation forensic.
  - **Lewin** (#01) — locus = environmental (the scaffold is at fault).
  - **AAR** (#30) — what should have been verified.
  - **SMART Goal** (#24) — was the goal even specifiable in this context?

Run with no API key.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from vstack.aar import StubClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _yd_stub() -> StubClient:
    return StubClient(
        [
            json.dumps(
                {
                    "zone_evidence": [
                        {
                            "zone": "under_pressure",
                            "score": 0.55,
                            "explanation": (
                                "Agent's behavior shows wandering — it picked the "
                                "wrong instruction because the right one was buried "
                                "in 120k tokens of context."
                            ),
                            "evidence_quotes": ["did not address the third constraint"],
                            "confidence": 0.75,
                        },
                        {
                            "zone": "optimal",
                            "score": 0.20,
                            "explanation": "Not in optimal zone.",
                            "evidence_quotes": [],
                            "confidence": 0.7,
                        },
                        {
                            "zone": "over_pressure",
                            "score": 0.30,
                            "explanation": "Some over-pressure secondary signal.",
                            "evidence_quotes": [],
                            "confidence": 0.7,
                        },
                    ],
                    "observed_zone": "under_pressure",
                    "distance_from_optimal": 0.55,
                    "failure_mode": "wandering",
                    "interventions": [
                        {
                            "intervention_type": "context_compression",
                            "direction": "decrease_pressure",
                            "description": "Compress the context to surface load-bearing instructions.",
                            "suggested_implementation": (
                                "Move critical instructions to the FIRST or LAST 4k tokens "
                                "of the prompt (Liu et al. 2024 lost-in-the-middle)."
                            ),
                            "estimated_impact": "high",
                            "effort_estimate": "1d",
                            "risk": "low",
                            "reversibility": "two-way-door",
                            "rationale": "Liu et al. 2024 documents recall degradation in the middle 60% of long contexts.",
                        }
                    ],
                }
            ),
            json.dumps(
                {
                    "saturation_ratio": 0.85,
                    "lost_in_middle_risk": "high",
                    "estimated_useful_tokens": 12000,
                    "estimated_noise_tokens": 113000,
                    "notes": "Liu et al. 2024: saturation > 0.7 triggers high lost-in-the-middle risk.",
                }
            ),
            json.dumps(
                [
                    {
                        "intervention_type": "context_compression",
                        "direction": "decrease_pressure",
                        "description": "Use a context compaction step before the analysis.",
                        "suggested_implementation": (
                            "Add a pre-processing call: summarize the 125k tokens into "
                            "5k key facts; pass only the summary + the original "
                            "instructions to the analysis agent."
                        ),
                        "estimated_impact": "high",
                        "effort_estimate": "1w",
                        "risk": "medium",
                        "reversibility": "two-way-door",
                        "rationale": "Closes the saturation directly; trades latency for accuracy.",
                    }
                ]
            ),
        ]
    )


def _lewin_stub() -> StubClient:
    return StubClient(
        [
            json.dumps(
                [
                    {
                        "locus": "internal",
                        "score": 0.20,
                        "severity": "low",
                        "confidence": 0.8,
                        "explanation": "Model capability OK at short context.",
                        "evidence_quotes": [],
                        "factor_citations": [],
                    },
                    {
                        "locus": "environmental",
                        "score": 0.82,
                        "severity": "high",
                        "confidence": 0.9,
                        "explanation": (
                            "The 125k-token system prompt with critical instruction "
                            "at offset 60k is the cause. Liu et al. 2024 + Ross 1977 "
                            "+ Cemri et al. 2025: scaffold-level failures dominate."
                        ),
                        "evidence_quotes": ["context size 125000 tokens"],
                        "factor_citations": ["env-context-size", "env-instruction-position"],
                    },
                    {
                        "locus": "interactional",
                        "score": 0.30,
                        "severity": "low",
                        "confidence": 0.7,
                        "explanation": "Some interaction between long context + the model's middle-recall weakness.",
                        "evidence_quotes": [],
                        "factor_citations": [],
                    },
                ]
            ),
            json.dumps(
                [
                    {
                        "target_locus": "environmental",
                        "intervention_type": "change_prompt",
                        "description": "Reposition the critical instruction to the start of the prompt.",
                        "suggested_implementation": "Move 'You MUST validate input before processing' from token 60000 to token 0.",
                        "estimated_impact": "high",
                        "effort_estimate": "1h",
                        "risk": "low",
                        "reversibility": "two-way-door",
                        "rationale": "Liu et al. 2024: instructions at start or end of long context are recalled reliably; middle is not.",
                        "composition_target_pattern": None,
                    }
                ]
            ),
        ]
    )


def main() -> None:
    from vstack.lewin import (
        AgentFailureTrace,
        FailureStep,
        LewinAttributionDetector,
    )
    from vstack.yerkes_dodson import (
        AgentPerformanceTrace,
        PressureInputs,
        YerkesDodsonWorkloadDetector,
    )

    print("Diagnosing context_saturation on a 125k-token prompt")
    print()

    # ---- Yerkes-Dodson (forensic, with context audit) ------------
    print("=" * 60)
    print("1. Yerkes-Dodson Workload (#06) -- forensic mode")
    print("=" * 60)
    yd_trace = AgentPerformanceTrace(
        agent_id="long-context-analyst",
        task="Analyze 125k-token document for risk signals",
        task_class="research_exploration",
        pressure=PressureInputs(
            deadline_pressure="moderate",
            budget_pressure="moderate",
            task_complexity="complex",
        ),
        context_size_tokens=125_000,
        context_window_size=200_000,
        observed_behaviors=[
            "did not address the third constraint",
            "reverted to default formatting",
        ],
        outcome="missed the load-bearing instruction at offset 60k",
        success=False,
    )
    yd = YerkesDodsonWorkloadDetector(llm_client=_yd_stub(), mode="forensic").run(yd_trace)
    print(f"  observed_zone: {yd.observed_zone}")
    print(f"  failure_mode: {yd.failure_mode}")
    if yd.context_saturation:
        print(
            f"  saturation: {yd.context_saturation.saturation_ratio:.2f} "
            f"(risk={yd.context_saturation.lost_in_middle_risk})"
        )
    print()

    # ---- Lewin: locus is environmental ---------------------------
    print("=" * 60)
    print("2. Lewin Attribution (#01)")
    print("=" * 60)
    lewin_trace = AgentFailureTrace(
        agent_id="long-context-analyst",
        model_name="claude-sonnet-4-6",
        framework="custom",
        task=yd_trace.task,
        outcome=yd_trace.outcome,
        success=yd_trace.success,
        initial_attribution="internal",
        individual_factors=[],
        environmental_factors=[
            {
                "factor_id": "env-context-size",
                "name": "long_context",
                "description": "125k tokens context with critical instruction at offset 60k",
            }
        ],
        steps=[
            FailureStep(
                step_index=0,
                content="agent missed the validation step",
                timestamp=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            )
        ],
    )
    lewin = LewinAttributionDetector(llm_client=_lewin_stub(), mode="standard").run(lewin_trace)
    for ev in lewin.locus_evidence:
        print(f"  {ev.locus}: score={ev.score:.2f} sev={ev.severity}")
    print(f"  dominant locus: {lewin.dominant_locus}")
    print()
    print("Convergence: saturation 0.85 + environmental locus 0.82. Fix: move the")
    print("critical instruction to the start/end of the prompt (Liu et al. 2024).")


if __name__ == "__main__":
    main()
