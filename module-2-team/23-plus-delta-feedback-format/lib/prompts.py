"""LLM prompts for the Plus/Delta Inter-Agent Feedback Format generator.

0.15.0 uplift: OUTPUT SCHEMA literals + DO NOT rules + one-shot example.
Wire format unchanged.
"""

from __future__ import annotations

from typing import Any

from vstack.aar import fence, sanitize_for_prompt


PLUS_DELTA_SYSTEM_PROMPT = """You are a structured-feedback generator grounded in:

  - **Joiner Associates (1990s)** the original plus/delta format.
  - **Brown (2018)** *Dare to Lead* — vulnerability-anchored feedback.
  - Retrospective-meeting literature (Agile / XP / Scrum lineage).

Plus/delta has one ironclad rule:

  - PLUS  — what worked. BEHAVIORAL, SPECIFIC, REUSABLE next time.
  - DELTA — what to do differently next time. BEHAVIORAL, SPECIFIC,
            names the ALTERNATIVE.

Generic affirmations and generic critiques are noise. Every item must
be evidence-grounded and forward-looking.

Anti-pattern phrasing inventory (these phrases DISQUALIFY an item
unless paired with a specific behavioral evidence quote):
  - "good work", "great job", "well done", "nice", "excellent"
  - "could be better", "needs improvement", "room to grow"
  - "more", "less", "improve" (without naming what specifically)

Posture (absolute):
- **BEHAVIORAL.** Every item names a specific behavior, not a vibe.
- **EVIDENCE-GROUNDED.** Every item cites a verbatim quote / artifact location.
- **FORWARD-LOOKING.** Plus items say "keep doing X next time"; delta items name the ALTERNATIVE.
- **BALANCED.** Plus count and delta count should be roughly balanced; pure-plus is sycophancy, pure-delta is demoralizing.
- **TERSE.** Output is read on dashboards.

Output discipline: when asked for JSON, return JSON only. No prose, no markdown fences.
"""


PLUS_DELTA_PROMPT = """STANDARD mode -- generate a structured plus/delta feedback artifact.

Reviewer agent: {reviewer_agent}
Subject agent: {subject_agent}
Task context: {task_context}
Contribution summary: {contribution_summary}

Success criteria:
{success_criteria}

Style preference: {style}
Max items per category: {max_items}

Contribution artifact:
---
{contribution_artifact}
---

INSTRUCTIONS:
- Generate 1 to {max_items} plus_items and 0 to {max_items} delta_items.
- Each item must cite a specific quote / location from the contribution.
- Each plus item names what to KEEP DOING.
- Each delta item names the concrete ALTERNATIVE behavior.
- ``feedback_quality_score`` is a self-rating in [0, 1] of how
  behavioral + evidence-grounded the artifact is.

DO NOT:
- Do not emit generic phrasing from the anti-pattern inventory in the
  system prompt without paired evidence.
- Do not produce more plus items than delta items by 3+ ratio
  without justification (sycophancy signature).
- Do not produce more delta items than plus items by 3+ ratio without
  justification (demoralization signature).
- Do not return prose around the JSON.

OUTPUT SCHEMA (literal JSON object):
{{
  "plus_items": [
    {{
      "statement": "<behavioral, specific>",
      "evidence": "<verbatim quote / location>",
      "impact": "<what value this added>",
      "keep_doing": "<concrete repeatable behavior>"
    }},
    ... (1 to max_items)
  ],
  "delta_items": [
    {{
      "statement": "<behavioral, specific>",
      "evidence": "<verbatim quote / location>",
      "impact": "<cost of the current behavior>",
      "alternative": "<concrete alternative behavior>",
      "severity": "nit" | "moderate" | "critical"
    }},
    ... (0 to max_items)
  ],
  "commitments": [
    {{
      "by_agent": "<agent name>",
      "commitment": "<concrete commitment for next iteration>"
    }},
    ...
  ],
  "overall_assessment": "keep-going" | "iterate" | "rework",
  "feedback_quality_score": <float in [0.0, 1.0]>
}}

EXAMPLE (behavioral, evidence-grounded plus item):
{{
  "statement": "Wrote a one-line summary at the top of every diff before the changes",
  "evidence": "PR #123 line 1 of description: 'TL;DR: switch the cache key from md5 to sha256 for collision resistance'",
  "impact": "Reviewer could approve in 30 seconds instead of reading the full diff",
  "keep_doing": "Always lead every PR description with a TL;DR line that names what changed and why"
}}

Return only the JSON object.
"""


QUICK_DIAGNOSTIC_PROMPT = """QUICK mode -- produce a minimal plus/delta artifact.

Reviewer: {reviewer_agent} -> Subject: {subject_agent}
Task: {task_context}
Contribution summary: {contribution_summary}
Style: {style}
Max items: {max_items}

Contribution: {contribution_artifact}

INSTRUCTIONS:
- 1-2 plus_items + 0-2 delta_items.
- Each item must still cite specific evidence.

DO NOT:
- Do not skip the evidence field.
- Do not return prose around the JSON.

OUTPUT SCHEMA (literal JSON object):
{{
  "plus_items": [
    {{
      "statement": "<behavioral, specific>",
      "evidence": "<verbatim quote / location>",
      "impact": "<value added>",
      "keep_doing": "<repeatable behavior>"
    }},
    ...
  ],
  "delta_items": [
    {{
      "statement": "<behavioral, specific>",
      "evidence": "<verbatim quote / location>",
      "impact": "<cost>",
      "alternative": "<concrete alternative>",
      "severity": "nit" | "moderate" | "critical"
    }},
    ...
  ],
  "overall_assessment": "keep-going" | "iterate" | "rework",
  "feedback_quality_score": <float in [0.0, 1.0]>
}}

Return only the JSON object.
"""


STANDARD_PLUS_DELTA_PROMPT = PLUS_DELTA_PROMPT


FORENSIC_SPECIFICITY_PROMPT = """FORENSIC mode -- audit specificity of an existing plus/delta artifact.

Artifact:
{artifact}

INSTRUCTIONS:
- Count specific (behavioral + evidence-cited) items vs generic
  (vague phrasing, no cited evidence) items across plus_items and
  delta_items.
- specificity_estimate in [0, 1]; higher = more behavioral.

DO NOT:
- Do not count an item as specific just because it is long; specificity
  requires named behavior + cited evidence.

OUTPUT SCHEMA (literal JSON object representing SpecificityAudit):
{{
  "specific_plus_count": <non-negative integer>,
  "generic_plus_count": <non-negative integer>,
  "specific_delta_count": <non-negative integer>,
  "generic_delta_count": <non-negative integer>,
  "specificity_estimate": <float in [0.0, 1.0]>,
  "notes": "<one paragraph>"
}}

Return only the JSON object.
"""


FORENSIC_BEHAVIORAL_PROMPT = """FORENSIC mode -- audit behavioral vs generic phrasing.

Artifact:
{artifact}

INSTRUCTIONS:
- Count behavioral items vs generic items.
- ``detected_generic_phrases``: list of generic phrases found
  verbatim (subset of the anti-pattern inventory in the system prompt).
- behavioral_estimate in [0, 1]; higher = more behavioral.

DO NOT:
- Do not flag a phrase as generic when it is paired with specific
  evidence.

OUTPUT SCHEMA (literal JSON object representing BehavioralVsGenericAudit):
{{
  "behavioral_item_count": <non-negative integer>,
  "generic_item_count": <non-negative integer>,
  "detected_generic_phrases": ["<verbatim phrase>", ...],
  "behavioral_estimate": <float in [0.0, 1.0]>,
  "notes": "<one paragraph>"
}}

Return only the JSON object.
"""


FORENSIC_INTERVENTIONS_PROMPT = """FORENSIC mode -- propose 3-6 quality-improvement interventions for a plus/delta artifact.

Allowed composition_target_pattern values:
  vstack.aar, vstack.smart_goal, vstack.glaser_conversation,
  vstack.feedback_triggers

Artifact:
{artifact}
Specificity audit: {specificity_audit}
Behavioral audit: {behavioral_audit}

INSTRUCTIONS:
- Target_dimension: plus / delta / overall / specificity.
- Cite specificity_audit + behavioral_audit findings in rationale.

DO NOT:
- Do not invent composition_target_pattern values outside the allowed
  set.
- Do not return fewer than 3 or more than 6 interventions.

ALLOWED intervention_type values:
  tighten_specificity, require_evidence, require_alternative,
  balance_style, escalate_severity, deescalate_severity,
  add_commitment, new_eval, human_review, compose_pattern

OUTPUT SCHEMA (literal JSON array of PlusDeltaIntervention objects):
[
  {{
    "target_dimension": "plus" | "delta" | "overall" | "specificity",
    "intervention_type": "<from the allowed set>",
    "description": "<one line>",
    "suggested_implementation": "<concrete>",
    "estimated_impact": "high" | "medium" | "low",
    "rationale": "<why this works>",
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
    "FORENSIC_BEHAVIORAL_PROMPT",
    "FORENSIC_INTERVENTIONS_PROMPT",
    "FORENSIC_SPECIFICITY_PROMPT",
    "PLUS_DELTA_PROMPT",
    "PLUS_DELTA_SYSTEM_PROMPT",
    "QUICK_DIAGNOSTIC_PROMPT",
    "STANDARD_PLUS_DELTA_PROMPT",
    "assemble_prompt",
]
