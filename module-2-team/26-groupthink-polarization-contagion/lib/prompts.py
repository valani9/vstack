"""LLM prompts for the Groupthink / Polarization / Contagion (Debate
Pathology) diagnostic.

Anchored in:
  - Janis (1972) *Victims of Groupthink* — premature consensus,
    dissent suppression, illusion of unanimity.
  - Stoner (1968) "Risky Shift and Group Discussion."
  - Sunstein (2002) "The Law of Group Polarization."
  - Hatfield, Cacioppo & Rapson (1993) *Emotional Contagion*.
  - Schwenk (1990) on structured dissent.

The detector identifies which of three canonical debate pathologies
dominated a multi-agent debate:

  - GROUPTHINK   — premature convergence + dissent suppression +
                   illusion of unanimity.
  - POLARIZATION — each round pushes positions toward an extreme
                   instead of toward common ground.
  - CONTAGION    — tone propagates across turns; tone dominates
                   content quality.

The 0.13.0 uplift adds OUTPUT SCHEMA literals, a one-shot example
on PATHOLOGY_SCORING_PROMPT, explicit DO NOT rules, and severity
calibration.
"""

from __future__ import annotations

from typing import Any

from vstack.aar import fence, sanitize_for_prompt


DEBATE_SYSTEM_PROMPT = """You are a debate-pathology diagnostician for multi-agent systems,
grounded in:

  - Janis (1972) *Victims of Groupthink*.
  - Stoner (1968) "Risky Shift and Group Discussion."
  - Sunstein (2002) "The Law of Group Polarization."
  - Hatfield, Cacioppo & Rapson (1993) *Emotional Contagion*.
  - Schwenk (1990) on structured dissent.

The three canonical debate pathologies (each a distinct failure
signature):

  - GROUPTHINK    — Janis 1972. Premature convergence + dissent
                    suppression + illusion of unanimity. Symptoms:
                    rapid agreement on the first viable proposal;
                    surface-level "any concerns?" with no concerns
                    raised; visible self-censorship after one
                    dissenting voice is shut down.
  - POLARIZATION  — Stoner 1968 + Sunstein 2002. Each round of debate
                    pushes positions toward an extreme rather than
                    toward common ground. Symptoms: positions in
                    round N are MORE extreme than the same agent's
                    positions in round 1; agents stake out tribal
                    positions instead of weighing trade-offs.
  - CONTAGION     — Hatfield/Cacioppo/Rapson 1993. Tone propagates
                    across turns; tone dominates content. Symptoms:
                    when one agent gets heated, others mirror;
                    decisions are driven by emotional energy rather
                    than by evaluation of the substance.

Central insight: these three pathologies are DISTINCT.
  - Rapid agreement WITHOUT extremity escalation -> groupthink.
  - Extremity escalation WITH visible disagreement -> polarization.
  - Tone-driven shifts INDEPENDENT of content -> contagion.

Severity calibration (score band -> severity label):

  - 0.00-0.09  none      — no signal.
  - 0.10-0.39  low       — present but minor.
  - 0.40-0.69  medium    — visible; one of the contributing factors.
  - 0.70-1.00  high      — the dominant pathology of this debate.

Posture (absolute):

  - EVIDENCE-GROUNDED. ``evidence_quotes`` must be verbatim
    substrings of the debate trace.
  - PATHOLOGY-SPECIFIC. Distinguish cleanly; do not score
    groupthink and polarization the same when only one signature
    is present.
  - INTERVENTION-FOCUSED. Diagnosis without prescription is wasted.
  - TRANSPARENT. Thin debate (fewer than 3 inter-agent rounds) ->
    reduce confidence, bias toward "low" band. Do not refuse to
    produce a diagnosis.

Output discipline: when the prompt says "return only the JSON ...",
emit JSON only. No prose. No markdown fences.
"""


# ----------------------------------------------------------------------
# Standard / legacy prompts.
# ----------------------------------------------------------------------

PATHOLOGY_SCORING_PROMPT = """TASK: Score each of the three debate pathologies against this trace.

Task: {task}
Agents: {agents}
Final decision: {final_decision}
Outcome: {outcome}
Success: {success}

Debate:
{trace}

INSTRUCTIONS:
- Return exactly 3 PathologyEvidence objects in this canonical order:
    1. groupthink
    2. polarization
    3. contagion
- Use the calibration table from the system prompt.
- ``evidence_quotes`` must be verbatim substrings of the debate above.
- ``confidence`` is in [0, 1]; reflect debate-trace richness.
- Distinguish pathologies cleanly: rapid agreement = groupthink;
  extremity escalation = polarization; tone-driven shifts = contagion.

DO NOT:
- Do not invent quotes that "feel like" the debate.
- Do not score every pathology the same; the debate has a structure
  -- find it.
- Do not return prose around the JSON.
- Do not reorder; canonical order is required.

OUTPUT SCHEMA (literal JSON array of 3 PathologyEvidence objects):
[
  {{
    "pathology": "groupthink" | "polarization" | "contagion",
    "score": <float in [0.0, 1.0]>,
    "severity": "none" | "low" | "medium" | "high",
    "explanation": "<2-3 sentence diagnosis anchored in Janis 1972 / Sunstein 2002 / Hatfield et al. 1993>",
    "evidence_quotes": ["<verbatim substring from the debate>", ...],
    "confidence": <float in [0.0, 1.0]>
  }},
  ...
]

EXAMPLE (groupthink with classic Janis signature):
{{
  "pathology": "groupthink",
  "score": 0.74,
  "severity": "high",
  "explanation": "Round 1 surfaces three positions; round 2 has all four agents agreeing with agent A's frame; the only dissenting voice in round 2 is met with 'we already decided' and never returns. Janis 1972 names this the illusion-of-unanimity signature.",
  "evidence_quotes": ["I agree with A's framing", "we already decided this, let's move on", "yeah, agreed"],
  "confidence": 0.75
}}

Return only the JSON array of exactly 3 objects in the canonical order.
"""


INTERVENTIONS_PROMPT = """TASK: Propose 2-4 ranked interventions targeting the dominant pathology.

Dominant pathology: {dominant}
Debate quality: {quality}
Evidence:
{evidence}

Trace (reference):
{trace}

INSTRUCTIONS:
- Target the dominant pathology first.
- Rank from highest expected impact to lowest.
- Each ``suggested_implementation`` must be concrete (literal prompt
  text, scaffold spec, role assignment, eval spec).
- Anchor each rationale in a named source (Janis 1972 for groupthink,
  Sunstein 2002 / Stoner 1968 for polarization, Hatfield et al. 1993
  for contagion, Schwenk 1990 for the structured-dissent fix).

DO NOT:
- Do not propose generic "encourage more discussion" interventions.
- Do not propose interventions an AI agent cannot execute (no
  in-person facilitators, no Zoom).
- Do not return prose around the JSON.

ALLOWED intervention_type values:
  assign_devils_advocate, require_silent_vote, round_robin_dissent,
  diverse_seed_positions, anchor_to_base_rates, tone_normalization,
  cool_down_pause, external_arbiter, smaller_panel, secret_ballot,
  new_eval, human_review, compose_pattern

OUTPUT SCHEMA (literal JSON array of DebateIntervention objects):
[
  {{
    "target_pathology": "groupthink" | "polarization" | "contagion",
    "intervention_type": "<one of the allowed values above>",
    "description": "<one-line summary>",
    "suggested_implementation": "<concrete prompt / scaffold / role spec>",
    "estimated_impact": "high" | "medium" | "low",
    "rationale": "<why this works, anchored in named source>",
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

QUICK_DIAGNOSTIC_PROMPT = """QUICK mode -- score all three pathologies PLUS the single highest-impact intervention.

Task: {task}
Final decision: {final_decision}
Debate: {trace}

INSTRUCTIONS:
- Score all 3 pathologies (canonical order: groupthink, polarization,
  contagion). Do not skip any.
- Pick exactly ONE intervention targeting the dominant pathology.
- Quick mode favors brevity. Explanations 1-2 sentences.

DO NOT:
- Do not return more than one intervention.
- Do not skip a pathology.

OUTPUT SCHEMA (literal JSON object):
{{
  "pathologies": [
    {{
      "pathology": "groupthink" | "polarization" | "contagion",
      "score": <float in [0.0, 1.0]>,
      "severity": "none" | "low" | "medium" | "high",
      "explanation": "<1-2 sentences>",
      "evidence_quotes": ["<verbatim substring>", ...],
      "confidence": <float in [0.0, 1.0]>
    }},
    ... (3 total, canonical order)
  ],
  "top_intervention": {{
    "target_pathology": "<canonical pathology>",
    "intervention_type": "<from the allowed set>",
    "description": "<one line>",
    "suggested_implementation": "<concrete>",
    "estimated_impact": "high" | "medium" | "low",
    "rationale": "<short, named-source anchored>"
  }}
}}

Return only the JSON object.
"""


STANDARD_PATHOLOGY_SCORING_PROMPT = PATHOLOGY_SCORING_PROMPT
STANDARD_INTERVENTIONS_PROMPT = INTERVENTIONS_PROMPT


FORENSIC_CONVERGENCE_TIMELINE_PROMPT = """FORENSIC mode -- convergence timeline audit.

Debate: {trace}

INSTRUCTIONS:
- initial_position_diversity: in [0, 1]. 0 = all agents started with
  identical positions; 1 = fully diverse starting positions.
- final_position_diversity: same scale, applied to the final round.
- convergence_round: the round number at which positions effectively
  merged (or null if positions never converged).
- abrupt_convergence: true if the diversity drop across two
  consecutive rounds exceeds 0.5; otherwise false. Abrupt convergence
  is the Janis 1972 "illusion of unanimity" signature.
- explanation: one paragraph naming the convergence shape (gradual /
  abrupt / divergent) anchored in Janis 1972 or Sunstein 2002.

DO NOT:
- Do not treat agreement on procedural matters (turn order, format)
  as convergence; only count substantive positions.

OUTPUT SCHEMA (literal JSON object representing ConvergenceTimelineAudit):
{{
  "initial_position_diversity": <float in [0.0, 1.0]>,
  "final_position_diversity": <float in [0.0, 1.0]>,
  "convergence_round": <non-negative integer or null>,
  "abrupt_convergence": true | false,
  "explanation": "<one paragraph anchored in Janis 1972 or Sunstein 2002>"
}}

Return only the JSON object.
"""


FORENSIC_TONE_CASCADE_PROMPT = """FORENSIC mode -- tone cascade audit.

Debate: {trace}

INSTRUCTIONS:
- heated_turn_count: number of debate turns with elevated emotional
  charge (anger, frustration, aggressive certainty).
- calm_turn_count: number of debate turns with measured tone.
- tone_flip_count: number of times the dominant tone of the
  conversation flipped between calm and heated within consecutive
  turns. Hatfield/Cacioppo/Rapson 1993 flag rapid flips as the
  contagion signature.
- dominant_tone: one of calm / neutral / heated / anxious /
  enthusiastic / dismissive / unknown. The tone that occupied the
  most turns.
- cascade_strength: in [0, 1]. High when tone clusters consecutively
  (one agent's heat triggers the next agent's heat); low when each
  turn's tone is independent of the prior turn's tone.
- explanation: one paragraph anchored in Hatfield et al. 1993.

DO NOT:
- Do not infer tone from word count or message length alone; tone
  is about emotional charge, not verbosity.

OUTPUT SCHEMA (literal JSON object representing ToneCascadeAudit):
{{
  "heated_turn_count": <non-negative integer>,
  "calm_turn_count": <non-negative integer>,
  "tone_flip_count": <non-negative integer>,
  "dominant_tone": "calm" | "neutral" | "heated" | "anxious" | "enthusiastic" | "dismissive" | "unknown",
  "cascade_strength": <float in [0.0, 1.0]>,
  "explanation": "<one paragraph anchored in Hatfield et al. 1993>"
}}

Return only the JSON object.
"""


FORENSIC_INTERVENTIONS_PROMPT = """FORENSIC mode -- propose 4-8 ranked interventions with composition targets.

Allowed composition_target_pattern values:

  vstack.devils_advocate    — separate generator and critic; the
                              canonical fix for groupthink.
  vstack.bias_stack         — surface cognitive biases (confirmation,
                              anchoring) that feed polarization.
  vstack.psych_safety       — Edmondson safety lift when the
                              groupthink is rooted in fear of
                              speaking up.
  vstack.aar                — close the failure into a learning loop.
  vstack.group_decision     — formal group-decision protocol (Stasser
                              1985, hidden-profile literature) when
                              the debate process itself is dysfunctional.

Dominant pathology: {dominant}
Quality: {quality}
Evidence: {evidence}
Convergence audit: {convergence_audit}
Tone cascade audit: {tone_cascade_audit}

INSTRUCTIONS:
- Generate 4-8 interventions, ranked highest-impact first.
- At least one intervention MUST set composition_target_pattern when
  the diagnosis warrants delegation.
- Cite the audit findings in rationale.

DO NOT:
- Do not invent composition_target_pattern values outside the
  allowed set.
- Do not return fewer than 4 or more than 8 interventions.

OUTPUT SCHEMA: same as INTERVENTIONS_PROMPT (literal JSON array of
DebateIntervention).

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
    "DEBATE_SYSTEM_PROMPT",
    "FORENSIC_CONVERGENCE_TIMELINE_PROMPT",
    "FORENSIC_INTERVENTIONS_PROMPT",
    "FORENSIC_TONE_CASCADE_PROMPT",
    "INTERVENTIONS_PROMPT",
    "PATHOLOGY_SCORING_PROMPT",
    "QUICK_DIAGNOSTIC_PROMPT",
    "STANDARD_INTERVENTIONS_PROMPT",
    "STANDARD_PATHOLOGY_SCORING_PROMPT",
    "assemble_prompt",
]
