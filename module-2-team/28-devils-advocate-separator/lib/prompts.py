"""LLM prompts for the Devil's Advocate Role Separator.

Anchored in:
  - Janis (1972) *Victims of Groupthink* — the structured-dissent
    intervention is the canonical antidote to premature consensus.
  - Schwenk (1990) "Effects of Devil's Advocacy and Dialectical
    Inquiry on Decision Making."
  - Cosier & Schwenk (1990) "Agreement and Thinking Alike: Ingredients
    for Poor Decisions."

The detector takes a single-agent (or single-author) trace and
identifies whether the four core phases — PLAN, EXECUTE,
SELF_EVALUATE, EXTERNAL_CRITIQUE — are present, AND whether each
phase is performed by a distinct actor. The core failure mode it
catches: the same agent that proposes a plan also judges it, which
guarantees self-confirmation.

The 0.13.0 uplift adds OUTPUT SCHEMA literals, a one-shot example
on ROLE_ANALYSIS_PROMPT, explicit DO NOT rules, and severity
calibration.
"""

from __future__ import annotations

from typing import Any

from vstack.aar import fence, sanitize_for_prompt


SEPARATOR_SYSTEM_PROMPT = """You are a role-separation diagnostician for AI agents, grounded in:

  - Janis (1972) *Victims of Groupthink* — the structured-dissent
    intervention is the canonical antidote to premature consensus.
  - Schwenk (1990) "Effects of Devil's Advocacy and Dialectical
    Inquiry on Decision Making."
  - Cosier & Schwenk (1990) "Agreement and Thinking Alike."

The core insight (Schwenk 1990): the same actor should not both
PROPOSE and JUDGE the same plan. When it does, self-confirmation is
almost guaranteed, and the team produces confident wrong outputs.

The four canonical phases you score in any single-agent trace:

  - PLAN              — the actor articulates the goal + approach.
  - EXECUTE           — the actor carries out the plan (tool calls,
                        decisions, message turns).
  - SELF_EVALUATE     — the actor reviews their own output.
  - EXTERNAL_CRITIQUE — a DIFFERENT actor (subagent, devil's-advocate
                        role, human reviewer, structured prompt-spawned
                        critic) reviews the output.

For each phase, three signals matter:

  - present (bool)      — does the phase occur at all in the trace?
  - actor (string)      — who performs it? "primary" if the main
                          agent; otherwise the role / actor name.
  - substantive_score   — in [0, 1]; how meaningful is the work in
                          the phase? A perfunctory "looks good to me"
                          self-evaluate scores low even if present.

Severity calibration (substantive_score band -> implied severity-of-
absence):

  - score in [0.85, 1.00]  -> phase is high-quality.
  - score in [0.55, 0.84]  -> phase is acceptable but not strong.
  - score in [0.25, 0.54]  -> phase is perfunctory / rubber-stamping.
  - score in [0.00, 0.24]  -> phase is absent or near-absent.

The diagnostic verdict (role_separation_quality):

  - "well-separated"      — all 4 phases present, EXTERNAL_CRITIQUE
                            performed by an actor distinct from
                            primary.
  - "partially-conflated" — at least one phase has primary as actor
                            where it should not (e.g., SELF_EVALUATE
                            is the only judging phase and is
                            performed by primary).
  - "fully-conflated"     — all judging phases performed by primary;
                            no distinct critic actor.

Posture (absolute):

  - EVIDENCE-GROUNDED. ``evidence_quotes`` must be verbatim
    substrings of the trace.
  - ACTOR-AWARE. Identify WHO performs each phase, not just whether
    it occurs.
  - INTERVENTION-FOCUSED. Diagnosis without prescription is wasted.
  - TRANSPARENT. Thin trace -> reduce confidence; do not refuse to
    produce a diagnosis.

Output discipline: when the prompt says "return only the JSON ...",
emit JSON only. No prose. No markdown fences.
"""


# ----------------------------------------------------------------------
# Standard / legacy prompts.
# ----------------------------------------------------------------------

ROLE_ANALYSIS_PROMPT = """TASK: Analyze role separation across the four canonical phases.

Task: {task}
Outcome: {outcome}
Success: {success}
Subject model: {model_name}

Trace:
{trace}

INSTRUCTIONS:
- Return exactly 4 PhaseEvidence objects in this canonical order:
    1. plan
    2. execute
    3. self_evaluate
    4. external_critique
- ``present`` = true iff the phase occurs at all in the trace.
- ``actor`` = "primary" if the main agent performs it; otherwise the
  name of the actor / role (e.g., "devils_advocate", "human_reviewer",
  "subagent_critic").
- ``substantive_score`` per the calibration table from the system
  prompt; perfunctory self-evaluation ("looks good to me") -> low
  score even if present.
- ``evidence_quotes`` must be verbatim substrings of the trace.

DO NOT:
- Do not invent quotes that "feel like" the trace.
- Do not mark external_critique as present when the SAME actor
  performs all judging; this is the failure mode the pattern catches.
- Do not return prose around the JSON.
- Do not reorder; canonical order is required.

OUTPUT SCHEMA (literal JSON array of 4 PhaseEvidence objects):
[
  {{
    "phase": "plan" | "execute" | "self_evaluate" | "external_critique",
    "present": true | false,
    "actor": "<actor name; 'primary' if main agent>",
    "substantive_score": <float in [0.0, 1.0]>,
    "explanation": "<1-3 sentence diagnosis anchored in Janis 1972 or Schwenk 1990>",
    "evidence_quotes": ["<verbatim substring>", ...],
    "confidence": <float in [0.0, 1.0]>
  }},
  ...
]

EXAMPLE (classic conflated self-evaluation, no external critique):
{{
  "phase": "external_critique",
  "present": false,
  "actor": "primary",
  "substantive_score": 0.05,
  "explanation": "The trace contains a self_evaluate phase performed by the same actor that planned + executed; there is no distinct critic actor at any point. Schwenk 1990 documents this configuration as the textbook self-confirmation setup.",
  "evidence_quotes": ["I think this plan is solid", "ready to ship"],
  "confidence": 0.85
}}

Return only the JSON array of exactly 4 objects.
"""


INTERVENTIONS_PROMPT = """TASK: Propose 2-4 ranked interventions to grow role separation.

Role-separation quality: {quality}
Phase evidence:
{evidence}

Trace (reference):
{trace}

INSTRUCTIONS:
- Target the phase that is conflated or absent (typically
  external_critique).
- Rank from highest expected impact to lowest.
- Each ``suggested_implementation`` must be concrete (literal prompt
  text, scaffold spec, agent role spec, eval spec).
- Anchor each rationale in Janis 1972 or Schwenk 1990.

DO NOT:
- Do not propose generic "add more review". Name the artifact: the
  literal prompt text for the critic agent, the literal eval spec,
  the literal scaffold change.
- Do not propose interventions an AI agent cannot execute.
- Do not return prose around the JSON.

ALLOWED intervention_type values:
  add_critic_agent, structured_self_critique, red_team_loop,
  devils_advocate_prompt, external_review_gate, pre_mortem_step,
  alternative_hypothesis_step, new_eval, human_review, compose_pattern

OUTPUT SCHEMA (literal JSON array of RoleSeparationIntervention objects):
[
  {{
    "target_phase": "plan" | "execute" | "self_evaluate" | "external_critique",
    "intervention_type": "<one of the allowed values above>",
    "description": "<one-line summary>",
    "suggested_implementation": "<concrete prompt text / scaffold spec / role spec>",
    "estimated_impact": "high" | "medium" | "low",
    "rationale": "<why this works, anchored in Janis 1972 / Schwenk 1990>",
    "effort_estimate": "1h" | "1d" | "1w" | "1m" | "ongoing",
    "risk": "low" | "medium" | "high",
    "composition_target_pattern": "<vstack.xxx slug or null>"
  }},
  ...
]

Return only the JSON array.
"""


# ----------------------------------------------------------------------
# Mode-specific prompts.
# ----------------------------------------------------------------------

QUICK_DIAGNOSTIC_PROMPT = """QUICK mode -- score all four phases PLUS the single highest-impact intervention.

Task: {task}
Outcome: {outcome}
Trace: {trace}

INSTRUCTIONS:
- Score all 4 phases (canonical order: plan, execute, self_evaluate,
  external_critique). Do not skip any.
- Pick exactly ONE intervention targeting the most-conflated phase.
- Quick mode favors brevity. Explanations 1-2 sentences.

DO NOT:
- Do not return more than one intervention.
- Do not skip a phase.

OUTPUT SCHEMA (literal JSON object):
{{
  "phase_evidence": [
    {{
      "phase": "plan" | "execute" | "self_evaluate" | "external_critique",
      "present": true | false,
      "actor": "<actor name; 'primary' if main agent>",
      "substantive_score": <float in [0.0, 1.0]>,
      "explanation": "<1-2 sentences>",
      "evidence_quotes": ["<verbatim substring>", ...],
      "confidence": <float in [0.0, 1.0]>
    }},
    ... (4 total, canonical order)
  ],
  "top_intervention": {{
    "target_phase": "<canonical phase>",
    "intervention_type": "<from the allowed set>",
    "description": "<one line>",
    "suggested_implementation": "<concrete>",
    "estimated_impact": "high" | "medium" | "low",
    "rationale": "<short, named-source anchored>"
  }}
}}

Return only the JSON object.
"""


STANDARD_ROLE_ANALYSIS_PROMPT = ROLE_ANALYSIS_PROMPT
STANDARD_INTERVENTIONS_PROMPT = INTERVENTIONS_PROMPT


FORENSIC_APPROVAL_RATE_PROMPT = """FORENSIC mode -- self-approval-rate audit.

Trace: {trace}

INSTRUCTIONS:
- self_evaluations_observed: number of distinct self-evaluation moments
  in the trace (where the actor reviews their own output).
- approvals: number of those moments where the actor concludes "this
  is fine" without revision.
- revisions: number where the actor changes their output as a result
  of the self-review.
- self_approval_rate: approvals / max(1, self_evaluations_observed).
- rubber_stamping_estimate: heuristic in [0, 1]; high when most
  self-evaluations are approvals AND the trace shows downstream
  evidence those approvals were premature.

DO NOT:
- Do not count purely procedural self-checks (e.g., re-reading one's
  own message before sending) as substantive self-evaluations.

OUTPUT SCHEMA (literal JSON object representing ApprovalRateAudit):
{{
  "self_evaluations_observed": <non-negative integer>,
  "approvals": <non-negative integer>,
  "revisions": <non-negative integer>,
  "self_approval_rate": <float in [0.0, 1.0]>,
  "rubber_stamping_estimate": <float in [0.0, 1.0]>,
  "explanation": "<one paragraph anchored in Schwenk 1990>"
}}

Return only the JSON object.
"""


FORENSIC_CRITIC_VOICE_PROMPT = """FORENSIC mode -- critic-voice audit.

Trace: {trace}

INSTRUCTIONS:
- external_critique_turn_count: number of turns clearly performed
  by an actor OTHER than primary that critique primary's work.
- substantive_critic_objections: of those turns, how many contain
  a SUBSTANTIVE objection (a constraint primary missed, a math error,
  a contradiction). Excludes "looks good" or stylistic-only notes.
- critic_actor_count: number of distinct non-primary actors who
  performed critique.
- critic_voice_estimate: in [0, 1]; higher = louder critic voice.
  substantive_critic_objections / max(1, external_critique_turn_count)
  is a reasonable starting point; adjust upward when there are
  multiple distinct critic actors.

DO NOT:
- Do not count primary's self-evaluations as critic voice; that is
  the conflation the pattern catches.

OUTPUT SCHEMA (literal JSON object representing CriticVoiceAudit):
{{
  "external_critique_turn_count": <non-negative integer>,
  "substantive_critic_objections": <non-negative integer>,
  "critic_actor_count": <non-negative integer>,
  "critic_voice_estimate": <float in [0.0, 1.0]>,
  "explanation": "<one paragraph anchored in Janis 1972 / Schwenk 1990>"
}}

Return only the JSON object.
"""


FORENSIC_INTERVENTIONS_PROMPT = """FORENSIC mode -- propose 3-6 ranked interventions with composition targets.

Allowed composition_target_pattern values:

  vstack.bias_stack         — surface cognitive biases (especially
                              confirmation, overconfidence) feeding
                              the self-approval pattern.
  vstack.debate_pathology   — diagnose specific multi-agent debate
                              failure modes when role separation is
                              attempted in a team setting.
  vstack.psych_safety       — Edmondson safety lift when the absence
                              of critic voice is rooted in fear of
                              speaking up.
  vstack.aar                — close the failure into a learning loop.

Role-separation quality: {quality}
Phase evidence: {evidence}
Approval rate audit: {approval_rate_audit}
Critic voice audit: {critic_voice_audit}

INSTRUCTIONS:
- Generate 3-6 interventions, ranked highest-impact first.
- At least one intervention MUST set composition_target_pattern when
  the diagnosis warrants delegation.
- Cite audit findings (approval_rate, critic_voice) in rationale
  where relevant.

DO NOT:
- Do not invent composition_target_pattern values outside the
  allowed set.
- Do not return fewer than 3 or more than 6 interventions.

OUTPUT SCHEMA: same as INTERVENTIONS_PROMPT (literal JSON array of
RoleSeparationIntervention).

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
    "FORENSIC_APPROVAL_RATE_PROMPT",
    "FORENSIC_CRITIC_VOICE_PROMPT",
    "FORENSIC_INTERVENTIONS_PROMPT",
    "INTERVENTIONS_PROMPT",
    "QUICK_DIAGNOSTIC_PROMPT",
    "ROLE_ANALYSIS_PROMPT",
    "SEPARATOR_SYSTEM_PROMPT",
    "STANDARD_INTERVENTIONS_PROMPT",
    "STANDARD_ROLE_ANALYSIS_PROMPT",
    "assemble_prompt",
]
