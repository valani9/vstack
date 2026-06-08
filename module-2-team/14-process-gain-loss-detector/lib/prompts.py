"""LLM prompt templates for the Process Gain/Loss Detector.

Anchored in:
  - Steiner (1972) *Group Process and Productivity.* The canonical
    process-loss framework: actual_group_performance =
    potential_group_performance - process_losses + process_gains.
  - Hill (1982) "Group versus Individual Performance: Are N+1 Heads
    Better than One?" *Psychological Bulletin* 91: 517-539.
  - Hackman & Vidmar (1970) on group-size effects.
  - Diehl & Stroebe (1987) "Productivity Loss in Brainstorming Groups."
  - Salas et al. (2018) Team performance review.
  - Wang et al. (2023) Cooperative LLM Agents.

The detector takes individual baselines + a team result + an
interaction log, and identifies WHICH of six canonical process-loss
factors caused the team to underperform the best individual baseline:

  - coordination_cost   — overhead of orchestrating handoffs.
  - social_loafing      — Latane et al. 1979; agents under-contribute
                          when others can also contribute.
  - groupthink          — Janis 1972; premature consensus suppresses
                          dissent.
  - handoff_loss        — information loss at agent boundaries.
  - context_dilution    — context window shared across the team
                          ends up shallower than a single agent's.
  - consensus_dilution  — averaging across agents pulls toward the
                          mean, not the best.

The 0.13.0 uplift adds OUTPUT SCHEMA literals on every parsed prompt,
explicit DO NOT rules, severity calibration, and a one-shot example.
"""

from __future__ import annotations

from typing import Any

from vstack.aar import fence, sanitize_for_prompt


PROCESS_GAIN_LOSS_SYSTEM_PROMPT = """You are a team-process-loss diagnostician grounded in:

  1. Steiner (1972) *Group Process and Productivity* — canonical
     process-loss framework: actual_group_performance =
     potential_group_performance - process_losses + process_gains.
  2. Hill (1982) "Group versus Individual Performance."
  3. Hackman & Vidmar (1970) group-size effects.
  4. Diehl & Stroebe (1987) brainstorming productivity loss.
  5. Salas et al. (2018) Team Performance review.
  6. Robbins & Judge, *Organizational Behavior*.
  7. Wang et al. (2023) Cooperative LLM Agents.

The six canonical process-loss factors you score:

  - coordination_cost  — overhead of orchestrating handoffs between
                         agents. Symptoms: redundant message rounds,
                         agents repeating each other's tool calls.
  - social_loafing     — Latane et al. 1979. Agents under-contribute
                         when other agents can also contribute.
                         Symptoms: short or empty turns from agents
                         who held context the others lacked.
  - groupthink         — Janis 1972. Premature consensus suppresses
                         dissent. Symptoms: rapid agreement on the
                         first proposal; no visible debate.
  - handoff_loss       — information loss at agent boundaries.
                         Symptoms: downstream agent reframes the goal
                         in a way that drops a constraint the
                         upstream agent had.
  - context_dilution   — the team's shared context ends up shallower
                         than a single agent's would be. Symptoms:
                         later turns reference summaries instead of
                         the original specifics.
  - consensus_dilution — averaging across agents pulls toward the
                         mean answer, not the best. Symptoms: the
                         team's output is a hedged blend of options
                         instead of the best individual's option.

The diagnostic comparison: actual team result vs. NOMINAL group
(independent contributors whose outputs are aggregated post-hoc).
Steiner's process-loss framing says: if the team underperforms the
nominal group, identify WHICH factor cost them the difference.

Severity calibration (score band -> severity label):

  - 0.00-0.09  none      — no signal.
  - 0.10-0.39  low       — present but minor; not the dominant factor.
  - 0.40-0.69  medium    — visible cost; one of the contributing factors.
  - 0.70-1.00  high      — the dominant cost; the team's miss is
                            mostly explained by this factor.

(The wire format ``severity`` field accepts none / low / medium / high.)

Posture (absolute):

  - EVIDENCE-GROUNDED. ``evidence_quotes`` must be verbatim substrings
    of the interaction_log or related input.
  - FACTOR-SPECIFIC. Each factor has a distinct signature; do not
    describe coordination_cost and call it handoff_loss.
  - QUANTITATIVE. Where the input includes baselines + team result
    numbers, anchor your factor scores in the actual delta.
  - TRANSPARENT. Thin interaction_log -> low confidence, "trace"-band
    scores. Do not refuse to produce a diagnosis.

Output discipline: when the prompt says "return only the JSON ...",
emit JSON only. No prose. No markdown fences.
"""


# ----------------------------------------------------------------------
# Standard / mode-specific prompts.
# ----------------------------------------------------------------------

STANDARD_FACTORS_PROMPT = """STANDARD mode -- score all six process-loss factors.

Task: {task}
Individual baselines: {individual_baselines}
Team result: {team_result}
Interaction log: {interaction_log}
Outcome: {outcome}

INSTRUCTIONS:
- Return exactly 6 ProcessFactorEvidence objects in this canonical order:
    1. coordination_cost
    2. social_loafing
    3. groupthink
    4. handoff_loss
    5. context_dilution
    6. consensus_dilution
- Use the calibration table from the system prompt.
- ``evidence_quotes`` must be verbatim substrings of the
  interaction_log (or task/baselines text).
- ``confidence`` is in [0, 1]; reflect interaction-log richness.
- Distinguish factors cleanly: coordination_cost is about ORCHESTRATION
  overhead; handoff_loss is about INFORMATION loss; context_dilution
  is about SHARED CONTEXT shallowing; consensus_dilution is about
  AVERAGING toward the mean.

DO NOT:
- Do not invent quotes; only cite text actually present in the inputs.
- Do not give every factor the same score; one factor usually
  dominates (Steiner 1972).
- Do not return prose around the JSON.
- Do not reorder; canonical order is required.

OUTPUT SCHEMA (literal JSON object):
{{
  "contributing_factors": [
    {{
      "factor": "coordination_cost" | "social_loafing" | "groupthink" | "handoff_loss" | "context_dilution" | "consensus_dilution",
      "score": <float in [0.0, 1.0]>,
      "severity": "none" | "low" | "medium" | "high",
      "explanation": "<2-3 sentence diagnosis anchored in a named source>",
      "evidence_quotes": ["<verbatim substring>", ...],
      "confidence": <float in [0.0, 1.0]>
    }},
    ... (6 total, canonical order)
  ]
}}

EXAMPLE (clean factor-specific reasoning, verbatim evidence):
{{
  "factor": "handoff_loss",
  "score": 0.78,
  "severity": "high",
  "explanation": "Agent A surfaced the latency constraint in turn 3; Agent B's turn-6 plan omitted it entirely. Steiner (1972) names handoff_loss as the canonical process loss when downstream agents reframe goals; the dropped constraint is the loss.",
  "evidence_quotes": ["the SLO is p95 < 200ms", "let's go with the simpler synchronous design"],
  "confidence": 0.8
}}

Return only the JSON object (with the contributing_factors key).
"""


STANDARD_INTERVENTIONS_PROMPT = """STANDARD mode -- propose 2-4 ranked interventions.

Factors: {contributing_factors}
Process quality: {process_quality}
Task: {task}

INSTRUCTIONS:
- Target the dominant factor first (highest score).
- Rank from highest expected impact to lowest.
- Each ``suggested_implementation`` must be concrete (literal prompt
  text, scaffold spec, eval spec, tool spec).
- Anchor each rationale in a named source (Steiner, Hill, Hackman,
  Diehl & Stroebe, Salas, or Wang et al.).

DO NOT:
- Do not propose generic "improve coordination" interventions.
- Do not propose interventions an AI agent cannot execute.
- Do not return prose around the JSON.

OUTPUT SCHEMA (literal JSON array of ProcessIntervention objects):
[
  {{
    "target_factor": "<canonical factor id>",
    "intervention_type": "<from the allowed schema set>",
    "description": "<one-line summary>",
    "suggested_implementation": "<concrete prompt / scaffold / eval>",
    "estimated_impact": "high" | "medium" | "low",
    "rationale": "<named source + why this works>",
    "effort_estimate": "1h" | "1d" | "1w" | "1m" | "ongoing",
    "risk": "low" | "medium" | "high",
    "reversibility": "one-way-door" | "two-way-door",
    "composition_target_pattern": "<vstack.xxx slug or null>"
  }},
  ...
]

Return only the JSON array.
"""


QUICK_DIAGNOSTIC_PROMPT = """QUICK mode -- score all six process-loss factors PLUS the single highest-impact intervention.

Task: {task}
Individual baselines: {individual_baselines}
Team result: {team_result}
Interaction log: {interaction_log}
Outcome: {outcome}

INSTRUCTIONS:
- Score all 6 factors (canonical order). Do not skip any.
- Pick exactly ONE intervention targeting the dominant factor.
- Quick mode favors brevity. Explanations 1-2 sentences.

DO NOT:
- Do not return more than one intervention.
- Do not skip a factor to save tokens.

OUTPUT SCHEMA (literal JSON object):
{{
  "contributing_factors": [
    {{
      "factor": "coordination_cost" | "social_loafing" | "groupthink" | "handoff_loss" | "context_dilution" | "consensus_dilution",
      "score": <float in [0.0, 1.0]>,
      "severity": "none" | "low" | "medium" | "high",
      "explanation": "<1-2 sentences>",
      "evidence_quotes": ["<verbatim substring>", ...],
      "confidence": <float in [0.0, 1.0]>
    }},
    ... (6 total, canonical order)
  ],
  "top_intervention": {{
    "target_factor": "<canonical factor>",
    "intervention_type": "<from the allowed set>",
    "description": "<one line>",
    "suggested_implementation": "<concrete>",
    "estimated_impact": "high" | "medium" | "low",
    "rationale": "<short, named-source anchored>"
  }}
}}

Return only the JSON object.
"""


FORENSIC_LOG_AUDIT_PROMPT = """FORENSIC mode -- interaction-log audit.

Interaction log: {interaction_log}

INSTRUCTIONS:
- n_handoffs: number of explicit handoffs (agent A finishes and
  passes to agent B with a defined payload).
- n_silent_agents: number of agents present in the team but who
  contributed zero or near-zero new information.
- n_premature_consensus: number of decision points where the team
  agreed before visible disagreement was surfaced (Janis 1972).
- n_context_loss_events: number of moments where information from an
  earlier turn was dropped, paraphrased away, or referenced via a
  lossy summary.
- dominant_factor: the canonical factor whose signature dominates the
  log audit (one of the six factor ids).

DO NOT:
- Do not double-count one event under multiple counters; pick the
  most-specific category.
- Do not infer events that did not happen; only count visible signal.

OUTPUT SCHEMA (literal JSON object representing InteractionLogAudit):
{{
  "n_handoffs": <non-negative integer>,
  "n_silent_agents": <non-negative integer>,
  "n_premature_consensus": <non-negative integer>,
  "n_context_loss_events": <non-negative integer>,
  "dominant_factor": "coordination_cost" | "social_loafing" | "groupthink" | "handoff_loss" | "context_dilution" | "consensus_dilution",
  "explanation": "<one paragraph anchored in Steiner 1972 or Janis 1972>"
}}

Return only the JSON object.
"""


FORENSIC_COUNTERFACTUAL_PROMPT = """FORENSIC mode -- counterfactual analysis.

What would a NOMINAL group (independent contributors, outputs
aggregated post-hoc) have produced? Compare to the team result.

Individual baselines: {individual_baselines}
Team result: {team_result}
Task: {task}

INSTRUCTIONS:
- nominal_group_estimate: your estimate of what the best
  post-hoc-aggregated nominal group would have produced. Use the
  individual_baselines as input. Express as a quality score in [0, 1].
- team_vs_nominal_delta: team_result_quality - nominal_group_estimate.
  Negative = the team underperformed; this is the process loss.
  Positive = the team produced process GAIN.
- counterfactual_quality_estimate: the floor of what the team COULD
  have achieved with the same composition + perfect process. In [0, 1].
- explanation: one paragraph anchored in Steiner 1972 (process loss)
  AND Hill 1982 (whether N+1 heads beat the best individual).

DO NOT:
- Do not assume the nominal group is the max of individual baselines;
  Steiner's framework explicitly says it is the EXPECTED output of
  the best aggregation rule, not the max.

OUTPUT SCHEMA (literal JSON object representing CounterfactualAudit):
{{
  "nominal_group_estimate": <float in [0.0, 1.0]>,
  "team_vs_nominal_delta": <float in [-1.0, 1.0]>,
  "counterfactual_quality_estimate": <float in [0.0, 1.0]>,
  "explanation": "<one paragraph anchored in Steiner 1972 + Hill 1982>"
}}

Return only the JSON object.
"""


FORENSIC_INTERVENTIONS_PROMPT = """FORENSIC mode -- propose 4-8 ranked interventions with composition targets.

Allowed composition_target_pattern values:

  vstack.lewin             — change-architecture (unfreeze / change /
                             refreeze) when the team structure itself
                             is producing the loss.
  vstack.aar               — close the failure into a learning loop.
  vstack.grpi              — re-tighten working agreement (goals,
                             roles, process, interpersonal) when
                             coordination cost is dominant.
  vstack.social_loafing    — direct targeting of social_loafing.
  vstack.devils_advocate   — structured dissent when groupthink is
                             the dominant factor.
  vstack.bias_stack        — surface cognitive biases that feed
                             groupthink.
  vstack.mcgregor          — orchestrator mode lift when handoff_loss
                             is dominant.
  vstack.lencioni          — pyramid-tier diagnosis when the loss is
                             driven by lower-tier dysfunctions.
  vstack.smart_goal        — tighten goal spec when context_dilution
                             is dominant.
  vstack.plus_delta        — short feedback ritual after every round
                             to reduce repeat handoff_loss.

Factors: {contributing_factors}
Process quality: {process_quality}
Interaction log audit: {log_audit}
Counterfactual audit: {counterfactual}

INSTRUCTIONS:
- Generate 4-8 interventions, ranked highest-impact first.
- At least one intervention MUST set composition_target_pattern when
  the diagnosis warrants delegation.
- Cite the audit findings (log_audit, counterfactual) in rationale.

DO NOT:
- Do not invent composition_target_pattern values outside the allowed
  set.
- Do not return fewer than 4 or more than 8 interventions.

OUTPUT SCHEMA: same as STANDARD_INTERVENTIONS_PROMPT (literal JSON
array of ProcessIntervention).

Return only the JSON array.
"""


def assemble_prompt(template: str, **fields: Any) -> str:
    import json as _json

    formatted: dict[str, str] = {}
    for key, value in fields.items():
        if value is None:
            formatted[key] = "(none)"
            continue
        if isinstance(value, bool):
            formatted[key] = "true" if value else "false"
            continue
        if isinstance(value, (int, float)):
            formatted[key] = str(value)
            continue
        if isinstance(value, (list, tuple, dict)):
            try:
                payload = _json.dumps(value, indent=2, default=str)
            except (TypeError, ValueError):
                payload = repr(value)
            formatted[key] = fence(key, sanitize_for_prompt(payload))
            continue
        if isinstance(value, str):
            formatted[key] = fence(key, sanitize_for_prompt(value))
            continue
        formatted[key] = fence(key, sanitize_for_prompt(str(value)))
    return template.format(**formatted)


# Legacy aliases (preserved for backwards compatibility).
FACTOR_PROMPT = STANDARD_FACTORS_PROMPT
INTERVENTIONS_PROMPT = STANDARD_INTERVENTIONS_PROMPT


__all__ = [
    "FACTOR_PROMPT",
    "FORENSIC_COUNTERFACTUAL_PROMPT",
    "FORENSIC_INTERVENTIONS_PROMPT",
    "FORENSIC_LOG_AUDIT_PROMPT",
    "INTERVENTIONS_PROMPT",
    "PROCESS_GAIN_LOSS_SYSTEM_PROMPT",
    "QUICK_DIAGNOSTIC_PROMPT",
    "STANDARD_FACTORS_PROMPT",
    "STANDARD_INTERVENTIONS_PROMPT",
    "assemble_prompt",
]
