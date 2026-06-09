"""vstack.trace_diff — structural comparison of two agent traces.

The trace_diff module compares two ``AgentTrace`` instances and
surfaces structural differences:

  - Step count delta.
  - Step types changed (e.g., observation became error).
  - Steps inserted / removed at a position.
  - Outcome change (success → failure, etc).
  - Goal change.
  - Aligned step diff (Myers-style).

Use cases
---------

* **Regression comparison** — pre/post a prompt change.
* **Reproduction analysis** — same trace run twice, what differs?
* **A/B testing** — compare model A's trace to model B's.

Quick start
-----------

    from vstack.trace_diff import diff_traces

    delta = diff_traces(trace_before, trace_after)
    print(delta.summary())
    print(delta.to_markdown())

    if delta.is_regression():
        # success → failure, or quality declined
        ...
"""

from __future__ import annotations

from ._diff import (
    StepDiff,
    TraceDelta,
    diff_traces,
)

__all__ = [
    "StepDiff",
    "TraceDelta",
    "diff_traces",
]
