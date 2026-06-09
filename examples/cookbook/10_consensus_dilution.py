"""Cookbook recipe 10 — consensus_dilution.

Scenario
--------
Crew averages three different proposals into a single hedged response
instead of picking the best one. Output is worse than what any single
agent would have produced. We diagnose with Process Gain/Loss
(consensus_dilution factor), Group Decision (model fit), Devil's
Advocate (no critic stage), and Debate Pathology.

Run with no API key.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from vstack.aar import StubClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _process_stub() -> StubClient:
    return StubClient(
        [
            json.dumps(
                {
                    "contributing_factors": [
                        {
                            "factor": "coordination_cost",
                            "score": 0.30,
                            "severity": "low",
                            "explanation": "Marginal.",
                            "evidence_quotes": [],
                            "confidence": 0.7,
                        },
                        {
                            "factor": "social_loafing",
                            "score": 0.20,
                            "severity": "none",
                            "explanation": "Not observed.",
                            "evidence_quotes": [],
                            "confidence": 0.8,
                        },
                        {
                            "factor": "groupthink",
                            "score": 0.30,
                            "severity": "low",
                            "explanation": "Some premature averaging, but no single-position dominance.",
                            "evidence_quotes": [],
                            "confidence": 0.7,
                        },
                        {
                            "factor": "handoff_loss",
                            "score": 0.20,
                            "severity": "none",
                            "explanation": "Not observed.",
                            "evidence_quotes": [],
                            "confidence": 0.7,
                        },
                        {
                            "factor": "context_dilution",
                            "score": 0.40,
                            "severity": "low",
                            "explanation": "Context preserved but specifics lost in the blend.",
                            "evidence_quotes": [],
                            "confidence": 0.7,
                        },
                        {
                            "factor": "consensus_dilution",
                            "score": 0.85,
                            "severity": "high",
                            "explanation": (
                                "Three high-quality proposals blended into one "
                                "hedged answer that picks elements from each. "
                                "Steiner 1972 canonical consensus_dilution: "
                                "averaging pulls toward the mean, not the best."
                            ),
                            "evidence_quotes": [
                                "incorporating elements of all three",
                                "balanced approach",
                            ],
                            "confidence": 0.9,
                        },
                    ]
                }
            ),
            json.dumps(
                [
                    {
                        "target_factor": "consensus_dilution",
                        "intervention_type": "compose_pattern",
                        "description": (
                            "Switch the decision protocol from 'averaging' to "
                            "'pick the best with explicit dissent capture'."
                        ),
                        "suggested_implementation": (
                            "Replace consensus aggregation with: '1. Each agent "
                            "rates each proposal 1-5 with rationale. 2. The "
                            "highest mean rating wins. 3. Dissents are captured "
                            "verbatim in the meeting log.'"
                        ),
                        "estimated_impact": "high",
                        "effort_estimate": "1h",
                        "risk": "low",
                        "rationale": (
                            "Steiner 1972: averaging is the diagnostic signal of "
                            "consensus_dilution. Pick-the-best preserves the "
                            "best individual's signal."
                        ),
                        "composition_target_pattern": "vstack.group_decision",
                    }
                ]
            ),
        ]
    )


def _group_decision_stub() -> StubClient:
    return StubClient(
        [
            json.dumps(
                {
                    "recommended_model": "fist_to_five",
                    "rationale": (
                        "Three substantive proposals + a need to surface "
                        "dissent intensity makes fist_to_five the right model. "
                        "Kaner 2014 + Vroom-Yetton 1973 contingency."
                    ),
                    "protocol_steps": [
                        "1. Each agent rates each proposal 0-5 with one-line rationale.",
                        "2. Any 0 or 1 blocks; convene 5-minute discussion on each block.",
                        "3. Re-rate; the proposal with highest mean wins.",
                    ],
                    "threshold": "highest mean rating >= 3.5",
                    "quorum": None,
                    "tie_breaker": "Re-vote after 1-minute discussion of the tied proposals",
                    "fallback_model": "majority",
                    "dissent_recording": "All <=1 ratings recorded with rationale",
                }
            )
        ]
    )


def main() -> None:
    from datetime import datetime, timezone

    from vstack.group_decision import (
        DecisionRequest,
        GroupDecisionGenerator,
        ProposalOption,
    )
    from vstack.process_gain_loss import (
        IndividualBaseline,
        ProcessGainLossDetector,
        ProcessTrace,
        TeamResult,
    )

    print("Diagnosing consensus_dilution on a 3-proposal decision")
    print()

    # ---- Process Gain/Loss ---------------------------------------
    print("=" * 60)
    print("1. Process Gain/Loss (#14)")
    print("=" * 60)
    process_input = ProcessTrace(
        team_id="cache-design-crew",
        task="Pick a cache eviction strategy",
        individual_baselines=[
            IndividualBaseline(agent_id="agent_a", quality_score=0.85),
            IndividualBaseline(agent_id="agent_b", quality_score=0.78),
            IndividualBaseline(agent_id="agent_c", quality_score=0.82),
        ],
        team_result=TeamResult(
            quality_score=0.62,
            notes="Blended LRU + LFU + TTL into a hedged hybrid; worse than any single proposal.",
        ),
        interaction_log=[
            "A: LRU for the auth-cache. Cache-friendly, simple.",
            "B: LFU. We have hot keys.",
            "C: TTL. Bounded staleness is what we need.",
            "lead: Incorporating elements of all three.",
            "lead: Going with a hybrid LRU+LFU+TTL.",
        ],
        outcome="Implementation complexity 3x; cache hit rate 30% lower.",
        success=False,
    )
    detection = ProcessGainLossDetector(llm_client=_process_stub(), mode="standard").run(
        process_input
    )
    for f in detection.contributing_factors:
        print(f"  {f.factor}: score={f.score:.2f} sev={f.severity}")
    print()

    # ---- Group Decision Models -----------------------------------
    print("=" * 60)
    print("2. Group Decision Models (#25)")
    print("=" * 60)
    decision_req = DecisionRequest(
        title="Cache eviction strategy",
        options=[
            ProposalOption(name="LRU", description="Least Recently Used"),
            ProposalOption(name="LFU", description="Least Frequently Used"),
            ProposalOption(name="TTL", description="Time To Live"),
        ],
        agents=["agent_a", "agent_b", "agent_c"],
        stakes="medium",
        reversibility="reversible",
        time_pressure="low",
        expertise_asymmetry="low",
        regulatory_exposure=False,
        buy_in_required="medium",
    )
    protocol = GroupDecisionGenerator(llm_client=_group_decision_stub(), mode="standard").generate(
        decision_req
    )
    print(f"  recommended_model: {protocol.recommended_model}")
    print(f"  threshold: {protocol.threshold}")
    print(f"  tie_breaker: {protocol.tie_breaker}")
    print()
    print("Convergence: consensus_dilution -> switch to fist_to_five to surface")
    print("dissent intensity and pick the best, not the mean.")


if __name__ == "__main__":
    main()
