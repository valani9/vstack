"""LLM prompts for the Robbins & Judge 7-Characteristics Culture Diagnostic.

0.15.0 uplift: OUTPUT SCHEMA literals + DO NOT rules + one-shot example.
Wire format unchanged.
"""

from __future__ import annotations

from vstack.aar import fence, sanitize_for_prompt

ROBBINS_SYSTEM_PROMPT = """You are a culture-profile diagnostician grounded in
Stephen P. Robbins and Timothy A. Judge, *Organizational Behavior*
(Pearson, 17th ed., 2017). The Robbins/Judge model decomposes
organizational culture into seven independent dimensions:

  - INNOVATION          tolerance for risk and novel approaches
  - ATTENTION_TO_DETAIL precision, analysis, attention to specifics
  - OUTCOME             emphasis on results vs process
  - PEOPLE              consideration for effects on team/stakeholders
  - TEAM                work organized around teams vs individuals
  - AGGRESSIVENESS      competitiveness vs easy-going
  - STABILITY           status-quo vs growth/dynamism

Each dimension is INDEPENDENT — a culture can be high-innovation
high-detail (research lab) or low-innovation high-detail (regulated
finance) or high-innovation low-detail (early-stage startup). There
is no universally "correct" profile; the right profile depends on
the task class.

Target profiles by task class (rough heuristics — adjust based on specifics):

  - research_exploration: high innovation, moderate detail, low aggressiveness,
                          low stability, moderate people, low-medium outcome,
                          moderate team
  - creative_generation:  high innovation, low-medium detail, low aggressiveness,
                          low stability
  - regulated_workflow:   low innovation, very high detail, low aggressiveness,
                          high stability, high outcome
  - financial_operation:  low innovation, very high detail, low aggressiveness,
                          high stability, very high outcome
  - customer_support:     low-medium innovation, high detail, high people,
                          moderate stability
  - code_review:          medium innovation, very high detail, medium people,
                          moderate aggressiveness (need to push back)
  - incident_response:    medium innovation, high detail, medium aggressiveness,
                          low stability (must adapt quickly), high outcome
  - general_purpose:      balanced (~0.5 on each)

Fit-quality calibration:
  - overall_fit >= 0.8  -> "well-fit"
  - overall_fit in [0.5, 0.79] -> "partial-fit"
  - overall_fit < 0.5  -> "misfit"

Posture (absolute):
- **EVIDENCE-GROUNDED.** Cite specific trace steps + system-prompt fragments.
- **TASK-CLASS-AWARE.** The same observed behavior is fit for some task classes and unfit for others.
- **INDEPENDENCE-RESPECTING.** The seven dimensions are independent; do not assume they correlate.
- **TERSE.** Output is read on dashboards.

Output discipline: when asked for JSON, return JSON only. No prose, no markdown fences.
"""


PROFILE_PROMPT = """STANDARD mode -- score each of the seven culture characteristics.

Task: {task}
Task class (target profile driver): {task_class}
Subject model: {model_name}
Outcome: {outcome}
Success: {success}

System prompt (espoused-values source):
{system_prompt}

Observed behaviors:
{observed_behaviors}

INSTRUCTIONS:
- Return exactly 7 CharacteristicScore objects in canonical order:
    1. innovation
    2. attention_to_detail
    3. outcome
    4. people
    5. team
    6. aggressiveness
    7. stability
- observed_score from trace; target_score from task_class profile.
- fit_score = 1 - abs(observed - target).
- overall_fit = mean of the seven fit_scores.
- ``risk`` per characteristic: low / medium / high based on what
  failure on this dimension would cost in this task class.

DO NOT:
- Do not give all 7 characteristics the same score; they are independent.
- Do not invent quotes.
- Do not reorder; canonical order required.
- Do not return prose around the JSON.

OUTPUT SCHEMA (literal JSON object):
{{
  "characteristics": [
    {{
      "characteristic": "innovation" | "attention_to_detail" | "outcome" | "people" | "team" | "aggressiveness" | "stability",
      "observed_score": <float in [0.0, 1.0]>,
      "target_score": <float in [0.0, 1.0]>,
      "fit_score": <float in [0.0, 1.0]>,
      "explanation": "<1-3 sentences citing evidence>",
      "evidence_quotes": ["<verbatim>", ...],
      "confidence": <float in [0.0, 1.0]>,
      "risk": "low" | "medium" | "high"
    }},
    ... (7 total, canonical order)
  ],
  "overall_fit": <float in [0.0, 1.0]>,
  "fit_quality": "well-fit" | "partial-fit" | "misfit",
  "biggest_gap": "<canonical characteristic name or 'none'>"
}}

EXAMPLE (regulated_workflow misfit on attention_to_detail):
{{
  "characteristic": "attention_to_detail",
  "observed_score": 0.42,
  "target_score": 0.95,
  "fit_score": 0.47,
  "explanation": "Agent produced regulatory disclosure with three numerical inconsistencies (lines 4, 7, 12). Robbins-Judge 2017 task-class target for regulated_workflow demands very high attention_to_detail; observed score is materially below target.",
  "evidence_quotes": ["net income $2.4M", "total of $2.6M", "$2.4M as previously stated"],
  "confidence": 0.9,
  "risk": "high"
}}

Return only the JSON object.
"""


QUICK_PROFILE_PROMPT = """QUICK mode -- 7-Characteristics profile + 1 top intervention.

Task: {task}
Task class: {task_class}
Subject model: {model_name}
Outcome: {outcome}
Success: {success}

System prompt: {system_prompt}

Observed behaviors:
{observed_behaviors}

INSTRUCTIONS:
- Same 7 characteristics + canonical order as STANDARD mode.
- Pick 1 top_intervention OR null if well-fit.

DO NOT:
- Do not return more than one intervention.

OUTPUT SCHEMA: same fields as PROFILE_PROMPT plus
``top_intervention`` (one CultureIntervention or null).

Return only the JSON object.
"""


INTERVENTIONS_PROMPT = """STANDARD mode -- propose 2-4 interventions to close the biggest gap.

Task class: {task_class}
Fit quality: {fit_quality}
Biggest gap: {biggest_gap}
All characteristic evidence:
{evidence}

INSTRUCTIONS:
- Target the biggest_gap characteristic.
- direction: increase (raise observed toward target) or decrease.
- Rank from highest expected impact to lowest.
- ``rationale`` cites Robbins-Judge 2017.

DO NOT:
- Do not target a characteristic with high fit_score.
- Do not return prose around the JSON.

ALLOWED intervention_type values:
  rewrite_system_prompt, adjust_temperature, add_guardrail,
  swap_model, add_team_scaffold, remove_solo_path, add_kill_criterion,
  new_eval, human_review, compose_pattern

OUTPUT SCHEMA (literal JSON array of CultureIntervention objects):
[
  {{
    "target_characteristic": "<canonical characteristic>",
    "direction": "increase" | "decrease",
    "intervention_type": "<from the allowed set>",
    "description": "<one line>",
    "suggested_implementation": "<concrete>",
    "estimated_impact": "high" | "medium" | "low",
    "rationale": "<Robbins-Judge 2017 anchored>",
    "effort_estimate": "1h" | "1d" | "1w" | "1m" | "ongoing",
    "risk": "low" | "medium" | "high"
  }},
  ...
]

Return only the JSON array.
"""


FORENSIC_PROVENANCE_PROMPT = """FORENSIC mode -- target-profile provenance.

Task class: {task_class}
System prompt: {system_prompt}
Observed behaviors:
{observed_behaviors}

INSTRUCTIONS:
- ``derived_from``: task_class_default (used canonical heuristic);
  trace_evidence (trace overrode the default); blended (mix).
- ``per_dim_overrides``: dict of dimension_name -> target_score for
  any dimension where the trace implies a different target.

DO NOT:
- Do not add an override without trace evidence supporting it.

OUTPUT SCHEMA (literal JSON object):
{{
  "derived_from": "task_class_default" | "trace_evidence" | "blended",
  "rationale": "<1-2 sentences>",
  "per_dim_overrides": {{
    "<characteristic_name>": <float in [0.0, 1.0]>,
    ...
  }}
}}

Return only the JSON object.
"""


FORENSIC_RISK_PROMPT = """FORENSIC mode -- per-dimension risk ranking.

Task class: {task_class}
Outcome: {outcome}
Success: {success}
Observed behaviors:
{observed_behaviors}

INSTRUCTIONS:
- For each of the 7 dimensions, classify what FAILURE on that
  dimension would cost in this task_class: low / medium / high.
- ``highest_risk_dimension`` names the worst.

DO NOT:
- Do not classify every dimension as the same risk.

OUTPUT SCHEMA (literal JSON object):
{{
  "highest_risk_dimension": "<canonical characteristic or 'none'>",
  "risk_explanation": "<1-3 sentences>",
  "per_dim_risk": {{
    "innovation": "low" | "medium" | "high",
    "attention_to_detail": "low" | "medium" | "high",
    "outcome": "low" | "medium" | "high",
    "people": "low" | "medium" | "high",
    "team": "low" | "medium" | "high",
    "aggressiveness": "low" | "medium" | "high",
    "stability": "low" | "medium" | "high"
  }}
}}

Return only the JSON object.
"""


FORENSIC_INTERVENTIONS_PROMPT = """FORENSIC mode -- interventions prioritized by (risk x gap-size).

Task class: {task_class}
Fit quality: {fit_quality}
Biggest gap: {biggest_gap}
Provenance: {provenance}
Per-dimension risk: {per_dim_risk}
All characteristic evidence:
{evidence}

INSTRUCTIONS:
- Generate 3-6 interventions, prioritized by (risk x gap-size).
- Same intervention schema as INTERVENTIONS_PROMPT.
- Cite per_dim_risk + provenance in rationale.

DO NOT:
- Do not return fewer than 3 or more than 6 interventions.

OUTPUT SCHEMA: same as INTERVENTIONS_PROMPT.

Return only the JSON array.
"""


def assemble_prompt(
    template: str,
    /,
    *,
    system_prompt: str = "",
    observed_behaviors: list[str] | None = None,
    inferred_assumptions: list[str] | None = None,
    **kwargs: object,
) -> str:
    """Fence + sanitize untrusted fields, then fill the template."""
    safe_prompt = fence("system_prompt", sanitize_for_prompt(system_prompt or "(none)"))
    behaviors = observed_behaviors or []
    if behaviors:
        behaviors_text = "\n".join(f"- {sanitize_for_prompt(b)}" for b in behaviors)
    else:
        behaviors_text = "(none)"
    safe_behaviors = fence("observed_behaviors", behaviors_text)
    fields: dict[str, object] = {
        "system_prompt": safe_prompt,
        "observed_behaviors": safe_behaviors,
    }
    if inferred_assumptions is not None:
        if inferred_assumptions:
            ass_text = "\n".join(f"- {sanitize_for_prompt(a)}" for a in inferred_assumptions)
        else:
            ass_text = "(none)"
        fields["inferred_assumptions"] = fence("inferred_assumptions", ass_text)
    fields.update(kwargs)
    return template.format(**fields)


__all__ = [
    "FORENSIC_INTERVENTIONS_PROMPT",
    "FORENSIC_PROVENANCE_PROMPT",
    "FORENSIC_RISK_PROMPT",
    "INTERVENTIONS_PROMPT",
    "PROFILE_PROMPT",
    "QUICK_PROFILE_PROMPT",
    "ROBBINS_SYSTEM_PROMPT",
    "assemble_prompt",
]
