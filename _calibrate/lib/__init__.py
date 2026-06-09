"""vstack.calibrate — confidence calibration curves for pattern findings.

LLM self-reported confidence is poorly calibrated (overconfident on
the high end, underconfident on the low). The calibrate module
provides:

  - **Isotonic calibration**: monotonic regression mapping raw
    confidence → calibrated confidence using a held-out eval set.
  - **Platt calibration**: logistic regression alternative.
  - **Brier score / log loss / ECE**: standard calibration metrics.
  - **Curve persistence**: load + save curves as JSON.

Use cases
---------

* Per-pattern calibration tuned to a specific LLM model.
* Post-fine-tune calibration drift detection.
* Production confidence rescaling for downstream gating.

Quick start
-----------

    from vstack.calibrate import (
        IsotonicCalibration,
        evaluate_calibration,
    )

    # Eval set: list of (raw_confidence, was_correct).
    eval_set = [
        (0.95, True), (0.93, True), (0.91, False),
        (0.55, True), (0.45, False), (0.30, False),
        # ...
    ]

    cal = IsotonicCalibration.fit(eval_set)

    # Apply to new findings:
    calibrated = cal.transform(raw_confidence=0.85)

    # Inspect calibration quality:
    metrics = evaluate_calibration(eval_set)
    print(f"ECE: {metrics.expected_calibration_error:.3f}")
    print(f"Brier: {metrics.brier_score:.3f}")
"""

from __future__ import annotations

from ._calibrate import (
    CalibrationMetrics,
    IsotonicCalibration,
    PlattCalibration,
    evaluate_calibration,
)

__all__ = [
    "CalibrationMetrics",
    "IsotonicCalibration",
    "PlattCalibration",
    "evaluate_calibration",
]
