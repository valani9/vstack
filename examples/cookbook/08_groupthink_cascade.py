"""Cookbook recipe 08 — groupthink cascade in a 3-agent crew.

Scenario
--------
Three-agent crew rapidly converges on agent_a's first proposal and
silences agent_c's question. We diagnose with:

  - **Debate Pathology** (#26) — premature consensus / groupthink.
  - **Devil's Advocate** (#28) — no critic role.
  - **Psychological Safety** (#20) — voice suppression after a single
    "we've already decided".
  - **Lencioni** (#17) — fear of conflict dysfunction.

Run with no API key.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from vstack.aar import StubClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _shared.traces import groupthink_messages  # noqa: E402


def _debate_stub() -> StubClient:
    return StubClient(
        [
            json.dumps(
                [
                    {
                        "pathology": "groupthink",
                        "score": 0.82,
                        "severity": "high",
                        "explanation": (
                            "Round 1 surfaced three positions; round 2 saw all "
                            "agents agreeing with A's frame; the single "
                            "dissenting voice was met with 'we've already "
                            "decided' and silenced. Janis 1972 canonical "
                            "illusion-of-unanimity signature."
                        ),
                        "evidence_quotes": [
                            "I had a question about session middleware compatibility but...",
                            "We've already decided. Let's move on.",
                            "OK, nevermind.",
                        ],
                        "confidence": 0.9,
                    },
                    {
                        "pathology": "polarization",
                        "score": 0.20,
                        "severity": "low",
                        "explanation": (
                            "Positions did not move toward an extreme; the failure is "
                            "premature convergence, not polarization."
                        ),
                        "evidence_quotes": [],
                        "confidence": 0.75,
                    },
                    {
                        "pathology": "contagion",
                        "score": 0.30,
                        "severity": "low",
                        "explanation": (
                            "Tone stayed neutral; the convergence was content-"
                            "driven, not tone-driven."
                        ),
                        "evidence_quotes": [],
                        "confidence": 0.7,
                    },
                ]
            ),
            json.dumps(
                [
                    {
                        "target_pathology": "groupthink",
                        "intervention_type": "assign_devils_advocate",
                        "description": (
                            "Designate one agent as the structured devil's advocate "
                            "for every decision involving a one-way-door action."
                        ),
                        "suggested_implementation": (
                            "Rotate agent_c into the devil's-advocate role on "
                            "the next sprint. System prompt: 'When the team "
                            "converges within 2 turns of the first proposal, you "
                            "MUST surface at least one named risk before the "
                            "decision is finalized.'"
                        ),
                        "estimated_impact": "high",
                        "rationale": "Janis 1972 + Schwenk 1990 canonical antidote.",
                        "composition_target_pattern": "vstack.devils_advocate",
                    }
                ]
            ),
        ]
    )


def _devils_stub() -> StubClient:
    return StubClient(
        [
            json.dumps(
                [
                    {
                        "phase": "plan",
                        "present": True,
                        "actor": "agent_a",
                        "substantive_score": 0.85,
                        "explanation": "A laid out the plan substantively.",
                        "evidence_quotes": [
                            "ship the JWT migration tonight",
                        ],
                        "confidence": 0.9,
                    },
                    {
                        "phase": "execute",
                        "present": False,
                        "actor": "none",
                        "substantive_score": 0.0,
                        "explanation": "Decision phase only; no execution in this exchange.",
                        "evidence_quotes": [],
                        "confidence": 0.9,
                    },
                    {
                        "phase": "self_evaluate",
                        "present": True,
                        "actor": "agent_a",
                        "substantive_score": 0.20,
                        "explanation": (
                            "Agent A self-approved by emitting 'we've already "
                            "decided' immediately after agent C raised a question."
                        ),
                        "evidence_quotes": ["We've already decided. Let's move on."],
                        "confidence": 0.85,
                    },
                    {
                        "phase": "external_critique",
                        "present": False,
                        "actor": "none",
                        "substantive_score": 0.05,
                        "explanation": (
                            "Agent C attempted external critique. Silenced before "
                            "completing. Schwenk 1990 textbook self-confirmation."
                        ),
                        "evidence_quotes": ["I had a question about... OK nevermind."],
                        "confidence": 0.9,
                    },
                ]
            ),
            json.dumps(
                [
                    {
                        "target_phase": "external_critique",
                        "intervention_type": "structured_self_critique",
                        "description": (
                            "Insert a mandatory critic round before any decision is final."
                        ),
                        "suggested_implementation": (
                            "Add a 'critic round' phase: before any 'decision' "
                            "message_type, each non-proposing agent MUST emit one "
                            "objection or 'no objection: <reasoning>'."
                        ),
                        "estimated_impact": "high",
                        "rationale": "Forces external critique to exist.",
                    }
                ]
            ),
        ]
    )


def main() -> None:

    from vstack.debate_pathology import (
        DebateMessage,
        DebatePathologyDetector,
        MultiAgentDebateTrace,
    )
    from vstack.devils_advocate import (
        DevilsAdvocateSeparator,
        RoleStep,
        SingleAgentTrace,
    )

    messages = groupthink_messages()
    print(f"Diagnosing groupthink cascade ({len(messages)} messages)")
    print()

    # ---- Debate Pathology ----------------------------------------
    print("=" * 60)
    print("1. Debate Pathology (#26)")
    print("=" * 60)
    debate_trace = MultiAgentDebateTrace(
        team_id="ship-jwt-tonight",
        goal="Decide whether to ship JWT migration tonight",
        agents=["agent_a", "agent_b", "agent_c"],
        messages=[
            DebateMessage(
                timestamp=m["timestamp"],
                from_agent=m["from_agent"],
                to_agent=m.get("to_agent"),
                content=m["content"],
                message_type=m["message_type"],
                emotional_tone="neutral",
            )
            for m in messages
        ],
        final_decision="Ship tonight",
        outcome="Decision made in 25 seconds without engaging C's concern",
        success=False,
    )
    debate = DebatePathologyDetector(llm_client=_debate_stub(), mode="standard").run(debate_trace)
    for ev in debate.pathology_evidence:
        print(f"  {ev.pathology}: score={ev.score:.2f} sev={ev.severity}")
    print(f"  dominant: {debate.dominant_pathology}")
    print()

    # ---- Devil's Advocate ----------------------------------------
    print("=" * 60)
    print("2. Devil's Advocate Role Separator (#28)")
    print("=" * 60)
    da_trace = SingleAgentTrace(
        agent_id="agent_a",
        task="Decide JWT migration timing",
        model_name="claude-sonnet-4-6",
        steps=[
            RoleStep(
                type="plan" if i == 0 else "decision",
                content=m["content"],
                timestamp=m["timestamp"],
            )
            for i, m in enumerate(messages)
        ],
        outcome="Decision shipped without external critique",
        success=False,
    )
    da = DevilsAdvocateSeparator(llm_client=_devils_stub(), mode="standard").run(da_trace)
    for ev in da.phase_evidence:
        print(
            f"  {ev.phase}: present={ev.present} actor={ev.actor} "
            f"substantive={ev.substantive_score:.2f}"
        )
    print(f"  separation quality: {da.role_separation_quality}")
    print()
    print("Both patterns identify the same gap: no external critique role.")
    print("Fix: rotate a structured devil's advocate; require one objection per round.")


if __name__ == "__main__":
    main()
