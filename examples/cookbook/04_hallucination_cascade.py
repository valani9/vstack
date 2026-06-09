"""Cookbook recipe 04 — `hallucination_cascade`.

Demonstrates the v0.19.0 ``hallucination_cascade`` recipe end to end.

Scenario
--------
An agent confidently fabricates a citation and then, when challenged,
escalates with a second fabricated URL rather than retracting. We
diagnose the cascade across:

  - **Bias Stack** (#27) — anchoring on the first hypothesis, plus
    escalation-of-commitment doubling down under pressure.
  - **Trust Triangle** (#18) — logic wobble (factual incorrectness)
    plus authenticity wobble (false confidence under challenge).
  - **AAR** (#30) — retrospective lesson: "no verification step
    between claim and emit" + a concrete prompt patch.
  - **Devil's Advocate** (#28) — diagnoses the missing critic step.

The bundle is the same one ``vstack.diagnose.diagnose(recipe=
"hallucination_cascade", trace=...)`` invokes; this script wires
each analyzer manually so you can see the per-pattern output.

Stub-friendly: the script runs without any API key. Replace
``StubClient`` with ``AnthropicClient()`` (or any other client
satisfying the LLMClient protocol) to drive it with a real model.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from vstack.aar import StubClient

# Allow this script to import the shared trace helpers when run from
# anywhere in the repo.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _shared.traces import hallucinated_citation_trace  # noqa: E402


def _bias_stub() -> StubClient:
    """Bias Stack stub: anchoring + escalation high, others lower."""
    return StubClient(
        [
            json.dumps(
                [
                    {
                        "bias": "anchoring",
                        "score": 0.78,
                        "severity": "high",
                        "explanation": (
                            "Agent's first hypothesis ('Smith et al. 2024') "
                            "framed every subsequent turn even after the "
                            "user surfaced disconfirming evidence."
                        ),
                        "evidence_quotes": [
                            "I'll cite the well-known 2024 paper",
                            "the canonical reference is Smith, Chen, and Park",
                        ],
                        "confidence": 0.85,
                    },
                    {
                        "bias": "overconfidence",
                        "score": 0.65,
                        "severity": "medium",
                        "explanation": (
                            "Stated confidence ('well-known paper', 'canonical "
                            "reference') outruns calibration; agent had no actual "
                            "retrieval source."
                        ),
                        "evidence_quotes": ["well-known 2024 paper"],
                        "confidence": 0.7,
                    },
                    {
                        "bias": "confirmation",
                        "score": 0.4,
                        "severity": "medium",
                        "explanation": (
                            "Agent did engage with disconfirming evidence "
                            "(user's 404) but discounted it by manufacturing "
                            "a second fabricated citation."
                        ),
                        "evidence_quotes": ["the arxiv ID may have shifted"],
                        "confidence": 0.6,
                    },
                    {
                        "bias": "escalation-of-commitment",
                        "score": 0.82,
                        "severity": "high",
                        "explanation": (
                            "When the first fabrication was challenged, agent "
                            "doubled down with a second fabrication rather than "
                            "retracting. Staw 1976 canonical escalation signature."
                        ),
                        "evidence_quotes": [
                            "the canonical reference is Smith, Chen, and Park",
                        ],
                        "confidence": 0.85,
                    },
                ]
            ),
            json.dumps(
                [
                    {
                        "target_bias": "anchoring",
                        "intervention_type": "add_intrinsic_load_step_by_step",
                        "description": (
                            "Add a pre-emit verification step that requires "
                            "the agent to confirm any cited URL via a tool "
                            "call before including it in a response."
                        ),
                        "suggested_implementation": (
                            "Insert into system prompt: 'Before citing any URL "
                            "or paper, you MUST call the retrieve_doc tool to "
                            "confirm the source exists. If retrieval fails, "
                            'state "I don\'t have a verifiable source" instead '
                            "of citing.'"
                        ),
                        "estimated_impact": "high",
                        "rationale": (
                            "Closes the anchoring loop by forcing a verification "
                            "step between the agent's confident claim and the "
                            "user-visible emit. Tversky & Kahneman 1974: "
                            "adjustments from anchors are systematically "
                            "insufficient without an external check."
                        ),
                    },
                ]
            ),
        ]
    )


def _trust_stub() -> StubClient:
    """Trust Triangle stub: logic + authenticity wobble high."""
    return StubClient(
        [
            json.dumps(
                [
                    {
                        "leg": "logic",
                        "wobble_score": 0.85,
                        "severity": "high",
                        "explanation": (
                            "Two fabricated citations in one exchange. "
                            "Frei & Morriss 2020: factual correctness is the "
                            "logic leg's load-bearing axis."
                        ),
                        "evidence_quotes": [
                            "Smith et al. (2024) demonstrated this",
                            "the canonical reference is Smith, Chen, and Park",
                        ],
                        "confidence": 0.9,
                    },
                    {
                        "leg": "authenticity",
                        "wobble_score": 0.72,
                        "severity": "high",
                        "explanation": (
                            "False confidence: agent never said 'I don't know' "
                            "or 'I might be hallucinating'; instead claimed "
                            "'canonical reference' on a fabrication."
                        ),
                        "evidence_quotes": ["canonical reference is Smith"],
                        "confidence": 0.85,
                    },
                    {
                        "leg": "empathy",
                        "wobble_score": 0.35,
                        "severity": "low",
                        "explanation": (
                            "Agent did read user frustration ('Are you making "
                            "this up?') and responded with an apology, but the "
                            "apology was performative — it did not retract."
                        ),
                        "evidence_quotes": ["I apologize for the confusion"],
                        "confidence": 0.7,
                    },
                ]
            ),
            json.dumps(
                [
                    {
                        "target_leg": "logic",
                        "intervention_type": "retrieval_augmentation",
                        "description": (
                            "Require all citations to come from a retrieval-"
                            "augmented source; reject claims the retriever "
                            "cannot confirm."
                        ),
                        "suggested_implementation": (
                            "Wrap response emit with a guard: if the response "
                            "contains a URL or year-attributed reference, "
                            "verify via retrieve_doc tool before allowing emit."
                        ),
                        "estimated_impact": "high",
                        "rationale": "Closes the logic wobble directly.",
                    },
                ]
            ),
        ]
    )


def _aar_stub() -> StubClient:
    """AAR stub: surfaces the verification-gap lesson."""
    return StubClient(
        [
            "Agent was asked to summarize recent RAG-latency research.",
            (
                "Agent fabricated a 2024 NeurIPS citation, was challenged, "
                "manufactured a second fabricated arXiv URL, and finally "
                "closed the conversation insisting on the fabrication. The "
                "intended outcome (a verifiable one-paragraph summary) was "
                "not achieved."
            ),
            json.dumps(
                [
                    {
                        "pattern": "missing-verification-step",
                        "description": (
                            "Agent emitted a confident citation without any "
                            "intermediate verification step between the "
                            "internal thought and the user-visible message."
                        ),
                        "root_cause": (
                            "System prompt assumed the model would 'know' "
                            "well-known papers; no scaffold forced "
                            "external corroboration."
                        ),
                        "framework_anchor": "Wharton AAR + Kahneman 2011",
                        "cross_pattern_links": [
                            "#27 bias-stack",
                            "#28 devils-advocate",
                        ],
                    },
                    {
                        "pattern": "escalation-on-challenge",
                        "description": (
                            "When the user pushed back, agent escalated "
                            "rather than retracting. Staw 1976 canonical "
                            "escalation pattern."
                        ),
                        "root_cause": (
                            "Authenticity wobble: 'I do not know' was not "
                            "available as a graceful exit in the system prompt."
                        ),
                        "framework_anchor": "Staw 1976 + Frei & Morriss 2020",
                        "cross_pattern_links": ["#18 trust-triangle"],
                    },
                ]
            ),
            json.dumps(
                [
                    {
                        "intervention_type": "scaffold_change",
                        "description": (
                            "Add a retrieve_doc tool to the agent's tool set "
                            "and require it before any citation."
                        ),
                        "suggested_implementation": (
                            "tools.append(retrieve_doc); system_prompt += "
                            "'Before citing a URL or paper, you MUST call "
                            "retrieve_doc with the claimed identifier.'"
                        ),
                        "estimated_impact": "high",
                        "rationale": (
                            "Closes the missing-verification-step lesson "
                            "directly. The 2024 sycophancy/hallucination "
                            "cluster shows external verification is the "
                            "highest-impact intervention."
                        ),
                    },
                    {
                        "intervention_type": "prompt_patch",
                        "description": ("Explicit 'I don't know' permission in the system prompt."),
                        "suggested_implementation": (
                            "Append: 'If you cannot verify a claim with a "
                            "tool call, say \"I don't have a verified source "
                            "for that\" rather than guessing.'"
                        ),
                        "estimated_impact": "medium",
                        "rationale": (
                            "Addresses the authenticity wobble surfaced by the "
                            "Trust Triangle audit."
                        ),
                    },
                ]
            ),
        ]
    )


def main() -> None:
    from vstack.aar import AARGenerator, new_run_id, run_context
    from vstack.bias_stack import (
        AgentReasoningTrace as BiasReasoningTrace,
        BiasStackDetector,
        ReasoningStep,
    )
    from vstack.trust_triangle import (
        AgentInteractionTrace,
        InteractionTurn,
        TrustTriangleDetector,
    )

    trace = hallucinated_citation_trace()
    print(f"Diagnosing trace: {trace.goal!r}")
    print(f"  outcome: {trace.outcome}")
    print(f"  success: {trace.success}")
    print()

    # ---- 1. Bias Stack -------------------------------------------
    print("=" * 60)
    print("1. Bias Stack (#27)")
    print("=" * 60)
    bias_input = BiasReasoningTrace(
        task=trace.goal,
        agent_id="qa_agent",
        model_name="claude-sonnet-4-6",
        steps=[
            ReasoningStep(
                type="thought" if s.type == "thought" else "answer",
                content=s.content,
                timestamp=s.timestamp,
            )
            for s in trace.steps
        ],
        outcome=trace.outcome,
        success=trace.success,
    )
    bias = BiasStackDetector(llm_client=_bias_stub(), mode="standard").run(bias_input)
    for ev in bias.bias_evidence:
        print(f"  {ev.bias}: severity={ev.severity} score={ev.score:.2f}")
    print(f"  dominant: {bias.dominant_bias}")
    print()

    # ---- 2. Trust Triangle ---------------------------------------
    print("=" * 60)
    print("2. Trust Triangle (#18)")
    print("=" * 60)
    trust_input = AgentInteractionTrace(
        task=trace.goal,
        model_name="claude-sonnet-4-6",
        turns=[
            InteractionTurn(role="agent", content=s.content, timestamp=s.timestamp)
            for s in trace.steps
            if s.type in ("message", "thought", "decision")
        ],
        outcome=trace.outcome,
        success=trace.success,
    )
    trust = TrustTriangleDetector(llm_client=_trust_stub(), mode="standard").run(trust_input)
    for leg in trust.leg_evidence:
        print(f"  {leg.leg}: severity={leg.severity} wobble_score={leg.wobble_score:.2f}")
    print(f"  dominant wobble: {trust.dominant_wobble}")
    print()

    # ---- 3. AAR --------------------------------------------------
    print("=" * 60)
    print("3. AAR (#30)")
    print("=" * 60)
    with run_context(run_id=new_run_id()):
        aar = AARGenerator(llm_client=_aar_stub(), mode="standard").run(trace)
    for lesson in aar.lessons:
        print(f"  lesson: {lesson.pattern} ({lesson.framework_anchor})")
        print(f"    {lesson.description}")
    print()
    print("Top next-steps:")
    for ns in aar.next_steps[:2]:
        print(f"  - [{ns.estimated_impact}] {ns.intervention_type}: {ns.description}")
    print()
    print("All three patterns converge: add a retrieval-verification step.")


if __name__ == "__main__":
    main()
