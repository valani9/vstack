"""vstack.markers — structured markers for AgentTrace steps.

The markers module provides a small DSL for annotating trace steps
with structured metadata that downstream analyzers can pivot on:

  - **Cost markers** — record cost per step.
  - **Quality markers** — record human-judged quality per step.
  - **Latency markers** — record duration per step.
  - **Safety markers** — record refusals / safety blocks per step.
  - **Custom markers** — any user-defined key/value.

Markers are pure metadata: they don't change the trace's analytic
behavior, but vstack analyzers can read them when present.

Quick start
-----------

    from vstack.markers import (
        attach_marker,
        cost_marker,
        latency_marker,
        analyze_markers,
    )

    # Mark steps:
    attach_marker(step, cost_marker(usd=0.012))
    attach_marker(step, latency_marker(ms=234))

    # Analyze:
    report = analyze_markers(trace)
    print(report.total_cost_usd)
    print(report.slow_steps)
"""

from __future__ import annotations

from ._markers import (
    CustomMarker,
    Marker,
    MarkerAnalysisReport,
    attach_marker,
    cost_marker,
    latency_marker,
    quality_marker,
    safety_marker,
    analyze_markers,
)

__all__ = [
    "CustomMarker",
    "Marker",
    "MarkerAnalysisReport",
    "analyze_markers",
    "attach_marker",
    "cost_marker",
    "latency_marker",
    "quality_marker",
    "safety_marker",
]
