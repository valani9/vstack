"""LLM prompt templates for the GRPI Working Agreement Generator.

0.15.0 uplift: OUTPUT SCHEMA literals, DO NOT rules, one-shot example.
Wire format unchanged.
"""

from __future__ import annotations

from typing import Any

from vstack.aar import fence, sanitize_for_prompt


GRPI_SYSTEM_PROMPT = """You are a team-structure generator grounded in:

1. **Beckhard (1972)** canonical GRPI four-dimensional model.
2. **Rubin, Plovnick, Fry (1977)** task-oriented team development.
3. **Hackman (2002)** *Leading Teams*.
4. **Salas et al. (2018)** Science of Team Performance annual review.
5. **Lencioni (2002)** *Five Dysfunctions of a Team*.
6. **Edmondson (1999)** psychological safety.
7. **Wang et al. (2023)** Cooperative LLM Agents / modern LLM orchestration.

GRPI = Goals + Roles + Processes + Interactions. A team without all
four dimensions explicit is set up to fail. Generate a Working
Agreement that:

- States primary_goal + measurable success criteria + kill criteria.
- Assigns each agent a role with explicit decision rights + accountability.
- Specifies decision protocol + escalation path + abandonment criteria + communication cadence.
- Codifies disagreement norms + feedback format + conflict resolution + psychological-safety commitments.

Posture (absolute):
- **CONCRETE, SPECIFIC, TERSE.** Vague working agreements fail; specific ones succeed.
- **EVERY AGENT GETS A ROLE.** Every agent in the request must appear in role_assignments. No agent left out.
- **DECISION RIGHTS EXPLICIT.** Decision_rights cannot be "consults with team" or "discusses with leader"; they must name who decides what.
- **MEASURABLE.** measurable_success_criteria must contain quantifiable thresholds.
- **PSYCH-SAFETY-EXPLICIT.** Edmondson 1999: explicitly grant permission for dissent in interactions.psychological_safety_commitments.

Output discipline: when asked for JSON, return JSON only. No prose, no markdown fences.
"""


QUICK_GENERATION_PROMPT = """QUICK mode -- generate a compact GRPI working agreement.

Task: {task}
Agents: {agents}
Constraints: {constraints}
Success criteria: {success_criteria}
Kill criteria: {kill_criteria}
Framework: {framework}
Risk level: {risk_level}

INSTRUCTIONS:
- Every agent in ``agents`` must appear in ``roles.role_assignments``.
- ``goals.measurable_success_criteria`` must contain at least one
  quantifiable threshold.
- ``interactions.psychological_safety_commitments`` must explicitly
  grant permission to dissent (Edmondson 1999).

DO NOT:
- Do not return a working agreement that omits any agent.
- Do not write vague decision_rights ("collaboratively decides");
  name who decides what.
- Do not return prose around the JSON.

OUTPUT SCHEMA (literal JSON object):
{{
  "goals": {{
    "primary_goal": "<one-sentence statement>",
    "measurable_success_criteria": ["<quantifiable threshold>", ...],
    "scope_boundaries": ["<in-scope or out-of-scope item>", ...],
    "deliverables": ["<concrete deliverable>", ...],
    "kill_criteria": ["<concrete kill trigger>", ...]
  }},
  "roles": {{
    "role_assignments": [
      {{
        "agent_name": "<from agents list>",
        "role_title": "<concrete role>",
        "responsibilities": ["<concrete responsibility>", ...],
        "decision_rights": ["<who decides what, name level>", ...],
        "accountability_owner_for": ["<concrete deliverable>", ...]
      }},
      ...
    ],
    "raci_summary": "<one-paragraph RACI map>"
  }},
  "processes": {{
    "decision_protocol": "<concrete>",
    "escalation_path": "<concrete>",
    "abandonment_criteria": "<concrete>",
    "communication_cadence": "<concrete>",
    "review_cadence": "<concrete>",
    "artifact_storage": "<concrete>"
  }},
  "interactions": {{
    "disagreement_norms": ["<norm>", ...],
    "feedback_format": "<plus_delta | reflective | direct | other>",
    "conflict_resolution": "<concrete>",
    "voice_and_turn_taking": "<concrete>",
    "psychological_safety_commitments": ["<explicit dissent-permission statement>", ...]
  }}
}}

Return only the JSON object.
"""


STANDARD_GENERATION_PROMPT = """STANDARD mode -- generate a detailed GRPI working agreement.

Task: {task}
Agents: {agents}
Constraints: {constraints}
Success criteria: {success_criteria}
Kill criteria: {kill_criteria}
Framework: {framework}
Risk level: {risk_level}

INSTRUCTIONS:
- Same fields as QUICK mode but longer / more detailed entries.
- Every agent in ``agents`` must appear in role_assignments.
- For higher risk_level, sharpen kill_criteria + escalation_path +
  psychological_safety_commitments.

DO NOT:
- Do not leave any agent unassigned.
- Do not write decision_rights that overlap between agents without
  explicit precedence rule.
- Do not return prose around the JSON.

OUTPUT SCHEMA: same as QUICK_GENERATION_PROMPT (literal JSON object
with goals + roles + processes + interactions sections).

EXAMPLE (role_assignments entry for a code-review agent in a
3-agent crew, explicit decision_rights):
{{
  "agent_name": "reviewer",
  "role_title": "Code Reviewer",
  "responsibilities": [
    "Read every PR before approval",
    "Block PRs that fail invariants in CONTRIBUTING.md"
  ],
  "decision_rights": [
    "Reviewer alone decides whether to BLOCK on style/correctness",
    "Tech-lead overrides reviewer only with written rationale in PR comment"
  ],
  "accountability_owner_for": [
    "Quality gate at PR-merge boundary"
  ]
}}

Return only the JSON object.
"""


STANDARD_REFINEMENT_PROMPT = """STANDARD mode -- refine the draft working agreement.

Draft: {draft}
Task: {task}
Risk level: {risk_level}

INSTRUCTIONS:
- For each section, identify gaps + propose tightening.
- Return the FULL refined WorkingAgreement (not just deltas) per the
  same schema as STANDARD_GENERATION_PROMPT.
- Preserve every agent's role assignment from the draft.

DO NOT:
- Do not drop agents from role_assignments during refinement.
- Do not loosen kill_criteria when refining.

OUTPUT SCHEMA: same as STANDARD_GENERATION_PROMPT.

Return only the JSON object.
"""


FORENSIC_ROLE_FIT_PROMPT = """FORENSIC mode -- audit per-role fit.

Agents: {agents}
Roles section: {roles_section}

INSTRUCTIONS:
- One RoleFitAudit per agent.
- ``fit_score`` in [0, 1]; 1.0 = role + agent capabilities aligned;
  0.0 = severe mismatch.
- Flag overlapping_responsibilities when two agents claim ownership
  of the same deliverable without precedence.

DO NOT:
- Do not give every agent the same fit_score; audit independently.

OUTPUT SCHEMA (literal JSON array of RoleFitAudit objects):
[
  {{
    "agent_name": "<from agents>",
    "fit_score": <float in [0.0, 1.0]>,
    "ambiguous_decision_rights": ["<rights claim with no clear owner>", ...],
    "overlapping_responsibilities": ["<deliverable claimed by 2+ agents>", ...],
    "notes": "<1-2 sentences>"
  }},
  ...
]

Return only the JSON array.
"""


FORENSIC_DYSFUNCTION_PROMPT = """FORENSIC mode -- Lencioni dysfunction-prevention audit.

Working agreement: {agreement}

INSTRUCTIONS:
- For each of Lencioni's 5 dysfunctions, does the agreement
  EXPLICITLY prevent it?
- ``preventions``: list of explicit clauses that map to each
  dysfunction.

DO NOT:
- Do not credit implicit-only prevention; require an explicit clause.

OUTPUT SCHEMA (literal JSON object representing DysfunctionPreventionAudit):
{{
  "absence_of_trust_prevented": true | false,
  "fear_of_conflict_prevented": true | false,
  "lack_of_commitment_prevented": true | false,
  "avoidance_of_accountability_prevented": true | false,
  "inattention_to_results_prevented": true | false,
  "preventions": [
    {{
      "dysfunction": "absence-of-trust" | "fear-of-conflict" | "lack-of-commitment" | "avoidance-of-accountability" | "inattention-to-results",
      "clauses": ["<verbatim clause from the agreement>", ...]
    }},
    ...
  ]
}}

Return only the JSON object.
"""


FORENSIC_INTERVENTIONS_PROMPT = """FORENSIC mode -- propose interventions to improve the working agreement.

Allowed composition_target_pattern values:
  vstack.lewin, vstack.aar, vstack.lencioni, vstack.psych_safety,
  vstack.trust_triangle, vstack.mcgregor, vstack.smart_goal,
  vstack.plus_delta, vstack.schein_culture, vstack.devils_advocate,
  vstack.bias_stack

Working agreement: {agreement}
Role fit audits: {role_fit}
Dysfunction audit: {dysfunction}

INSTRUCTIONS:
- Each intervention names a specific section (goals / roles /
  processes / interactions) and a concrete edit.
- Cite the role_fit + dysfunction audits in rationale.

DO NOT:
- Do not invent composition_target_pattern values outside the allowed
  set.
- Do not propose interventions that conflict with explicit constraints
  in the original task.

OUTPUT SCHEMA (literal JSON array of GRPIIntervention objects):
[
  {{
    "target_section": "goals" | "roles" | "processes" | "interactions",
    "intervention_type": "<short snake_case label>",
    "description": "<one line>",
    "suggested_edit": "<concrete textual edit to the agreement>",
    "estimated_impact": "high" | "medium" | "low",
    "effort_estimate": "1h" | "1d" | "1w" | "1m" | "ongoing",
    "risk": "low" | "medium" | "high",
    "rationale": "<named source + why this works>",
    "composition_target_pattern": "<vstack.xxx or null>"
  }},
  ...
]

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


# Legacy aliases.
GRPI_GENERATION_PROMPT = STANDARD_GENERATION_PROMPT
GENERATION_PROMPT = STANDARD_GENERATION_PROMPT


__all__ = [
    "FORENSIC_DYSFUNCTION_PROMPT",
    "FORENSIC_INTERVENTIONS_PROMPT",
    "FORENSIC_ROLE_FIT_PROMPT",
    "GENERATION_PROMPT",
    "GRPI_GENERATION_PROMPT",
    "GRPI_SYSTEM_PROMPT",
    "QUICK_GENERATION_PROMPT",
    "STANDARD_GENERATION_PROMPT",
    "STANDARD_REFINEMENT_PROMPT",
    "assemble_prompt",
]
