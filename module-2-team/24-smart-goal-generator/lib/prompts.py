"""LLM prompts for the SMART Goal Generator.

0.15.0 uplift: OUTPUT SCHEMA literals + DO NOT rules + one-shot example.
Wire format unchanged.
"""

from __future__ import annotations

from typing import Any

from vstack.aar import fence, sanitize_for_prompt


SMART_SYSTEM_PROMPT = """You are a SMART-goal generator grounded in:

  - **Doran (1981)** "There's a S.M.A.R.T. Way to Write Management's
    Goals and Objectives," Management Review.
  - **Locke & Latham (1990)** Theory of Goal Setting and Task Performance.

You take a VAGUE goal and produce a structured SMART goal spec the
agent can hold itself accountable to. Goals must be SPECIFIC,
MEASURABLE, ACHIEVABLE, RELEVANT, TIME-BOUND.

Kill criteria are the MOST important field: agents without abandonment
conditions cause the most expensive incidents.

SMART quality calibration (overall_smart_score band -> smart_quality):
  - score in [0.85, 1.00] -> "production-ready"
  - score in [0.65, 0.84] -> "usable"
  - score in [0.35, 0.64] -> "draft"
  - score in [0.00, 0.34] -> "vague" (should be regenerated)

Posture (absolute):
- **HONEST ABOUT ACHIEVABILITY.** If the goal is not achievable in the
  named timeframe with the named resources, say so and surface as an
  open_question.
- **KILL-CRITERIA-FIRST.** Always populate kill_criteria. An agent
  without abandonment conditions is the most dangerous configuration.
- **NO INVENTED DETAILS.** When critical context is missing, surface
  it as open_questions; do not invent details.
- **TERSE.** Output is read on dashboards.

Output discipline: when asked for JSON, return JSON only. No prose, no markdown fences.
"""


SMART_GENERATION_PROMPT = """STANDARD mode -- generate a SMART goal spec from the vague request.

Vague goal: {vague_goal}
Context: {context}
Available resources: {available_resources}
Known constraints: {known_constraints}
Deadline hint: {deadline_hint}
Framework hint: {framework}

INSTRUCTIONS:
- Each of the 5 SMART criteria must be addressed.
- ``criteria`` returns a 5-entry array in canonical order: specific,
  measurable, achievable, relevant, time_bound.
- ``kill_criteria`` MUST be populated even if you have to surface
  open_questions to find them.
- ``success_metrics`` should be MACHINE-CHECKABLE where possible
  (Locke-Latham 1990: specific quantifiable goals beat vague ones).

DO NOT:
- Do not invent details to fill gaps; surface as open_questions.
- Do not return an empty kill_criteria list.
- Do not return prose around the JSON.
- Do not reorder criteria.

OUTPUT SCHEMA (literal JSON object):
{{
  "smart_statement": "<the rewritten SMART version of the vague goal>",
  "criteria": [
    {{
      "criterion": "specific" | "measurable" | "achievable" | "relevant" | "time_bound",
      "addressed": true | false,
      "evidence": "<which part of smart_statement addresses this>",
      "score": <float in [0.0, 1.0]>
    }},
    ... (5 total, canonical order)
  ],
  "completion_criteria": ["<concrete done condition>", ...],
  "success_metrics": [
    {{
      "name": "<short name>",
      "operational_definition": "<how it's measured>",
      "target_value": "<concrete target>",
      "machine_checkable": true | false
    }},
    ...
  ],
  "kill_criteria": ["<concrete kill trigger>", ...],
  "deadline": "<ISO date or relative>",
  "open_questions": ["<unanswered question blocking achievability>", ...],
  "overall_smart_score": <float in [0.0, 1.0]>,
  "smart_quality": "production-ready" | "usable" | "draft" | "vague"
}}

EXAMPLE (transforming "improve test coverage" -> machine-checkable SMART):
{{
  "smart_statement": "Raise pytest line-coverage on the auth/ module from current 42% to >=80% by 2026-07-31, measured by the CI run on `main`.",
  "completion_criteria": [
    "coverage.xml on main shows line-rate >= 0.80 for auth/**",
    "All new tests pass in CI on the merge commit"
  ],
  "success_metrics": [
    {{
      "name": "auth_module_line_coverage",
      "operational_definition": "pytest --cov=auth coverage.xml line-rate",
      "target_value": ">= 0.80",
      "machine_checkable": true
    }}
  ],
  "kill_criteria": [
    "If achieving 80% requires testing private APIs that are scheduled for refactor in Q3, ABANDON and re-spec after refactor",
    "If on 2026-07-15 coverage is still < 60%, escalate to tech-lead"
  ]
}}

Return only the JSON object.
"""


QUICK_DIAGNOSTIC_PROMPT = """QUICK mode -- produce a minimal SMART goal spec.

Vague goal: {vague_goal}
Context: {context}
Deadline hint: {deadline_hint}

INSTRUCTIONS:
- Same fields as STANDARD mode but compact: 1-2 success_metrics,
  1-2 kill_criteria.
- kill_criteria still required.

DO NOT:
- Do not invent details.
- Do not return empty kill_criteria.

OUTPUT SCHEMA: same as SMART_GENERATION_PROMPT but with compact lists.

Return only the JSON object.
"""


STANDARD_SMART_GENERATION_PROMPT = SMART_GENERATION_PROMPT


FORENSIC_CRITERIA_COMPLETENESS_PROMPT = """FORENSIC mode -- audit criteria completeness.

Goal spec:
{goal}

INSTRUCTIONS:
- For each of the 5 SMART criteria, judge whether it is substantively
  addressed.
- addressed_criteria_count in [0, 5].
- ``weak_criteria``: criteria addressed but with poor evidence.
- ``missing_criteria``: criteria not addressed at all.
- completeness in [0, 1].

DO NOT:
- Do not credit a criterion as addressed if the evidence is vague.

OUTPUT SCHEMA (literal JSON object representing CriteriaCompletenessAudit):
{{
  "addressed_criteria_count": <integer in [0, 5]>,
  "weak_criteria": ["specific" | "measurable" | "achievable" | "relevant" | "time_bound", ...],
  "missing_criteria": ["specific" | "measurable" | "achievable" | "relevant" | "time_bound", ...],
  "completeness": <float in [0.0, 1.0]>,
  "notes": "<one paragraph>"
}}

Return only the JSON object.
"""


FORENSIC_MEASUREMENT_RIGOR_PROMPT = """FORENSIC mode -- audit measurement rigor.

Goal spec:
{goal}

INSTRUCTIONS:
- Count operationalizable (machine-checkable) success metrics +
  operationalizable kill criteria.
- Count qualitative (judgment-required) success metrics + kill criteria.
- rigor in [0, 1]; higher = more machine-checkable.

DO NOT:
- Do not count "we will know it when we see it" as operationalizable.

OUTPUT SCHEMA (literal JSON object representing MeasurementRigorAudit):
{{
  "operationalizable_metric_count": <non-negative integer>,
  "qualitative_metric_count": <non-negative integer>,
  "operationalizable_kill_count": <non-negative integer>,
  "qualitative_kill_count": <non-negative integer>,
  "rigor": <float in [0.0, 1.0]>,
  "notes": "<one paragraph>"
}}

Return only the JSON object.
"""


FORENSIC_INTERVENTIONS_PROMPT = """FORENSIC mode -- propose 3-6 quality-improvement interventions for a SMART goal spec.

Allowed composition_target_pattern values:
  vstack.grpi, vstack.aar, vstack.plus_delta, vstack.lewin,
  vstack.devils_advocate

Goal spec:
{goal}
Criteria audit: {criteria_audit}
Rigor audit: {rigor_audit}

INSTRUCTIONS:
- target_criterion: specific / measurable / achievable / relevant /
  time_bound / overall.
- Cite criteria_audit + rigor_audit findings in rationale.

DO NOT:
- Do not invent composition_target_pattern values outside the allowed
  set.
- Do not return fewer than 3 or more than 6 interventions.

ALLOWED intervention_type values:
  tighten_specificity, add_measurement, calibrate_achievability,
  ground_relevance, add_deadline, add_kill_criteria,
  add_completion_criteria, decompose_goal, new_eval, human_review,
  compose_pattern

OUTPUT SCHEMA (literal JSON array of SmartGoalIntervention objects):
[
  {{
    "target_criterion": "specific" | "measurable" | "achievable" | "relevant" | "time_bound" | "overall",
    "intervention_type": "<from the allowed set>",
    "description": "<one line>",
    "suggested_implementation": "<concrete>",
    "estimated_impact": "high" | "medium" | "low",
    "rationale": "<Doran 1981 / Locke-Latham 1990 anchored>",
    "composition_target_pattern": "<vstack.xxx or null>"
  }},
  ...
]

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


__all__ = [
    "FORENSIC_CRITERIA_COMPLETENESS_PROMPT",
    "FORENSIC_INTERVENTIONS_PROMPT",
    "FORENSIC_MEASUREMENT_RIGOR_PROMPT",
    "QUICK_DIAGNOSTIC_PROMPT",
    "SMART_GENERATION_PROMPT",
    "SMART_SYSTEM_PROMPT",
    "STANDARD_SMART_GENERATION_PROMPT",
    "assemble_prompt",
]
