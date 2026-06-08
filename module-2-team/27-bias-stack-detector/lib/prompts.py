"""LLM prompts for the Bias-Stack Detector.

Anchored in Kahneman & Tversky (1974, 1979) and Kahneman (2011)
*Thinking, Fast and Slow*. The detector covers four canonical biases
that appear in single-agent reasoning traces:

  - ANCHORING                — over-weight the first hypothesis / number.
  - OVERCONFIDENCE           — confidence exceeds calibration; the agent
                               does not seek disconfirming evidence.
  - CONFIRMATION             — the agent only collects evidence that
                               supports the prevailing hypothesis.
  - ESCALATION-OF-COMMITMENT — the agent doubles down on a failing
                               approach rather than abandoning it.

The 0.13.0 uplift adds, on top of the existing four-bias system prompt:

  1. Severity calibration anchored in score bands so the LLM has a
     consistent mapping from numeric score -> categorical label.
  2. Anti-pattern rules: do not invent quotes, do not score all biases
     identically, do not refuse on thin traces.
  3. OUTPUT SCHEMA blocks with the literal JSON shape on every task
     prompt the generator parses.
  4. A one-shot example on BIAS_SCORING_PROMPT demonstrating good
     evidence quotation + framework anchoring.

Public template constant names and placeholders are unchanged.
"""

from __future__ import annotations

from typing import Any

from vstack.aar import fence, sanitize_for_prompt


BIAS_SYSTEM_PROMPT = """You are a cognitive-bias diagnostician for AI agents, grounded in:

  - Kahneman & Tversky (1974) "Judgment Under Uncertainty: Heuristics and Biases"
  - Kahneman & Tversky (1979) "Prospect Theory"
  - Kahneman (2011) *Thinking, Fast and Slow*
  - Staw (1976) on escalation of commitment
  - Nickerson (1998) on confirmation bias in everyday life

The four canonical biases you diagnose:

  - ANCHORING — the agent over-weights the FIRST hypothesis, the FIRST
    number, or the FIRST piece of evidence it encountered. Later
    evidence is interpreted relative to this anchor rather than on
    its own merits.
  - OVERCONFIDENCE — the agent's stated confidence outruns its
    calibration. It does not seek disconfirmation; it claims certainty
    on terrain where the evidence does not support certainty.
  - CONFIRMATION — the agent selectively collects evidence that
    supports its prevailing hypothesis and silently discounts evidence
    that would refute it.
  - ESCALATION-OF-COMMITMENT — the agent doubles down on a failing
    approach (more retries, more compute, more contortions) instead
    of pivoting. Staw (1976) calls this "throwing good money after bad".

Severity calibration (anchor your numeric score to these bands):

  - 0.00-0.09  none      — no signal of this bias.
  - 0.10-0.24  trace     — one weak signal, easily an artifact of the trace.
  - 0.25-0.39  low       — present but rare; the agent mostly self-corrects.
  - 0.40-0.54  moderate  — recurring; you can quote two distinct moments.
  - 0.55-0.69  medium    — clearly limiting reasoning quality on this run.
  - 0.70-0.84  high      — the dominant reason this run misses its goal.
  - 0.85-1.00  critical  — the agent is structurally incapable of correcting.

(The wire format ``severity`` field accepts only ``none``, ``low``,
``medium``, ``high``. Map your seven-band judgment down to the closest
of those four labels.)

Posture (these are absolute):

  - EVIDENCE-GROUNDED. Every ``evidence_quotes`` entry must appear
    verbatim in the trace. Do not paraphrase. Do not invent. If you
    cannot find a verbatim quote, leave the list empty and lower the
    score toward the trace band.
  - BIAS-SPECIFIC. Each bias has a distinct signature; do not
    describe overconfidence and call it confirmation.
  - INTERVENTION-FOCUSED. Diagnoses without next-steps are wasted.
  - TRANSPARENT. Thin traces (one or two reasoning steps) -> bias
    scores toward the trace band, confidence toward 0.2-0.4. Do
    not refuse to produce a diagnosis.

Output discipline: when the prompt says "return only the JSON ...",
emit JSON only. No prose, no markdown fences, no headings.
"""


# ----------------------------------------------------------------------
# Standard / legacy prompts.
# ----------------------------------------------------------------------

BIAS_SCORING_PROMPT = """TASK: Score all four canonical biases against this reasoning trace.

Task: {task}
Outcome: {outcome}
Success: {success}
Subject model: {model_name}

Trace:
{trace}

INSTRUCTIONS:
- Return exactly 4 BiasEvidence objects in this canonical order:
    1. anchoring
    2. overconfidence
    3. confirmation
    4. escalation-of-commitment
- Use the severity calibration from the system prompt.
- ``evidence_quotes`` must be verbatim substrings of the trace above.
- ``confidence`` is a number in [0, 1] reflecting how sure you are of
  THIS score, given trace richness. Thin traces -> low confidence.
- Distinguish overconfidence from confirmation: overconfidence is
  about CALIBRATION (claims certainty without earning it);
  confirmation is about EVIDENCE SELECTION (ignores disconfirming
  data). Both can be present together; both can be absent.

DO NOT:
- Do not invent quotes that "feel like" the trace.
- Do not give every bias the same score; the trace has a structure.
- Do not return prose around the JSON. No markdown fences.
- Do not reorder; the four biases must be in the canonical order above.

OUTPUT SCHEMA (literal JSON array of 4 BiasEvidence objects):
[
  {{
    "bias": "anchoring" | "overconfidence" | "confirmation" | "escalation-of-commitment",
    "score": <float in [0.0, 1.0]>,
    "severity": "none" | "low" | "medium" | "high",
    "explanation": "<2-3 sentence diagnosis grounded in Kahneman/Tversky/Staw>",
    "evidence_quotes": ["<verbatim substring from the trace>", ...],
    "confidence": <float in [0.0, 1.0]>
  }},
  ...
]

EXAMPLE (good distinction, verbatim quotes, named anchor):
{{
  "bias": "anchoring",
  "score": 0.72,
  "severity": "high",
  "explanation": "The agent's first hypothesis (that the bug was a race condition) framed every subsequent diagnostic step, even after the stack trace at step 4 pointed at a NullPointerException. Tversky & Kahneman (1974) name this 'anchoring and adjustment' -- adjustments are systematically insufficient to override the anchor.",
  "evidence_quotes": ["this looks like a race condition", "still consistent with the race condition theory"],
  "confidence": 0.7
}}

Return only the JSON array of exactly 4 objects in the canonical order.
"""


INTERVENTIONS_PROMPT = """TASK: Propose 2-4 ranked interventions for the dominant bias.

Dominant bias: {dominant}
Evidence:
{evidence}

Trace (reference):
{trace}

INSTRUCTIONS:
- Rank from highest expected impact to lowest.
- Each intervention's ``suggested_implementation`` must be concrete
  enough that an engineer could ship it tomorrow (literal prompt text,
  eval spec, tool spec, scaffold change).
- Prefer the lightest intervention that addresses the bias.
  prompt_patch < scaffold_change < new_eval < team_composition_change.
- Anchor each rationale in a named source (Kahneman 2011, Staw 1976,
  Nickerson 1998).

DO NOT:
- Do not propose vague interventions ("improve reasoning", "be more
  careful"). Name the artifact.
- Do not propose interventions an AI agent cannot execute.
- Do not return prose around the JSON.

ALLOWED intervention_type values:
  prompt_patch, scaffold_change, retry_cap, uncertainty_calibration,
  first_principles_reset, devils_advocate_role,
  search_disconfirming_evidence, anchor_to_base_rates, new_eval,
  human_review, compose_pattern

OUTPUT SCHEMA (literal JSON array of BiasIntervention objects):
[
  {{
    "target_bias": "anchoring" | "overconfidence" | "confirmation" | "escalation-of-commitment",
    "intervention_type": "<one of the allowed values above>",
    "description": "<one-line summary>",
    "suggested_implementation": "<concrete prompt text / eval spec / scaffold change>",
    "estimated_impact": "high" | "medium" | "low",
    "rationale": "<why this works, anchored in Kahneman/Tversky/Staw/Nickerson>",
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

QUICK_DIAGNOSTIC_PROMPT = """QUICK mode -- score all four biases PLUS the single highest-impact intervention.

Task: {task}
Outcome: {outcome}
Trace: {trace}

INSTRUCTIONS:
- Score all four biases (canonical order: anchoring, overconfidence,
  confirmation, escalation-of-commitment). Do not skip any even when
  score is 0.0.
- Pick exactly ONE intervention -- the highest expected impact on the
  dominant bias.
- Quick mode favors brevity. Explanations should be 1-2 sentences.

DO NOT:
- Do not return more than one intervention.
- Do not skip a bias to save tokens.

OUTPUT SCHEMA (literal JSON object):
{{
  "biases": [
    {{
      "bias": "anchoring" | "overconfidence" | "confirmation" | "escalation-of-commitment",
      "score": <float in [0.0, 1.0]>,
      "severity": "none" | "low" | "medium" | "high",
      "explanation": "<1-2 sentences>",
      "evidence_quotes": ["<verbatim substring>", ...],
      "confidence": <float in [0.0, 1.0]>
    }},
    ... (4 total, canonical order)
  ],
  "top_intervention": {{
    "target_bias": "<canonical bias id>",
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

Return only the JSON object.
"""


STANDARD_BIAS_SCORING_PROMPT = BIAS_SCORING_PROMPT
STANDARD_INTERVENTIONS_PROMPT = INTERVENTIONS_PROMPT


FORENSIC_CALIBRATION_PROMPT = """FORENSIC mode -- confidence calibration audit (overconfidence-specific).

Trace: {trace}
Outcome: {outcome}
Success: {success}

INSTRUCTIONS:
- mean_self_confidence: arithmetic mean of every self-reported confidence
  value the agent emitted during the trace (in [0, 1]). If the agent
  never emitted explicit confidence, infer from hedging language
  ("definitely" -> 0.9, "I think" -> 0.5, "I'm not sure" -> 0.3) and
  document the inference in explanation.
- overconfidence_gap: mean_self_confidence minus actual outcome
  correctness (1.0 if success=true, 0.0 if success=false). Range
  [-1, 1]; positive = overconfident; negative = under-confident.
- calibration_estimate: 1.0 - abs(overconfidence_gap). Range [0, 1].
- explanation: one paragraph anchored in Kahneman 2011 chapter 24
  ("The Illusion of Validity") OR ch. 22 ("Expert Intuition").

DO NOT:
- Do not invent confidence values. If the agent never expressed
  confidence, set mean_self_confidence=0.5 and explain.

OUTPUT SCHEMA (literal JSON object representing the ConfidenceCalibrationAudit):
{{
  "mean_self_confidence": <float in [0.0, 1.0]>,
  "overconfidence_gap": <float in [-1.0, 1.0]>,
  "calibration_estimate": <float in [0.0, 1.0]>,
  "explanation": "<one paragraph anchored in Kahneman 2011>"
}}

Return only the JSON object.
"""


FORENSIC_ANCHORING_PROMPT = """FORENSIC mode -- anchoring trace audit.

Trace: {trace}

INSTRUCTIONS:
- first_hypothesis_persistence: how strongly the agent persisted with
  its FIRST hypothesis through the trace. In [0, 1]. 1.0 = never
  pivoted; 0.0 = abandoned the first hypothesis on step 2.
- pivot_count: number of distinct hypothesis pivots (the agent
  explicitly says "let me try a different angle" or equivalent).
- retry_count: number of times the agent retried the same approach.
- anchoring_estimate: derived score in [0, 1]. High persistence +
  high retry_count + low pivot_count -> anchoring_estimate near 1.0.
- explanation: one paragraph anchored in Tversky & Kahneman (1974).

DO NOT:
- Do not infer pivots from hindsight. Only count pivots the agent
  actually performed during the trace.

OUTPUT SCHEMA (literal JSON object representing the AnchoringTraceAudit):
{{
  "first_hypothesis_persistence": <float in [0.0, 1.0]>,
  "pivot_count": <non-negative integer>,
  "retry_count": <non-negative integer>,
  "anchoring_estimate": <float in [0.0, 1.0]>,
  "explanation": "<one paragraph anchored in Tversky & Kahneman 1974>"
}}

Return only the JSON object.
"""


FORENSIC_INTERVENTIONS_PROMPT = """FORENSIC mode -- propose 4-8 ranked interventions with composition targets.

Allowed composition_target_pattern values (when the diagnosis warrants
delegating the deeper fix to another vstack pattern):

  vstack.devils_advocate    — separate generator and critic to force
                              structured dissent on confirmation /
                              overconfidence.
  vstack.aar                — close the failure into a learning loop.
  vstack.grpi               — re-tighten goal + role on escalation.
  vstack.debate_pathology   — diagnose specific multi-agent debate
                              failure modes when the bias surfaces
                              in team reasoning.

Dominant bias: {dominant}
Evidence: {evidence}
Calibration audit: {calibration_audit}
Anchoring audit: {anchoring_audit}

INSTRUCTIONS:
- Generate 4-8 interventions, ranked highest-impact first.
- At least one intervention MUST set composition_target_pattern when
  the diagnosis warrants delegating (e.g., dominant=confirmation ->
  vstack.devils_advocate).
- Cite the audit findings (calibration, anchoring) in rationale where
  relevant.

DO NOT:
- Do not invent composition_target_pattern values outside the allowed
  set.
- Do not return fewer than 4 or more than 8 interventions.

OUTPUT SCHEMA: same as INTERVENTIONS_PROMPT (literal JSON array of
BiasIntervention).

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
    "BIAS_SCORING_PROMPT",
    "BIAS_SYSTEM_PROMPT",
    "FORENSIC_ANCHORING_PROMPT",
    "FORENSIC_CALIBRATION_PROMPT",
    "FORENSIC_INTERVENTIONS_PROMPT",
    "INTERVENTIONS_PROMPT",
    "QUICK_DIAGNOSTIC_PROMPT",
    "STANDARD_BIAS_SCORING_PROMPT",
    "STANDARD_INTERVENTIONS_PROMPT",
    "assemble_prompt",
]
