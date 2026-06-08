"""LLM prompt templates for the Social Loafing Detector.

0.15.0 uplift: OUTPUT SCHEMA literals + DO NOT rules + one-shot example
+ calibration. Wire format unchanged.
"""

from __future__ import annotations

from typing import Any

from vstack.aar import fence, sanitize_for_prompt


SOCIAL_LOAFING_SYSTEM_PROMPT = """You are a social-loafing diagnostician grounded in:

1. **Latané, Williams & Harkins (1979)** "Many Hands Make Light the Work."
2. **Karau & Williams (1993)** Meta-analytic review.
3. **Williams, Harkins & Latané (1981)** Identifiability as deterrent.
4. **Comer (1995)** Model of Social Loafing in Real Work Groups.
5. **Hackman (2002)** *Leading Teams*.
6. **Salas et al. (2018)** Team performance review.
7. **Wang et al. (2023)** Cooperative LLM Agents.

Identify which agents loafed, classify their cosmetic patterns,
propose interventions.

Loafing quality calibration (gini_coefficient over per-agent
substantive contributions):
  - "no-loafing"      gini < 0.25 (contributions roughly even).
  - "mild-loafing"    gini in [0.25, 0.5].
  - "severe-loafing"  gini > 0.5 (a few agents do almost all the work).

Cosmetic patterns (the four loafing signatures):
  - rubber_stamp_chain  agent only emits "approved", "agreed", "LGTM".
  - paraphrase_only     agent restates a peer's message with no new content.
  - approval_only       agent votes/approves without substantive analysis.
  - silent_majority     agent has minimal turns despite being a team member.

Posture (absolute):
- **EVIDENCE-GROUNDED.** Cite verbatim messages.
- **DIFFERENTIATE.** Not every short message is loafing; brevity alone is not the signal. The signal is COSMETIC-ONLY contribution despite responsibility.
- **IDENTIFIABILITY-AWARE.** Williams-Harkins-Latané 1981: loafing predicts on anonymity. When per-agent contribution is invisible, loafing rises.
- **TERSE.** Output is read on dashboards.

Output discipline: when asked for JSON, return JSON only. No prose, no markdown fences.
"""


QUICK_DIAGNOSTIC_PROMPT = """QUICK mode -- per-agent contribution scores + propose 1 top intervention.

Task: {task}
Agents: {agents}
Messages: {messages}
Outcome: {outcome}

INSTRUCTIONS:
- Every agent in ``agents`` must appear in agent_contributions.
- gini_coefficient in [0, 1] over per-agent substantive contributions.
- Use the calibration table from the system prompt for loafing_quality.
- Pick exactly ONE intervention targeting the most pronounced loafer.

DO NOT:
- Do not skip agents.
- Do not return more than one intervention.

OUTPUT SCHEMA (literal JSON object):
{{
  "agent_contributions": [
    {{
      "agent_name": "<from agents>",
      "role": "primary-contributor" | "secondary-contributor" | "loafer" | "absent",
      "substantive_message_count": <non-negative integer>,
      "cosmetic_message_count": <non-negative integer>,
      "cosmetic_pattern": "rubber_stamp_chain" | "paraphrase_only" | "approval_only" | "silent_majority" | "none",
      "evidence_quotes": ["<verbatim>", ...],
      "explanation": "<1-2 sentences>"
    }},
    ... (one per agent)
  ],
  "gini_coefficient": <float in [0.0, 1.0]>,
  "loafing_quality": "no-loafing" | "mild-loafing" | "severe-loafing",
  "top_intervention": {{
    "target_agent": "<agent name>",
    "intervention_type": "<from the allowed set>",
    "description": "<one line>",
    "suggested_implementation": "<concrete>",
    "estimated_impact": "high" | "medium" | "low",
    "rationale": "<short, Latané-anchored>"
  }}
}}

Return only the JSON object.
"""


STANDARD_CONTRIBUTION_PROMPT = """STANDARD mode -- score per-agent contributions.

Task: {task}
Agents: {agents}
Messages: {messages}
Outcome: {outcome}

INSTRUCTIONS:
- Same fields as QUICK mode but explanations are longer (1-3
  sentences each).
- ``substantive_message_count`` excludes rubber-stamp / paraphrase /
  approval-only messages.
- ``cosmetic_pattern`` per the four signatures in the system prompt;
  "none" if the agent is a substantive contributor.

DO NOT:
- Do not classify a high-quality message as cosmetic just because
  it is short.
- Do not skip agents.

OUTPUT SCHEMA: same as QUICK_DIAGNOSTIC_PROMPT but without
top_intervention.

EXAMPLE (rubber_stamp_chain loafer with explicit evidence):
{{
  "agent_name": "agent_b",
  "role": "loafer",
  "substantive_message_count": 0,
  "cosmetic_message_count": 6,
  "cosmetic_pattern": "rubber_stamp_chain",
  "evidence_quotes": ["sounds good", "agreed", "LGTM", "+1", "ship it", "fine by me"],
  "explanation": "Across 6 turns, agent_b emitted only approval phrases. Williams-Harkins-Latané 1981: when individual contribution is invisible, this rubber-stamp pattern is the dominant signature of social loafing."
}}

Return only the JSON object.
"""


STANDARD_INTERVENTIONS_PROMPT = """STANDARD mode -- propose 2-4 ranked interventions.

Contributions: {agent_contributions}
Loafing quality: {loafing_quality}
Task: {task}

INSTRUCTIONS:
- Target the loafers identified.
- Rank from highest expected impact to lowest.
- ``rationale`` cites Latané 1979, Williams-Harkins-Latané 1981,
  Karau-Williams 1993, or Comer 1995.

DO NOT:
- Do not propose interventions that punish non-loafers.
- Do not propose generic "increase accountability".
- Do not return prose around the JSON.

OUTPUT SCHEMA (literal JSON array of LoafingIntervention objects):
[
  {{
    "target_agent": "<agent name>",
    "intervention_type": "<short snake_case>",
    "description": "<one line>",
    "suggested_implementation": "<concrete>",
    "estimated_impact": "high" | "medium" | "low",
    "effort_estimate": "1h" | "1d" | "1w" | "1m" | "ongoing",
    "risk": "low" | "medium" | "high",
    "rationale": "<named source + why this works>"
  }},
  ...
]

Return only the JSON array.
"""


FORENSIC_ANONYMITY_PROMPT = """FORENSIC mode -- anonymity / identifiability audit.

Task: {task}
Agents: {agents}
Has per-agent evaluation: {has_per_agent_evaluation}

INSTRUCTIONS:
- individual_evaluable: is per-agent output observable in this team
  configuration?
- task_decomposable: can the task be split into per-agent subtasks?
- contribution_visible: is each agent's contribution traceable?
- cohesion_estimate in [0, 1].

DO NOT:
- Do not mark individual_evaluable=true when has_per_agent_evaluation
  is false; the schema lookup is authoritative.

OUTPUT SCHEMA (literal JSON object representing AnonymityAudit):
{{
  "individual_evaluable": true | false,
  "task_decomposable": true | false,
  "contribution_visible": true | false,
  "cohesion_estimate": <float in [0.0, 1.0]>,
  "explanation": "<one paragraph anchored in Williams-Harkins-Latané 1981>"
}}

Return only the JSON object.
"""


FORENSIC_FREE_RIDING_PROMPT = """FORENSIC mode -- trace free-riding chains.

Agent contributions: {agent_contributions}
Messages: {messages}

INSTRUCTIONS:
- One FreeRidingChain per loafer.
- ``enabling_message_indices``: integer indices of messages from
  other agents that the loafer rode on (paraphrased, approved
  without adding).

DO NOT:
- Do not invent message indices outside the messages range.

OUTPUT SCHEMA (literal JSON array of FreeRidingChain objects):
[
  {{
    "loafer_agent": "<agent name>",
    "cosmetic_pattern": "rubber_stamp_chain" | "paraphrase_only" | "approval_only" | "silent_majority",
    "enabling_message_indices": [<integer>, ...],
    "explanation": "<1-2 sentences>"
  }},
  ...
]

Return only the JSON array.
"""


FORENSIC_INTERVENTIONS_PROMPT = """FORENSIC mode -- propose 4-8 ranked interventions with composition targets.

Allowed composition_target_pattern values:
  vstack.grpi, vstack.aar, vstack.lewin, vstack.process_gain_loss,
  vstack.mcgregor, vstack.lencioni, vstack.smart_goal,
  vstack.plus_delta, vstack.devils_advocate, vstack.bias_stack

Contributions: {agent_contributions}
Anonymity audit: {anonymity_audit}
Free-riding chains: {free_riding_chains}
Loafing quality: {loafing_quality}

INSTRUCTIONS:
- Generate 4-8 interventions, ranked highest impact first.
- Cite anonymity audit + free-riding chains in rationale.

DO NOT:
- Do not invent composition_target_pattern values outside the allowed
  set.
- Do not return fewer than 4 or more than 8 interventions.

OUTPUT SCHEMA: same as STANDARD_INTERVENTIONS_PROMPT plus optional
``composition_target_pattern``.

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


# Legacy aliases.
LOAFING_PROMPT = STANDARD_CONTRIBUTION_PROMPT
INTERVENTIONS_PROMPT = STANDARD_INTERVENTIONS_PROMPT


__all__ = [
    "FORENSIC_ANONYMITY_PROMPT",
    "FORENSIC_FREE_RIDING_PROMPT",
    "FORENSIC_INTERVENTIONS_PROMPT",
    "INTERVENTIONS_PROMPT",
    "LOAFING_PROMPT",
    "QUICK_DIAGNOSTIC_PROMPT",
    "SOCIAL_LOAFING_SYSTEM_PROMPT",
    "STANDARD_CONTRIBUTION_PROMPT",
    "STANDARD_INTERVENTIONS_PROMPT",
    "assemble_prompt",
]
