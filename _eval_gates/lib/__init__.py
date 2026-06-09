"""vstack.eval_gates — CI gate primitives for blocking merges on regression.

The eval_gates module ships pluggable gate primitives that compose
into a single CI decision. Each gate evaluates a metric against a
threshold; a single failing gate fails the overall check.

Use cases
---------

* Pre-merge: block PRs that increase pattern false-positive rate.
* Nightly: block release if pattern accuracy drops below threshold.
* Drift: block a scorecard grade from dropping a letter.

Quick start
-----------

    from vstack.eval_gates import (
        Gate,
        GateSet,
        SeverityCountGate,
        BaselineComparisonGate,
        F1Gate,
    )

    gates = GateSet([
        SeverityCountGate(severity="high", max_count=0),
        F1Gate(min_f1=0.7),
        BaselineComparisonGate(max_score_drop=10.0),
    ])

    result = gates.check(
        report=current_report,
        baseline=baseline_report,
        eval_metrics=metrics,
    )

    if not result.passed:
        for failure in result.failures:
            print(f"{failure.gate_name}: {failure.reason}")
        sys.exit(1)
"""

from __future__ import annotations

from ._gates import (
    BaselineComparisonGate,
    CustomGate,
    F1Gate,
    Gate,
    GateFailure,
    GateResult,
    GateSet,
    PrecisionGate,
    RecallGate,
    SeverityCountGate,
)

__all__ = [
    "BaselineComparisonGate",
    "CustomGate",
    "F1Gate",
    "Gate",
    "GateFailure",
    "GateResult",
    "GateSet",
    "PrecisionGate",
    "RecallGate",
    "SeverityCountGate",
]
