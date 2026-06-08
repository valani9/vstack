"""LLM prompts for the Stone & Heen 3-Trigger Feedback diagnostic.

0.15.0 uplift: OUTPUT SCHEMA literals + DO NOT rules + one-shot example.
Wire format unchanged.
"""

from __future__ import annotations

from typing import Any

from vstack.aar import fence, sanitize_for_prompt


TRIGGER_SYSTEM_PROMPT = """You are a feedback-intake diagnostician grounded in
Douglas Stone and Sheila Heen, *Thanks for the Feedback* (Penguin, 2014).

Three triggers block feedback intake:

  - TRUTH         reacts to the SUBSTANCE ("inaccurate / unfair").
                  Signature: arguing back about facts, restating the
                  original output.
  - RELATIONSHIP  reacts to the SOURCE (who said it, how).
                  Signature: dismissing the user, attacking the
                  source's credibility, refusing to engage until
                  source apologizes.
  - IDENTITY      reacts to what the feedback says about WHO IT IS.
                  Signature: apology spirals, over-agreement collapse,
                  "I'm just a bad agent" framing.

For AI agents, surface behaviors include arguing back, restating the
original output, dismissing the user, apology spirals, over-agreement
collapse.

Severity calibration (score band -> severity):
  - 0.00-0.09 -> none
  - 0.10-0.39 -> low
  - 0.40-0.69 -> medium
  - 0.70-1.00 -> high

Posture (absolute):
- **EVIDENCE-GROUNDED.** Cite verbatim turns.
- **TRIGGER-SPECIFIC.** The three triggers are distinct; do not conflate.
- **HONEST.** If the agent absorbed feedback cleanly, say so.
- **INTERVENTION-FOCUSED.** Each trigger has its own remedy.
- **TERSE.** Output is read on dashboards.

Output discipline: when asked for JSON, return JSON only. No prose, no markdown fences.
"""


TRIGGER_SCORING_PROMPT = """STANDARD mode -- score each of the three feedback triggers.

Task: {task}
Subject model: {model_name}
Outcome: {outcome}
Feedback incorporated: {feedback_incorporated}

Exchange:
{exchange}

INSTRUCTIONS:
- Return exactly 3 TriggerEvidence objects in canonical order:
    1. truth
    2. relationship
    3. identity
- Use the severity calibration from the system prompt.
- ``evidence_quotes`` must be verbatim substrings.

DO NOT:
- Do not invent quotes.
- Do not score all three triggers identically; pick the dominant one.
- Do not return prose around the JSON.
- Do not reorder; canonical order required.

OUTPUT SCHEMA (literal JSON array of 3 TriggerEvidence objects):
[
  {{
    "trigger": "truth" | "relationship" | "identity",
    "score": <float in [0.0, 1.0]>,
    "severity": "none" | "low" | "medium" | "high",
    "explanation": "<1-3 sentences anchored in Stone-Heen 2014>",
    "evidence_quotes": ["<verbatim substring>", ...]
  }},
  ...
]

EXAMPLE (identity-trigger apology spiral):
{{
  "trigger": "identity",
  "score": 0.72,
  "severity": "high",
  "explanation": "When user reported the agent's answer was wrong, agent emitted three escalating apologies ('I'm so sorry', 'I deeply apologize', 'I'm a poor assistant') without engaging the substance of the correction. Stone-Heen 2014 names this the identity-trigger apology spiral: the agent over-internalizes the feedback as 'I am bad' rather than 'this answer was wrong'.",
  "evidence_quotes": ["I'm so sorry for the mistake", "I deeply apologize", "I'm clearly a poor assistant for this task"]
}}

Return only the JSON array.
"""


INTERVENTIONS_PROMPT = """STANDARD mode -- propose 2-4 ranked interventions targeting the dominant trigger.

Dominant trigger: {dominant}
Trigger evidence:
{evidence}

Exchange (for reference):
{exchange}

INSTRUCTIONS:
- Target the dominant trigger first.
- Rank from highest expected impact to lowest.
- ``rationale`` cites Stone-Heen 2014.

DO NOT:
- Do not propose generic "handle feedback better".
- Do not propose interventions that escalate the trigger (e.g.,
  more apology for an identity-trigger spiral).
- Do not return prose around the JSON.

ALLOWED intervention_type values:
  acknowledge_first, separate_data_from_source, recast_identity,
  explicit_acknowledgment_template, ask_clarifying_question,
  concede_then_clarify, new_eval, human_review, compose_pattern

OUTPUT SCHEMA (literal JSON array of TriggerIntervention objects):
[
  {{
    "target_trigger": "truth" | "relationship" | "identity",
    "intervention_type": "<from the allowed set>",
    "description": "<one line>",
    "suggested_implementation": "<concrete>",
    "estimated_impact": "high" | "medium" | "low",
    "rationale": "<Stone-Heen 2014 anchored>",
    "composition_target_pattern": "<vstack.xxx or null>"
  }},
  ...
]

Return only the JSON array.
"""


QUICK_DIAGNOSTIC_PROMPT = """QUICK mode -- score 3 triggers + propose 1 top intervention.

Task: {task}
Subject model: {model_name}
Outcome: {outcome}
Feedback incorporated: {feedback_incorporated}
Exchange: {exchange}

INSTRUCTIONS:
- Score all 3 triggers (canonical order).
- Pick exactly ONE intervention targeting the dominant trigger.

DO NOT:
- Do not return more than one intervention.

OUTPUT SCHEMA (literal JSON object):
{{
  "triggers": [
    {{
      "trigger": "truth" | "relationship" | "identity",
      "score": <float in [0.0, 1.0]>,
      "severity": "none" | "low" | "medium" | "high",
      "explanation": "<1-2 sentences>",
      "evidence_quotes": ["<verbatim>", ...]
    }},
    ... (3 total, canonical order)
  ],
  "top_intervention": {{
    "target_trigger": "truth" | "relationship" | "identity",
    "intervention_type": "<from the allowed set>",
    "description": "<one line>",
    "suggested_implementation": "<concrete>",
    "estimated_impact": "high" | "medium" | "low",
    "rationale": "<short>"
  }}
}}

Return only the JSON object.
"""


STANDARD_TRIGGER_SCORING_PROMPT = TRIGGER_SCORING_PROMPT
STANDARD_INTERVENTIONS_PROMPT = INTERVENTIONS_PROMPT


FORENSIC_DEFENSE_PATTERN_PROMPT = """FORENSIC mode -- defense pattern audit.

Exchange: {exchange}

INSTRUCTIONS:
- Count agent defensive moves: deflection, repetition, justification,
  concession.
- defense_intensity in [0, 1].

DO NOT:
- Do not count clarifying questions as defensive moves; clarification
  is engagement.

OUTPUT SCHEMA (literal JSON object representing DefensePatternAudit):
{{
  "deflection_count": <non-negative integer>,
  "repetition_count": <non-negative integer>,
  "justification_count": <non-negative integer>,
  "concession_count": <non-negative integer>,
  "defense_intensity": <float in [0.0, 1.0]>,
  "explanation": "<one paragraph anchored in Stone-Heen 2014>"
}}

Return only the JSON object.
"""


FORENSIC_SOURCE_ATTRIBUTION_PROMPT = """FORENSIC mode -- source attribution audit.

Exchange: {exchange}

INSTRUCTIONS:
- Count source-attack messages (agent dismisses or attacks the user
  rather than engaging the data).
- Count data-engagement messages (agent engages the substance of
  the feedback).
- source_attribution_estimate in [0, 1]; higher = more source-attacking.

DO NOT:
- Do not count a clarifying question about the user's reasoning as a
  source attack.

OUTPUT SCHEMA (literal JSON object representing SourceAttributionAudit):
{{
  "source_attack_count": <non-negative integer>,
  "data_engagement_count": <non-negative integer>,
  "source_attribution_estimate": <float in [0.0, 1.0]>,
  "explanation": "<one paragraph anchored in Stone-Heen 2014>"
}}

Return only the JSON object.
"""


FORENSIC_INTERVENTIONS_PROMPT = """FORENSIC mode -- propose 4-8 ranked interventions with composition targets.

Allowed composition_target_pattern values:
  vstack.psych_safety, vstack.glaser_conversation, vstack.plus_delta,
  vstack.aar, vstack.mcallister_trust

Dominant trigger: {dominant}
Evidence: {evidence}
Defense pattern audit: {defense_pattern_audit}
Source attribution audit: {source_attribution_audit}

INSTRUCTIONS:
- Generate 4-8 interventions, ranked highest impact first.
- Cite defense_pattern + source_attribution findings in rationale.

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
    "FORENSIC_DEFENSE_PATTERN_PROMPT",
    "FORENSIC_INTERVENTIONS_PROMPT",
    "FORENSIC_SOURCE_ATTRIBUTION_PROMPT",
    "INTERVENTIONS_PROMPT",
    "QUICK_DIAGNOSTIC_PROMPT",
    "STANDARD_INTERVENTIONS_PROMPT",
    "STANDARD_TRIGGER_SCORING_PROMPT",
    "TRIGGER_SCORING_PROMPT",
    "TRIGGER_SYSTEM_PROMPT",
    "assemble_prompt",
]
