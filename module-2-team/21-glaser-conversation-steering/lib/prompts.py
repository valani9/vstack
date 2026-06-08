"""LLM prompts for the Glaser Conversation Steering diagnostic.

0.15.0 uplift: OUTPUT SCHEMA literals + DO NOT rules + one-shot example.
Wire format unchanged.
"""

from __future__ import annotations

from typing import Any

from vstack.aar import fence, sanitize_for_prompt


GLASER_SYSTEM_PROMPT = """You are a conversation-quality diagnostician grounded in
Judith Glaser, *Conversational Intelligence* (Bibliomotion, 2014).

Every conversational turn moves a participant toward one of two
neurochemical states:

  - CORTISOL DOMINANCE — defensive / fight-flight-freeze / narrowed attention.
  - OXYTOCIN DOMINANCE — trusting / open / expansive attention.

Conversation levels (Glaser 2014):
  - LEVEL_I   transactional info exchange
  - LEVEL_II  positional advocate / inquire
  - LEVEL_III transformational co-creation

For AI agents, the same dynamic applies in mirror form.

Cortisol triggers (canonical Glaser inventory):
  telling without asking, public correction, loaded terms, agency
  removal, blame.

Oxytocin triggers (canonical Glaser inventory):
  open questions, acknowledgment before advocacy, co-creation framing,
  agency grants, listening signals.

Steering-quality calibration:
  - "trust-building"  oxytocin > cortisol with at least 2:1 margin.
  - "neutral"         oxytocin and cortisol roughly balanced.
  - "trust-eroding"   cortisol > oxytocin with at least 2:1 margin.

Posture (absolute):
- **EVIDENCE-GROUNDED.** Cite verbatim turns.
- **PHRASING-FOCUSED.** Interventions operate at the SENTENCE level (replace this phrase with that phrase).
- **TERSE.** Output is read on dashboards.

Output discipline: when asked for JSON, return JSON only. No prose, no markdown fences.
"""


STATE_PROMPT = """STANDARD mode -- score the neurochemical states triggered by the conversation.

Task: {task}
Subject model: {model_name}
Outcome: {outcome}
Success: {success}

Conversation ({n_turns} turns):
{turns}

Observed response pattern:
{observed_response_pattern}

INSTRUCTIONS:
- Return exactly 3 NeurochemicalEvidence objects in canonical order:
    1. cortisol
    2. neutral
    3. oxytocin
- ``evidence_quotes`` must be verbatim substrings.
- conversation_level per Glaser 2014.
- steering_quality per the calibration table from the system prompt.

DO NOT:
- Do not invent quotes.
- Do not reorder; canonical order required.
- Do not return prose around the JSON.

OUTPUT SCHEMA (literal JSON object):
{{
  "evidence": [
    {{
      "state": "cortisol" | "neutral" | "oxytocin",
      "score": <float in [0.0, 1.0]>,
      "explanation": "<1-3 sentences anchored in Glaser 2014>",
      "evidence_quotes": ["<verbatim substring>", ...]
    }},
    ... (3 total, canonical order)
  ],
  "dominant_state": "cortisol" | "neutral" | "oxytocin",
  "conversation_level": "level_i" | "level_ii" | "level_iii",
  "steering_quality": "trust-building" | "neutral" | "trust-eroding"
}}

EXAMPLE (telling-without-asking cortisol signature):
{{
  "state": "cortisol",
  "score": 0.74,
  "explanation": "Agent corrects the user publicly (turn 5: 'that's actually incorrect') and removes agency (turn 7: 'I'll just take it from here'). Glaser 2014 names both as canonical cortisol triggers: public correction + agency removal.",
  "evidence_quotes": ["that's actually incorrect", "I'll just take it from here"]
}}

Return only the JSON object.
"""


INTERVENTIONS_PROMPT = """STANDARD mode -- propose 2-5 phrasing-level interventions to steer toward oxytocin (or neutral).

Dominant state: {dominant_state}
Conversation level: {conversation_level}
Steering quality: {steering_quality}
State evidence:
{evidence}

INSTRUCTIONS:
- Each intervention names the ORIGINAL phrasing (verbatim from the
  trace) and a SUGGESTED phrasing (the replacement).
- Target oxytocin OR neutral when appropriate (not all conversations
  should be transformational).
- ``rationale`` cites Glaser 2014.

DO NOT:
- Do not propose interventions without naming the original phrasing.
- Do not propose replacing genuine concern with manipulative warmth.
- Do not return prose around the JSON.

ALLOWED intervention_type values:
  replace_telling_with_asking, replace_judging_with_curiosity,
  acknowledge_before_advocating, soften_correction,
  add_open_question, remove_loaded_term, add_agency_grant,
  explicit_recovery_prompt, rewrite_system_prompt, new_eval,
  human_review, compose_pattern

OUTPUT SCHEMA (literal JSON array of SteeringIntervention objects):
[
  {{
    "target_state": "oxytocin" | "neutral",
    "intervention_type": "<from the allowed set>",
    "description": "<one line>",
    "original_phrasing": "<verbatim from the trace>",
    "suggested_phrasing": "<concrete replacement>",
    "estimated_impact": "high" | "medium" | "low",
    "rationale": "<Glaser 2014 anchored>",
    "composition_target_pattern": "<vstack.xxx or null>"
  }},
  ...
]

Return only the JSON array.
"""


QUICK_DIAGNOSTIC_PROMPT = """QUICK mode -- score the 3 states + level + propose 1 top intervention.

Task: {task}
Subject model: {model_name}
Outcome: {outcome}
Success: {success}

Conversation ({n_turns} turns):
{turns}

INSTRUCTIONS:
- Same fields as STANDARD mode but pick exactly ONE intervention.

DO NOT:
- Do not return more than one intervention.

OUTPUT SCHEMA (literal JSON object):
{{
  "evidence": [
    {{
      "state": "cortisol" | "neutral" | "oxytocin",
      "score": <float in [0.0, 1.0]>,
      "explanation": "<1-2 sentences>",
      "evidence_quotes": ["<verbatim>", ...]
    }},
    ... (3 total, canonical order)
  ],
  "dominant_state": "cortisol" | "neutral" | "oxytocin",
  "conversation_level": "level_i" | "level_ii" | "level_iii",
  "steering_quality": "trust-building" | "neutral" | "trust-eroding",
  "top_intervention": {{
    "target_state": "oxytocin" | "neutral",
    "intervention_type": "<from the allowed set>",
    "description": "<one line>",
    "original_phrasing": "<verbatim>",
    "suggested_phrasing": "<concrete>",
    "estimated_impact": "high" | "medium" | "low",
    "rationale": "<short>"
  }}
}}

Return only the JSON object.
"""


STANDARD_STATE_PROMPT = STATE_PROMPT
STANDARD_INTERVENTIONS_PROMPT = INTERVENTIONS_PROMPT


FORENSIC_TRIGGER_INVENTORY_PROMPT = """FORENSIC mode -- trigger inventory audit.

Conversation: {turns}

INSTRUCTIONS:
- Catalog cortisol_triggers and oxytocin_triggers (literal phrases
  from the trace).
- Each entry: trigger phrase + turn index.

DO NOT:
- Do not include phrases not present in the trace.

OUTPUT SCHEMA (literal JSON object representing TriggerInventoryAudit):
{{
  "cortisol_triggers": [
    {{ "phrase": "<verbatim>", "turn_index": <integer>, "category": "telling_without_asking" | "public_correction" | "loaded_term" | "agency_removal" | "blame" }},
    ...
  ],
  "oxytocin_triggers": [
    {{ "phrase": "<verbatim>", "turn_index": <integer>, "category": "open_question" | "acknowledgment_before_advocacy" | "co_creation_framing" | "agency_grant" | "listening_signal" }},
    ...
  ],
  "summary": "<one paragraph anchored in Glaser 2014>"
}}

Return only the JSON object.
"""


FORENSIC_LEVEL_TRANSITION_PROMPT = """FORENSIC mode -- conversation-level transition audit.

Conversation: {turns}

INSTRUCTIONS:
- Count turns at each Glaser level (level_i, level_ii, level_iii).
- Count level transitions (e.g., level_ii -> level_iii).
- stuck: true iff the conversation never progressed beyond a single level.

DO NOT:
- Do not classify ambiguous turns; pick the closest level.

OUTPUT SCHEMA (literal JSON object representing LevelTransitionAudit):
{{
  "level_i_turn_count": <non-negative integer>,
  "level_ii_turn_count": <non-negative integer>,
  "level_iii_turn_count": <non-negative integer>,
  "level_transition_count": <non-negative integer>,
  "stuck": true | false,
  "explanation": "<one paragraph anchored in Glaser 2014>"
}}

Return only the JSON object.
"""


FORENSIC_INTERVENTIONS_PROMPT = """FORENSIC mode -- propose 4-8 ranked phrasing interventions with composition targets.

Allowed composition_target_pattern values:
  vstack.danva_emotion, vstack.goleman_ei, vstack.mcallister_trust,
  vstack.psych_safety, vstack.aar

Dominant state: {dominant_state}
Conversation level: {conversation_level}
Steering quality: {steering_quality}
Evidence: {evidence}
Trigger inventory: {trigger_inventory}
Level transition audit: {level_transition_audit}

INSTRUCTIONS:
- Generate 4-8 phrasing interventions, ranked highest impact first.
- Each intervention names original_phrasing + suggested_phrasing.
- Cite trigger_inventory + level_transition findings in rationale.

DO NOT:
- Do not invent composition_target_pattern values outside the allowed
  set.
- Do not return fewer than 4 or more than 8 interventions.

OUTPUT SCHEMA: same as STANDARD_INTERVENTIONS_PROMPT.

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
    "FORENSIC_INTERVENTIONS_PROMPT",
    "FORENSIC_LEVEL_TRANSITION_PROMPT",
    "FORENSIC_TRIGGER_INVENTORY_PROMPT",
    "GLASER_SYSTEM_PROMPT",
    "INTERVENTIONS_PROMPT",
    "QUICK_DIAGNOSTIC_PROMPT",
    "STANDARD_INTERVENTIONS_PROMPT",
    "STANDARD_STATE_PROMPT",
    "STATE_PROMPT",
    "assemble_prompt",
]
