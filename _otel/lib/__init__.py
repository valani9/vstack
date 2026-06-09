"""vstack.otel — OpenTelemetry exporter for vstack diagnostics.

The otel module emits OpenTelemetry spans for every diagnose() run
and every per-pattern analyzer call. Use with any OTLP-compatible
collector (Jaeger, Tempo, Honeycomb, Datadog, etc.).

Use cases
---------

* **Distributed tracing.** Correlate vstack diagnostics with
  upstream service traces (e.g., the FastAPI request that
  triggered the diagnostic).
* **Production cost tracing.** Every span carries token + cost
  attributes for fleet-wide cost rollup.
* **Latency profiling.** Find the slowest patterns; identify
  contention.

Quick start
-----------

    from vstack.otel import setup_otel
    from vstack import diagnose

    # Configure once at startup:
    setup_otel(
        service_name="vstack-prod",
        otlp_endpoint="http://otel-collector:4317",
    )

    # All vstack calls now emit spans:
    report = diagnose(trace=trace, llm_client=llm)

    # Spans carry these attributes:
    #   vstack.pattern        — pattern name
    #   vstack.mode           — quick / standard / forensic
    #   vstack.run_id         — correlation ID
    #   vstack.severity       — top finding's severity
    #   vstack.llm.tokens_in  — LLM input tokens
    #   vstack.llm.tokens_out — LLM output tokens
    #   vstack.llm.cost_usd   — call cost

The module is designed to be a no-op if OpenTelemetry is not
configured. If you don't call ``setup_otel()`` (or OpenTelemetry
isn't installed), all the instrumentation collapses to plain
function calls.
"""

from __future__ import annotations

from ._exporter import (
    OTelSpanContext,
    is_enabled,
    setup_otel,
    start_pattern_span,
    start_run_span,
)
from ._instrumented_client import OTelInstrumentedClient

__all__ = [
    "OTelInstrumentedClient",
    "OTelSpanContext",
    "is_enabled",
    "setup_otel",
    "start_pattern_span",
    "start_run_span",
]
