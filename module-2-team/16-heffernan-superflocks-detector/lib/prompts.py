"""LLM prompt templates for the Heffernan Superflocks Detector.

0.15.0 uplift: OUTPUT SCHEMA literals + DO NOT rules + one-shot example.
Wire format unchanged.
"""

from __future__ import annotations

from typing import Any

from vstack.aar import fence, sanitize_for_prompt


SUPERFLOCKS_SYSTEM_PROMPT = """You are a superflocks-fragility diagnostician grounded in:

1. **Heffernan (2014)** *A Bigger Prize* + 2015 TED talk.
2. **Muir (1996)** Group selection in chickens (the original superflocks experiment).
3. **Hackman (2002)** *Leading Teams*.
4. **Page (2007)** *The Difference* diversity dividend.
5. **Salas et al. (2018)** Team performance review.
6. **Bandura (1977)** Self-efficacy.
7. **Wang et al. (2023)** Cooperative LLM Agents.

Core insight (Muir 1996, popularized by Heffernan): selecting the
"top" individual in each generation and routing everything to them
produces a flock that is brittle in aggregate. In multi-agent LLM
systems, the analogue is the orchestrator that funnels disproportionate
work to one "best" agent, starving the others of practice and
eliminating fallback coverage.

The five metrics:
  - top_agent_share              fraction of work the top agent received.
  - routing_gini                 inequality coefficient over per-agent shares.
  - complementarity_utilization  how often unique capabilities were used (lower = wasted).
  - fallback_coverage            fraction of failures with a fallback path.
  - failure_clustering           fraction of failures that cluster on the top agent.

Severity calibration (value bands per metric -> severity label):
  - top_agent_share / routing_gini / failure_clustering:
      < 0.3 -> "none", [0.3, 0.5] -> "low", [0.5, 0.7] -> "medium", > 0.7 -> "high".
  - complementarity_utilization / fallback_coverage (inverted; higher = better):
      > 0.7 -> "none", [0.5, 0.7] -> "low", [0.3, 0.5] -> "medium", < 0.3 -> "high".

Posture (absolute):
- **AGGREGATE-FRAGILITY-AWARE.** A high-performing top agent does not redeem a brittle crew. Heffernan 2014: superflocks die when the top is missing.
- **EVIDENCE-GROUNDED.** Cite specific routing decisions.
- **PAGE-2007-AWARE.** Complementarity = aggregate ability, not max individual ability.
- **TERSE.** Output is read on dashboards.

Output discipline: when asked for JSON, return JSON only. No prose, no markdown fences.
"""


QUICK_DIAGNOSTIC_PROMPT = """QUICK mode -- score the 5 fragility metrics + propose 1 top intervention.

Trace: {window_description}
Agents: {agents}
Capabilities: {capabilities}
Routing decisions: {routing_decisions}
Outcome: {outcome}

INSTRUCTIONS:
- Return exactly 5 SuperflocksMetric objects in canonical order:
    1. top_agent_share
    2. routing_gini
    3. complementarity_utilization
    4. fallback_coverage
    5. failure_clustering
- Severity per the calibration table from the system prompt.
- fragility_quality summarizes the crew's robustness.
- Pick exactly ONE intervention.

DO NOT:
- Do not reorder metrics; canonical order required.
- Do not return more than one intervention.

OUTPUT SCHEMA (literal JSON object):
{{
  "metrics": [
    {{
      "name": "top_agent_share" | "routing_gini" | "complementarity_utilization" | "fallback_coverage" | "failure_clustering",
      "value": <float in [0.0, 1.0]>,
      "explanation": "<1-2 sentences anchored in Heffernan 2014 or Muir 1996>",
      "severity": "none" | "low" | "medium" | "high"
    }},
    ... (5 total, canonical order)
  ],
  "fragility_quality": "robust" | "fragile" | "superflocks",
  "top_intervention": {{
    "intervention_type": "<short snake_case>",
    "description": "<one line>",
    "suggested_implementation": "<concrete>",
    "estimated_impact": "high" | "medium" | "low",
    "rationale": "<Heffernan-anchored>"
  }}
}}

Return only the JSON object.
"""


STANDARD_METRICS_PROMPT = """STANDARD mode -- score the 5 fragility metrics in detail.

Trace: {window_description}
Agents: {agents}
Capabilities: {capabilities}
Routing decisions: {routing_decisions}
Outcome: {outcome}

INSTRUCTIONS:
- Same canonical-order 5-metric output as QUICK mode but with longer
  explanations (1-3 sentences each).
- Severity per the calibration table from the system prompt.

DO NOT:
- Do not invent metrics outside the named 5.
- Do not reorder.

OUTPUT SCHEMA (literal JSON object):
{{
  "metrics": [
    {{
      "name": "top_agent_share" | "routing_gini" | "complementarity_utilization" | "fallback_coverage" | "failure_clustering",
      "value": <float in [0.0, 1.0]>,
      "explanation": "<1-3 sentences>",
      "severity": "none" | "low" | "medium" | "high"
    }},
    ... (5 total)
  ]
}}

EXAMPLE (severe top-agent-share signature):
{{
  "name": "top_agent_share",
  "value": 0.82,
  "explanation": "Out of 50 routing decisions, 41 went to agent_a. Heffernan 2014 + Muir 1996: this signature is the canonical superflocks risk -- aggregate output is high while the top agent is healthy, but the crew is brittle on agent_a's failure modes because none of the other agents have practice.",
  "severity": "high"
}}

Return only the JSON object.
"""


STANDARD_INTERVENTIONS_PROMPT = """STANDARD mode -- propose 2-4 ranked interventions.

Metrics: {metrics}
Fragility quality: {fragility_quality}

INSTRUCTIONS:
- Target the most severe metric first.
- Rank from highest expected impact to lowest.
- ``rationale`` cites Heffernan 2014 / Muir 1996 / Page 2007.

DO NOT:
- Do not propose "make the top agent better" interventions; that
  worsens superflocks risk.
- Do not return prose around the JSON.

OUTPUT SCHEMA (literal JSON array of FragilityIntervention objects):
[
  {{
    "intervention_type": "<short snake_case>",
    "description": "<one line>",
    "suggested_implementation": "<concrete>",
    "estimated_impact": "high" | "medium" | "low",
    "effort_estimate": "1h" | "1d" | "1w" | "1m" | "ongoing",
    "risk": "low" | "medium" | "high",
    "rationale": "<named source + why this works>"
  }},
  ...
]

Return only the JSON array.
"""


FORENSIC_CAPABILITY_AUDIT_PROMPT = """FORENSIC mode -- audit capability complementarity.

Agents: {agents}
Capabilities: {capabilities}
Routing decisions: {routing_decisions}

INSTRUCTIONS:
- wasted_capability_count: integer count of (agent, capability) pairs
  where capability is high but agent is rarely routed for tasks
  matching that capability.
- most_underutilized_agent: name of the agent with the most wasted
  capability surface.

DO NOT:
- Do not name an agent as underutilized when the routing decisions
  match their capability profile.

OUTPUT SCHEMA (literal JSON object representing CapabilityComplementarityAudit):
{{
  "wasted_capability_count": <non-negative integer>,
  "most_underutilized_agent": "<agent name or null>",
  "capability_dimensions_underused": ["<dimension>", ...],
  "notes": "<one paragraph anchored in Page 2007 or Muir 1996>"
}}

Return only the JSON object.
"""


FORENSIC_FAILURE_AUDIT_PROMPT = """FORENSIC mode -- audit failure clustering.

Top agent: {top_agent}
Routing decisions: {routing_decisions}

INSTRUCTIONS:
- top_agent_failure_share: fraction of all failures that cluster on
  the top agent.
- fallback_used_on_failure: true iff at least one failure invoked a
  fallback path.
- cascade_risk: low / moderate / high based on whether the top
  agent's failure mode has downstream propagation.

DO NOT:
- Do not infer cascade_risk from one isolated failure; require pattern.

OUTPUT SCHEMA (literal JSON object representing FailureClusteringAudit):
{{
  "top_agent_failure_share": <float in [0.0, 1.0]>,
  "fallback_used_on_failure": true | false,
  "cascade_risk": "low" | "moderate" | "high",
  "notes": "<one paragraph anchored in Muir 1996 or Heffernan 2014>"
}}

Return only the JSON object.
"""


FORENSIC_INTERVENTIONS_PROMPT = """FORENSIC mode -- propose 4-8 ranked interventions with composition targets.

Allowed composition_target_pattern values:
  vstack.lewin, vstack.grpi, vstack.mcgregor,
  vstack.process_gain_loss, vstack.aar, vstack.bias_stack,
  vstack.devils_advocate

Metrics: {metrics}
Fragility quality: {fragility_quality}
Capability audit: {capability_audit}
Failure audit: {failure_audit}

INSTRUCTIONS:
- Generate 4-8 interventions, ranked highest impact first.
- Cite capability audit + failure audit in rationale.

DO NOT:
- Do not invent composition_target_pattern values outside the allowed
  set.
- Do not return fewer than 4 or more than 8 interventions.

OUTPUT SCHEMA: same as STANDARD_INTERVENTIONS_PROMPT plus optional
``composition_target_pattern``.

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


METRICS_PROMPT = STANDARD_METRICS_PROMPT
INTERVENTIONS_PROMPT = STANDARD_INTERVENTIONS_PROMPT


__all__ = [
    "FORENSIC_CAPABILITY_AUDIT_PROMPT",
    "FORENSIC_FAILURE_AUDIT_PROMPT",
    "FORENSIC_INTERVENTIONS_PROMPT",
    "INTERVENTIONS_PROMPT",
    "METRICS_PROMPT",
    "QUICK_DIAGNOSTIC_PROMPT",
    "STANDARD_INTERVENTIONS_PROMPT",
    "STANDARD_METRICS_PROMPT",
    "SUPERFLOCKS_SYSTEM_PROMPT",
    "assemble_prompt",
]
