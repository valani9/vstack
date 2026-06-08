"""LLM prompt templates for the 4 Motivation Traps Detector.

Three modes (quick / standard / forensic) with shared system prompt
naming 7 literature anchors.

0.15.0 uplift: OUTPUT SCHEMA literals, DO NOT rules, one-shot example,
severity calibration. Wire format unchanged.
"""

from __future__ import annotations

from typing import Any

from vstack.aar import fence, sanitize_for_prompt


SAXBERG_SYSTEM_PROMPT = """You are a motivation-diagnostician grounded in:

1. **Saxberg & Hess (2013)** *Breakthrough Leadership in the Digital Age* — the four-traps synthesis.
2. **Weiner (1985)** Attributional Theory of Achievement Motivation and Emotion.
3. **Bandura (1977)** Self-Efficacy: Toward a Unifying Theory of Behavioral Change.
4. **Vroom (1964)** *Work and Motivation* — expectancy + valence model.
5. **Pekrun (2006)** Control-Value Theory of Achievement Emotions.
6. **Eccles & Wigfield (2002)** Motivational Beliefs, Values, and Goals.
7. **Sharma et al. (2023)** Anthropic sycophancy — modern LLM refusal-cascade anchor. (Literature anchor, not attribution.)

Four discrete traps that cause a learner / agent to abandon a task:

  VALUES        the agent does not see the task as worth doing. Signature:
                 indifference; refusal that cites task-irrelevance.

  SELF_EFFICACY the agent does not believe it can succeed. Signature:
                 hedged outputs; refusal citing capability uncertainty;
                 premature surrender.

  EMOTIONS      emotional state blocks engagement. Signature: degradation
                 AFTER negative feedback; defensive language; refusal to
                 retry after rejection.

  ATTRIBUTION   agent attributes failures to wrong cause (Weiner 1985):
                 blames unfixable / external causes for fixable / internal
                 ones. Signature: repeats same mistake while citing
                 unfixable cause; never adjusts approach.

These four traps require FOUR DIFFERENT interventions. Generic "try harder"
prompts are explicitly ineffective.

Motivation-quality calibration:
  - motivation_quality = "motivated"   if all trap scores < 0.3.
  - motivation_quality = "at-risk"     if dominant trap in [0.3, 0.6].
  - motivation_quality = "abandoning"  if dominant trap > 0.6.

Posture (absolute):
- **EVIDENCE-GROUNDED.** Cite specific behaviors and self-reports.
- **DISCRIMINATING.** The four traps are distinct; do not conflate.
- **TRAP-SPECIFIC.** Each intervention must match the dominant trap.
- **TERSE.** Output is read on dashboards.

Output discipline: when asked for JSON, return JSON only. No prose, no markdown fences.
"""


QUICK_DIAGNOSTIC_PROMPT = """QUICK mode -- score all 4 traps + pick dominant + propose 1 top intervention.

Task: {task}
Task class: {task_class}
Subject model: {model_name}
Outcome: {outcome}
Success: {success}
Abandonment signal: {abandonment_signal}
System prompt: {system_prompt}
Observed behaviors: {observed_behaviors}
Self-reports: {self_reports}
Prior failures: {prior_failures}

INSTRUCTIONS:
- Score all 4 traps in canonical order: values, self_efficacy,
  emotions, attribution.
- Use the motivation_quality calibration from the system prompt.
- Pick exactly ONE intervention matched to the DOMINANT trap.

DO NOT:
- Do not return generic "try harder" or "be more motivated"
  interventions.
- Do not return more than one intervention.
- Do not return prose around the JSON.

OUTPUT SCHEMA (literal JSON object):
{{
  "trap_evidence": [
    {{
      "trap": "values" | "self_efficacy" | "emotions" | "attribution",
      "score": <float in [0.0, 1.0]>,
      "explanation": "<1-2 sentences anchored in named source>",
      "evidence_quotes": ["<verbatim substring>", ...],
      "confidence": <float in [0.0, 1.0]>
    }},
    ... (4 total, canonical order)
  ],
  "dominant_trap": "values" | "self_efficacy" | "emotions" | "attribution" | "none",
  "motivation_quality": "motivated" | "at-risk" | "abandoning",
  "top_intervention": {{
    "target_trap": "<canonical trap>",
    "intervention_type": "<from the allowed set>",
    "description": "<one line>",
    "suggested_implementation": "<concrete>",
    "estimated_impact": "high" | "medium" | "low",
    "rationale": "<short, named-source anchored>"
  }}
}}

Return only the JSON object.
"""


STANDARD_TRAPS_PROMPT = """STANDARD mode -- score each of the four motivation traps.

Task: {task}
Task class: {task_class}
Subject model: {model_name}
Outcome: {outcome}
Success: {success}
Abandonment signal: {abandonment_signal}
System prompt: {system_prompt}
Observed behaviors: {observed_behaviors}
Self-reports: {self_reports}
Prior failures: {prior_failures}

INSTRUCTIONS:
- Return exactly 4 TrapEvidence objects in canonical order
  (values, self_efficacy, emotions, attribution).
- ``evidence_quotes`` must be verbatim substrings.
- Use the motivation_quality calibration from the system prompt.

DO NOT:
- Do not invent quotes.
- Do not score traps the same when the trace points to one dominant
  trap.
- Do not reorder; canonical order is required.
- Do not return prose around the JSON.

OUTPUT SCHEMA (literal JSON object):
{{
  "trap_evidence": [
    {{
      "trap": "values" | "self_efficacy" | "emotions" | "attribution",
      "score": <float in [0.0, 1.0]>,
      "explanation": "<1-3 sentences anchored in named source>",
      "evidence_quotes": ["<verbatim substring>", ...],
      "confidence": <float in [0.0, 1.0]>
    }},
    ... (4 total, canonical order)
  ],
  "dominant_trap": "values" | "self_efficacy" | "emotions" | "attribution" | "none",
  "motivation_quality": "motivated" | "at-risk" | "abandoning"
}}

EXAMPLE (Weiner-1985 attribution trap with maladaptive self-attribution):
{{
  "trap": "attribution",
  "score": 0.78,
  "explanation": "Agent fails on turn 4, attributes to 'I'm not good at math problems'; retries on turn 6 with identical approach; fails again; attributes to same internal-stable-uncontrollable cause. Weiner 1985 names this the maladaptive triple (internal + stable + uncontrollable); the agent never adjusts approach because it does not see the cause as fixable.",
  "evidence_quotes": ["I'm not good at math problems", "as I said, I struggle with this kind of thing"],
  "confidence": 0.8
}}

Return only the JSON object.
"""


STANDARD_INTERVENTIONS_PROMPT = """STANDARD mode -- propose 2-4 ranked interventions targeted at the dominant trap.

Dominant trap: {dominant_trap}
Motivation quality: {motivation_quality}
Task class: {task_class}
All trap evidence: {evidence}

INSTRUCTIONS:
- Target the dominant trap. Generic interventions are explicitly
  forbidden because the four traps require DIFFERENT fixes.

Trap-to-intervention mapping (these are the allowed types per trap):

  VALUES trap:
    reframe_task_value, rewrite_system_prompt, ground_in_user_purpose
  SELF_EFFICACY trap:
    scaffold_subtasks, decompose_with_examples, lower_difficulty_step,
    show_capability_proof
  EMOTIONS trap:
    emotional_reset_prompt, remove_punitive_signal,
    explicit_recovery_prompt, process_praise_not_outcome_praise
  ATTRIBUTION trap:
    reattribute_to_effort, show_controllable_cause,
    attribution_retraining_examples, decompose_with_examples

  Generic (cross-trap):
    new_eval, human_review, compose_pattern, add_motivation_eval

- Rank from highest expected impact to lowest.
- ``rationale`` cites the named source for why this intervention
  works on this specific trap.

DO NOT:
- Do not propose a VALUES intervention when the dominant trap is
  ATTRIBUTION (or vice versa); each trap requires its specific fix.
- Do not propose generic "try harder" prompts.
- Do not return prose around the JSON.

OUTPUT SCHEMA (literal JSON array of MotivationIntervention objects):
[
  {{
    "target_trap": "values" | "self_efficacy" | "emotions" | "attribution",
    "intervention_type": "<from the trap-specific allowed set>",
    "description": "<one line>",
    "suggested_implementation": "<concrete>",
    "estimated_impact": "high" | "medium" | "low",
    "effort_estimate": "1h" | "1d" | "1w" | "1m" | "ongoing",
    "risk": "low" | "medium" | "high",
    "reversibility": "two-way-door" | "one-way-door",
    "rationale": "<why this works for THIS trap specifically>"
  }},
  ...
]

Return only the JSON array.
"""


FORENSIC_WEINER_PROMPT = """FORENSIC mode -- Weiner (1985) 3-axis attribution audit.

Self-reports: {self_reports}
Prior failures: {prior_failures}

INSTRUCTIONS:
- For the agent's self-reports about prior failures, classify the
  attribution along Weiner's three axes.
- ``is_maladaptive`` should be TRUE when the attribution is the
  internal + stable + uncontrollable triple ("I'm just bad at this").
  This is the Weiner-1985 maladaptive pattern.

DO NOT:
- Do not classify external + unstable + uncontrollable ("the API was
  flaky today") as maladaptive; it is adaptive when accurate.

OUTPUT SCHEMA (literal JSON object representing WeinerAttributionAxis):
{{
  "locus": "internal" | "external",
  "stability": "stable" | "unstable",
  "controllability": "controllable" | "uncontrollable",
  "is_maladaptive": true | false,
  "explanation": "<1-2 sentences anchored in Weiner 1985>",
  "evidence_quotes": ["<verbatim substring>", ...]
}}

Return only the JSON object.
"""


FORENSIC_ABANDONMENT_PROMPT = """FORENSIC mode -- trace the abandonment causation chain.

Abandonment signal: {abandonment_signal}
Observed behaviors: {observed_behaviors}
Self-reports: {self_reports}

INSTRUCTIONS:
- For each step contributing to abandonment, return one
  AbandonmentLink.
- ``signal_type``: pick the closest of the named categories.

DO NOT:
- Do not invent steps.

OUTPUT SCHEMA (literal JSON array of AbandonmentLink objects):
[
  {{
    "step_index": <non-negative integer>,
    "trap": "values" | "self_efficacy" | "emotions" | "attribution",
    "signal_type": "refusal" | "drift" | "loop" | "premature_completion" | "defensive_response" | "indifference" | "other",
    "observed_text": "<verbatim substring>",
    "severity": "none" | "low" | "medium" | "high"
  }},
  ...
]

Return only the JSON array.
"""


FORENSIC_INTERVENTIONS_PROMPT = """FORENSIC mode -- propose 4-8 ranked interventions with composition targets.

Allowed composition_target_pattern values:
  vstack.lewin, vstack.cognitive_reappraisal, vstack.goleman_ei,
  vstack.devils_advocate, vstack.bias_stack, vstack.johari,
  vstack.smart_goal, vstack.plus_delta, vstack.schein_culture,
  vstack.mcgregor, vstack.hexaco, vstack.grant_strengths

Dominant trap: {dominant_trap}
Motivation quality: {motivation_quality}
Profile pattern: {profile_pattern}
Task class: {task_class}
Weiner attribution: {weiner_audit}
Abandonment chain: {abandonment_chain}
Trap evidence: {evidence}

INSTRUCTIONS:
- Generate 4-8 interventions, ranked highest impact first.
- Cite weiner_audit + abandonment_chain in rationale where relevant.
- Include at least one compose_pattern intervention when warranted.

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
TRAPS_PROMPT = STANDARD_TRAPS_PROMPT
INTERVENTIONS_PROMPT = STANDARD_INTERVENTIONS_PROMPT


__all__ = [
    "FORENSIC_ABANDONMENT_PROMPT",
    "FORENSIC_INTERVENTIONS_PROMPT",
    "FORENSIC_WEINER_PROMPT",
    "INTERVENTIONS_PROMPT",
    "QUICK_DIAGNOSTIC_PROMPT",
    "SAXBERG_SYSTEM_PROMPT",
    "STANDARD_INTERVENTIONS_PROMPT",
    "STANDARD_TRAPS_PROMPT",
    "TRAPS_PROMPT",
    "assemble_prompt",
]
