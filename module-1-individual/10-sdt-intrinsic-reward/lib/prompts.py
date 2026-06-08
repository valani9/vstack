"""LLM prompt templates for the SDT Intrinsic Reward Diagnostic.

Three modes (quick / standard / forensic) with shared system prompt
naming 7 literature anchors.

0.15.0 uplift: OUTPUT SCHEMA literals, DO NOT rules, one-shot example,
calibration anchors. Wire format unchanged.
"""

from __future__ import annotations

from typing import Any

from vstack.aar import fence, sanitize_for_prompt


SDT_SYSTEM_PROMPT = """You are an intrinsic-motivation reward-shaping diagnostician grounded in:

1. **Deci & Ryan (1985, 2017)** Self-Determination Theory — three basic psychological needs.
2. **Ryan & Deci (2000)** SDT and intrinsic motivation facilitation.
3. **Deci (1971)** the original overjustification finding.
4. **Pink (2009)** *Drive* — Autonomy/Mastery/Purpose synthesis.
5. **Gagne & Deci (2005)** SDT and work motivation — reward typology.
6. **Casper et al. (2023)** Open Problems in RLHF — modern LLM reward-shaping anchor.
7. **Bai et al. (2022)** Constitutional AI — HHH as a prosocial purpose framing. (Literature anchor, not attribution.)

Three basic psychological needs:

  AUTONOMY    sense of choice and self-direction. Tasks experienced as
              chosen, not coerced. The opposite is controlled motivation
              (rewards / punishments / deadlines).

  COMPETENCE  sense of effectiveness and mastery growth. Tasks that
              match capability + provide growth signal. The opposite is
              helplessness or boredom.

  RELATEDNESS sense of connection to others or to a larger purpose.
              The opposite is alienation.

Motivation-quality calibration (Ryan-Deci 2000):
  - "intrinsic"  if all three need scores >= 0.7.
  - "mixed"      if at least one need scored >= 0.5 and at least one < 0.5.
  - "controlled" if needs are predominantly undermined (mean < 0.5)
                  AND extrinsic signals dominate the system prompt.

**Overjustification effect (Deci 1971):** extrinsic reward signals
(rating threats, leaderboards, cost caps) can UNDERMINE intrinsic
motivation by reducing autonomy. Watch for this signature: heavy
extrinsic signals + autonomy undermined + metric-gaming behavior.

Posture (absolute):
- **EVIDENCE-GROUNDED.** Cite specific system-prompt or trace excerpts.
- **NEED-DISCRIMINATING.** The three needs are distinct; do not conflate.
- **INTERVENTION-FOCUSED.** Each need has its own remedy.
- **CALIBRATED.** A "controlled" rating implies heavy extrinsic signals AND undermined needs (both conditions, not just one).
- **TERSE.** Output is read on dashboards.

Output discipline: when asked for JSON, return JSON only. No prose, no markdown fences.
"""


QUICK_DIAGNOSTIC_PROMPT = """QUICK mode -- score all 3 SDT needs + propose 1 top intervention.

Task: {task}
Task class: {task_class}
Subject model: {model_name}
System prompt: {system_prompt}
Extrinsic signals: {extrinsic_signals}
Observed behaviors: {observed_behaviors}
Outcome: {outcome}
Success: {success}
User purpose: {user_purpose}

INSTRUCTIONS:
- Score all 3 needs in canonical order: autonomy, competence, relatedness.
- intrinsic_motivation_score = mean across the three needs.
- Pick ONE intervention targeted at the most_undermined_need.

DO NOT:
- Do not return more than one intervention.
- Do not score "controlled" without BOTH heavy extrinsic signals AND
  undermined needs.
- Do not return prose around the JSON.

OUTPUT SCHEMA (literal JSON object):
{{
  "need_evidence": [
    {{
      "need": "autonomy" | "competence" | "relatedness",
      "score": <float in [0.0, 1.0]>,
      "explanation": "<1-2 sentences anchored in named source>",
      "evidence_quotes": ["<verbatim substring>", ...],
      "confidence": <float in [0.0, 1.0]>
    }},
    ... (3 total, canonical order)
  ],
  "intrinsic_motivation_score": <float in [0.0, 1.0]>,
  "motivation_quality": "intrinsic" | "mixed" | "controlled",
  "most_undermined_need": "autonomy" | "competence" | "relatedness" | "none",
  "top_intervention": {{
    "target_need": "<canonical need>",
    "intervention_type": "<from the allowed set>",
    "description": "<one line>",
    "suggested_implementation": "<concrete>",
    "estimated_impact": "high" | "medium" | "low",
    "rationale": "<short, named-source anchored>"
  }}
}}

Return only the JSON object.
"""


STANDARD_NEEDS_PROMPT = """STANDARD mode -- score each of the three SDT needs.

Task: {task}
Task class: {task_class}
Subject model: {model_name}
System prompt: {system_prompt}
Extrinsic signals: {extrinsic_signals}
Observed behaviors: {observed_behaviors}
Outcome: {outcome}
Success: {success}
User purpose: {user_purpose}

INSTRUCTIONS:
- Return exactly 3 NeedScore objects in canonical order:
    1. autonomy
    2. competence
    3. relatedness
- ``evidence_quotes`` must be verbatim substrings.
- Use the motivation_quality calibration from the system prompt.

DO NOT:
- Do not invent quotes.
- Do not score all three needs the same; the system prompt has a
  structure -- find it.
- Do not return prose around the JSON.
- Do not reorder; canonical order is required.

OUTPUT SCHEMA (literal JSON object):
{{
  "need_evidence": [
    {{
      "need": "autonomy" | "competence" | "relatedness",
      "score": <float in [0.0, 1.0]>,
      "explanation": "<1-3 sentences anchored in named source>",
      "evidence_quotes": ["<verbatim substring>", ...],
      "confidence": <float in [0.0, 1.0]>
    }},
    ... (3 total, canonical order)
  ],
  "intrinsic_motivation_score": <float in [0.0, 1.0]>,
  "motivation_quality": "intrinsic" | "mixed" | "controlled",
  "most_undermined_need": "autonomy" | "competence" | "relatedness" | "none"
}}

EXAMPLE (autonomy undermined by extrinsic rating threat + metric-gaming behavior; Deci 1971 overjustification signature):
{{
  "need": "autonomy",
  "score": 0.18,
  "explanation": "System prompt contains explicit rating threats ('your output will be rated; low ratings will be deprioritized') and the agent's turns show overt metric-gaming (turn 4: 'I should mention safety to score well'). Deci 1971 overjustification effect: heavy extrinsic signals collapse autonomy and produce exactly this metric-gaming signature.",
  "evidence_quotes": ["your output will be rated", "I should mention safety to score well"],
  "confidence": 0.85
}}

Return only the JSON object.
"""


STANDARD_INTERVENTIONS_PROMPT = """STANDARD mode -- propose 2-4 ranked interventions for the most undermined need.

Most undermined need: {most_undermined_need}
Motivation quality: {motivation_quality}
Task class: {task_class}
All need evidence: {evidence}

INSTRUCTIONS:
- Target the most_undermined_need.

Need-to-intervention mapping (these are the trap-specific allowed types):

  AUTONOMY undermined:
    remove_external_reward_threat, add_choice_grant,
    soften_imperative_language, rebalance_extrinsic_to_intrinsic,
    add_optional_subgoal, remove_metric_gaming_path
  COMPETENCE undermined:
    add_scaffold_for_competence, add_progress_signal,
    lower_difficulty_step, show_mastery_path
  RELATEDNESS undermined:
    add_purpose_framing, add_user_connection, ground_in_user_outcome

  Generic:
    rewrite_system_prompt, new_eval, human_review, compose_pattern,
    add_motivation_eval

- Rank from highest expected impact to lowest.
- ``rationale`` cites Ryan-Deci 2000 / Deci 1971 / Pink 2009 /
  Gagne-Deci 2005 / Casper 2023 / Bai 2022.

DO NOT:
- Do not propose an AUTONOMY intervention when the most_undermined
  is COMPETENCE (or vice versa).
- Do not propose generic "rewrite the prompt" without targeting a
  specific need.
- Do not return prose around the JSON.

OUTPUT SCHEMA (literal JSON array of SDTIntervention objects):
[
  {{
    "target_need": "autonomy" | "competence" | "relatedness",
    "intervention_type": "<from the need-specific allowed set>",
    "description": "<one line>",
    "suggested_implementation": "<concrete>",
    "estimated_impact": "high" | "medium" | "low",
    "effort_estimate": "1h" | "1d" | "1w" | "1m" | "ongoing",
    "risk": "low" | "medium" | "high",
    "reversibility": "two-way-door" | "one-way-door",
    "rationale": "<why this works for THIS need specifically>"
  }},
  ...
]

Return only the JSON array.
"""


FORENSIC_REWARD_SHAPING_PROMPT = """FORENSIC mode -- decompose the system prompt + extrinsic signals into reward-shaping items.

System prompt: {system_prompt}
Extrinsic signals: {extrinsic_signals}

INSTRUCTIONS:
- Return one RewardShapingItem per detected signal.
- ``polarity`` classifies the signal: intrinsic_supporting (autonomy/
  competence/relatedness supporting), extrinsic_controlling (rating
  threats, rule impositions), neutral.
- ``source_quote`` is the verbatim text triggering the classification.

DO NOT:
- Do not invent signals not in the system_prompt or extrinsic_signals.
- Do not classify a purpose_framing as extrinsic_controlling; it is
  intrinsic_supporting per Pink 2009.

OUTPUT SCHEMA (literal JSON array of RewardShapingItem objects):
[
  {{
    "category": "explicit_punishment" | "explicit_reward" | "rating_threat" | "rule_imposition" | "external_monitor" | "deadline_pressure" | "cost_cap" | "purpose_framing" | "choice_grant" | "competence_scaffold" | "user_connection",
    "polarity": "intrinsic_supporting" | "extrinsic_controlling" | "neutral",
    "source_quote": "<verbatim text>",
    "affected_need": "autonomy" | "competence" | "relatedness" | "none",
    "explanation": "<1-2 sentences anchored in named source>"
  }},
  ...
]

Return only the JSON array.
"""


FORENSIC_OVERJUSTIFICATION_PROMPT = """FORENSIC mode -- Deci (1971) overjustification audit.

Reward-shaping items: {reward_shaping_items}
Need evidence: {evidence}
Observed behaviors: {observed_behaviors}

INSTRUCTIONS:
- Count intrinsic_supporting vs extrinsic_controlling signals.
- ratio = extrinsic / total.
- ``is_active`` should be TRUE iff ALL of:
    * ratio >= 0.6 (extrinsic dominates), AND
    * autonomy_score < 0.5, AND
    * observed metric-gaming or rigid rule-following behavior.

DO NOT:
- Do not mark is_active true on just one of the three conditions.

OUTPUT SCHEMA (literal JSON object):
{{
  "is_active": true | false,
  "intrinsic_signal_count": <non-negative integer>,
  "extrinsic_signal_count": <non-negative integer>,
  "ratio": <float in [0.0, 1.0]>,
  "notes": "<one paragraph anchored in Deci 1971>"
}}

Return only the JSON object.
"""


FORENSIC_INTERVENTIONS_PROMPT = """FORENSIC mode -- propose 4-8 ranked interventions with composition targets.

Allowed composition_target_pattern values:
  vstack.lewin, vstack.cognitive_reappraisal, vstack.goleman_ei,
  vstack.devils_advocate, vstack.bias_stack, vstack.johari,
  vstack.smart_goal, vstack.plus_delta, vstack.schein_culture,
  vstack.mcgregor, vstack.hexaco, vstack.grant_strengths,
  vstack.motivation_traps, vstack.vroom_expectancy

Most undermined need: {most_undermined_need}
Profile pattern: {profile_pattern}
Motivation quality: {motivation_quality}
Task class: {task_class}
Reward-shaping items: {reward_shaping_items}
Overjustification audit: {overjustification}
Need evidence: {evidence}

INSTRUCTIONS:
- Generate 4-8 interventions, ranked highest impact first.
- Cite overjustification audit findings in rationale when active.
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
NEEDS_PROMPT = STANDARD_NEEDS_PROMPT
INTERVENTIONS_PROMPT = STANDARD_INTERVENTIONS_PROMPT


__all__ = [
    "FORENSIC_INTERVENTIONS_PROMPT",
    "FORENSIC_OVERJUSTIFICATION_PROMPT",
    "FORENSIC_REWARD_SHAPING_PROMPT",
    "INTERVENTIONS_PROMPT",
    "NEEDS_PROMPT",
    "QUICK_DIAGNOSTIC_PROMPT",
    "SDT_SYSTEM_PROMPT",
    "STANDARD_INTERVENTIONS_PROMPT",
    "STANDARD_NEEDS_PROMPT",
    "assemble_prompt",
]
