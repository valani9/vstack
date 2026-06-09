"""vstack.veval — pattern-vs-ground-truth evaluation harness.

The veval module evaluates a pattern's findings against known
ground truth labels, computing precision, recall, F1, accuracy,
and a confusion matrix. Use to:

  - Track pattern quality regression across releases.
  - Compare two pattern versions on the same labeled set.
  - Set CI gates on pattern accuracy.

Quick start
-----------

    from vstack.veval import (
        EvalCase,
        EvalHarness,
        compute_metrics,
    )

    cases = [
        EvalCase(
            trace=trace1,
            expected_severity="high",
            expected_pattern="lewin",
        ),
        EvalCase(
            trace=trace2,
            expected_severity="low",
            expected_pattern="lewin",
        ),
    ]

    harness = EvalHarness(cases=cases, pattern="lewin")
    result = harness.run(llm_client=llm)
    metrics = compute_metrics(result)
    print(f"F1: {metrics.f1:.3f}")
"""

from __future__ import annotations

from ._eval import (
    ConfusionMatrix,
    EvalCase,
    EvalHarness,
    EvalMetrics,
    EvalResult,
    EvalRun,
    compute_metrics,
)

__all__ = [
    "ConfusionMatrix",
    "EvalCase",
    "EvalHarness",
    "EvalMetrics",
    "EvalResult",
    "EvalRun",
    "compute_metrics",
]
