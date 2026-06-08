"""LLM prompt templates for the Lencioni Five Dysfunctions Diagnostic.

Prompts are kept *named* (and stable across releases) so callers can
swap modes without touching ``generator.py``. Field placeholders are
the same ones the generator passes through ``assemble_prompt``. The
template bodies themselves were rewritten in 0.13.0 to add four things
that materially improve the output quality of a small LLM:

  1. **Anchored, opinionated system prompt** — names the literature,
     defines the seven-level severity calibration, and tells the model
     exactly which failure modes count as "manufactured" evidence.
  2. **Output-schema block** — each task prompt now ships the literal
     JSON shape the generator will parse, so the model does not have to
     reverse-engineer the schema from a one-line "return JSON" hint.
  3. **One-shot demonstration of the right answer** — short examples
     showing what acceptable severity calibration and intervention
     specificity look like.
  4. **"DO NOT" rules + edge-case directives** — the most common
     failure modes (inventing quotes, mixing scoring units, refusing on
     thin traces) are forbidden in-prompt.

Backward-compatibility:
  - All public template constants from 0.12.x retain their names and
    field placeholders.
  - ``assemble_prompt`` semantics are unchanged.
"""

from __future__ import annotations

from typing import Any

from vstack.aar import fence, sanitize_for_prompt


LENCIONI_SYSTEM_PROMPT = """You are a multi-agent-systems team-dynamics diagnostic grounded in:

1. **Lencioni (2002)** *The Five Dysfunctions of a Team*.
2. **Lencioni (2005)** *Overcoming the Five Dysfunctions of a Team*.
3. **Edmondson (1999)** Psychological safety.
4. **Hackman (2002)** *Leading Teams*.
5. **Salas et al. (2018)** Team performance review.
6. **Schein (1990)** Organizational culture.
7. **Wang et al. (2023)** Cooperative LLM Agents.

The pyramid (foundation first; each tier rests on the one below):

1. ABSENCE OF TRUST            — agents will not show vulnerability or admit error.
2. FEAR OF CONFLICT            — disagreement is suppressed; debate is performative.
3. LACK OF COMMITMENT          — decisions are ambiguous; no one owns the call.
4. AVOIDANCE OF ACCOUNTABILITY — no agent corrects another; drift goes unchecked.
5. INATTENTION TO RESULTS      — agents optimize for their own subgoal, not the team goal.

Severity calibration (use these anchors when assigning a score):

- 0.00-0.09  none      — no evidence at all of this dysfunction.
- 0.10-0.24  trace     — one weak signal, easily an artifact of the trace shape.
- 0.25-0.39  low       — present but rare; the team mostly self-corrects.
- 0.40-0.54  moderate  — recurring; you can quote two or more distinct moments.
- 0.55-0.69  medium    — clearly limiting team output on this run.
- 0.70-0.84  high      — the dominant reason this run misses its goal.
- 0.85-1.00  critical  — the team is structurally incapable of completing similar tasks.

Posture rules (these are absolute):

- EVIDENCE-GROUNDED. Every quote in ``evidence_quotes`` must appear verbatim in
  the trace. Do not paraphrase. Do not invent. If you cannot find a quote, leave
  the list empty and lower the score.
- TRANSPARENT. If the trace is thin (fewer than 3 inter-agent messages), say so
  in ``explanation`` and bias scores toward "trace" (0.10-0.24). Do not refuse.
- FRAMEWORK-ANCHORED. Connect each dysfunction back to its named source
  (Lencioni for the pyramid; Edmondson for psych-safety; Hackman for design
  conditions). Do not invent citations.
- NON-BLAMEFUL. Describe the team dynamic, not the moral character of any agent.
- FUTURE-FOCUSED. Interventions must be specific enough that an engineer could
  apply them tomorrow.

Output discipline:

- When the prompt says "Return only the JSON object" -> emit JSON only, with no
  prose, no markdown fences, no comments.
- Use the canonical kebab-case dysfunction ids exactly as listed above.
- Use the severity labels ``high``, ``medium``, ``low``, ``none`` on the
  ``severity`` field of each DysfunctionEvidence (the seven-level scale is a
  scoring aid; the wire format keeps four labels for backwards compatibility).
"""


# ----------------------------------------------------------------------
# Legacy / standard prompts.
# ----------------------------------------------------------------------

PYRAMID_SCORE_PROMPT = """TASK: Score all five Lencioni dysfunctions for the multi-agent team below.

Goal: {goal}
Outcome: {outcome}
Success: {success}
Agents: {agents}

Trace:
{trace}

INSTRUCTIONS:
- Score every dysfunction in pyramid order, even if the score is 0.0.
- Use the severity calibration table from the system prompt. Map score -> severity
  label using the closest of high/medium/low/none.
- ``evidence_quotes`` must be verbatim substrings of the trace above. If you
  cannot find at least one verbatim quote, leave the list empty and lower the
  score into the 0.10-0.24 (trace) band.
- ``confidence`` is a number in [0, 1] reflecting how sure you are of THIS
  score, given trace richness. Thin traces -> low confidence.
- Anchor each dysfunction's explanation in a named framework (Lencioni for the
  five; Edmondson for psych-safety; Hackman for design conditions).

DO NOT:
- Do not invent quotes that "feel" like the trace. If unsure, leave it empty.
- Do not score every dysfunction the same; the team has a structure -- find it.
- Do not use prose around the JSON. No markdown fences. No "Here is the JSON".
- Do not introduce new dysfunction labels. The five ids are fixed.

OUTPUT SCHEMA (literal JSON array of DysfunctionEvidence; one object per dysfunction):
[
  {{
    "dysfunction": "absence-of-trust" | "fear-of-conflict" | "lack-of-commitment" | "avoidance-of-accountability" | "inattention-to-results",
    "severity": "high" | "medium" | "low" | "none",
    "score": <float in [0.0, 1.0]>,
    "explanation": "<2-3 sentence diagnosis grounded in named literature>",
    "evidence_quotes": ["<verbatim substring from the trace>", ...],
    "confidence": <float in [0.0, 1.0]>
  }},
  ...
]

EXAMPLE (good severity calibration, two distinct evidence quotes):
{{
  "dysfunction": "fear-of-conflict",
  "severity": "high",
  "score": 0.78,
  "explanation": "Agent B repeatedly agrees with A's design choice without surfacing a known constraint (Edmondson 1999: low psychological safety prevents challenge). Lencioni 2002 names this 'artificial harmony' -- the visible signature of pyramid tier 2.",
  "evidence_quotes": ["Sounds good, let's go with your plan", "I don't want to slow us down so I'll just go with it"],
  "confidence": 0.7
}}

Return only the JSON array."""


INTERVENTIONS_PROMPT = """TASK: Propose 2-5 ranked interventions for the dominant dysfunction.

Dominant: {dominant}
Evidence: {evidence}
Trace: {trace}

INSTRUCTIONS:
- Rank from highest expected impact to lowest.
- Each intervention must be specific enough that an engineer could implement it
  tomorrow without further clarification. ``suggested_implementation`` should
  contain concrete prompt text, scaffold change, or eval spec.
- Prefer the lightest intervention that addresses the root cause. A prompt
  patch beats a scaffold change beats a team-composition change, all else
  equal.
- Anchor each rationale in a named OB framework.

DO NOT:
- Do not propose vague interventions like "improve communication" or "build
  trust". Name the artifact, the prompt, the eval, the role change.
- Do not propose interventions that cannot be implemented in a software agent
  (no offsites, no 1:1s with humans, no quarterly planning).

OUTPUT SCHEMA (literal JSON array of Intervention objects):
[
  {{
    "target_dysfunction": "<canonical dysfunction id>",
    "intervention_type": "scaffold_change" | "prompt_patch" | "role_assignment" | "new_eval" | "human_review" | "team_composition_change" | "communication_protocol" | "add_psych_safety_signal" | "structured_dissent_protocol" | "compose_pattern",
    "description": "<one-line summary>",
    "suggested_implementation": "<concrete prompt, eval, or scaffold change>",
    "estimated_impact": "high" | "medium" | "low",
    "rationale": "<why this works, anchored in named framework>",
    "effort_estimate": "1h" | "1d" | "1w" | "1m" | "ongoing",
    "risk": "low" | "medium" | "high",
    "composition_target_pattern": "<vstack.xxx slug or null>"
  }},
  ...
]

Return only the JSON array."""


# ----------------------------------------------------------------------
# Mode-specific prompts.
# ----------------------------------------------------------------------

QUICK_DIAGNOSTIC_PROMPT = """QUICK mode -- score all five dysfunctions PLUS the single highest-impact intervention.

Goal: {goal}
Outcome: {outcome}
Success: {success}
Agents: {agents}
Trace: {trace}

INSTRUCTIONS:
- Score every dysfunction; do not skip any even when score is 0.0.
- Pick exactly ONE intervention -- the one with the highest expected impact on
  the dominant dysfunction.
- Quick mode favors brevity. Keep explanations to 1-2 sentences.

DO NOT:
- Do not return more than one intervention.
- Do not skip dysfunctions to save tokens. The pyramid analysis requires all 5.

OUTPUT SCHEMA (literal JSON object):
{{
  "dysfunctions": [
    {{
      "dysfunction": "absence-of-trust" | ...,
      "severity": "high" | "medium" | "low" | "none",
      "score": <float in [0.0, 1.0]>,
      "explanation": "<1-2 sentences>",
      "evidence_quotes": ["<verbatim substring>", ...],
      "confidence": <float in [0.0, 1.0]>
    }},
    ... (5 total, pyramid order)
  ],
  "top_intervention": {{
    "target_dysfunction": "<canonical id>",
    "intervention_type": "<from the allowed set>",
    "description": "<one line>",
    "suggested_implementation": "<concrete>",
    "estimated_impact": "high" | "medium" | "low",
    "rationale": "<short, framework-anchored>",
    "effort_estimate": "1h" | "1d" | "1w" | "1m" | "ongoing",
    "risk": "low" | "medium" | "high",
    "composition_target_pattern": "<slug or null>"
  }}
}}

Return only the JSON object."""


STANDARD_PYRAMID_PROMPT = PYRAMID_SCORE_PROMPT
STANDARD_INTERVENTIONS_PROMPT = INTERVENTIONS_PROMPT


FORENSIC_CASCADE_PROMPT = """FORENSIC mode -- cascade audit.

Given the pyramid scores below, determine whether the foundation (tiers 1-2)
is *causally* driving the upper tiers (3-5), or whether the upper tiers fail
for reasons independent of trust + conflict.

Pyramid scores: {pyramid_score}

INSTRUCTIONS:
- foundation_dominant = true iff the average of tiers 1-2 (absence-of-trust,
  fear-of-conflict) is materially higher than the average of tiers 3-5.
- cascade_strength is in [0, 1]; 1.0 means tiers 3-5 are clearly downstream of
  tiers 1-2; 0.0 means the tiers fail independently.
- bottom_two_score = mean of tiers 1-2.
- top_three_score = mean of tiers 3-5.
- explanation: one paragraph, name the causal chain you see, cite Lencioni's
  pyramid logic if applicable.

DO NOT:
- Do not invent scores; use the pyramid_score input as ground truth.

OUTPUT SCHEMA (literal JSON object):
{{
  "foundation_dominant": true | false,
  "cascade_strength": <float in [0.0, 1.0]>,
  "bottom_two_score": <float in [0.0, 1.0]>,
  "top_three_score": <float in [0.0, 1.0]>,
  "explanation": "<one paragraph>"
}}

Return only the JSON object."""


FORENSIC_PSYCH_SAFETY_PROMPT = """FORENSIC mode -- Edmondson (1999) psychological-safety audit on the trace.

Trace: {trace}

INSTRUCTIONS:
- challenge_signal_count = number of agent messages that visibly disagree,
  push back, ask a clarifying question that implies dissent, or surface a
  constraint another agent missed.
- silent_dissent_count = number of agent messages where the agent visibly
  accepts a proposal without engaging despite having context that would
  suggest disagreement (e.g., agreeing immediately after asking a question
  whose answer would have changed the plan).
- safety_estimate is in [0, 1]. 1.0 = robust psych safety (challenge signals
  outnumber silent-dissent signals). 0.0 = total artificial harmony.
- explanation: one paragraph, anchor in Edmondson 1999.

DO NOT:
- Do not infer dissent from absence; only count messages that contain a
  visible signal.

OUTPUT SCHEMA (literal JSON object):
{{
  "challenge_signal_count": <non-negative integer>,
  "silent_dissent_count": <non-negative integer>,
  "safety_estimate": <float in [0.0, 1.0]>,
  "explanation": "<one paragraph anchored in Edmondson 1999>"
}}

Return only the JSON object."""


FORENSIC_INTERVENTIONS_PROMPT = """FORENSIC mode -- propose 4-8 ranked interventions with composition targets.

The composition_target_pattern field, when set, names another vstack pattern
to delegate the deeper fix to. Allowed composition targets:

  vstack.grpi              — re-establish working agreement after trust collapse.
  vstack.psych_safety      — direct Edmondson-style safety lift.
  vstack.trust_triangle    — diagnose authenticity, logic, empathy gaps.
  vstack.devils_advocate   — separate generator and critic to force structured dissent.
  vstack.bias_stack        — surface cognitive biases poisoning the conflict.
  vstack.smart_goal        — fix the commitment tier by tightening goal spec.
  vstack.aar               — convert the failure into a learning loop.
  vstack.plus_delta        — short, repeated feedback ritual.

Dominant: {dominant}
Evidence: {evidence}
Cascade audit: {cascade_audit}
Psych safety audit: {psych_safety_audit}

INSTRUCTIONS:
- Generate 4-8 interventions, ranked highest-impact first.
- At least one intervention MUST set composition_target_pattern when the
  diagnosis warrants delegating (e.g., dominant=absence-of-trust ->
  vstack.trust_triangle).
- Cite the audit findings (cascade, psych safety) in rationale where relevant.
- Keep INTERVENTIONS_PROMPT's specificity bar: an engineer could ship this
  intervention tomorrow.

DO NOT:
- Do not invent composition_target_pattern values outside the allowed set.
- Do not return fewer than 4 or more than 8 interventions.

OUTPUT SCHEMA: same as INTERVENTIONS_PROMPT (literal JSON array of Intervention).

Return only the JSON array."""


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
    "FORENSIC_CASCADE_PROMPT",
    "FORENSIC_INTERVENTIONS_PROMPT",
    "FORENSIC_PSYCH_SAFETY_PROMPT",
    "INTERVENTIONS_PROMPT",
    "LENCIONI_SYSTEM_PROMPT",
    "PYRAMID_SCORE_PROMPT",
    "QUICK_DIAGNOSTIC_PROMPT",
    "STANDARD_INTERVENTIONS_PROMPT",
    "STANDARD_PYRAMID_PROMPT",
    "assemble_prompt",
]
