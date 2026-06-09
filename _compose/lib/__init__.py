"""vstack.compose — declarative pattern pipeline composition.

The compose module provides a fluent builder for chaining vstack
patterns into a pipeline. Each step can be conditional, retry on
failure, or branch based on prior results.

Quick start
-----------

    from vstack.compose import Pipeline

    pipeline = (
        Pipeline("incident_triage")
        .step("lewin", mode="standard")
        .step("yerkes_dodson", mode="quick")
        .when_severity("high", run="bias_stack")
        .then("aar", mode="forensic")
        .with_baseline("baselines/incident-triage.json")
    )

    result = pipeline.run(trace, llm_client=client)
    print(result.dimension_summary())

Why declarative composition
---------------------------

The Python ``diagnose()`` API is imperative: you build the trace,
call ``diagnose()``, inspect findings. Pipelines instead capture
the *intent* of a multi-pattern chain — and the same Pipeline can
be reused across many traces, exported as JSON for sharing, or
loaded from config.
"""

from __future__ import annotations

from ._pipeline import (
    Pipeline,
    PipelineResult,
    PipelineStep,
    Stop,
)

__all__ = [
    "Pipeline",
    "PipelineResult",
    "PipelineStep",
    "Stop",
]
