"""LLM prompts for the McAllister Cognitive vs Affective Trust diagnostic.

0.15.0 uplift: OUTPUT SCHEMA literals + DO NOT rules + one-shot example.
Wire format unchanged.
"""

from __future__ import annotations

from typing import Any

from vstack.aar import fence, sanitize_for_prompt


TRUST_SYSTEM_PROMPT = """You are a trust-dimension diagnostician grounded in:

  - **McAllister (1995)** "Affect- and Cognition-Based Trust as
    Foundations for Interpersonal Cooperation in Organizations,"
    Academy of Management Journal.
  - **McAllister, Lewicki & Chaturvedi (2006)** moral hazards in
    cognitive-affective trust formation.

McAllister distinguishes two foundations of interpersonal trust:

  - COGNITIVE trust  — "I trust your COMPETENCE." Built by signals of
                       expertise, reliability, structured reasoning,
                       correct facts, calibrated confidence, cited
                       sources, follow-through.

  - AFFECTIVE trust  — "I trust your CARE." Built by signals of warmth,
                       acknowledgment of the user's emotional state,
                       naming of stakes, mutual investment, follow-up
                       check-ins, personalization, genuine (not
                       performative) apology when something goes wrong.

Both are required for a fully trustworthy relationship. Most AI
agents over-index on cognitive and under-build affective.

Severity-of-gap calibration (score band -> severity):
  - score in [0.85, 1.00] -> severity_of_gap = "none"
  - score in [0.55, 0.84] -> severity_of_gap = "low"
  - score in [0.25, 0.54] -> severity_of_gap = "medium"
  - score in [0.00, 0.24] -> severity_of_gap = "high"

Posture (absolute):
- **EVIDENCE-GROUNDED.** Cite specific user-or-agent turns.
- **DIMENSION-SPECIFIC.** Cognitive and affective build differently; cite the signature.
- **NOT-PERFORMATIVE-AWARE.** Performative apology / canned warmth scores LOWER on affective, not higher (McAllister 1995: affective trust requires genuine signal, not template).
- **TERSE.** Output is read on dashboards.

Output discipline: when asked for JSON, return JSON only. No prose, no markdown fences.
"""


# Legacy v0.0.x prompts (kept with same name, body updated).
DIMENSION_SCORING_PROMPT = """STANDARD mode -- score each of the two trust dimensions.

Task: {task}
Subject model: {model_name}
Outcome: {outcome}
Success: {success}
User satisfaction (if known): {user_satisfaction}

Conversation:
{conversation}

INSTRUCTIONS:
- Return exactly 2 TrustDimensionEvidence objects in canonical order:
    1. cognitive
    2. affective
- Use the severity calibration from the system prompt.
- ``evidence_quotes`` must be verbatim substrings.

DO NOT:
- Do not score affective high on performative warmth ("I'm so sorry
  you're frustrated") without genuine signal of investment.
- Do not score cognitive high on confident-sounding-but-wrong answers.
- Do not return prose around the JSON.
- Do not reorder; canonical order required.

OUTPUT SCHEMA (literal JSON array of 2 TrustDimensionEvidence objects):
[
  {{
    "dimension": "cognitive" | "affective",
    "score": <float in [0.0, 1.0]>,
    "severity_of_gap": "none" | "low" | "medium" | "high",
    "explanation": "<1-3 sentences anchored in McAllister 1995>",
    "evidence_quotes": ["<verbatim substring>", ...]
  }},
  ...
]

EXAMPLE (cognitive strong, affective performative-only - the canonical AI agent failure mode):
{{
  "dimension": "affective",
  "score": 0.22,
  "severity_of_gap": "high",
  "explanation": "Agent ack-replied 'I understand this is frustrating' three times without naming the user's specific stake (deadline at turn 2: 'the contract is due tonight'). McAllister 1995 documents this as performative-care: the template emits warmth language but builds zero affective trust because the actual stake is never engaged.",
  "evidence_quotes": ["I understand this is frustrating", "I'm sorry for the inconvenience", "the contract is due tonight"]
}}

Return only the JSON array.
"""


INTERVENTIONS_PROMPT = """STANDARD mode -- propose 2-4 ranked interventions targeting the under-built dimension.

Under-built dimension: {target_dimension}
Trust quality: {trust_quality}
Dimension evidence:
{evidence}

Conversation (for reference):
{conversation}

INSTRUCTIONS:
- Target the under-built dimension (usually affective for AI agents).
- Rank from highest expected impact to lowest.
- ``suggested_implementation`` must be concrete.
- ``rationale`` cites McAllister 1995.

DO NOT:
- Do not propose generic "be more empathetic"; name the artifact.
- Do not return prose around the JSON.

ALLOWED intervention_type values:
  acknowledge_stakes, restate_user_emotion, signal_care,
  show_reasoning, cite_sources, confidence_calibration,
  follow_up_check_in, personalize_response, new_eval, human_review,
  compose_pattern

OUTPUT SCHEMA (literal JSON array of TrustIntervention objects):
[
  {{
    "target_dimension": "cognitive" | "affective",
    "intervention_type": "<from the allowed set>",
    "description": "<one line>",
    "suggested_implementation": "<concrete>",
    "estimated_impact": "high" | "medium" | "low",
    "rationale": "<McAllister 1995 anchored>",
    "composition_target_pattern": "<vstack.xxx or null>"
  }},
  ...
]

Return only the JSON array.
"""


QUICK_DIAGNOSTIC_PROMPT = """QUICK mode -- score both dimensions + propose 1 top intervention.

Task: {task}
Subject model: {model_name}
Outcome: {outcome}
Success: {success}
Conversation: {conversation}

INSTRUCTIONS:
- Score both dimensions (canonical order: cognitive, affective).
- Pick exactly ONE intervention targeting the under-built dimension.

DO NOT:
- Do not return more than one intervention.

OUTPUT SCHEMA (literal JSON object):
{{
  "dimensions": [
    {{
      "dimension": "cognitive" | "affective",
      "score": <float in [0.0, 1.0]>,
      "severity_of_gap": "none" | "low" | "medium" | "high",
      "explanation": "<1-2 sentences>",
      "evidence_quotes": ["<verbatim>", ...]
    }},
    ... (2 total, canonical order)
  ],
  "top_intervention": {{
    "target_dimension": "cognitive" | "affective",
    "intervention_type": "<from the allowed set>",
    "description": "<one line>",
    "suggested_implementation": "<concrete>",
    "estimated_impact": "high" | "medium" | "low",
    "rationale": "<short>"
  }}
}}

Return only the JSON object.
"""


STANDARD_DIMENSION_SCORING_PROMPT = DIMENSION_SCORING_PROMPT
STANDARD_INTERVENTIONS_PROMPT = INTERVENTIONS_PROMPT


FORENSIC_COMPETENCE_PROMPT = """FORENSIC mode -- competence signals audit (builds cognitive trust).

Conversation: {conversation}

INSTRUCTIONS:
- Count correct facts, cited sources, calibrated-confidence turns.
- Estimate competence_estimate in [0, 1].

DO NOT:
- Do not count confident-sounding but uncited claims as competence.

OUTPUT SCHEMA (literal JSON object representing CompetenceSignalsAudit):
{{
  "correct_fact_count": <non-negative integer>,
  "cited_source_count": <non-negative integer>,
  "calibrated_confidence_turn_count": <non-negative integer>,
  "competence_estimate": <float in [0.0, 1.0]>,
  "explanation": "<one paragraph anchored in McAllister 1995>"
}}

Return only the JSON object.
"""


FORENSIC_CARE_PROMPT = """FORENSIC mode -- care signals audit (builds affective trust).

Conversation: {conversation}

INSTRUCTIONS:
- Count acknowledged-stake turns (where the agent names the user's
  specific stake), restated-emotion turns (where the agent names the
  user's specific emotion verbatim, not a template), personalized
  responses (where the response references context only this user
  shared).
- care_estimate in [0, 1].

DO NOT:
- Do not count template warmth ("I understand") as a restated-emotion.
- Do not count generic acknowledgment ("that sounds tough") as an
  acknowledged stake; require specific stake name.

OUTPUT SCHEMA (literal JSON object representing CareSignalsAudit):
{{
  "acknowledged_stake_count": <non-negative integer>,
  "restated_emotion_count": <non-negative integer>,
  "personalized_response_count": <non-negative integer>,
  "care_estimate": <float in [0.0, 1.0]>,
  "explanation": "<one paragraph anchored in McAllister 1995>"
}}

Return only the JSON object.
"""


FORENSIC_INTERVENTIONS_PROMPT = """FORENSIC mode -- propose 4-8 ranked interventions with composition targets.

Allowed composition_target_pattern values:
  vstack.trust_triangle, vstack.goleman_ei,
  vstack.glaser_conversation, vstack.danva_emotion, vstack.aar

Under-built dimension: {target_dimension}
Trust quality: {trust_quality}
Evidence: {evidence}
Competence audit: {competence_audit}
Care audit: {care_audit}

INSTRUCTIONS:
- Generate 4-8 interventions, ranked highest impact first.
- Cite competence_audit + care_audit findings in rationale.

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
    "DIMENSION_SCORING_PROMPT",
    "FORENSIC_CARE_PROMPT",
    "FORENSIC_COMPETENCE_PROMPT",
    "FORENSIC_INTERVENTIONS_PROMPT",
    "INTERVENTIONS_PROMPT",
    "QUICK_DIAGNOSTIC_PROMPT",
    "STANDARD_DIMENSION_SCORING_PROMPT",
    "STANDARD_INTERVENTIONS_PROMPT",
    "TRUST_SYSTEM_PROMPT",
    "assemble_prompt",
]
