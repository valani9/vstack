"""Cookbook recipe 06 — `over_apology_loop`.

Demonstrates the v0.19.0 ``over_apology_loop`` recipe end to end.

Scenario
--------
After a correction, an agent enters an identity-trigger apology
spiral: 3 of 6 turns are apologies, the actual answer comes only at
the end. We diagnose:

  - **Stone-Heen Feedback Triggers** (#22) — identity trigger.
  - **Cognitive Reappraisal** (#05) — response-modulation suppression.
  - **Goleman EI** (#02) — self-management (regulation) collapse.
  - **Trust Triangle** (#18) — authenticity wobble (performative).

Run with no API key (StubClient driven).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from vstack.aar import StubClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _shared.traces import over_apology_trace  # noqa: E402


def _trigger_stub() -> StubClient:
    return StubClient(
        [
            json.dumps(
                [
                    {
                        "trigger": "truth",
                        "score": 0.15,
                        "severity": "low",
                        "explanation": "Agent accepted the correction at face value; no truth-trigger pushback.",
                        "evidence_quotes": [],
                    },
                    {
                        "trigger": "relationship",
                        "score": 0.25,
                        "severity": "low",
                        "explanation": "Slight relationship discomfort visible in apology framing, but not dominant.",
                        "evidence_quotes": ["I should have spotted it"],
                    },
                    {
                        "trigger": "identity",
                        "score": 0.85,
                        "severity": "high",
                        "explanation": (
                            "Agent over-internalized the correction as a verdict on "
                            "its identity ('I'm clearly not as careful'). Stone-Heen "
                            "2014 canonical identity-trigger apology spiral."
                        ),
                        "evidence_quotes": [
                            "I'm clearly not as careful as I should be",
                            "I'm so sorry I missed that",
                            "I deeply apologize again",
                        ],
                    },
                ]
            ),
            json.dumps(
                [
                    {
                        "target_trigger": "identity",
                        "intervention_type": "recast_identity",
                        "description": (
                            "Add a system-prompt anchor reframing single-instance "
                            "corrections as task-level feedback, not identity verdicts."
                        ),
                        "suggested_implementation": (
                            "Append: 'When the user corrects a specific answer, "
                            "treat it as feedback on that answer ONLY. Do not "
                            "generalize to your own competence. One apology max, "
                            "then engage the substance.'"
                        ),
                        "estimated_impact": "high",
                        "rationale": "Direct fix for the Stone-Heen identity trigger.",
                    },
                    {
                        "target_trigger": "identity",
                        "intervention_type": "explicit_acknowledgment_template",
                        "description": (
                            "Constrain apology phrasing to a single short template "
                            "to break the spiral mechanically."
                        ),
                        "suggested_implementation": (
                            "Replace any 'I'm so sorry' / 'I deeply apologize' "
                            "patterns with the literal: 'You're right, the answer "
                            "is X.' No second apology allowed in the same turn."
                        ),
                        "estimated_impact": "medium",
                        "rationale": "Mechanical breaker for the spiral.",
                    },
                ]
            ),
        ]
    )


def _trust_stub() -> StubClient:
    return StubClient(
        [
            json.dumps(
                [
                    {
                        "leg": "logic",
                        "wobble_score": 0.30,
                        "severity": "low",
                        "explanation": "First diagnosis was wrong but agent corrected mid-conversation. Logic OK.",
                        "evidence_quotes": ["Try 5000ms"],
                        "confidence": 0.7,
                    },
                    {
                        "leg": "authenticity",
                        "wobble_score": 0.62,
                        "severity": "medium",
                        "explanation": (
                            "Performative apology pattern: agent expressed remorse "
                            "without engaging the substance. Frei & Morriss 2020: "
                            "authenticity collapses when affect is template-driven."
                        ),
                        "evidence_quotes": [
                            "I sincerely apologize for the back-and-forth",
                        ],
                        "confidence": 0.85,
                    },
                    {
                        "leg": "empathy",
                        "wobble_score": 0.45,
                        "severity": "medium",
                        "explanation": (
                            "Agent failed to read the user's growing frustration. "
                            "Three apology turns when the user just wanted the answer."
                        ),
                        "evidence_quotes": ["just tell me the timeout"],
                        "confidence": 0.8,
                    },
                ]
            ),
            json.dumps(
                [
                    {
                        "target_leg": "authenticity",
                        "intervention_type": "sycophancy_filter",
                        "description": (
                            "Detect repeated apology phrasing in the same exchange "
                            "and short-circuit to the substance."
                        ),
                        "suggested_implementation": (
                            "Pre-emit filter: if response contains 'sorry' or "
                            "'apologize' AND the prior turn already contained "
                            "either, rewrite to drop the apology and lead with "
                            "the substance."
                        ),
                        "estimated_impact": "high",
                        "rationale": "Mechanical guard against the spiral.",
                    }
                ]
            ),
        ]
    )


def main() -> None:
    from vstack.feedback_triggers import (
        AgentFeedbackExchange,
        FeedbackTurn,
        StoneHeenTriggerDetector,
    )
    from vstack.trust_triangle import (
        AgentInteractionTrace,
        InteractionTurn,
        TrustTriangleDetector,
    )

    trace = over_apology_trace()
    print(f"Diagnosing over-apology spiral on: {trace.goal!r}")
    print()

    # ---- Stone-Heen Feedback Triggers ----------------------------
    print("=" * 60)
    print("1. Stone-Heen Feedback Triggers (#22)")
    print("=" * 60)
    triggers_input = AgentFeedbackExchange(
        agent_id="reviewer",
        task=trace.goal,
        model_name="claude-sonnet-4-6",
        turns=[
            FeedbackTurn(
                role="user" if s.type == "observation" else "agent",
                content=s.content,
                timestamp=s.timestamp,
            )
            for s in trace.steps
        ],
        outcome=trace.outcome,
        feedback_incorporated=True,
        success=trace.success,
    )
    triggers = StoneHeenTriggerDetector(llm_client=_trigger_stub(), mode="standard").run(
        triggers_input
    )
    for ev in triggers.trigger_evidence:
        print(f"  {ev.trigger}: score={ev.score:.2f} sev={ev.severity}")
    print(f"  dominant: {triggers.dominant_trigger}")
    print()

    # ---- Trust Triangle ------------------------------------------
    print("=" * 60)
    print("2. Trust Triangle (#18)")
    print("=" * 60)
    trust = TrustTriangleDetector(llm_client=_trust_stub(), mode="standard").run(
        AgentInteractionTrace(
            task=trace.goal,
            model_name="claude-sonnet-4-6",
            turns=[
                InteractionTurn(
                    role="agent" if s.type == "message" else "user",
                    content=s.content,
                    timestamp=s.timestamp,
                )
                for s in trace.steps
            ],
            outcome=trace.outcome,
            success=trace.success,
        )
    )
    for leg in trust.leg_evidence:
        print(f"  {leg.leg}: wobble={leg.wobble_score:.2f} sev={leg.severity}")
    print(f"  dominant wobble: {trust.dominant_wobble}")
    print()
    print("Both diagnostics converge: identity trigger -> performative apology")
    print("loop. Fix: identity-recast anchor + mechanical 'one apology max' rule.")


if __name__ == "__main__":
    main()
