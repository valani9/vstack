"""LLM prompt templates for the Yerkes-Dodson Workload Diagnostic.

Anchored in:
  - Yerkes & Dodson (1908) — the original inverted-U arousal-
    performance curve.
  - Sweller (1988, 1994, 2011) Cognitive Load Theory.
  - Kahneman (1973) *Attention and Effort.*
  - Hancock & Warm (1989) dynamic adaptability framework.
  - Eysenck & Calvo (1992) Attentional Control Theory.
  - Hebb (1955) arousal as physiological precursor of performance.
  - Liu et al. (2024) lost-in-the-middle LLM context-saturation
    finding.

The detector takes a task + pressure inputs + observed behaviors and
classifies the agent's WORKLOAD ZONE on the Yerkes-Dodson curve:

  - under_pressure   — wandering, drift, low engagement.
  - optimal          — focused, productive, calibrated.
  - over_pressure    — corner-cutting, freezing, hallucinating,
                       refusing.

Three modes (quick / standard / forensic). Forensic mode adds
Sweller CLT decomposition and Liu et al. 2024 context-saturation
analysis.

The 0.13.0 uplift adds OUTPUT SCHEMA literals (formalizing what
v0.12.x had inline), a one-shot example on STANDARD_WORKLOAD_PROMPT,
explicit DO NOT rules, and zone-score calibration anchors.
"""

from __future__ import annotations

from typing import Any

from vstack.aar import fence, sanitize_for_prompt


YERKES_DODSON_SYSTEM_PROMPT = """You are a workload-pressure diagnostician for AI agents, grounded in:

  - Yerkes & Dodson (1908) — the original inverted-U
    arousal-performance curve. Complex tasks peak at LOWER arousal
    than simple tasks.
  - Sweller (1988, 1994, 2011) Cognitive Load Theory — three load
    components: intrinsic (task-inherent), extraneous (presentation-
    induced), germane (productive learning).
  - Kahneman (1973) *Attention and Effort* — capacity model:
    attention is a limited resource that depletes under load.
  - Hancock & Warm (1989) — dynamic adaptability framework.
  - Eysenck & Calvo (1992) Attentional Control Theory — anxiety
    reduces processing EFFICIENCY before EFFECTIVENESS.
  - Hebb (1955) — arousal as physiological precursor of performance.
  - Liu et al. (2024) lost-in-the-middle — LLM context-saturation
    finding: information in the MIDDLE of long contexts is recalled
    worse than information at the start or end.

The three workload zones (Yerkes-Dodson inverted-U):

  - under_pressure  — wandering, drift, exploring tangents, low
                      output rate. Symptoms: long thinking turns
                      with no decision; multiple unrelated tool
                      calls; verbose meandering text.
  - optimal         — focused, calibrated, productive. Symptoms:
                      decisive tool calls; tight reasoning; matched
                      output to task complexity.
  - over_pressure   — corner-cutting, freezing, hallucinating,
                      refusing. Symptoms: skipped verification steps;
                      claims without evidence; "I can't help with
                      that" on a task the agent can clearly help
                      with; abrupt early stopping.

Critical Yerkes-Dodson insight: COMPLEX tasks peak at LOWER pressure
than SIMPLE tasks. The same pressure level that puts a simple-task
agent in the "optimal" zone may push a complex-task agent into the
"over_pressure" zone. Account for task_complexity in your scoring.

Zone-score calibration (each zone independently in [0, 1]):

  - 0.00-0.09  zone is absent.
  - 0.10-0.39  zone is mildly present (one or two indicators).
  - 0.40-0.69  zone is materially present (multiple indicators,
                some action implications).
  - 0.70-1.00  zone is dominant (the agent's behavior is best
                described by this zone's signature).

The three scores DO NOT need to sum to 1.0. They are independent
assessments. observed_zone is the zone with the highest score.

Failure mode taxonomy (pick the one that best matches observed
behavior):

  - wandering        — under_pressure signature.
  - focused          — optimal signature (no failure).
  - corner_cutting   — over_pressure; skipped steps.
  - freezing         — over_pressure; agent stalls.
  - hallucinating    — over_pressure; agent invents.
  - refusing         — over_pressure; agent declines to act.
  - unknown          — insufficient evidence.

Posture (absolute):

  - ZONE-AWARE. Score all three zones independently; pick the
    dominant one for observed_zone.
  - TASK-COMPLEXITY SENSITIVE. Apply Yerkes-Dodson 1908 inverted-U:
    complex tasks peak at lower pressure.
  - CLT-AWARE. Distinguish intrinsic / extraneous / germane load
    when forensic mode asks for the decomposition.
  - CONTEXT-SATURATION AWARE. saturation_ratio > 0.7 triggers
    lost_in_middle_risk = "high" (Liu et al. 2024).
  - CALIBRATED. Score 0.0 when a zone is absent. Score 1.0 only
    when the zone is dominant AND the evidence is unambiguous.
  - TERSE. Output is read on dashboards.

Output discipline: when the prompt says "return only the JSON ...",
emit JSON only. No prose. No markdown fences.
"""


QUICK_DIAGNOSTIC_PROMPT = """QUICK mode -- score all three workload zones PLUS the single highest-impact intervention.

Task: {task}
Pressure inputs: {pressure}
Observed behaviors: {observed_behaviors}
Outcome: {outcome}
Success: {success}

INSTRUCTIONS:
- Score all 3 zones (canonical order: under_pressure, optimal,
  over_pressure). Use the calibration table from the system prompt.
- observed_zone = zone with the highest score.
- distance_from_optimal in [0, 1]; 0 means perfectly in the optimal
  zone, 1 means maximally far from it.
- Map failure_mode to the dominant observed behavior.
- Pick exactly ONE intervention with direction = increase_pressure
  (if observed_zone = under_pressure) OR decrease_pressure (if
  observed_zone = over_pressure).

DO NOT:
- Do not return more than one intervention.
- Do not set direction = increase_pressure on an over_pressure
  observation (that would push the agent further off the curve).
- Do not score every zone the same; the agent has a zone signature.

OUTPUT SCHEMA (literal JSON object):
{{
  "zone_evidence": [
    {{
      "zone": "under_pressure" | "optimal" | "over_pressure",
      "score": <float in [0.0, 1.0]>,
      "explanation": "<1-2 sentences anchored in Yerkes-Dodson 1908>",
      "evidence_quotes": ["<verbatim substring>", ...],
      "confidence": <float in [0.0, 1.0]>
    }},
    ... (3 total, canonical order)
  ],
  "observed_zone": "under_pressure" | "optimal" | "over_pressure",
  "distance_from_optimal": <float in [0.0, 1.0]>,
  "failure_mode": "wandering" | "focused" | "corner_cutting" | "freezing" | "hallucinating" | "refusing" | "unknown",
  "top_intervention": {{
    "intervention_type": "<from the allowed set>",
    "direction": "increase_pressure" | "decrease_pressure",
    "description": "<one line>",
    "suggested_implementation": "<concrete>",
    "estimated_impact": "high" | "medium" | "low",
    "rationale": "<short, named-source anchored>"
  }}
}}

Return only the JSON object.
"""


STANDARD_WORKLOAD_PROMPT = """STANDARD mode -- score 3 workload zones, identify failure mode, propose interventions.

Task: {task}
Pressure inputs: {pressure}
Observed behaviors: {observed_behaviors}
Outcome: {outcome}
Success: {success}

INSTRUCTIONS:
- Score all 3 zones (canonical order: under_pressure, optimal,
  over_pressure). Use the calibration table from the system prompt.
- ``evidence_quotes`` must be verbatim substrings of the task /
  pressure / observed_behaviors inputs.
- observed_zone, distance_from_optimal, failure_mode as defined in
  the system prompt.
- Propose 2-4 ranked interventions:
    * direction = increase_pressure if observed_zone = under_pressure.
    * direction = decrease_pressure if observed_zone = over_pressure.
    * If observed_zone = optimal, propose hardening interventions
      (locks in the current calibration).
- Anchor each rationale in a named source (Yerkes-Dodson 1908,
  Sweller, Kahneman 1973, Hancock & Warm 1989, Eysenck-Calvo 1992,
  Liu et al. 2024 for context).

DO NOT:
- Do not propose generic "improve focus" interventions. Name the
  literal artifact: the prompt edit, the eval, the scaffold change,
  the budget cap.
- Do not propose direction=increase_pressure on over_pressure or
  direction=decrease_pressure on under_pressure; both would push
  the agent further off the inverted-U curve.
- Do not return prose around the JSON.

ALLOWED intervention_type values:
  tighten_deadline, add_budget_cap, loosen_deadline, loosen_budget,
  add_kill_criterion, raise_retry_cap, lower_retry_cap,
  explicit_focus_prompt, human_review, new_eval,
  reduce_extraneous_load, chunk_context, add_scaffolding,
  remove_irrelevant_context, add_intrinsic_load_step_by_step,
  promote_germane_load, context_compression, compose_pattern

OUTPUT SCHEMA (literal JSON object):
{{
  "zone_evidence": [
    {{
      "zone": "under_pressure" | "optimal" | "over_pressure",
      "score": <float in [0.0, 1.0]>,
      "explanation": "<2-3 sentence diagnosis anchored in named source>",
      "evidence_quotes": ["<verbatim substring>", ...],
      "confidence": <float in [0.0, 1.0]>
    }},
    ... (3 total, canonical order)
  ],
  "observed_zone": "under_pressure" | "optimal" | "over_pressure",
  "distance_from_optimal": <float in [0.0, 1.0]>,
  "failure_mode": "wandering" | "focused" | "corner_cutting" | "freezing" | "hallucinating" | "refusing" | "unknown",
  "interventions": [
    {{
      "intervention_type": "<from the allowed set>",
      "direction": "increase_pressure" | "decrease_pressure",
      "description": "<one-line summary>",
      "suggested_implementation": "<concrete prompt / scaffold / eval>",
      "estimated_impact": "high" | "medium" | "low",
      "effort_estimate": "1h" | "1d" | "1w" | "1m" | "ongoing",
      "risk": "low" | "medium" | "high",
      "reversibility": "one-way-door" | "two-way-door",
      "rationale": "<named source + why this works>"
    }},
    ...
  ]
}}

EXAMPLE (clear over_pressure signature with hallucination failure mode):
{{
  "zone": "over_pressure",
  "score": 0.82,
  "explanation": "The agent skipped the verification step under absurd deadline pressure and fabricated three API field names that do not exist in the input contract. Yerkes-Dodson 1908 + Eysenck-Calvo 1992 predict exactly this: complex task at maximal pressure -> processing-efficiency collapse before effectiveness loss is visible.",
  "evidence_quotes": ["deadline_pressure: absurd", "the endpoint returns a 'session_token' field", "I'll skip the contract check to save time"],
  "confidence": 0.85
}}

Return only the JSON object.
"""


FORENSIC_COGNITIVE_LOAD_PROMPT = """FORENSIC mode -- Sweller Cognitive Load Theory three-component decomposition.

Task: {task}
Pressure inputs: {pressure}
Context size: {context_size_tokens} tokens (window: {context_window_size})
Observed behaviors: {observed_behaviors}

INSTRUCTIONS:
- intrinsic_load: task-inherent complexity in [0, 1]. Higher when the
  task domain is unfamiliar or the goal requires deep reasoning.
- extraneous_load: presentation-induced overhead in [0, 1]. Higher
  when the prompt is poorly structured, context is bloated, or
  formatting fights the agent.
- germane_load: productive learning load in [0, 1]. Higher when the
  task forces the agent to build schemas that transfer.
- total_load: not necessarily the sum; use your judgment for the
  agent's effective load.
- dominant_component: the component carrying the most load.
- notes: one paragraph anchored in Sweller 1988/1994/2011.

DO NOT:
- Do not double-count overhead under both intrinsic and extraneous.
- Do not score extraneous high just because the context is large;
  size alone is not noise.

OUTPUT SCHEMA (literal JSON object):
{{
  "intrinsic_load": <float in [0.0, 1.0]>,
  "extraneous_load": <float in [0.0, 1.0]>,
  "germane_load": <float in [0.0, 1.0]>,
  "total_load": <float in [0.0, 1.0]>,
  "dominant_component": "intrinsic" | "extraneous" | "germane",
  "notes": "<one paragraph anchored in Sweller>"
}}

Return only the JSON object.
"""


FORENSIC_CONTEXT_SATURATION_PROMPT = """FORENSIC mode -- context saturation analysis (Liu et al. 2024).

context_size_tokens: {context_size_tokens}
context_window_size: {context_window_size}
Observed behaviors: {observed_behaviors}

INSTRUCTIONS:
- saturation_ratio: context_size_tokens / context_window_size.
- lost_in_middle_risk:
    * "low"      if saturation_ratio <= 0.4.
    * "moderate" if saturation_ratio in (0.4, 0.7].
    * "high"     if saturation_ratio > 0.7.
- estimated_useful_tokens: your estimate of how many context tokens
  are actually load-bearing for the task.
- estimated_noise_tokens: context_size_tokens - estimated_useful_tokens.
- notes: one paragraph anchored in Liu et al. 2024.

DO NOT:
- Do not estimate useful_tokens at face value of context size;
  Liu et al. 2024 explicitly documents that middle-of-context
  information is recalled worse.

OUTPUT SCHEMA (literal JSON object):
{{
  "saturation_ratio": <float in [0.0, 1.0]>,
  "lost_in_middle_risk": "low" | "moderate" | "high",
  "estimated_useful_tokens": <non-negative integer>,
  "estimated_noise_tokens": <non-negative integer>,
  "notes": "<one paragraph anchored in Liu et al. 2024>"
}}

Return only the JSON object.
"""


FORENSIC_INTERVENTIONS_PROMPT = """FORENSIC mode -- propose 4-8 ranked interventions with composition targets.

Allowed composition_target_pattern values:

  vstack.smart_goal              — tighten goal spec when intrinsic
                                   load is dominant.
  vstack.cognitive_reappraisal   — reframe anxiety load (Eysenck-Calvo 1992).
  vstack.devils_advocate         — separate proposer + critic when
                                   over_pressure produces corner-cutting.
  vstack.lewin                   — re-architect the scaffold when the
                                   structural pressure is the issue.
  vstack.aar                     — close the failure into a learning loop.
  vstack.johari                  — surface unknown-unknowns when
                                   under_pressure manifests as wandering.
  vstack.bias_stack              — surface cognitive biases activated
                                   under pressure.
  vstack.mcgregor                — orchestrator mode lift for
                                   coordination-heavy pressure.
  vstack.schein_culture          — when the pressure is cultural
                                   (norms, not deadlines).
  vstack.plus_delta              — short feedback ritual after each
                                   round to recalibrate pressure.

Observed zone: {observed_zone}
Failure mode: {failure_mode}
Profile pattern: {profile_pattern}
Cognitive load analysis: {cognitive_load}
Context saturation: {context_saturation}
Zone evidence: {zone_evidence}

INSTRUCTIONS:
- Generate 4-8 interventions, ranked highest impact first.
- At least one intervention MUST set composition_target_pattern
  when delegation is warranted.
- Direction MUST be consistent with observed_zone (no
  increase_pressure on over_pressure observations).
- Cite the cognitive_load and context_saturation findings in
  rationale.

DO NOT:
- Do not invent composition_target_pattern values outside the
  allowed set.
- Do not return fewer than 4 or more than 8 interventions.

OUTPUT SCHEMA: literal JSON array of intervention objects with the
same shape as STANDARD_WORKLOAD_PROMPT's interventions array, plus
an optional composition_target_pattern field.

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


WORKLOAD_PROMPT = STANDARD_WORKLOAD_PROMPT  # legacy alias


__all__ = [
    "FORENSIC_CONTEXT_SATURATION_PROMPT",
    "FORENSIC_COGNITIVE_LOAD_PROMPT",
    "FORENSIC_INTERVENTIONS_PROMPT",
    "QUICK_DIAGNOSTIC_PROMPT",
    "STANDARD_WORKLOAD_PROMPT",
    "WORKLOAD_PROMPT",
    "YERKES_DODSON_SYSTEM_PROMPT",
    "assemble_prompt",
]
