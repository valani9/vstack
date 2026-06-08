"""LLM prompt templates for the DANVA Emotion Reader diagnostic.

Three modes (quick / standard / forensic) with shared system prompt
naming 12+ literature anchors. Templates filled via
:func:`assemble_prompt` which sanitizes + fences free-text fields.

DANVA performs deterministic per-emotion accuracy + intensity MAE
scoring outside the LLM; the LLM is responsible for diagnosing
failure modes + proposing interventions. The 0.15.0 uplift adds
OUTPUT SCHEMA literals, DO NOT rules, and a one-shot example.
"""

from __future__ import annotations

from typing import Any

from vstack.aar import fence, sanitize_for_prompt


DANVA_SYSTEM_PROMPT = """You are a DANVA-style emotion-recognition diagnostician for AI agents, grounded in:

1. **Nowicki & Duke (1994, 2001)** — Diagnostic Analysis of Nonverbal Accuracy (DANVA/DANVA2). Per-emotion accuracy + confusion-matrix methodology.
2. **Ekman (1992, 1999)** — six basic emotions (anger, disgust, fear, joy, sadness, surprise) + neutral.
3. **Plutchik (2001)** — wheel-of-emotions with three intensity gradations per emotion. Primary dyads (joy+trust=love, anger+disgust=contempt).
4. **Russell (1980)** — circumplex model: valence x arousal 2D projection. Complementary lens to categorical Ekman.
5. **Mehrabian (1980)** — PAD: pleasure-arousal-dominance 3D extension.
6. **Posner, Russell & Peterson (2005)** — categorical-dimensional reconciliation. Publish BOTH lenses separately rather than collapsing.
7. **Mohammad (2018)** NRC-VAD lexicon — deterministic per-word valence/arousal/dominance scores; provides no-LLM ground-truth baseline.
8. **GoEmotions (Demszky et al. 2020)** + Cowen-Keltner 2017 — 27-category extended taxonomy bridges discrete with continuous gradients.
9. **EmoBench (Sabour et al. 2024)** + EmotionQueen (Wang et al. 2024) — LLM emotion-intelligence benchmarks; implicit-emotion task is operationally hard.
10. **WASSA-2017** (Mohammad & Bravo-Marquez) — per-emotion intensity shared task; Pearson 0.747 target.
11. **Matsumoto & Hwang (2018)** — cultural display rules; emotion expression is culturally regulated.
12. **Tausczik & Pennebaker (2010)** LIWC — word-count linguistic style detects emotion in text deterministically.

Posture (absolute):
- **EVIDENCE-GROUNDED.** Cite specific user_input quotes + cue features.
- **CUE-AWARE.** Recognize the cue inventory: ALL-CAPS spans, exclamation density, hedge words ('might', 'maybe'), intensifiers ('just', 'really'), future tense (fear), past tense + loss (sad), moral-violation language (disgust), surprise tokens ('oh', 'wait').
- **SARCASM-AWARE.** Sarcasm signatures ('oh sure', 'totally', praise-followed-by-ellipsis) flip surface valence; downweight positive classification.
- **CASCADE-AWARE.** A high categorical match with collapsed intensity is a cascade break (perceived cue -> categorized correctly -> failed at intensity).
- **CULTURAL-AWARE.** Display-rule context shifts the ground-truth: same caps-spam reads as 'angry' in en-US, possibly 'frustrated-suppressed' in JP context.
- **CALIBRATED.** Use 'uncertain' as a last resort; force best-guess with confidence < 0.3 before falling back.
- **TERSE.** Output is read on dashboards.

Output discipline: when asked for JSON, return JSON only. No prose, no markdown fences.
"""


QUICK_DIAGNOSTIC_PROMPT = """QUICK mode -- propose 1-2 interventions for the dominant weakness in this DANVA batch.

Items: {n_items}
Overall accuracy: {overall_accuracy}
Overall intensity MAE: {overall_intensity_mae}
Weakest emotion: {weakest_emotion}
Accuracy quality: {accuracy_quality}
Per-emotion metrics:
{metrics_table}
Confusion patterns:
{confusion_table}
Sample misclassifications:
{sample_errors}

INSTRUCTIONS:
- Return 1 or 2 EmotionIntervention objects.
- Each ``suggested_implementation`` must be concrete.
- Target_emotion can be the weakest specific emotion or "all" when
  the failure is global.

DO NOT:
- Do not return more than 2 interventions.
- Do not propose generic "be more accurate" interventions.
- Do not return prose around the JSON.

OUTPUT SCHEMA (literal JSON array of 1-2 EmotionIntervention objects):
[
  {{
    "target_emotion": "happy" | "sad" | "angry" | "fearful" | "disgust" | "surprise" | "neutral" | "all",
    "intervention_type": "<from the allowed set>",
    "description": "<one line>",
    "suggested_implementation": "<concrete>",
    "estimated_impact": "high" | "medium" | "low",
    "effort_estimate": "1h" | "1d" | "1w" | "1m" | "ongoing",
    "risk": "low" | "medium" | "high",
    "reversibility": "two-way-door" | "one-way-door",
    "rationale": "<short, named-source anchored>"
  }},
  ...
]

Return only the JSON array.
"""


STANDARD_INTERVENTIONS_PROMPT = """STANDARD mode -- propose 2-4 ranked interventions for this DANVA batch.

Items: {n_items}
Overall accuracy: {overall_accuracy}
Overall intensity MAE: {overall_intensity_mae}
Weakest emotion: {weakest_emotion}
Accuracy quality: {accuracy_quality}
Profile pattern: {profile_pattern}
Per-emotion metrics:
{metrics_table}
Confusion patterns:
{confusion_table}
Sample misclassifications:
{sample_errors}

INSTRUCTIONS:
- Target the weakest_emotion first.
- Rank from highest expected impact to lowest.
- Each ``suggested_implementation`` must be concrete (literal prompt
  text, eval spec, cue-inventory snippet).
- ``rationale`` anchors in named source (Ekman, Plutchik, Russell,
  Mehrabian, Mohammad NRC-VAD, GoEmotions, Matsumoto-Hwang).

DO NOT:
- Do not propose vague "improve emotion reading" interventions.
- Do not propose interventions outside the allowed set.
- Do not return prose around the JSON.

ALLOWED intervention_type values:
  add_emotion_reading_step, add_intensity_calibration_step,
  add_cue_inventory, add_confusion_clarification, few_shot_examples,
  rewrite_system_prompt, swap_model, new_eval, human_review,
  add_sarcasm_detection_step, add_cultural_context_check,
  add_uncertainty_threshold, add_min_cue_threshold,
  add_dimensional_overlay, add_valence_arousal_disambig,
  compose_pattern, add_constitutional_principle, swap_to_reasoning_model

OUTPUT SCHEMA (literal JSON array of EmotionIntervention objects):
[
  {{
    "target_emotion": "happy" | "sad" | "angry" | "fearful" | "disgust" | "surprise" | "neutral" | "all",
    "intervention_type": "<from the allowed set>",
    "description": "<one line>",
    "suggested_implementation": "<concrete prompt / eval / cue inventory>",
    "estimated_impact": "high" | "medium" | "low",
    "effort_estimate": "1h" | "1d" | "1w" | "1m" | "ongoing",
    "risk": "low" | "medium" | "high",
    "reversibility": "two-way-door" | "one-way-door",
    "rationale": "<named source + why this works>"
  }},
  ...
]

EXAMPLE (sarcasm-induced confusion on angry, NRC-VAD anchored):
{{
  "target_emotion": "angry",
  "intervention_type": "add_sarcasm_detection_step",
  "description": "Insert a sarcasm pre-classifier that flips valence on positive-surface + negative-context utterances.",
  "suggested_implementation": "Add to system prompt: 'Before assigning emotion, check for sarcasm signatures: praise followed by ellipsis (\"great...\"), \"oh sure\" / \"totally\" sentence-starters, exclamation marks attached to negative-valence content. If sarcasm detected, FLIP surface valence before scoring.'",
  "estimated_impact": "high",
  "effort_estimate": "1d",
  "risk": "low",
  "reversibility": "two-way-door",
  "rationale": "Mohammad 2018 NRC-VAD lexicon misclassifies sarcastic praise as positive valence; explicit pre-step counters the systematic bias. WASSA-2017 task 2 results show sarcasm detection is the single biggest lift for emotion-intensity Pearson."
}}

Return only the JSON array.
"""


FORENSIC_DIMENSIONAL_OVERLAY_PROMPT = """FORENSIC mode -- project the batch onto Russell's circumplex (valence x arousal).

Items sample:
{items}

INSTRUCTIONS:
- valence_truth + arousal_truth: means across items using
  Mohammad 2018 NRC-VAD as ground-truth anchor.
- valence_inferred + arousal_inferred: means across items using the
  agent's classification.
- euclidean_distance: between truth and inferred points.
- quadrants: per Russell 1980 (high-pos = high arousal positive
  valence; etc.).

DO NOT:
- Do not use the LLM's own emotion classifications as ground-truth;
  the deterministic NRC-VAD lexicon is the anchor.

OUTPUT SCHEMA (literal JSON object representing CircumplexProjection):
{{
  "valence_truth": <float in [-1.0, 1.0]>,
  "arousal_truth": <float in [-1.0, 1.0]>,
  "valence_inferred": <float in [-1.0, 1.0]>,
  "arousal_inferred": <float in [-1.0, 1.0]>,
  "euclidean_distance": <non-negative float>,
  "quadrant_truth": "high-pos" | "high-neg" | "low-pos" | "low-neg",
  "quadrant_inferred": "high-pos" | "high-neg" | "low-pos" | "low-neg",
  "quadrant_match": true | false
}}

Return only the JSON object.
"""


FORENSIC_CASCADE_RECONCILE_PROMPT = """FORENSIC mode -- diagnose the recognition cascade break.

Cascade order: perceive_cue -> categorize -> intensity -> respond.
The earliest stage at which competence drops below threshold is the
cascade break.

Per-emotion metrics:
{metrics_table}
Confusion patterns:
{confusion_table}
Russell projection:
{circumplex}

INSTRUCTIONS:
- cascade_break_point: name the earliest stage that fails OR "intact".
- Each stage_score in [0, 1]; 1.0 = competent at that stage.
- notes: 1-3 sentences naming WHICH evidence points to the break.

DO NOT:
- Do not invent a cascade break that the metrics do not support.

OUTPUT SCHEMA (literal JSON object):
{{
  "cascade_break_point": "intact" | "fails_at_perceive_cue" | "fails_at_categorize" | "fails_at_intensity" | "fails_at_respond",
  "perceive_score": <float in [0.0, 1.0]>,
  "categorize_score": <float in [0.0, 1.0]>,
  "intensity_score": <float in [0.0, 1.0]>,
  "respond_score": <float in [0.0, 1.0]>,
  "notes": "<1-3 sentences citing metric evidence>"
}}

Return only the JSON object.
"""


FORENSIC_INTERVENTIONS_PROMPT = """FORENSIC mode -- propose 4-8 ranked interventions with composition targets and full operational fields.

Allowed composition_target_pattern values:
  vstack.goleman_ei, vstack.cognitive_reappraisal,
  vstack.glaser_conversation, vstack.hexaco, vstack.aar,
  vstack.lewin, vstack.johari, vstack.yerkes_dodson,
  vstack.schein_culture, vstack.plus_delta

Profile pattern: {profile_pattern}
Cascade break: {cascade_break_point}
Weakest emotion: {weakest_emotion}
Per-emotion metrics:
{metrics_table}
Sample errors:
{sample_errors}

INSTRUCTIONS:
- Generate 4-8 interventions, ranked highest impact first.
- Include at least one compose_pattern intervention when a downstream
  pattern is warranted.
- Each intervention must include preconditions + success_metric.

DO NOT:
- Do not invent composition_target_pattern values outside the allowed
  set.
- Do not return fewer than 4 or more than 8 interventions.

OUTPUT SCHEMA: same as STANDARD_INTERVENTIONS_PROMPT plus
``preconditions`` (string array) and ``success_metric`` (string) on
each intervention.

Return only the JSON array.
"""


def assemble_prompt(template: str, **fields: Any) -> str:
    """Fill a prompt template, sanitizing + fencing every free-text field."""
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


INTERVENTIONS_PROMPT = STANDARD_INTERVENTIONS_PROMPT


__all__ = [
    "DANVA_SYSTEM_PROMPT",
    "FORENSIC_CASCADE_RECONCILE_PROMPT",
    "FORENSIC_DIMENSIONAL_OVERLAY_PROMPT",
    "FORENSIC_INTERVENTIONS_PROMPT",
    "INTERVENTIONS_PROMPT",
    "QUICK_DIAGNOSTIC_PROMPT",
    "STANDARD_INTERVENTIONS_PROMPT",
    "assemble_prompt",
]
