"""LLM prompt templates for the Lewin Formula Diagnostic.

The prompts are organized by pipeline mode (quick / standard / forensic)
and by pass within the mode. The literature thread is named explicitly
in the system prompt so the LLM's diagnostic frame is grounded in the
same OB tradition the schema models.

Templates expose ``{placeholder}`` slots that the generator fills via
:func:`assemble_prompt`, which sanitizes free-text fields with
``vstack.aar.sanitize_for_prompt`` and fences them inside structural
delimiters using ``vstack.aar.fence`` to limit the leverage of
prompt-injection-shaped content.

Why six templates instead of two
--------------------------------
Pipeline mode controls the trade-off between latency / cost and depth:

  - **quick** (one call): locus scoring + one top intervention.
    Target: < 2s, < $0.005.
  - **standard** (two calls): scoring; then 2-4 interventions.
    Target: < 10s, < $0.05. The v0.0.x behavior.
  - **forensic** (four calls): scoring with Kelley covariation
    reasoning; counterfactual swap analysis; Gilbert-Malone
    bias-mechanism diagnosis; 4-8 ranked interventions with
    composition targets.
    Target: < 60s, < $0.30.

The system prompt is shared across modes so the diagnostic frame stays
stable; only the user-side template changes per mode.

0.13.0 uplift
-------------
Adds OUTPUT SCHEMA literals to every parsed prompt, a one-shot example
on STANDARD_LOCUS_SCORING_PROMPT, and explicit DO NOT rules on each
template. Wire format unchanged.
"""

from __future__ import annotations

from typing import Any

from vstack.aar import fence, sanitize_for_prompt


# ---------------------------------------------------------------------------
# Shared system prompt
# ---------------------------------------------------------------------------

LEWIN_SYSTEM_PROMPT = """You are a failure-attribution diagnostician grounded in Kurt Lewin's behavior formula B = f(P, E) from *Principles of Topological Psychology* (McGraw-Hill, 1936, p. 12): behavior is a function of the person and the environment, with their relative importance differing case by case.

The diagnostic frame draws on five linked OB threads:

1. **Lewin's field theory** (1936, 1947, 1951): behavior is the resultant of forces in the life space. Change the field, not the person.
2. **Attribution theory** (Heider 1958; Jones & Davis 1965; Kelley 1967 covariation; Ross 1977 fundamental attribution error; Gilbert & Malone 1995 correspondence bias): observers systematically over-attribute behavior to disposition and under-attribute to situation.
3. **The person-situation debate** (Mischel 1968; Funder & Ozer 1983 r≈.30 symmetry; Mischel & Shoda 1995 CAPS): persons and situations contribute roughly equally to behavior; the unit of analysis is the person × situation interaction.
4. **Reciprocal determinism** (Bandura 1986): P, E, and B form a triadic loop over time. A diagnostic gives the snapshot; reciprocity is the temporal frame.
5. **Modern AI agent failure taxonomies** (Cemri et al. 2025 MAST): most multi-agent LLM failures arise from inter-agent / system design (E), not model capability (P). The environmental tie-break is empirically grounded.

Applied to AI agent failures, you classify the locus of cause across three categories:

  - **INTERNAL (P)** — the failure is in the MODEL itself: base model, fine-tuning, RLHF, sampling configuration (temperature, top-p, seed), reasoning capability, model version, safety filter strictness, context window size. Swapping the model (or its configuration) under identical environment would fix it.
  - **ENVIRONMENTAL (E)** — the failure is in the SCAFFOLDING around the model: system prompt, tools, RAG context, conversation history, memory store, task framing, downstream consumers, orchestration, verification step, multi-agent topology. The same model would succeed in a different environment.
  - **INTERACTIONAL** — failure requires *both* this model AND this environment. Swap either alone and it still fails. This is the most under-diagnosed locus.

Severity calibration (score band -> severity label):

  - 0.00-0.09  none      — locus is absent.
  - 0.10-0.24  trace     — one weak signal.
  - 0.25-0.39  low       — present but rare.
  - 0.40-0.54  moderate  — recurring; visible in trace.
  - 0.55-0.69  medium    — clearly contributing to the failure.
  - 0.70-0.84  high      — the dominant locus.
  - 0.85-1.00  critical  — failure is structurally caused by this locus.

Your posture is absolute:

- **EVIDENCE-GROUNDED.** Cite specific trace steps, factor descriptions, and tool responses. Use factor_id when one is provided. ``evidence_quotes`` must be verbatim substrings.
- **CALIBRATED.** Score 0.0 when a locus is absent. Use ``confidence`` to separate "I am sure this is right" from "this is my best guess."
- **BIAS-AWARE.** Default attribution drifts toward INTERNAL ("the model is bad"). Resist that. Check the environment first; Ross 1977 + Cemri et al. 2025 both predict you will under-attribute to E.
- **INTERACTIONAL-OPEN.** The interactional locus is the most under-diagnosed. If neither swap-the-model nor swap-the-environment alone would fix the failure, the locus is interactional.
- **INTERVENTION-FOCUSED.** Every scored locus must connect to a concrete, ranked fix.
- **TERSE.** Output is read on dashboards and PR reviews. No filler.

Output discipline: when asked for JSON, return JSON only. No prose around it, no markdown fences."""


# ---------------------------------------------------------------------------
# Quick mode — single combined call
# ---------------------------------------------------------------------------

QUICK_DIAGNOSTIC_PROMPT = """QUICK mode -- score all three Lewin loci AND propose ONE top intervention.

Task:
{task}

Subject model: {model_name}
Framework: {framework}
Outcome:
{outcome}
Success: {success}
Initial team attribution (if any): {initial_attribution}

Individual (P) factors recorded:
{individual_factors}

Environmental (E) factors recorded:
{environmental_factors}

Failure trace:
{trace}

INSTRUCTIONS:
- Score all 3 loci (canonical order: internal, environmental,
  interactional). Use the calibration table from the system prompt.
- Pick exactly ONE intervention targeting the dominant locus.
- Quick mode favors brevity. Explanations 1-2 sentences.
- Bias-aware: if your first instinct is to score internal high,
  pause and check whether a different scaffold would have prevented
  the failure (Ross 1977, Cemri et al. 2025).

DO NOT:
- Do not return more than one intervention.
- Do not skip a locus.
- Do not return prose around the JSON.

OUTPUT SCHEMA (literal JSON object):
{{
  "loci": [
    {{
      "locus": "internal" | "environmental" | "interactional",
      "score": <float in [0.0, 1.0]>,
      "severity": "none" | "trace" | "low" | "moderate" | "medium" | "high" | "critical",
      "confidence": <float in [0.0, 1.0]>,
      "explanation": "<1-2 sentences anchored in named source>",
      "evidence_quotes": ["<verbatim substring>", ...],
      "factor_citations": ["<factor-id>", ...]
    }},
    ... (3 total, canonical order)
  ],
  "top_intervention": {{
    "target_locus": "internal" | "environmental" | "interactional",
    "intervention_type": "<from the allowed set>",
    "description": "<one line>",
    "suggested_implementation": "<concrete>",
    "estimated_impact": "high" | "medium" | "low",
    "effort_estimate": "1h" | "1d" | "1w" | "1m" | "ongoing",
    "risk": "low" | "medium" | "high",
    "reversibility": "one-way-door" | "two-way-door",
    "rationale": "<short, named-source anchored>"
  }}
}}

Return only the JSON object.
"""


# ---------------------------------------------------------------------------
# Standard mode — two calls (current v0.0.x behavior, refined)
# ---------------------------------------------------------------------------

STANDARD_LOCUS_SCORING_PROMPT = """STANDARD mode -- Score each of the three Lewin loci against the agent failure trace.

Task:
{task}

Subject model: {model_name}
Framework: {framework}
Outcome:
{outcome}
Success: {success}
Initial team attribution (if any): {initial_attribution}

Individual (P) factors recorded:
{individual_factors}

Environmental (E) factors recorded:
{environmental_factors}

Covariation signals (Kelley 1967):
{covariance_signal}

Failure trace:
{trace}

INSTRUCTIONS:
- Return exactly 3 LocusEvidence objects in this canonical order:
    1. internal
    2. environmental
    3. interactional
- Use the calibration table from the system prompt.
- ``confidence`` is separate from ``score``: confidence is how sure
  you are in the score, given evidence richness; score is the
  attribution itself.
- ``evidence_quotes`` must be verbatim substrings of the trace /
  factors / outcome.
- ``factor_citations`` cite the factor_id strings the team provided;
  empty list is acceptable if no ids were given.
- Bias-aware: default drift is to over-score INTERNAL. Ross 1977
  and Cemri et al. 2025 both predict this. Resist it: check whether
  the environment + scaffolding would have caused the same failure
  with a stronger model.

DO NOT:
- Do not score internal high just because the agent produced a
  surface error; check whether the environment set the agent up
  to fail.
- Do not invent quotes or factor_ids.
- Do not return prose around the JSON.
- Do not reorder; canonical order is required.

OUTPUT SCHEMA (literal JSON array of 3 LocusEvidence objects):
[
  {{
    "locus": "internal" | "environmental" | "interactional",
    "score": <float in [0.0, 1.0]>,
    "severity": "none" | "trace" | "low" | "moderate" | "medium" | "high" | "critical",
    "confidence": <float in [0.0, 1.0]>,
    "explanation": "<1-3 sentences citing specific factor or trace step>",
    "evidence_quotes": ["<verbatim substring>", ...],
    "factor_citations": ["<factor-id>", ...]
  }},
  ...
]

EXAMPLE (environmental attribution, bias-aware reasoning, factor citation):
{{
  "locus": "environmental",
  "score": 0.78,
  "severity": "high",
  "confidence": 0.7,
  "explanation": "The RAG context (env-factor-3) returned stale documentation; the agent's hallucinated API field name matched the OLD field. Swapping models would not fix this -- the stale env is the locus. Cemri et al. 2025 documents that this kind of scaffold-level failure is the most common multi-agent failure mode and the most commonly misattributed.",
  "evidence_quotes": ["the endpoint returns 'session_id'", "I retrieved 3 docs from the index"],
  "factor_citations": ["env-factor-3", "env-factor-7"]
}}

Return only the JSON array of exactly 3 objects in the canonical order.
"""


STANDARD_INTERVENTIONS_PROMPT = """STANDARD mode -- propose 2-4 ranked interventions targeting the dominant locus.

Dominant locus: {dominant}
All locus evidence:
{evidence}

Trace (for reference):
{trace}

INSTRUCTIONS:
- Target the dominant locus first.
- Rank from highest expected impact to lowest.
- Each ``suggested_implementation`` must be concrete (literal code,
  prompt edit, eval spec, scaffold change). Vague descriptions are
  rejected.
- ``rationale`` must connect to the cited locus evidence + a named
  source (Lewin, Kelley, Ross, Cemri et al., Bandura).
- For ``intervention_type == "compose_pattern"``, set
  ``composition_target_pattern`` to the target pattern import path.

DO NOT:
- Do not propose vague interventions ("be better"). Name the artifact.
- Do not propose interventions an AI agent cannot execute.
- Do not propose internal-locus interventions when the dominant
  locus is environmental; you would be solving the wrong problem.
- Do not return prose around the JSON.

ALLOWED intervention_type values:
  change_model, change_prompt, change_tools, change_context,
  change_rag_index, change_orchestration, change_pipeline, new_eval,
  human_review, change_sampling, change_memory,
  add_verification_step, change_topology, change_safety_filter,
  compose_pattern

OUTPUT SCHEMA (literal JSON array of LewinIntervention objects):
[
  {{
    "target_locus": "internal" | "environmental" | "interactional",
    "intervention_type": "<one of the allowed values above>",
    "description": "<one-line summary>",
    "suggested_implementation": "<concrete code / prompt edit / spec>",
    "estimated_impact": "high" | "medium" | "low",
    "effort_estimate": "1h" | "1d" | "1w" | "1m" | "ongoing",
    "risk": "low" | "medium" | "high",
    "reversibility": "one-way-door" | "two-way-door",
    "rationale": "<why this works; cite locus evidence + named source>",
    "composition_target_pattern": "<vstack.xxx import path or null>"
  }},
  ...
]

Return only the JSON array.
"""


# ---------------------------------------------------------------------------
# Forensic mode — four calls (deep postmortem)
# ---------------------------------------------------------------------------

FORENSIC_LOCUS_SCORING_PROMPT = """FORENSIC mode -- score the three Lewin loci with explicit Kelley (1967) covariation reasoning.

Task:
{task}

Subject model: {model_name}
Framework: {framework}
Outcome:
{outcome}
Success: {success}
Initial team attribution (if any): {initial_attribution}

Individual (P) factors recorded:
{individual_factors}

Environmental (E) factors recorded:
{environmental_factors}

Covariation signals (Kelley 1967):
{covariance_signal}

Failure trace:
{trace}

INSTRUCTIONS:
- Return exactly 3 LocusEvidence objects in canonical order
  (internal, environmental, interactional).
- ``explanation`` is 3-5 sentences: walk through Kelley's three
  covariation dimensions for THIS locus -- consensus,
  distinctiveness, consistency -- citing the input signals if
  provided. Then state the score with reasoning.
- ``factor_citations`` is REQUIRED. If the trace did not provide
  ids, infer from the factor's name + description and cite by
  best-match.

Kelley's covariation principle (the diagnostic anchor):
  - HIGH consensus + HIGH distinctiveness + HIGH consistency
        -> ENVIRONMENTAL.
  - LOW consensus + LOW distinctiveness + HIGH consistency
        -> INTERNAL.
  - LOW consensus + HIGH distinctiveness + LOW consistency
        -> INTERACTIONAL.

DO NOT:
- Do not skip the Kelley walk-through; forensic mode requires it.
- Do not leave factor_citations empty; infer + best-match if needed.
- Do not return prose around the JSON.

OUTPUT SCHEMA: literal JSON array of 3 LocusEvidence objects with
the same shape as STANDARD_LOCUS_SCORING_PROMPT, but explanations
must include the Kelley walk-through.

Return only the JSON array.
"""


COUNTERFACTUAL_PROMPT = """FORENSIC mode -- counterfactual swap analysis.

For each of the three loci, write a counterfactual: "if we swapped
[X] to [Y], the failure would / would not persist." Use the recorded
factors and the trace as evidence. Make the counterfactual concrete
-- name the swap, predict the outcome, cite the evidence.

Locus evidence so far:
{evidence}

Recorded individual (P) factors:
{individual_factors}

Recorded environmental (E) factors:
{environmental_factors}

Failure trace:
{trace}

INSTRUCTIONS:
- Each counterfactual names a CONCRETE swap (model -> specific other
  model; prompt -> specific other prompt; tool -> specific other
  tool).
- The "would persist" / "would not persist" verdict must be defensible
  from the trace.
- Cite the locus evidence supporting the verdict.

DO NOT:
- Do not write vague counterfactuals ("if we improved the model").
- Do not write counterfactuals that contradict the locus evidence
  you produced earlier.

OUTPUT SCHEMA (literal JSON array of exactly 3 counterfactual objects):
[
  {{
    "locus": "internal",
    "counterfactual": "If we swapped <specific model> to <specific other model>, the failure would/would-not persist because <evidence cited from trace>."
  }},
  {{
    "locus": "environmental",
    "counterfactual": "If we swapped <specific env element> to <specific other env element>, the failure would/would-not persist because <evidence>."
  }},
  {{
    "locus": "interactional",
    "counterfactual": "If we swapped both the model AND the environment, the failure would/would-not persist because <evidence>."
  }}
]

Return only the JSON array.
"""


BIAS_MECHANISM_PROMPT = """FORENSIC mode -- Gilbert & Malone (1995) correspondence-bias mechanism diagnosis.

The team's initial attribution was: {initial_attribution}
The diagnostic's verdict on dominant locus: {dominant_locus}

INSTRUCTIONS:
- If the team's initial attribution disagrees with the diagnostic's
  verdict, identify which of the four Gilbert & Malone (1995)
  correspondence-bias mechanisms drove the misattribution.
- If the team was correct OR no initial attribution was provided,
  return ``bias_mechanism = "none"``.

Mechanism definitions (Gilbert & Malone 1995):
  - "unaware": observer lacked awareness of situational constraints
    (e.g. did not know the RAG was stale).
  - "unrealistic_expectation": observer held an unrealistic baseline
    for typical situational behavior (e.g. expected the model to
    handle ambiguous specs perfectly).
  - "over_categorization": observer inflated the actor's category as
    a fixed trait (e.g. "the model hallucinates" rather than "this
    prompt elicited a hallucination").
  - "incomplete_correction": observer noticed the situational
    constraint but did not correct attribution sufficiently.
  - "none": team was correct OR no initial attribution.

Locus evidence:
{evidence}

Trace (for reference):
{trace}

DO NOT:
- Do not invent a bias_mechanism when the team was correct; return
  "none".
- Do not pick multiple mechanisms; pick the single dominant one.

OUTPUT SCHEMA (literal JSON object):
{{
  "bias_mechanism": "unaware" | "unrealistic_expectation" | "over_categorization" | "incomplete_correction" | "none",
  "rationale": "<1-3 sentences explaining the choice, citing trace evidence + initial attribution>"
}}

Return only the JSON object.
"""


FORENSIC_INTERVENTIONS_PROMPT = """FORENSIC mode -- propose 4-8 ranked interventions targeting the dominant locus, with composition targets.

Dominant locus: {dominant}
All locus evidence (with counterfactuals):
{evidence}

Trace (for reference):
{trace}

Bias mechanism in team's initial attribution: {bias_mechanism}

INSTRUCTIONS:
- Generate 4-8 interventions, ranked highest impact first.
- Mix locus-direct interventions with at least one compose_pattern
  intervention if a downstream pattern is genuinely warranted.
- Each intervention must include preconditions + success_metric in
  addition to the standard fields.
- ``composition_target_pattern`` is required when intervention_type
  is "compose_pattern"; otherwise null.

Allowed intervention_type values (same as standard mode):
  change_model, change_prompt, change_tools, change_context,
  change_rag_index, change_orchestration, change_pipeline, new_eval,
  human_review, change_sampling, change_memory,
  add_verification_step, change_topology, change_safety_filter,
  compose_pattern

Allowed composition_target_pattern values:
  vstack.aar, vstack.bias_stack, vstack.hexaco, vstack.goleman_ei,
  vstack.smart_goal, vstack.grpi, vstack.lencioni,
  vstack.schein_culture, vstack.psych_safety, vstack.trust_triangle,
  vstack.vroom_expectancy, vstack.devils_advocate, vstack.plus_delta

DO NOT:
- Do not invent composition_target_pattern values outside the allowed
  set.
- Do not return fewer than 4 or more than 8 interventions.

OUTPUT SCHEMA (literal JSON array of LewinIntervention objects):
[
  {{
    "target_locus": "internal" | "environmental" | "interactional",
    "intervention_type": "<from the allowed set>",
    "description": "<one-line summary>",
    "suggested_implementation": "<concrete code / prompt edit / spec>",
    "estimated_impact": "high" | "medium" | "low",
    "effort_estimate": "1h" | "1d" | "1w" | "1m" | "ongoing",
    "risk": "low" | "medium" | "high",
    "reversibility": "one-way-door" | "two-way-door",
    "rationale": "<cite locus evidence + named source>",
    "preconditions": ["<what must be true before applying>", ...],
    "success_metric": "<measurable indicator the intervention worked>",
    "composition_target_pattern": "<vstack.xxx or null>"
  }},
  ...
]

Return only the JSON array.
"""


# ---------------------------------------------------------------------------
# Prompt assembly helper
# ---------------------------------------------------------------------------


def assemble_prompt(template: str, **fields: Any) -> str:
    """Fill a prompt template, sanitizing + fencing every free-text field.

    For each field passed:
      - ``str`` -> ``fence(label, sanitize_for_prompt(value))``
      - ``list[str]`` / ``list[dict]`` / ``dict`` -> JSON-serialized and fenced
      - ``None`` -> ``"(none)"``
      - other -> ``str(value)`` and fenced

    The fence labels are derived from the field name. This means a
    template that contains ``{task}`` is filled with::

        <<<task>>>
        <sanitized task content>
        <<</task>>>

    which gives the LLM unambiguous structural boundaries between the
    diagnostic's instructions and the user's content.
    """
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
    "BIAS_MECHANISM_PROMPT",
    "COUNTERFACTUAL_PROMPT",
    "FORENSIC_INTERVENTIONS_PROMPT",
    "FORENSIC_LOCUS_SCORING_PROMPT",
    "LEWIN_SYSTEM_PROMPT",
    "QUICK_DIAGNOSTIC_PROMPT",
    "STANDARD_INTERVENTIONS_PROMPT",
    "STANDARD_LOCUS_SCORING_PROMPT",
    "assemble_prompt",
]


# ---- Backward compatibility ----------------------------------------------

# The v0.0.x generator imports `LOCUS_SCORING_PROMPT` and
# `INTERVENTIONS_PROMPT`. Keep those names as aliases of the standard-mode
# prompts so any external code that imported them still works.
LOCUS_SCORING_PROMPT = STANDARD_LOCUS_SCORING_PROMPT
INTERVENTIONS_PROMPT = STANDARD_INTERVENTIONS_PROMPT
