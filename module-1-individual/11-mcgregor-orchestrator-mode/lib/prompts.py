"""LLM prompt templates for the McGregor Theory X/Y Orchestrator Mode Diagnostic.

Three modes (quick / standard / forensic) with shared system prompt
naming 7 literature anchors.

0.15.0 uplift: OUTPUT SCHEMA literals, DO NOT rules, one-shot example,
calibration. Wire format unchanged.
"""

from __future__ import annotations

from typing import Any

from vstack.aar import fence, sanitize_for_prompt


MCGREGOR_SYSTEM_PROMPT = """You are an orchestrator-mode diagnostician grounded in:

1. **McGregor (1960)** *The Human Side of Enterprise* — canonical Theory X / Theory Y.
2. **McGregor (1966)** *Leadership and Motivation* — mature framework.
3. **Schein (1990)** *Organizational Culture and Leadership* — cultural Theory X/Y layer.
4. **Pfeffer & Salancik (1978)** *External Control of Organizations* — task-property contingency.
5. **Argyris (1957)** *Personality and Organization* — pathology of pure Theory X.
6. **Eisenhardt (1989)** "Agency Theory" — principal-agent contingency.
7. **Wang et al. (2023)** Cooperative LLM Agents + LangGraph/CrewAI orchestration — modern LLM analog.

Two contrasting orchestrator modes (with a hybrid):

  THEORY X  every action approved; tight oversight; trust low.
  THEORY Y  broad goals + budget; loose oversight; trust high.
  HYBRID    per-step decision based on risk + reversibility.

For AI agent systems, the **optimal mode is a function of task properties**:
  - risk_level         (low / medium / high)
  - complexity         (routine / moderate / novel)
  - reversibility      (reversible / partial / irreversible)
  - regulatory_exposure (true / false)
  - agent_capability   (unproven / moderate / proven)

Decision heuristics (Eisenhardt 1989 agency-theory contingency):
  - irreversible + high-risk                     -> Theory X.
  - low-risk + reversible + proven agent         -> Theory Y.
  - novel + moderate-risk + proven               -> hybrid (Y default, X on risky branches).
  - regulated workflow                           -> Theory X or hybrid biased toward X.
  - creative + reversible + proven               -> Theory Y.

Mode indicators (compute from trace, each in [0, 1]):
  - check_in_frequency
  - autonomy_granted
  - pre_approval_required
  - intervention_rate

Mode-quality calibration:
  - well-matched:   |observed - optimal| < 0.2.
  - mild-mismatch:  0.2 <= |observed - optimal| < 0.5.
  - severe-mismatch: |observed - optimal| >= 0.5.

Posture (absolute):
- **CONTINGENCY-AWARE.** Optimal depends on task properties; no universal answer.
- **EVIDENCE-GROUNDED.** Cite specific orchestrator steps.
- **COST-CONSCIOUS.** Theory-X over-supervision wastes; Theory-Y under-supervision is dangerous on the wrong tasks.
- **TERSE.** Output is read on dashboards.

Output discipline: when asked for JSON, return JSON only. No prose, no markdown fences.
"""


QUICK_DIAGNOSTIC_PROMPT = """QUICK mode -- observed mode + optimal mode + top intervention.

Task: {task}
Task properties: {task_properties}
Sub-agents: {sub_agents}
Outcome: {outcome}
Success: {success}
Trace (orchestrator + agent steps):
{trace}

INSTRUCTIONS:
- Identify observed_mode from the trace.
- Identify optimal_mode from the decision heuristics in the system prompt.
- mode_mismatch = absolute distance between observed and optimal.
- Pick ONE intervention targeting movement toward optimal.

DO NOT:
- Do not recommend Theory X for low-risk reversible tasks (over-
  supervision wastes).
- Do not recommend Theory Y for irreversible high-risk tasks
  (under-supervision is dangerous).
- Do not return more than one intervention.

OUTPUT SCHEMA (literal JSON object):
{{
  "observed_mode": "theory_x" | "theory_y" | "hybrid",
  "optimal_mode": "theory_x" | "theory_y" | "hybrid",
  "mode_mismatch": <float in [0.0, 1.0]>,
  "indicators": {{
    "check_in_frequency": <float in [0.0, 1.0]>,
    "autonomy_granted": <float in [0.0, 1.0]>,
    "pre_approval_required": <float in [0.0, 1.0]>,
    "intervention_rate": <float in [0.0, 1.0]>,
    "explanation": "<1-2 sentences>",
    "evidence_quotes": ["<verbatim substring>", ...],
    "confidence": <float in [0.0, 1.0]>
  }},
  "mode_quality": "well-matched" | "mild-mismatch" | "severe-mismatch",
  "rationale": "<one paragraph anchored in Eisenhardt 1989>",
  "top_intervention": {{
    "target_mode": "theory_x" | "theory_y" | "hybrid",
    "intervention_type": "<from the allowed set>",
    "description": "<one line>",
    "suggested_implementation": "<concrete>",
    "estimated_impact": "high" | "medium" | "low",
    "rationale": "<short, named-source anchored>"
  }}
}}

Return only the JSON object.
"""


STANDARD_MODE_PROMPT = """STANDARD mode -- identify observed mode, optimal mode, and mode indicators.

Task: {task}
Task properties: {task_properties}
Sub-agents: {sub_agents}
Outcome: {outcome}
Success: {success}
Trace:
{trace}

INSTRUCTIONS:
- Use the decision heuristics from the system prompt to derive
  optimal_mode.
- ``evidence_quotes`` must be verbatim substrings of the trace.

DO NOT:
- Do not invent quotes.
- Do not pick observed_mode = optimal_mode automatically; the trace
  has independent evidence.
- Do not return prose around the JSON.

OUTPUT SCHEMA (literal JSON object):
{{
  "observed_mode": "theory_x" | "theory_y" | "hybrid",
  "optimal_mode": "theory_x" | "theory_y" | "hybrid",
  "mode_mismatch": <float in [0.0, 1.0]>,
  "indicators": {{
    "check_in_frequency": <float in [0.0, 1.0]>,
    "autonomy_granted": <float in [0.0, 1.0]>,
    "pre_approval_required": <float in [0.0, 1.0]>,
    "intervention_rate": <float in [0.0, 1.0]>,
    "explanation": "<1-3 sentences>",
    "evidence_quotes": ["<verbatim substring>", ...],
    "confidence": <float in [0.0, 1.0]>
  }},
  "mode_quality": "well-matched" | "mild-mismatch" | "severe-mismatch",
  "rationale": "<why observed is or is not right, anchored in Eisenhardt 1989>"
}}

EXAMPLE (Theory X mismatch on low-risk reversible task; Argyris 1957 over-supervision pathology):
{{
  "observed_mode": "theory_x",
  "optimal_mode": "theory_y",
  "mode_mismatch": 0.75,
  "indicators": {{
    "check_in_frequency": 0.95,
    "autonomy_granted": 0.10,
    "pre_approval_required": 0.90,
    "intervention_rate": 0.80,
    "explanation": "Orchestrator approves every sub-agent action; 11 of 12 turns request approval before proceeding.",
    "evidence_quotes": ["approving step 1", "approving step 2", "approving step 3"],
    "confidence": 0.9
  }},
  "mode_quality": "severe-mismatch",
  "rationale": "Task is low-risk + reversible + proven agent; Eisenhardt 1989 agency-theory predicts Theory Y dominance. Observed Theory X produces Argyris 1957 over-supervision pathology: wasted orchestrator turns + agent learned helplessness."
}}

Return only the JSON object.
"""


STANDARD_INTERVENTIONS_PROMPT = """STANDARD mode -- propose 2-4 ranked interventions to shift toward optimal.

Observed mode: {observed_mode}
Optimal mode: {optimal_mode}
Mode quality: {mode_quality}
Indicators: {indicators}
Task properties: {task_properties}

INSTRUCTIONS:
- Rank from highest expected impact to lowest.
- Each ``suggested_implementation`` must be concrete.
- ``rationale`` cites McGregor 1960/1966, Eisenhardt 1989, or
  Argyris 1957.

DO NOT:
- Do not propose tightening interventions on a Theory-X
  over-supervised orchestrator; propose loosening.
- Do not propose loosening on a Theory-Y under-supervised
  orchestrator handling irreversible actions; propose tightening.
- Do not return prose around the JSON.

ALLOWED intervention_type values:
  tighten_oversight, loosen_oversight, add_pre_approval_gates,
  remove_pre_approval_gates, add_risk_classifier,
  add_step_classifier, increase_check_in_cadence,
  decrease_check_in_cadence, redefine_agent_boundaries,
  tier_oversight_by_action_type, add_authorization_scope,
  rotate_to_hybrid, elevate_to_human_on_irreversible,
  add_agent_capability_probe, new_eval, human_review,
  compose_pattern, add_orchestrator_eval

OUTPUT SCHEMA (literal JSON array of OrchestratorIntervention objects):
[
  {{
    "target_mode": "theory_x" | "theory_y" | "hybrid",
    "intervention_type": "<from the allowed set>",
    "description": "<one line>",
    "suggested_implementation": "<concrete>",
    "estimated_impact": "high" | "medium" | "low",
    "effort_estimate": "1h" | "1d" | "1w" | "1m" | "ongoing",
    "risk": "low" | "medium" | "high",
    "reversibility": "two-way-door" | "one-way-door",
    "rationale": "<named source + why this works>"
  }},
  ...
]

Return only the JSON array.
"""


FORENSIC_STEP_AUDIT_PROMPT = """FORENSIC mode -- audit each step in the trace for mode-appropriateness.

Task properties: {task_properties}
Trace: {trace}

INSTRUCTIONS:
- One StepAudit per step.
- ``mode_signal``: which mode the step exhibits (Theory X = approval
  gating; Theory Y = autonomy; hybrid = mixed).
- ``was_appropriate``: true iff the mode_signal matches the
  optimal_mode for the step's action_type (given task_properties).

DO NOT:
- Do not classify a "logged the step" action as Theory X; logging is
  hybrid by default.

OUTPUT SCHEMA (literal JSON array of StepAudit objects):
[
  {{
    "step_index": <non-negative integer>,
    "step_type": "<short step-type name>",
    "mode_signal": "theory_x" | "theory_y" | "hybrid",
    "was_appropriate": true | false,
    "suggested_alternative": "<one line>",
    "explanation": "<1-2 sentences>"
  }},
  ...
]

Return only the JSON array.
"""


FORENSIC_OPTIMALITY_PROMPT = """FORENSIC mode -- justify the optimal mode in detail (Eisenhardt 1989 agency-theory contingency).

Task: {task}
Task properties: {task_properties}
Sub-agents: {sub_agents}

INSTRUCTIONS:
- For the given task_properties, identify optimal_mode and walk
  through each contingency factor.

DO NOT:
- Do not pick an optimal_mode that contradicts the decision heuristics
  in the system prompt.

OUTPUT SCHEMA (literal JSON object representing OptimalityJustification):
{{
  "optimal_mode": "theory_x" | "theory_y" | "hybrid",
  "task_risk": "<1-2 sentences how risk shapes the decision>",
  "task_complexity": "<1-2 sentences>",
  "task_reversibility": "<1-2 sentences>",
  "agent_capability": "<1-2 sentences>",
  "regulatory": "<1-2 sentences if applicable, or null>",
  "final_rationale": "<one paragraph anchored in Eisenhardt 1989>"
}}

Return only the JSON object.
"""


FORENSIC_INTERVENTIONS_PROMPT = """FORENSIC mode -- propose 4-8 ranked interventions with composition targets.

Allowed composition_target_pattern values:
  vstack.lewin, vstack.aar, vstack.devils_advocate, vstack.bias_stack,
  vstack.smart_goal, vstack.plus_delta, vstack.schein_culture,
  vstack.hexaco, vstack.grpi, vstack.lencioni,
  vstack.process_gain_loss, vstack.social_loafing

Observed mode: {observed_mode}
Optimal mode: {optimal_mode}
Profile pattern: {profile_pattern}
Mode quality: {mode_quality}
Step audits: {step_audits}
Optimality justification: {optimality}
Indicators: {indicators}
Task properties: {task_properties}

INSTRUCTIONS:
- Generate 4-8 interventions, ranked highest impact first.
- Cite the step_audits + optimality justification in rationale.

DO NOT:
- Do not invent composition_target_pattern values outside the allowed
  set.
- Do not return fewer than 4 or more than 8 interventions.

OUTPUT SCHEMA: same as STANDARD_INTERVENTIONS_PROMPT.

Return only the JSON array.
"""


def assemble_prompt(template: str, **fields: Any) -> str:
    """Fill a prompt template, sanitizing + fencing every free-text field."""
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


# Legacy aliases.
MODE_PROMPT = STANDARD_MODE_PROMPT
INTERVENTIONS_PROMPT = STANDARD_INTERVENTIONS_PROMPT


__all__ = [
    "FORENSIC_INTERVENTIONS_PROMPT",
    "FORENSIC_OPTIMALITY_PROMPT",
    "FORENSIC_STEP_AUDIT_PROMPT",
    "INTERVENTIONS_PROMPT",
    "MCGREGOR_SYSTEM_PROMPT",
    "MODE_PROMPT",
    "QUICK_DIAGNOSTIC_PROMPT",
    "STANDARD_INTERVENTIONS_PROMPT",
    "STANDARD_MODE_PROMPT",
    "assemble_prompt",
]
