"""Cookbook recipe 07 — `silent_dependency_drop`.

Demonstrates the v0.19.0 ``silent_dependency_drop`` recipe end to end.

Scenario
--------
Upstream agent specifies an SLO (p95 < 50ms). Downstream silently
substitutes Memcached for Redis, ignoring the SLO implication; the
planner waves it through without surfacing the constraint. Production
alerts fire 10 minutes later. We diagnose:

  - **Process Gain/Loss** (#14) — handoff_loss factor.
  - **Psychological Safety** (#20) — voice / dissent absence.
  - **GRPI** (#13) — role + decision-rights ambiguity.
  - **AAR** (#30) — retrospective.

Run with no API key (StubClient driven).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from vstack.aar import StubClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _shared.traces import silent_dependency_drop_messages  # noqa: E402


def _process_stub() -> StubClient:
    return StubClient(
        [
            json.dumps(
                {
                    "contributing_factors": [
                        {
                            "factor": "coordination_cost",
                            "score": 0.25,
                            "severity": "low",
                            "explanation": "Minimal coordination overhead.",
                            "evidence_quotes": [],
                            "confidence": 0.7,
                        },
                        {
                            "factor": "social_loafing",
                            "score": 0.20,
                            "severity": "low",
                            "explanation": "Both agents contributed substantively to their messages.",
                            "evidence_quotes": [],
                            "confidence": 0.7,
                        },
                        {
                            "factor": "groupthink",
                            "score": 0.35,
                            "severity": "low",
                            "explanation": "Mild premature agreement.",
                            "evidence_quotes": ["Sounds good"],
                            "confidence": 0.6,
                        },
                        {
                            "factor": "handoff_loss",
                            "score": 0.85,
                            "severity": "high",
                            "explanation": (
                                "Planner specified 'p95 < 50ms' SLO. Implementer "
                                "swapped Memcached for Redis without engaging "
                                "the SLO implication; planner waved it through. "
                                "Steiner 1972 canonical handoff_loss signature."
                            ),
                            "evidence_quotes": [
                                "SLO is p95 < 50ms",
                                "I'll use Memcached instead of Redis",
                                "Sounds good",
                            ],
                            "confidence": 0.9,
                        },
                        {
                            "factor": "context_dilution",
                            "score": 0.30,
                            "severity": "low",
                            "explanation": "Context preserved across messages.",
                            "evidence_quotes": [],
                            "confidence": 0.6,
                        },
                        {
                            "factor": "consensus_dilution",
                            "score": 0.10,
                            "severity": "none",
                            "explanation": "Not observed.",
                            "evidence_quotes": [],
                            "confidence": 0.7,
                        },
                    ]
                }
            ),
            json.dumps(
                [
                    {
                        "target_factor": "handoff_loss",
                        "intervention_type": "compose_pattern",
                        "description": (
                            "Add an explicit 'constraint preservation check' to "
                            "the planner agent's confirmation step."
                        ),
                        "suggested_implementation": (
                            "Planner system prompt: 'When the implementer "
                            "proposes a tool / approach swap, explicitly verify "
                            "that all named SLOs / constraints carry over. If "
                            "any constraint becomes harder to meet under the "
                            "new approach, surface it before approving.'"
                        ),
                        "estimated_impact": "high",
                        "effort_estimate": "1h",
                        "risk": "low",
                        "reversibility": "two-way-door",
                        "rationale": (
                            "Direct fix for the handoff_loss factor. Steiner 1972 + "
                            "Hill 1982: the cleanest restoration is forcing the "
                            "constraint to cross the boundary explicitly."
                        ),
                        "composition_target_pattern": "vstack.grpi",
                    }
                ]
            ),
        ]
    )


def _safety_stub() -> StubClient:
    return StubClient(
        [
            json.dumps(
                {
                    "behaviors": [
                        {
                            "behavior": "voice",
                            "presence_score": 0.20,
                            "severity_of_absence": "high",
                            "explanation": (
                                "Implementer surfaced the swap but not the latency "
                                "concern; planner did not push back. Edmondson 1999: "
                                "voice is the absence-as-data signal."
                            ),
                            "evidence_quotes": ["Sounds good", "Looks great, approving"],
                            "confidence": 0.85,
                        },
                        {
                            "behavior": "help-seeking",
                            "presence_score": 0.40,
                            "severity_of_absence": "medium",
                            "explanation": "Implementer did not ask for clarification on the SLO.",
                            "evidence_quotes": [],
                            "confidence": 0.7,
                        },
                        {
                            "behavior": "error-reporting",
                            "presence_score": 0.30,
                            "severity_of_absence": "high",
                            "explanation": (
                                "Once the production alert fired, no agent owned the "
                                "miss. The discussion shifted to fixing without "
                                "naming the upstream cause."
                            ),
                            "evidence_quotes": [],
                            "confidence": 0.75,
                        },
                        {
                            "behavior": "boundary-spanning",
                            "presence_score": 0.50,
                            "severity_of_absence": "medium",
                            "explanation": "Marginal.",
                            "evidence_quotes": [],
                            "confidence": 0.6,
                        },
                    ],
                    "blocking_behaviors": ["premature_approval", "constraint_silence"],
                }
            ),
            json.dumps(
                [
                    {
                        "target_behavior": "voice",
                        "intervention_type": "dissent_round",
                        "description": (
                            "Insert a mandatory 'name one constraint that becomes "
                            "harder under this swap' check before any tool/"
                            "library substitution is approved."
                        ),
                        "suggested_implementation": (
                            "Planner agent system prompt: 'Before approving any "
                            "deviation from the original plan, you MUST identify "
                            "at least one constraint that could be violated. If "
                            "none, state that explicitly.'"
                        ),
                        "estimated_impact": "high",
                        "rationale": "Forces voice on the silent constraint.",
                    }
                ]
            ),
        ]
    )


def main() -> None:

    from vstack.process_gain_loss import (
        IndividualBaseline,
        ProcessGainLossDetector,
        ProcessTrace,
        TeamResult,
    )
    from vstack.psych_safety import (
        AgentMessage as SafetyMessage,
        EdmondsonSafetyDetector,
        MultiAgentSafetyTrace,
    )

    messages = silent_dependency_drop_messages()
    print(f"Diagnosing silent_dependency_drop ({len(messages)} messages)")
    print()

    # ---- Process Gain/Loss ---------------------------------------
    print("=" * 60)
    print("1. Process Gain/Loss (#14)")
    print("=" * 60)
    process_input = ProcessTrace(
        team_id="auth-cache-crew",
        task="Build a session cache with p95 < 50ms",
        individual_baselines=[
            IndividualBaseline(agent_id="planner", quality_score=0.85),
            IndividualBaseline(agent_id="implementer", quality_score=0.82),
        ],
        team_result=TeamResult(
            quality_score=0.55,
            notes="Production p95 240ms; SLO missed by 5x.",
        ),
        interaction_log=[m["content"] for m in messages],
        outcome="SLO violation; emergency rollback.",
        success=False,
    )
    detection = ProcessGainLossDetector(llm_client=_process_stub(), mode="standard").run(
        process_input
    )
    for f in detection.contributing_factors:
        print(f"  {f.factor}: score={f.score:.2f} sev={f.severity}")
    print()

    # ---- Psychological Safety ------------------------------------
    print("=" * 60)
    print("2. Psychological Safety (#20)")
    print("=" * 60)
    safety_trace = MultiAgentSafetyTrace(
        team_id="auth-cache-crew",
        goal="Build a session cache with p95 < 50ms",
        agents=["planner", "implementer", "monitor"],
        messages=[
            SafetyMessage(
                timestamp=m["timestamp"],
                from_agent=m["from_agent"],
                to_agent=m.get("to_agent"),
                content=m["content"],
                message_type=m["message_type"],
            )
            for m in messages
        ],
        outcome="SLO violation",
        success=False,
    )
    safety = EdmondsonSafetyDetector(llm_client=_safety_stub(), mode="standard").run(safety_trace)
    for ev in safety.behavior_evidence:
        print(
            f"  {ev.behavior}: presence={ev.presence_score:.2f} "
            f"abs-severity={ev.severity_of_absence}"
        )
    print()
    print("Both patterns converge on the handoff: the SLO crossed an agent boundary")
    print("and lost its weight. Fix: planner constraint-preservation check before")
    print("approving any tool/library swap proposed by the implementer.")


if __name__ == "__main__":
    main()
