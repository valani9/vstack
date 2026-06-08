"""LLM prompts for the Group Decision Models generator.

0.15.0 uplift: OUTPUT SCHEMA literals + DO NOT rules + one-shot example.
Wire format unchanged.
"""

from __future__ import annotations

from typing import Any

from vstack.aar import fence, sanitize_for_prompt


DECISION_SYSTEM_PROMPT = """You are a decision-protocol generator grounded in:

  - **Kaner (2014)** *Facilitator's Guide to Participatory Decision-Making.*
  - **Vroom & Yetton (1973)** Decision-Making and Leadership.
  - **Janis (1972)** *Victims of Groupthink* — when unanimous flags consensus failure.

Five canonical decision-aggregation models:

  - CONCURRING    single decisive vote. Fast; low buy-in.
  - MAJORITY      > 50 percent. Speed + legitimacy compromise.
  - CONSENSUS     all affirm or do not block. High buy-in; slow.
  - FIST_TO_FIVE  graded 0-5; 0 blocks. Surfaces dissent intensity.
  - UNANIMOUS     all positively vote yes. High buy-in; slowest.

Model selection heuristics (Kaner 2014 + Vroom-Yetton 1973):
  - high stakes + irreversible + regulatory       -> consensus or unanimous.
  - low stakes + reversible + time pressure       -> concurring or majority.
  - high expertise asymmetry                      -> concurring (expert's call).
  - high buy-in required                          -> consensus or fist_to_five.
  - novel debate with dissent surfacing wanted    -> fist_to_five.

Posture (absolute):
- **HONEST.** Name trade-offs of the recommended model.
- **KILL-AMBIGUITY-FIRST.** Always populate threshold, tie_breaker, fallback. Ambiguous protocols cause expensive disputes.
- **TERSE.** Output is read on dashboards.

Output discipline: when asked for JSON, return JSON only. No prose, no markdown fences.
"""


DECISION_PROTOCOL_PROMPT = """STANDARD mode -- generate a decision-aggregation protocol.

Decision title: {title}
Options:
{options}
Agents: {agents}
Stakes: {stakes}
Reversibility: {reversibility}
Time pressure: {time_pressure}
Expertise asymmetry: {expertise_asymmetry}
Regulatory exposure: {regulatory_exposure}
Buy-in required: {buy_in_required}
Forced model (if any): {forced_model}

INSTRUCTIONS:
- Apply the selection heuristics from the system prompt.
- If ``forced_model`` is non-null, USE it regardless of heuristic
  preference (caller has already decided).
- ``threshold``: concrete numeric or rule (e.g., ">= 50%", "all affirm").
- ``quorum``: integer minimum participants for a valid vote, or null.
- ``tie_breaker``: concrete rule (e.g., "chair decides", "re-vote
  after discussion").
- ``fallback_model``: what to use if the primary model fails to
  produce a decision in the time budget.

DO NOT:
- Do not return an empty tie_breaker on consensus / unanimous models.
- Do not return prose around the JSON.
- Do not invent agent names not in ``agents``.

OUTPUT SCHEMA (literal JSON object):
{{
  "recommended_model": "concurring" | "majority" | "consensus" | "fist_to_five" | "unanimous",
  "rationale": "<one paragraph anchored in Kaner 2014 / Vroom-Yetton 1973>",
  "protocol_steps": ["<step>", ...],
  "threshold": "<concrete numeric or rule>",
  "quorum": <integer or null>,
  "tie_breaker": "<concrete rule>",
  "fallback_model": "concurring" | "majority" | "consensus" | "fist_to_five" | "unanimous" | null,
  "dissent_recording": "<how dissent is captured>"
}}

EXAMPLE (irreversible high-stakes regulatory decision -> consensus with concrete tie-breaker):
{{
  "recommended_model": "consensus",
  "rationale": "Stakes are high + reversibility is one-way-door + regulatory exposure is present. Kaner 2014: consensus is the appropriate model when the cost of a non-buy-in dissent later is higher than the cost of consensus-process time now. Vroom-Yetton 1973 contingency also routes here.",
  "protocol_steps": [
    "1. Each agent reads the proposal and produces a fist_to_five rating with comment",
    "2. Anyone at 0 or 1 blocks; convene 15-minute discussion on each block",
    "3. Re-rate; iterate until no 0 or 1 remains OR until 3 iterations elapse",
    "4. If iterations exhausted, escalate to fallback_model"
  ],
  "threshold": "all agents at fist_to_five rating >= 2",
  "quorum": null,
  "tie_breaker": "After 3 iterations, fallback to majority vote with chair recording dissent in writing",
  "fallback_model": "majority",
  "dissent_recording": "Each blocking dissent (rating <=1) recorded verbatim in the meeting log, attributed to the agent"
}}

Return only the JSON object.
"""


QUICK_DIAGNOSTIC_PROMPT = """QUICK mode -- minimal decision protocol.

Title: {title}
Stakes: {stakes}
Reversibility: {reversibility}
Buy-in required: {buy_in_required}

INSTRUCTIONS:
- Apply selection heuristics from the system prompt.
- Compact: recommended_model + rationale + threshold + protocol_steps.

DO NOT:
- Do not return ambiguous threshold.
- Do not return prose around the JSON.

OUTPUT SCHEMA (literal JSON object):
{{
  "recommended_model": "concurring" | "majority" | "consensus" | "fist_to_five" | "unanimous",
  "rationale": "<1-2 sentences anchored in Kaner 2014>",
  "threshold": "<concrete>",
  "protocol_steps": ["<step>", ...]
}}

Return only the JSON object.
"""


STANDARD_DECISION_PROTOCOL_PROMPT = DECISION_PROTOCOL_PROMPT


FORENSIC_METHOD_FIT_PROMPT = """FORENSIC mode -- method-fit audit.

Protocol:
{protocol}
Request properties: {properties}

INSTRUCTIONS:
- Score fit on each axis (stakes, reversibility, time_pressure, buy_in,
  regulatory). Each in [0, 1].
- overall_fit = mean across axes.

DO NOT:
- Do not score every axis the same; the axes are independent.

OUTPUT SCHEMA (literal JSON object representing MethodFitAudit):
{{
  "stakes_fit": <float in [0.0, 1.0]>,
  "reversibility_fit": <float in [0.0, 1.0]>,
  "time_pressure_fit": <float in [0.0, 1.0]>,
  "buy_in_fit": <float in [0.0, 1.0]>,
  "regulatory_fit": <float in [0.0, 1.0]>,
  "overall_fit": <float in [0.0, 1.0]>,
  "notes": "<one paragraph anchored in Kaner 2014 / Vroom-Yetton 1973>"
}}

Return only the JSON object.
"""


FORENSIC_TALLY_INTEGRITY_PROMPT = """FORENSIC mode -- tally integrity audit.

Protocol:
{protocol}

INSTRUCTIONS:
- Check whether the protocol specifies quorum, tie_breaker, fallback,
  dissent_recording.
- integrity in [0, 1].

DO NOT:
- Do not credit "obvious from context" as specified.

OUTPUT SCHEMA (literal JSON object representing TallyIntegrityAudit):
{{
  "has_quorum": true | false,
  "has_tie_breaker": true | false,
  "has_fallback": true | false,
  "records_dissent": true | false,
  "integrity": <float in [0.0, 1.0]>,
  "notes": "<one paragraph>"
}}

Return only the JSON object.
"""


FORENSIC_INTERVENTIONS_PROMPT = """FORENSIC mode -- propose 3-6 protocol-improvement interventions.

Allowed composition_target_pattern values:
  vstack.devils_advocate, vstack.bias_stack, vstack.aar, vstack.grpi,
  vstack.lencioni

Protocol:
{protocol}
Method fit audit: {method_fit_audit}
Tally integrity audit: {tally_integrity_audit}

INSTRUCTIONS:
- target_dimension: model / threshold / quorum / tie_breaker / fallback / overall.
- Cite method_fit_audit + tally_integrity_audit in rationale.

DO NOT:
- Do not invent composition_target_pattern values outside the allowed
  set.
- Do not return fewer than 3 or more than 6 interventions.

ALLOWED intervention_type values:
  switch_to_concurring, switch_to_majority, switch_to_consensus,
  switch_to_fist_to_five, switch_to_unanimous, add_quorum,
  add_tie_breaker, add_fallback, tighten_threshold, new_eval,
  human_review, compose_pattern

OUTPUT SCHEMA (literal JSON array of GroupDecisionIntervention objects):
[
  {{
    "target_dimension": "model" | "threshold" | "quorum" | "tie_breaker" | "fallback" | "overall",
    "intervention_type": "<from the allowed set>",
    "description": "<one line>",
    "suggested_implementation": "<concrete>",
    "estimated_impact": "high" | "medium" | "low",
    "rationale": "<Kaner 2014 / Vroom-Yetton 1973 anchored>",
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
    "DECISION_PROTOCOL_PROMPT",
    "DECISION_SYSTEM_PROMPT",
    "FORENSIC_INTERVENTIONS_PROMPT",
    "FORENSIC_METHOD_FIT_PROMPT",
    "FORENSIC_TALLY_INTEGRITY_PROMPT",
    "QUICK_DIAGNOSTIC_PROMPT",
    "STANDARD_DECISION_PROTOCOL_PROMPT",
    "assemble_prompt",
]
