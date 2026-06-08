"""LLM prompts for the Edmondson Psychological Safety diagnostic.

Anchored in:
  - Edmondson (1999) "Psychological Safety and Learning Behavior in
    Work Teams." *Administrative Science Quarterly* 44(2): 350-383.
  - Edmondson (2018) *The Fearless Organization.* Wiley.

The detector observes four canonical safety behaviors in a multi-
agent trace:

  - VOICE             - members speak up with ideas, including disagreement.
  - HELP-SEEKING      - members ask for help when they do not know.
  - ERROR-REPORTING   - members admit mistakes promptly.
  - BOUNDARY-SPANNING - members challenge premises from outside their lane.

The core insight Edmondson surfaces: LOW-safety teams APPEAR smoother
(no visible disagreement, no admitted errors) but produce confident
wrong outputs because issues were never surfaced. ABSENCE of these
behaviors is therefore the diagnostic signal, not their presence.

The 0.13.0 uplift adds OUTPUT SCHEMA literals, a one-shot example
on BEHAVIOR_SCORING_PROMPT, anti-pattern rules, and a seven-band
severity calibration to the system prompt. The wire format and the
public template constant names are unchanged.
"""

from __future__ import annotations

from typing import Any

from vstack.aar import fence, sanitize_for_prompt


SAFETY_SYSTEM_PROMPT = """You are an Edmondson psychological-safety diagnostician for multi-agent
AI systems, grounded in:

  - Edmondson (1999) "Psychological Safety and Learning Behavior in
    Work Teams." Administrative Science Quarterly 44(2): 350-383.
  - Edmondson (2018) *The Fearless Organization.* Wiley.

The four observable behaviors that mark psychological safety:

  - VOICE             — members speak up with ideas, including
                        disagreement, even when it is costly.
  - HELP-SEEKING      — members ask for help when they do not know.
                        Asking is treated as competence, not weakness.
  - ERROR-REPORTING   — members admit mistakes promptly. The team
                        treats errors as data, not threats.
  - BOUNDARY-SPANNING — members challenge premises from outside their
                        formal lane. Junior agents push back on
                        senior ones; specialists question the
                        generalist's frame.

For each behavior, PRESENCE is good (presence_score 1.0); ABSENCE is
bad (presence_score 0.0).

CRITICAL INSIGHT (Edmondson 1999): low-safety teams APPEAR smoother.
No visible disagreement. No admitted errors. No help requests. The
trace looks clean. But the team produces confident wrong outputs
because issues were never surfaced. ABSENCE OF SIGNAL IS THE SIGNAL.

Severity calibration (presence_score -> severity_of_absence label):

  - presence_score in [0.85, 1.00]  -> severity_of_absence = "none"
  - presence_score in [0.55, 0.84]  -> severity_of_absence = "low"
  - presence_score in [0.25, 0.54]  -> severity_of_absence = "medium"
  - presence_score in [0.00, 0.24]  -> severity_of_absence = "high"

Posture (these are absolute):

  - EVIDENCE-GROUNDED. Every ``evidence_quotes`` entry must appear
    verbatim in the trace.
  - ABSENCE IS DATA. If you cannot find evidence of a behavior, that
    is a high-severity finding -- not a non-finding. Set
    presence_score low and explain the absence.
  - INTERVENTION-FOCUSED. Diagnosis without next-steps is wasted.
  - TRANSPARENT. Very thin traces (one or two messages) -> reduce
    confidence and bias toward "absence as data unknown". Do not
    refuse to produce a diagnosis.

Output discipline: when the prompt says "return only the JSON ...",
emit JSON only. No prose. No markdown fences. No headings.
"""


# ----------------------------------------------------------------------
# Standard / legacy prompts.
# ----------------------------------------------------------------------

BEHAVIOR_SCORING_PROMPT = """TASK: Score the four Edmondson safety behaviors against this multi-agent trace.

Goal: {goal}
Outcome: {outcome}
Success: {success}
Agents: {agents}

Messages:
{trace}

INSTRUCTIONS:
- Return exactly 4 BehaviorEvidence objects in this canonical order:
    1. voice
    2. help-seeking
    3. error-reporting
    4. boundary-spanning
- Use the calibration table from the system prompt to map presence_score
  to severity_of_absence.
- ``evidence_quotes`` must be verbatim substrings of the trace above.
- ABSENCE IS DATA. If you cannot find a behavior, set presence_score
  low (closer to 0.0), set severity_of_absence to "medium" or "high",
  and explain the absence (Edmondson 1999: silence in high-stakes
  contexts is itself a signal).
- ``blocking_behaviors`` (string array): name patterns in the trace
  that actively SUPPRESSED safety, e.g. "senior agent dismissed
  junior agent's question", "leader closed debate with a quip".

DO NOT:
- Do not invent quotes that "feel like" the trace.
- Do not assume safety from a smooth-looking trace. Smooth is suspicious.
- Do not return prose around the JSON. No markdown fences.
- Do not reorder; the four behaviors must be in the canonical order above.

OUTPUT SCHEMA (literal JSON object):
{{
  "behaviors": [
    {{
      "behavior": "voice" | "help-seeking" | "error-reporting" | "boundary-spanning",
      "presence_score": <float in [0.0, 1.0]>,
      "severity_of_absence": "none" | "low" | "medium" | "high",
      "explanation": "<2-3 sentence diagnosis anchored in Edmondson 1999 or 2018>",
      "evidence_quotes": ["<verbatim substring from the trace>", ...],
      "confidence": <float in [0.0, 1.0]>
    }},
    ... (4 total, canonical order)
  ],
  "blocking_behaviors": ["<short kebab-case pattern name>", ...]
}}

EXAMPLE (good absence-as-data reasoning, Edmondson-anchored):
{{
  "behavior": "voice",
  "presence_score": 0.15,
  "severity_of_absence": "high",
  "explanation": "Across all 12 messages, no agent disagrees with the lead. Two agents asked clarifying questions but did not voice the constraint each had earlier identified. Edmondson 1999 documents this as the classic 'undiscussables' pattern -- silence is the signal.",
  "evidence_quotes": ["Sounds great, let's go with that", "I'll defer to your judgment"],
  "confidence": 0.65
}}

Return only the JSON object (with both behaviors and blocking_behaviors keys).
"""


INTERVENTIONS_PROMPT = """TASK: Propose 2-4 ranked interventions to grow psychological safety.

Lowest-presence behavior: {lowest_behavior}
Behavior analysis:
{evidence}

Trace (reference):
{trace}

INSTRUCTIONS:
- Target the behavior with the LOWEST presence_score first.
- Rank from highest expected impact to lowest.
- Each ``suggested_implementation`` must be concrete (literal prompt
  text, eval spec, scaffold change, role assignment).
- Anchor each rationale in Edmondson 1999 (the four-behavior model)
  or 2018 (the leader-behavior chapters).

DO NOT:
- Do not propose generic interventions ("foster open communication").
  Name the artifact, the prompt, the eval.
- Do not propose interventions an AI agent cannot execute (no
  retreats, no skip-level 1:1s).
- Do not return prose around the JSON. No markdown fences.

ALLOWED intervention_type values:
  prompt_patch, scaffold_change, role_assignment, new_eval,
  human_review, norms_in_working_agreement, dissent_round,
  uncertainty_surfacing, error_amnesty_policy, compose_pattern

OUTPUT SCHEMA (literal JSON array of SafetyIntervention objects):
[
  {{
    "target_behavior": "voice" | "help-seeking" | "error-reporting" | "boundary-spanning",
    "intervention_type": "<one of the allowed values above>",
    "description": "<one-line summary>",
    "suggested_implementation": "<concrete prompt text / eval spec / role spec>",
    "estimated_impact": "high" | "medium" | "low",
    "rationale": "<why this works, anchored in Edmondson>",
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

QUICK_DIAGNOSTIC_PROMPT = """QUICK mode -- score all four safety behaviors PLUS the single highest-impact intervention.

Goal: {goal}
Outcome: {outcome}
Success: {success}
Agents: {agents}
Trace: {trace}

INSTRUCTIONS:
- Score all 4 behaviors (canonical order: voice, help-seeking,
  error-reporting, boundary-spanning). Do not skip any.
- Identify blocking_behaviors as in standard mode.
- Pick exactly ONE intervention targeting the lowest-presence behavior.
- Quick mode favors brevity. Explanations 1-2 sentences.

DO NOT:
- Do not return more than one intervention.
- Do not skip a behavior to save tokens.

OUTPUT SCHEMA (literal JSON object):
{{
  "behaviors": [
    {{
      "behavior": "voice" | "help-seeking" | "error-reporting" | "boundary-spanning",
      "presence_score": <float in [0.0, 1.0]>,
      "severity_of_absence": "none" | "low" | "medium" | "high",
      "explanation": "<1-2 sentences>",
      "evidence_quotes": ["<verbatim substring>", ...],
      "confidence": <float in [0.0, 1.0]>
    }},
    ... (4 total, canonical order)
  ],
  "blocking_behaviors": ["<short kebab-case pattern>", ...],
  "top_intervention": {{
    "target_behavior": "<canonical behavior>",
    "intervention_type": "<from the allowed set>",
    "description": "<one line>",
    "suggested_implementation": "<concrete>",
    "estimated_impact": "high" | "medium" | "low",
    "rationale": "<short, Edmondson-anchored>",
    "effort_estimate": "1h" | "1d" | "1w" | "1m" | "ongoing",
    "risk": "low" | "medium" | "high",
    "composition_target_pattern": "<slug or null>"
  }}
}}

Return only the JSON object.
"""


STANDARD_BEHAVIOR_SCORING_PROMPT = BEHAVIOR_SCORING_PROMPT
STANDARD_INTERVENTIONS_PROMPT = INTERVENTIONS_PROMPT


FORENSIC_VOICE_AUDIT_PROMPT = """FORENSIC mode -- voice / challenge-signal audit.

Trace: {trace}

INSTRUCTIONS:
- challenge_message_count: number of messages where an agent visibly
  pushes back, surfaces a constraint another agent missed, or
  proposes an alternative path.
- agreement_only_count: number of messages that purely agree, defer,
  or accept without adding information.
- silence_after_decision_count: number of decision points after which
  no agent surfaces follow-up questions or constraints. Edmondson 1999
  flags this as the signature of "undiscussables".
- voice_estimate: derived score in [0, 1]. challenge / (challenge +
  agreement_only) is a reasonable starting point; adjust for trace
  length and stakes.
- explanation: one paragraph anchored in Edmondson 1999.

DO NOT:
- Do not count questions as challenges unless they imply dissent.

OUTPUT SCHEMA (literal JSON object representing the VoiceSignalAudit):
{{
  "challenge_message_count": <non-negative integer>,
  "agreement_only_count": <non-negative integer>,
  "silence_after_decision_count": <non-negative integer>,
  "voice_estimate": <float in [0.0, 1.0]>,
  "explanation": "<one paragraph anchored in Edmondson 1999>"
}}

Return only the JSON object.
"""


FORENSIC_ERROR_REPORTING_PROMPT = """FORENSIC mode -- error-reporting culture audit.

Trace: {trace}

INSTRUCTIONS:
- admitted_error_count: number of messages where an agent openly
  admits a mistake, retracts a prior claim, or surfaces an error
  before being caught.
- concealed_error_count: number of moments where the trace contains
  an error (factual, tool, logical) AND the responsible agent moves
  on without acknowledging it.
- error_reporting_estimate: derived score in [0, 1]. admitted /
  (admitted + concealed) is a reasonable starting point.
- explanation: one paragraph anchored in Edmondson 1996/2018 (the
  hospital-error study or the Fearless Organization chapter on
  error culture).

DO NOT:
- Do not count "small clarifications" as admitted errors.

OUTPUT SCHEMA (literal JSON object representing the ErrorReportingAudit):
{{
  "admitted_error_count": <non-negative integer>,
  "concealed_error_count": <non-negative integer>,
  "error_reporting_estimate": <float in [0.0, 1.0]>,
  "explanation": "<one paragraph anchored in Edmondson>"
}}

Return only the JSON object.
"""


FORENSIC_INTERVENTIONS_PROMPT = """FORENSIC mode -- propose 4-8 ranked interventions with composition targets.

Allowed composition_target_pattern values (when delegating the deeper
fix to another vstack pattern):

  vstack.lencioni          — pyramid-tier diagnosis when low safety
                             cascades into accountability gaps.
  vstack.grpi              — re-tighten working agreement after a
                             safety collapse.
  vstack.aar               — close the failure into a learning loop.
  vstack.devils_advocate   — separate generator and critic to force
                             structured dissent.
  vstack.bias_stack        — surface cognitive biases that get
                             reinforced by low safety.
  vstack.glaser            — conversational-steering protocol for
                             how to surface dissent without rupture.

Lowest-presence behavior: {lowest_behavior}
Behavior evidence: {evidence}
Voice audit: {voice_audit}
Error reporting audit: {error_reporting_audit}

INSTRUCTIONS:
- Generate 4-8 interventions, ranked highest-impact first.
- At least one intervention MUST set composition_target_pattern when
  the diagnosis warrants delegation.
- Cite the audit findings in rationale where relevant.

DO NOT:
- Do not invent composition_target_pattern values outside the
  allowed set.
- Do not return fewer than 4 or more than 8 interventions.

OUTPUT SCHEMA: same as INTERVENTIONS_PROMPT (literal JSON array of
SafetyIntervention).

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
    "BEHAVIOR_SCORING_PROMPT",
    "FORENSIC_ERROR_REPORTING_PROMPT",
    "FORENSIC_INTERVENTIONS_PROMPT",
    "FORENSIC_VOICE_AUDIT_PROMPT",
    "INTERVENTIONS_PROMPT",
    "QUICK_DIAGNOSTIC_PROMPT",
    "SAFETY_SYSTEM_PROMPT",
    "STANDARD_BEHAVIOR_SCORING_PROMPT",
    "STANDARD_INTERVENTIONS_PROMPT",
    "assemble_prompt",
]
