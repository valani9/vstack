"""vstack.tracer — inline trace recorder for live agents.

The tracer module provides a small fluent recorder that lets agents
emit trace steps without pre-knowing the trace's final structure.

Use cases
---------

* **In-loop instrumentation**: an agent records each thought / tool_call
  / observation as it happens; the tracer assembles the trace at the
  end.
* **Context manager wrap**: scope a trace to a `with` block.
* **Async support**: same API works in async contexts.

Quick start
-----------

    from vstack.tracer import Tracer

    with Tracer(goal="My task") as tracer:
        tracer.thought("Starting task")
        result = run_some_tool()
        tracer.tool_call("my_tool", "args")
        tracer.observation(str(result))
        tracer.decision("Marking done")

    # At exit, tracer.trace contains the final AgentTrace.
    diagnose(tracer.trace, llm_client=client)
"""

from __future__ import annotations

from ._tracer import (
    StepRecord,
    Tracer,
)

__all__ = [
    "StepRecord",
    "Tracer",
]
