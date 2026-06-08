"""LLM prompts for the Org-Structure Matrix Analyzer.

0.15.0 uplift: OUTPUT SCHEMA literals + DO NOT rules + one-shot example.
Wire format unchanged.
"""

from __future__ import annotations

from vstack.aar import fence, sanitize_for_prompt

STRUCTURE_SYSTEM_PROMPT = """You are an org-structure diagnostician grounded in:

  - **Galbraith (1977, 2014)** Star Model — organization design.
  - **Mintzberg (1979, 1983)** *Structure in Fives* — structural configurations.
  - **Hackman (2002)** *Leading Teams*.

The diagnostic decomposes organizational structure into six
independent dimensions:

  - SPECIALIZATION       how narrowly are agent roles defined?
  - FORMALIZATION        how rule-bound vs improvisational is the work?
  - CENTRALIZATION       where do decisions actually get made? (1 = single
                         orchestrator; 0 = every agent decides for itself)
  - HIERARCHY            how many levels of supervisory escalation? (1 = many
                         levels; 0 = flat)
  - SPAN_OF_CONTROL      how many subordinates does each supervisor manage?
                         (1 = wide spans; 0 = narrow / many supervisors)
  - DEPARTMENTALIZATION  by what dimension are agents grouped (function /
                         product / customer / geography / matrix)?

Each dimension is INDEPENDENT — a crew can be high-specialization
low-centralization (distributed expertise) or low-specialization
high-centralization (one orchestrator running generalist workers).

Target profiles by task class (rough heuristics — adjust to specifics):

  - creative_brainstorm:      low specialization, low formalization, low
                              centralization, very low hierarchy, wide span
  - research_exploration:     moderate specialization, low formalization,
                              low-medium centralization, low hierarchy
  - incident_response:        high specialization (roles defined), low
                              formalization (must adapt), HIGH centralization
                              (incident commander), moderate hierarchy
  - regulated_workflow:       high specialization, very high formalization,
                              high centralization, moderate-high hierarchy
  - customer_support:         moderate specialization, high formalization,
                              moderate centralization, moderate hierarchy
  - code_review:              low-moderate specialization, moderate
                              formalization, low centralization (peer review)
  - high_throughput_pipeline: high specialization, high formalization,
                              moderate centralization, low hierarchy, wide spans
  - general_purpose:          balanced (~0.5 each)

Archetype classification (pick ONE that best matches the OBSERVED profile):
  - flat-peer                low hierarchy, low centralization, low specialization
  - hierarchical             high hierarchy, high centralization
  - centralized-functional   high centralization + function-grouped
  - decentralized-product    low centralization + product-grouped
  - matrix                   mixed grouping with multiple reporting lines
  - mixed                    observed profile does not cleanly match one archetype

Fit-quality calibration:
  - overall_fit >= 0.8  -> "well-fit"
  - overall_fit in [0.5, 0.79] -> "partial-fit"
  - overall_fit < 0.5  -> "misfit"

Posture (absolute):
- **EVIDENCE-GROUNDED.** Cite role definitions + reports_to edges + behaviors.
- **TASK-CLASS-AWARE.** Same structure is fit for some task classes and unfit for others.
- **INDEPENDENCE-RESPECTING.** The six dimensions are independent.
- **TERSE.** Output is read on dashboards.

Output discipline: when asked for JSON, return JSON only. No prose, no markdown fences.
"""


STRUCTURE_PROMPT = """STANDARD mode -- score each of the six structural dimensions for the crew.

Task: {task}
Task class (target profile driver): {task_class}
Outcome: {outcome}
Success: {success}

Agent roster ({n_agents} agents):
{roster}

Observed behaviors:
{observed_behaviors}

INSTRUCTIONS:
- Return exactly 6 StructureDimensionScore objects in canonical order:
    1. specialization
    2. formalization
    3. centralization
    4. hierarchy
    5. span_of_control
    6. departmentalization
- archetype per the allowed labels.
- fit_score = 1 - abs(observed - target).
- overall_fit = mean of the 6 fit_scores.
- ``risk`` per dimension: low / medium / high based on failure cost.

DO NOT:
- Do not give all 6 dimensions the same score; they are independent.
- Do not invent evidence quotes.
- Do not reorder; canonical order required.
- Do not return prose around the JSON.

OUTPUT SCHEMA (literal JSON object):
{{
  "archetype": "flat-peer" | "hierarchical" | "centralized-functional" | "decentralized-product" | "matrix" | "mixed",
  "dimensions": [
    {{
      "dimension": "specialization" | "formalization" | "centralization" | "hierarchy" | "span_of_control" | "departmentalization",
      "observed_score": <float in [0.0, 1.0]>,
      "target_score": <float in [0.0, 1.0]>,
      "fit_score": <float in [0.0, 1.0]>,
      "explanation": "<1-3 sentences>",
      "evidence_quotes": ["<verbatim>", ...],
      "confidence": <float in [0.0, 1.0]>,
      "risk": "low" | "medium" | "high"
    }},
    ... (6 total, canonical order)
  ],
  "overall_fit": <float in [0.0, 1.0]>,
  "fit_quality": "well-fit" | "partial-fit" | "misfit",
  "biggest_gap": "<canonical dimension name or 'none'>"
}}

EXAMPLE (incident_response with low-centralization mismatch):
{{
  "dimension": "centralization",
  "observed_score": 0.20,
  "target_score": 0.85,
  "fit_score": 0.35,
  "explanation": "Three agents independently issued conflicting status updates (turns 4, 7, 11) with no incident-commander reconciliation. Mintzberg 1983 + standard incident-response heuristic: high centralization is required so that one commander owns the source of truth.",
  "evidence_quotes": ["I'm declaring SEV-2", "actually I think this is SEV-3", "I just rolled back the deploy"],
  "confidence": 0.85,
  "risk": "high"
}}

Return only the JSON object.
"""


QUICK_STRUCTURE_PROMPT = """QUICK mode -- org-structure profile + 1 top intervention.

Task: {task}
Task class: {task_class}
Outcome: {outcome}
Success: {success}

Agent roster ({n_agents} agents):
{roster}

Observed behaviors:
{observed_behaviors}

INSTRUCTIONS:
- Same 6 dimensions + canonical order as STANDARD mode.
- Pick 1 top_intervention OR null if well-fit.

DO NOT:
- Do not return more than one intervention.

OUTPUT SCHEMA: same as STRUCTURE_PROMPT plus ``top_intervention``
(one StructureIntervention or null).

Return only the JSON object.
"""


INTERVENTIONS_PROMPT = """STANDARD mode -- propose 2-4 interventions to close the biggest gap.

Task class: {task_class}
Archetype: {archetype}
Fit quality: {fit_quality}
Biggest gap: {biggest_gap}
All dimension evidence:
{evidence}

INSTRUCTIONS:
- Target biggest_gap.
- direction: increase / decrease / redesign.
- ``rationale`` cites Mintzberg 1979/1983, Galbraith 1977/2014, or Hackman 2002.

DO NOT:
- Do not target a dimension with high fit_score.
- Do not return prose around the JSON.

ALLOWED intervention_type values:
  flatten_hierarchy, add_supervisor_layer, consolidate_roles,
  split_roles, shift_decision_authority, regroup_by_product,
  regroup_by_function, introduce_matrix, add_routing_layer,
  remove_routing_layer, new_eval, human_review, compose_pattern

OUTPUT SCHEMA (literal JSON array of StructureIntervention objects):
[
  {{
    "target_dimension": "<canonical dimension>",
    "direction": "increase" | "decrease" | "redesign",
    "intervention_type": "<from the allowed set>",
    "description": "<one line>",
    "suggested_implementation": "<concrete>",
    "estimated_impact": "high" | "medium" | "low",
    "rationale": "<named source anchored>",
    "effort_estimate": "1h" | "1d" | "1w" | "1m" | "ongoing",
    "risk": "low" | "medium" | "high"
  }},
  ...
]

Return only the JSON array.
"""


FORENSIC_REPORTING_GRAPH_PROMPT = """FORENSIC mode -- analyze the reporting graph as a DAG.

Roster ({n_agents} agents):
{roster}

INSTRUCTIONS:
- depth: longest reporting path (integer).
- branching_factor: mean direct reports per supervisor (0 if no supervisors).
- cycles_detected: true if reports_to contains a cycle.
- orphans: agents with no reports_to AND nobody reports to them.
- bottleneck_agents: agents whose removal would disconnect the graph.

DO NOT:
- Do not omit cycle detection; if cycles exist, the graph is not a DAG.

OUTPUT SCHEMA (literal JSON object):
{{
  "depth": <non-negative integer>,
  "branching_factor": <non-negative float>,
  "cycles_detected": true | false,
  "orphans": ["<agent_id>", ...],
  "bottleneck_agents": ["<agent_id>", ...],
  "explanation": "<1-2 sentences>"
}}

Return only the JSON object.
"""


FORENSIC_BOTTLENECK_PROMPT = """FORENSIC mode -- identify the decision bottleneck (if any).

Task class: {task_class}
Roster:
{roster}
Observed behaviors:
{observed_behaviors}

INSTRUCTIONS:
- bottleneck_agent_id: the agent through whom too many decisions
  funnel, OR null if no bottleneck.
- affected_dimensions: list of dimensions the bottleneck blocks from
  reaching target.
- severity_estimate: low / medium / high.

DO NOT:
- Do not nominate the orchestrator as a bottleneck when high
  centralization is the target.

OUTPUT SCHEMA (literal JSON object):
{{
  "bottleneck_agent_id": "<agent_id or null>",
  "affected_dimensions": ["<canonical dimension>", ...],
  "severity_estimate": "low" | "medium" | "high",
  "explanation": "<1-2 sentences>"
}}

Return only the JSON object.
"""


FORENSIC_INTERVENTIONS_PROMPT = """FORENSIC mode -- interventions ranked by (structural-leverage x gap-size).

Task class: {task_class}
Archetype: {archetype}
Fit quality: {fit_quality}
Biggest gap: {biggest_gap}
Reporting graph: {reporting_graph}
Decision bottleneck: {decision_bottleneck}
All dimension evidence:
{evidence}

INSTRUCTIONS:
- Generate 3-6 interventions, ranked by structural leverage x gap size.
- Cite reporting_graph + decision_bottleneck findings in rationale.

DO NOT:
- Do not return fewer than 3 or more than 6 interventions.

OUTPUT SCHEMA: same as INTERVENTIONS_PROMPT.

Return only the JSON array.
"""


def assemble_prompt(
    template: str,
    /,
    *,
    roster: str = "",
    observed_behaviors: list[str] | None = None,
    **kwargs: object,
) -> str:
    """Fence + sanitize untrusted fields, then fill the template."""
    safe_roster = fence("roster", sanitize_for_prompt(roster or "(empty)"))
    behaviors = observed_behaviors or []
    if behaviors:
        behaviors_text = "\n".join(f"- {sanitize_for_prompt(b)}" for b in behaviors)
    else:
        behaviors_text = "(none)"
    safe_behaviors = fence("observed_behaviors", behaviors_text)
    fields: dict[str, object] = {
        "roster": safe_roster,
        "observed_behaviors": safe_behaviors,
    }
    fields.update(kwargs)
    return template.format(**fields)


__all__ = [
    "FORENSIC_BOTTLENECK_PROMPT",
    "FORENSIC_INTERVENTIONS_PROMPT",
    "FORENSIC_REPORTING_GRAPH_PROMPT",
    "INTERVENTIONS_PROMPT",
    "QUICK_STRUCTURE_PROMPT",
    "STRUCTURE_PROMPT",
    "STRUCTURE_SYSTEM_PROMPT",
    "assemble_prompt",
]
