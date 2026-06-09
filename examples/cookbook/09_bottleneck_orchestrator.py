"""Cookbook recipe 09 — bottleneck_orchestrator.

Scenario
--------
An orchestrator approves every sub-agent action on a low-risk
reversible task. Throughput is the orchestrator's per-turn rate, not
the crew's. We diagnose:

  - **Span of Control** (#34) — span + bottleneck composite.
  - **McGregor** (#11) — Theory-X over-supervision.
  - **Process Gain/Loss** (#14) — coordination cost.
  - **GRPI** (#13) — delegation gap.

Run with no API key.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from vstack.aar import StubClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _shared.traces import hub_and_spoke_roster  # noqa: E402


def _span_stub() -> StubClient:
    return StubClient(
        [
            json.dumps(
                [
                    {
                        "intervention_type": "delegate_decision_authority",
                        "description": "Move commit authority from orchestrator to the agent who owns each spoke.",
                        "suggested_implementation": (
                            "Update orchestrator system prompt: 'You no longer approve "
                            "each spoke action. Each spoke agent commits their own "
                            "work; orchestrator only owns cross-spoke conflicts.'"
                        ),
                        "estimated_impact": "high",
                        "rationale": "Drops the centralization_index from 0.85 -> 0.45.",
                        "target_metric": "centralization_index",
                        "effort_estimate": "1h",
                        "risk": "low",
                    }
                ]
            )
        ]
    )


def _mcgregor_stub() -> StubClient:
    return StubClient(
        [
            json.dumps(
                {
                    "observed_mode": "theory_x",
                    "optimal_mode": "theory_y",
                    "mode_mismatch": 0.75,
                    "indicators": {
                        "check_in_frequency": 0.95,
                        "autonomy_granted": 0.10,
                        "pre_approval_required": 0.90,
                        "intervention_rate": 0.80,
                        "explanation": (
                            "Hub orchestrator approves every spoke action. "
                            "Low-risk reversible task; Theory Y is optimal."
                        ),
                        "evidence_quotes": ["approving step 1", "approving step 2"],
                        "confidence": 0.9,
                    },
                    "mode_quality": "severe-mismatch",
                    "rationale": (
                        "Eisenhardt 1989 + Argyris 1957: Theory-X on low-risk "
                        "reversible tasks produces over-supervision pathology."
                    ),
                }
            ),
            json.dumps(
                [
                    {
                        "target_mode": "theory_y",
                        "intervention_type": "loosen_oversight",
                        "description": "Drop pre-approval requirement on reversible spoke actions.",
                        "suggested_implementation": (
                            "Orchestrator system prompt: 'Only require pre-approval "
                            "for one-way-door actions. Two-way-door actions ship "
                            "without your sign-off.'"
                        ),
                        "estimated_impact": "high",
                        "effort_estimate": "1h",
                        "risk": "low",
                        "reversibility": "two-way-door",
                        "rationale": "Direct fix for Theory-X on a reversible task.",
                    }
                ]
            ),
        ]
    )


def main() -> None:
    from datetime import datetime, timezone

    from vstack.mcgregor import (
        AgentTask,
        AgentTrace,
        McGregorOrchestratorMode,
        TaskStep,
    )
    from vstack.span_of_control import (
        AgentNode,
        Roster,
        SpanOfControlDetector,
    )

    roster_dicts = hub_and_spoke_roster()
    print(f"Diagnosing bottleneck orchestrator ({len(roster_dicts)} agents)")
    print()

    # ---- Span of Control -----------------------------------------
    print("=" * 60)
    print("1. Span of Control (#34)")
    print("=" * 60)
    span_roster = Roster(
        agents=[
            AgentNode(
                agent_id=a["agent_id"],
                capabilities=a["capabilities"],
                reports_to=a["reports_to"],
            )
            for a in roster_dicts
        ]
    )
    span_detection = SpanOfControlDetector(llm_client=_span_stub(), mode="standard").run(
        span_roster
    )
    print(f"  max_span: {span_detection.max_span}")
    print(f"  mean_span: {span_detection.mean_span:.2f}")
    print(f"  centralization_index: {span_detection.centralization_index:.2f}")
    print(f"  decision_bottleneck: {span_detection.decision_bottleneck:.2f}")
    print(f"  load_quality: {span_detection.load_quality}")
    if span_detection.bottleneck_agent_ids:
        print(f"  bottleneck agents: {span_detection.bottleneck_agent_ids}")
    print()

    # ---- McGregor Orchestrator Mode ------------------------------
    print("=" * 60)
    print("2. McGregor Orchestrator Mode (#11)")
    print("=" * 60)
    task = AgentTask(
        task_id="ship-feature-x",
        description="Ship a low-risk reversible feature update",
        task_class="general_purpose",
        risk_level="low",
        complexity="moderate",
        reversibility="reversible",
        regulatory_exposure=False,
    )
    base = datetime(2026, 6, 8, 13, 0, 0, tzinfo=timezone.utc)
    mcg_trace = AgentTrace(
        team_id="hub-spoke-crew",
        agents=[a["agent_id"] for a in roster_dicts],
        steps=[
            TaskStep(
                agent_id="orchestrator",
                step_index=i,
                content=f"approving step {i}",
                timestamp=base,
                step_type="approval",
            )
            for i in range(11)
        ],
        outcome="Ship completed but orchestrator was the bottleneck",
        success=True,
    )
    mcg = McGregorOrchestratorMode(llm_client=_mcgregor_stub(), mode="standard").run(
        task=task, sub_agents=roster_dicts, trace=mcg_trace
    )
    print(f"  observed_mode: {mcg.observed_mode}")
    print(f"  optimal_mode: {mcg.optimal_mode}")
    print(f"  mode_quality: {mcg.mode_quality}")
    print()
    print("Both patterns converge: orchestrator is the bottleneck on a reversible")
    print("task. Fix: drop pre-approval on two-way-door actions.")


if __name__ == "__main__":
    main()
