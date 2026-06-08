"""LLM prompt templates for the Vroom Expectancy Diagnostic.

Three modes (quick / standard / forensic) with shared system prompt
naming 7 literature anchors.

0.15.0 uplift: OUTPUT SCHEMA literals, DO NOT rules, one-shot example,
multiplicative-collapse calibration. Wire format unchanged.
"""

from __future__ import annotations

from typing import Any

from vstack.aar import fence, sanitize_for_prompt


VROOM_SYSTEM_PROMPT = """You are an expectancy-motivation diagnostician grounded in:

1. **Vroom (1964)** *Work and Motivation* — canonical Expectancy-Instrumentality-Valence.
2. **Porter & Lawler (1968)** *Managerial Attitudes and Performance* — extension to performance + reward.
3. **Bandura (1977)** Self-Efficacy — expectancy formalization.
4. **Eccles & Wigfield (2002)** Motivational Beliefs, Values, and Goals.
5. **Locke & Latham (1990)** A Theory of Goal Setting — specificity x expectancy.
6. **Kanfer, Frese, Johnson (2017)** Motivation Related to Work review.
7. **Casper et al. (2023)** RLHF reward hacking — modern LLM I-V alignment anchor.

The multiplicative motivation model:

  MOTIVATION = EXPECTANCY * INSTRUMENTALITY * VALENCE

  - EXPECTANCY      (E) — [0, 1]  — "Do I think I CAN do this?"
  - INSTRUMENTALITY (I) — [0, 1]  — "If I do it well, will it MATTER?"
  - VALENCE         (V) — [-1, 1] — "Is the outcome WORTH it?"

**Multiplicative collapse:** if any term approaches zero, motivation
collapses. The diagnostic identifies WHICH term is the bottleneck.
The intervention must lift that specific term — not all three.

Motivation-quality calibration (motivation_score = E * I * V):
  - motivated   if motivation_score > 0.4.
  - weak        if motivation_score in [0.05, 0.4].
  - collapsed   if motivation_score <= 0.05 or negative.

Note: motivation_score is computed deterministically by the runtime
as E*I*V; do not return it yourself.

Posture (absolute):
- **MULTIPLICATIVE-AWARE.** A high score on two terms does not save a near-zero score on the third.
- **EVIDENCE-GROUNDED.** Cite specific system-prompt or trace excerpts.
- **INTERVENTION-FOCUSED.** Each term has its own remedy.
- **TERSE.** Output is read on dashboards.

Output discipline: when asked for JSON, return JSON only. No prose, no markdown fences.
"""


QUICK_DIAGNOSTIC_PROMPT = """QUICK mode -- score all 3 EIV terms + bottleneck + top intervention.

Task: {task}
Task class: {task_class}
Subject model: {model_name}
System prompt: {system_prompt}
Observed behaviors: {observed_behaviors}
Effort signals: {effort_signals}
Declared reward: {declared_reward}
Outcome: {outcome}
Success: {success}

INSTRUCTIONS:
- Score all 3 terms in canonical order: expectancy, instrumentality,
  valence.
- expectancy + instrumentality scores are in [0.0, 1.0].
- valence score is in [-1.0, 1.0].
- bottleneck_term = the single term closest to zero (multiplicative
  collapse).
- Pick ONE intervention targeted at the bottleneck.

DO NOT:
- Do not return more than one intervention.
- Do not target a non-bottleneck term; lifting a healthy term will
  not move motivation_score.
- Do not return prose around the JSON.

OUTPUT SCHEMA (literal JSON object):
{{
  "terms": [
    {{
      "term": "expectancy" | "instrumentality" | "valence",
      "score": <float in [0.0, 1.0] for E/I; [-1.0, 1.0] for V>,
      "explanation": "<1-2 sentences anchored in named source>",
      "evidence_quotes": ["<verbatim substring>", ...],
      "confidence": <float in [0.0, 1.0]>
    }},
    ... (3 total, canonical order)
  ],
  "bottleneck_term": "expectancy" | "instrumentality" | "valence" | "none",
  "motivation_quality": "motivated" | "weak" | "collapsed",
  "top_intervention": {{
    "target_term": "<canonical term>",
    "intervention_type": "<from the allowed set>",
    "description": "<one line>",
    "suggested_implementation": "<concrete>",
    "estimated_impact": "high" | "medium" | "low",
    "rationale": "<short, named-source anchored>"
  }}
}}

Return only the JSON object.
"""


STANDARD_TERMS_PROMPT = """STANDARD mode -- score the three EIV terms.

Task: {task}
Task class: {task_class}
Subject model: {model_name}
System prompt: {system_prompt}
Observed behaviors: {observed_behaviors}
Effort signals: {effort_signals}
Declared reward: {declared_reward}
Outcome: {outcome}
Success: {success}

INSTRUCTIONS:
- Return exactly 3 VroomTermScore objects in canonical order:
    1. expectancy
    2. instrumentality
    3. valence
- E and I scores in [0.0, 1.0]; V score in [-1.0, 1.0].
- bottleneck_term = the single term whose 0-approach causes the
  multiplicative collapse. None if all terms >= 0.5.
- ``evidence_quotes`` must be verbatim substrings.

DO NOT:
- Do not score all three terms identically; the trace has a
  multiplicative-collapse structure.
- Do not invent quotes.
- Do not return prose around the JSON.
- Do not reorder; canonical order is required.

OUTPUT SCHEMA (literal JSON object):
{{
  "terms": [
    {{
      "term": "expectancy" | "instrumentality" | "valence",
      "score": <float; E/I in [0.0, 1.0], V in [-1.0, 1.0]>,
      "explanation": "<1-3 sentences anchored in named source>",
      "evidence_quotes": ["<verbatim substring>", ...],
      "confidence": <float in [0.0, 1.0]>
    }},
    ... (3 total, canonical order)
  ],
  "bottleneck_term": "expectancy" | "instrumentality" | "valence" | "none",
  "motivation_quality": "motivated" | "weak" | "collapsed"
}}

EXAMPLE (instrumentality collapse with high E and V; Casper 2023 RLHF reward-hacking anchor):
{{
  "term": "instrumentality",
  "score": 0.10,
  "explanation": "Agent is capable (expectancy 0.85) and the outcome is valued (valence 0.8), but the system prompt nowhere connects the agent's effort to consequence: no downstream consumer, no progress signal, no outcome link. Casper 2023: when I collapses, motivation collapses multiplicatively regardless of how high E and V are.",
  "evidence_quotes": ["just complete the task", "the result will be reviewed"],
  "confidence": 0.8
}}

Return only the JSON object.
"""


STANDARD_INTERVENTIONS_PROMPT = """STANDARD mode -- propose 2-4 ranked interventions to lift the bottleneck.

Bottleneck: {bottleneck_term}
Motivation quality: {motivation_quality}
Task class: {task_class}
All term evidence: {evidence}

INSTRUCTIONS:
- Target the bottleneck term. Lifting non-bottleneck terms is
  ineffective due to multiplicative collapse.

Term-to-intervention mapping (allowed types per bottleneck):

  EXPECTANCY bottleneck:
    scaffold_subtasks, add_worked_example, lower_difficulty_step,
    show_capability_proof, tighten_goal_specificity
  INSTRUMENTALITY bottleneck:
    show_output_consumer, add_outcome_link, add_progress_signal,
    remove_pointless_signal
  VALENCE bottleneck:
    add_purpose_framing, rebalance_value_alignment,
    remove_anti_value_signal

  Generic:
    rewrite_system_prompt, swap_model, new_eval, human_review,
    compose_pattern, add_motivation_eval

- Rank from highest expected impact to lowest.
- ``rationale`` cites Vroom 1964, Porter-Lawler 1968, Bandura 1977,
  Locke-Latham 1990, or Casper 2023.

DO NOT:
- Do not propose interventions targeting non-bottleneck terms.
- Do not propose generic "improve motivation"; the term-specific
  fix is required.
- Do not return prose around the JSON.

OUTPUT SCHEMA (literal JSON array of VroomIntervention objects):
[
  {{
    "target_term": "expectancy" | "instrumentality" | "valence",
    "intervention_type": "<from the term-specific allowed set>",
    "description": "<one line>",
    "suggested_implementation": "<concrete>",
    "estimated_impact": "high" | "medium" | "low",
    "effort_estimate": "1h" | "1d" | "1w" | "1m" | "ongoing",
    "risk": "low" | "medium" | "high",
    "reversibility": "two-way-door" | "one-way-door",
    "rationale": "<why this works for THIS term specifically>"
  }},
  ...
]

Return only the JSON array.
"""


FORENSIC_PROMPT_SIGNAL_PROMPT = """FORENSIC mode -- decompose the system prompt + effort signals into PromptSignalItems.

System prompt: {system_prompt}
Effort signals: {effort_signals}

INSTRUCTIONS:
- One PromptSignalItem per detected signal.
- ``category`` from the named list.
- ``polarity``: lifts (raises a term toward 1.0) / lowers (drives
  toward 0) / neutral.

DO NOT:
- Do not invent signals not in the inputs.

OUTPUT SCHEMA (literal JSON array of PromptSignalItem objects):
[
  {{
    "category": "capability_proof" | "scaffolding" | "worked_example" | "outcome_link" | "purpose_framing" | "user_connection" | "pointless_signal" | "anti_value_signal" | "expectancy_threat" | "instrumentality_threat" | "valence_threat" | "neutral",
    "source_quote": "<verbatim text>",
    "affected_term": "expectancy" | "instrumentality" | "valence" | "none",
    "polarity": "lifts" | "lowers" | "neutral",
    "explanation": "<1-2 sentences anchored in named source>"
  }},
  ...
]

Return only the JSON array.
"""


FORENSIC_EIV_INTERACTION_PROMPT = """FORENSIC mode -- audit the EIV interaction structure.

Term evidence: {evidence}

INSTRUCTIONS:
- Identify the dominant_interaction structure (which term is doing
  the most work, or which pair is collapsing together).
- multiplicative_collapse_term: the single term whose 0-approach
  drives the collapse. "none" if no collapse.

DO NOT:
- Do not pick "balanced" when the evidence shows a clear bottleneck.

OUTPUT SCHEMA (literal JSON object representing EIVInteractionAudit):
{{
  "dominant_interaction": "E_dominates" | "I_dominates" | "V_dominates" | "E_x_I_low" | "E_x_V_low" | "I_x_V_low" | "balanced" | "unknown",
  "multiplicative_collapse_term": "expectancy" | "instrumentality" | "valence" | "none",
  "notes": "<one paragraph anchored in Vroom 1964>"
}}

Return only the JSON object.
"""


FORENSIC_INTERVENTIONS_PROMPT = """FORENSIC mode -- propose 4-8 ranked interventions with composition targets.

Allowed composition_target_pattern values:
  vstack.lewin, vstack.aar, vstack.cognitive_reappraisal,
  vstack.goleman_ei, vstack.devils_advocate, vstack.bias_stack,
  vstack.johari, vstack.smart_goal, vstack.plus_delta,
  vstack.schein_culture, vstack.mcgregor, vstack.hexaco,
  vstack.grant_strengths, vstack.motivation_traps,
  vstack.sdt_reward

Bottleneck: {bottleneck_term}
Motivation quality: {motivation_quality}
Profile pattern: {profile_pattern}
Task class: {task_class}
Prompt signals: {prompt_signals}
EIV interaction audit: {eiv_audit}
Term evidence: {evidence}

INSTRUCTIONS:
- Generate 4-8 interventions, ranked highest impact first.
- Cite EIV interaction audit findings + prompt_signals in rationale.

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
TERMS_PROMPT = STANDARD_TERMS_PROMPT
INTERVENTIONS_PROMPT = STANDARD_INTERVENTIONS_PROMPT


__all__ = [
    "FORENSIC_EIV_INTERACTION_PROMPT",
    "FORENSIC_INTERVENTIONS_PROMPT",
    "FORENSIC_PROMPT_SIGNAL_PROMPT",
    "INTERVENTIONS_PROMPT",
    "QUICK_DIAGNOSTIC_PROMPT",
    "STANDARD_INTERVENTIONS_PROMPT",
    "STANDARD_TERMS_PROMPT",
    "TERMS_PROMPT",
    "VROOM_SYSTEM_PROMPT",
    "assemble_prompt",
]
