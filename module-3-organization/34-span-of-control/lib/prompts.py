"""LLM prompts for the Span-of-Control / Centralization Calculator.

0.15.0 uplift: OUTPUT SCHEMA literals + DO NOT rules + one-shot example.
Wire format unchanged.
"""

from __future__ import annotations

from vstack.aar import fence, sanitize_for_prompt

SPAN_SYSTEM_PROMPT = """You are an org-design intervention assistant grounded in:

  - **Galbraith (1977, 2014)** Star Model.
  - **Mintzberg (1979, 1983)** Structure in Fives.
  - **Hackman (2002)** Leading Teams.

You will be given six DETERMINISTICALLY-COMPUTED metrics on an AI
agent crew's structure:

  - max_span               widest supervisor span (>7 problematic; >10 severe).
  - mean_span              mean span across supervisors (>5 heavy).
  - centralization_index   fraction of decision authority concentrated
                           in top supervisors (>0.6 concerning).
  - hierarchy_depth        longest reports_to chain (>3 adds latency).
  - span_gini              inequality across the span distribution
                           (>0.4 imbalanced).
  - decision_bottleneck    composite of span + authority + incoming load
                           (>0.5 single-point-of-failure under load).

You DO NOT modify the metric values. They are computed deterministically.

Metric-to-intervention mapping (use as a guide):

  - max_span or span_gini high:
      split_supervisor_load / redistribute_subordinates / add_supervisor_layer
  - centralization_index high or decision_bottleneck high:
      delegate_decision_authority / add_redundant_path /
      remove_bottleneck_agent
  - hierarchy_depth high:
      flatten_hierarchy / consolidate_supervisors
  - mean_span low (everyone supervises 1-2 -> over-layered):
      flatten_hierarchy / consolidate_supervisors

Posture (absolute):
- **METRIC-RESPECTFUL.** Do not contradict the computed numbers.
- **TARGETED.** Each intervention names the SPECIFIC metric it relieves.
- **CONCRETE.** Implementation must specify which agents change roles / edges.
- **TERSE.** Output is read on dashboards.

Output discipline: when asked for JSON, return JSON only. No prose, no markdown fences.
"""


INTERVENTIONS_PROMPT = """STANDARD mode -- propose 2-4 structural interventions.

The crew below was diagnosed with the following metrics (values are
DETERMINISTIC; do not change them):

{metrics_table}

Bottleneck agent_ids (if any): {bottleneck_ids}
Structural-load quality: {load_quality}
Composite load score: {load_score}

Roster snapshot:
{roster}

INSTRUCTIONS:
- Target the worst-scoring metric(s) per the mapping in the system prompt.
- ``suggested_implementation`` must name WHICH agents change roles or
  reports_to edges (e.g., "agent_3 becomes supervisor of agent_7 and
  agent_8; remove the edge agent_7 -> agent_2").
- ``rationale`` cites Galbraith / Mintzberg.

DO NOT:
- Do not propose interventions that contradict the metrics (e.g.,
  flatten_hierarchy when hierarchy_depth is already 1).
- Do not propose vague "improve structure" interventions.
- Do not return prose around the JSON.

ALLOWED intervention_type values:
  add_supervisor_layer, flatten_hierarchy, split_supervisor_load,
  delegate_decision_authority, consolidate_supervisors,
  redistribute_subordinates, add_redundant_path,
  remove_bottleneck_agent, new_eval, human_review, compose_pattern

OUTPUT SCHEMA (literal JSON array of SpanIntervention objects):
[
  {{
    "target_metric": "max_span" | "mean_span" | "centralization_index" | "hierarchy_depth" | "span_gini" | "decision_bottleneck",
    "intervention_type": "<from the allowed set>",
    "description": "<1-2 sentences>",
    "suggested_implementation": "<which agents change roles / edges>",
    "estimated_impact": "high" | "medium" | "low",
    "rationale": "<Galbraith / Mintzberg anchored>",
    "effort_estimate": "1h" | "1d" | "1w" | "1m" | "ongoing",
    "risk": "low" | "medium" | "high"
  }},
  ...
]

EXAMPLE (max_span = 11 triage: split_supervisor_load with concrete edge changes):
{{
  "target_metric": "max_span",
  "intervention_type": "split_supervisor_load",
  "description": "Split supervisor_A's 11-subordinate span into two ~5-subordinate spans by introducing supervisor_B as a lieutenant.",
  "suggested_implementation": "Promote agent_4 to supervisor_B; redirect reports_to of agents 7-11 from supervisor_A to supervisor_B; supervisor_B reports to supervisor_A. Span drops from 11 to 6 + 5 + 1.",
  "estimated_impact": "high",
  "rationale": "Mintzberg 1983 + Galbraith Star Model: spans > 10 fail coordination tasks; the split halves coordination load while preserving the single line of escalation supervisor_A holds.",
  "effort_estimate": "1d",
  "risk": "low"
}}

Return only the JSON array.
"""


QUICK_TOP_INTERVENTION_PROMPT = """QUICK mode -- single top intervention.

Metrics (DETERMINISTIC):
{metrics_table}

Bottleneck agent_ids: {bottleneck_ids}

INSTRUCTIONS:
- Return one SpanIntervention targeted at the worst-scoring metric.
- Same schema as a single entry in INTERVENTIONS_PROMPT.

DO NOT:
- Do not return multiple interventions.
- Do not contradict the metric values.

OUTPUT SCHEMA (literal JSON object): single SpanIntervention with the
same field set as INTERVENTIONS_PROMPT entries.

Return only the JSON object.
"""


FORENSIC_INTERVENTIONS_PROMPT = """FORENSIC mode -- propose 3-6 interventions ranked by (severity x leverage).

Metrics (DETERMINISTIC):
{metrics_table}

Structural anomaly audit:
{structural_anomaly}

Load amplification audit:
{load_amplification}

Bottleneck agent_ids: {bottleneck_ids}
Load quality: {load_quality}

INSTRUCTIONS:
- Generate 3-6 interventions, ranked by severity x leverage.
- Cite structural_anomaly + load_amplification findings in rationale.

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
    metrics_table: str = "",
    observed_behaviors: list[str] | None = None,
    **kwargs: object,
) -> str:
    """Fence + sanitize untrusted fields, then fill the template."""
    safe_roster = fence("roster", sanitize_for_prompt(roster or "(empty)"))
    safe_metrics = sanitize_for_prompt(metrics_table or "(none)")
    behaviors = observed_behaviors or []
    if behaviors:
        behaviors_text = "\n".join(f"- {sanitize_for_prompt(b)}" for b in behaviors)
    else:
        behaviors_text = "(none)"
    safe_behaviors = fence("observed_behaviors", behaviors_text)
    fields: dict[str, object] = {
        "roster": safe_roster,
        "metrics_table": safe_metrics,
        "observed_behaviors": safe_behaviors,
    }
    fields.update(kwargs)
    return template.format(**fields)


__all__ = [
    "FORENSIC_INTERVENTIONS_PROMPT",
    "INTERVENTIONS_PROMPT",
    "QUICK_TOP_INTERVENTION_PROMPT",
    "SPAN_SYSTEM_PROMPT",
    "assemble_prompt",
]
