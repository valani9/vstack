"""vstack.synth — programmatic synthetic trace generator.

The synth module generates parameterized synthetic agent traces
for testing patterns at scale. Each trace shape (stuck_in_loop,
hallucination, etc.) has a generator that produces a family of
traces by varying difficulty, length, agent count, etc.

Use cases
---------

* Generate 1000 stuck_in_loop variants for stress testing.
* Build a regression suite that exercises every pattern.
* Stress-test a pattern's calibration with synthetic adversarial
  traces.

Quick start
-----------

    from vstack.synth import (
        TraceGenerator,
        generate_stuck_in_loop,
        generate_batch,
    )

    # Single generation:
    trace = generate_stuck_in_loop(
        retry_count=5,
        outcome_severity="high",
        seed=42,
    )

    # Batch generation:
    traces = generate_batch(
        generator=generate_stuck_in_loop,
        count=100,
        seed=42,
    )
"""

from __future__ import annotations

from ._generators import (
    TraceGenerator,
    generate_anxious_overhedge,
    generate_batch,
    generate_hallucination,
    generate_healthy,
    generate_over_apology,
    generate_premature_completion,
    generate_stuck_in_loop,
    generate_sycophancy,
    generate_tool_misuse,
)
from ._templates import (
    TraceTemplate,
    register_template,
    get_template,
    list_templates,
)

__all__ = [
    "TraceGenerator",
    "TraceTemplate",
    "generate_anxious_overhedge",
    "generate_batch",
    "generate_hallucination",
    "generate_healthy",
    "generate_over_apology",
    "generate_premature_completion",
    "generate_stuck_in_loop",
    "generate_sycophancy",
    "generate_tool_misuse",
    "get_template",
    "list_templates",
    "register_template",
]
