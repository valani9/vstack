"""Calibration curves + metrics — pure-Python implementation.

No dependency on scikit-learn or scipy. Implements:

  - Isotonic regression via pool-adjacent-violators (PAV).
  - Platt's sigmoid calibration via simple gradient descent.
  - Brier score, log loss, expected calibration error.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence


def _clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


@dataclass
class CalibrationMetrics:
    """Standard calibration quality metrics."""

    brier_score: float
    """Mean squared error between predicted and actual probabilities."""

    log_loss: float
    """Average negative log-likelihood."""

    expected_calibration_error: float
    """Weighted average gap between average confidence and accuracy
    within each bin. Lower is better."""

    n_bins: int = 10

    def to_dict(self) -> dict[str, float]:
        return {
            "brier_score": self.brier_score,
            "log_loss": self.log_loss,
            "expected_calibration_error": self.expected_calibration_error,
            "n_bins": self.n_bins,
        }


def evaluate_calibration(
    pairs: Sequence[tuple[float, bool]],
    n_bins: int = 10,
) -> CalibrationMetrics:
    """Compute calibration metrics over (confidence, was_correct) pairs."""
    if not pairs:
        return CalibrationMetrics(brier_score=0.0, log_loss=0.0, expected_calibration_error=0.0)

    # Brier score.
    brier = sum((c - int(y)) ** 2 for c, y in pairs) / len(pairs)

    # Log loss (with epsilon to avoid log(0)).
    eps = 1e-15
    ll = -sum(
        int(y) * math.log(max(c, eps)) + (1 - int(y)) * math.log(max(1 - c, eps)) for c, y in pairs
    ) / len(pairs)

    # ECE.
    bins: list[list[tuple[float, bool]]] = [[] for _ in range(n_bins)]
    for c, y in pairs:
        idx = min(int(c * n_bins), n_bins - 1)
        bins[idx].append((c, y))

    ece = 0.0
    total = len(pairs)
    for bucket in bins:
        if not bucket:
            continue
        avg_conf = sum(c for c, _ in bucket) / len(bucket)
        acc = sum(1 for _, y in bucket if y) / len(bucket)
        ece += (len(bucket) / total) * abs(avg_conf - acc)

    return CalibrationMetrics(
        brier_score=brier,
        log_loss=ll,
        expected_calibration_error=ece,
        n_bins=n_bins,
    )


@dataclass
class IsotonicCalibration:
    """Pool-adjacent-violators isotonic calibration.

    Use to map raw LLM confidence onto a calibrated probability.
    Monotonic by construction.
    """

    breakpoints: list[float] = field(default_factory=list)
    values: list[float] = field(default_factory=list)

    @classmethod
    def fit(cls, pairs: Sequence[tuple[float, bool]]) -> IsotonicCalibration:
        """Fit an isotonic curve to (confidence, was_correct) pairs.

        Implementation: classical Pool-Adjacent-Violators using
        block aggregation. Each block holds (sum_x, sum_y, count);
        adjacent blocks merge when prior_avg > next_avg.
        """
        if not pairs:
            return cls()

        sorted_pairs = sorted(pairs, key=lambda p: p[0])

        # Block representation: list of (sum_x, sum_y, count).
        blocks: list[list[float]] = []
        for x, y in sorted_pairs:
            blocks.append([float(x), float(int(y)), 1.0])

            # Merge with previous while violation exists.
            while len(blocks) >= 2:
                prev = blocks[-2]
                curr = blocks[-1]
                prev_avg = prev[1] / prev[2]
                curr_avg = curr[1] / curr[2]
                if prev_avg <= curr_avg:
                    break
                # Merge.
                merged = [
                    prev[0] + curr[0],
                    prev[1] + curr[1],
                    prev[2] + curr[2],
                ]
                blocks.pop()
                blocks.pop()
                blocks.append(merged)

        # Convert blocks → breakpoints + values.
        breakpoints = [b[0] / b[2] for b in blocks]  # avg x
        values = [b[1] / b[2] for b in blocks]  # avg y

        return cls(breakpoints=breakpoints, values=values)

    def transform(self, raw_confidence: float) -> float:
        """Map a raw confidence value through the fitted curve."""
        if not self.breakpoints:
            return _clip(raw_confidence)

        if raw_confidence <= self.breakpoints[0]:
            return _clip(self.values[0])
        if raw_confidence >= self.breakpoints[-1]:
            return _clip(self.values[-1])

        # Linear interpolation between bracketing breakpoints.
        for i in range(len(self.breakpoints) - 1):
            lo = self.breakpoints[i]
            hi = self.breakpoints[i + 1]
            if lo <= raw_confidence <= hi:
                if hi == lo:
                    return _clip(self.values[i])
                frac = (raw_confidence - lo) / (hi - lo)
                return _clip(self.values[i] + frac * (self.values[i + 1] - self.values[i]))

        return _clip(self.values[-1])

    def transform_many(self, values: Sequence[float]) -> list[float]:
        return [self.transform(v) for v in values]

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "isotonic",
            "breakpoints": self.breakpoints,
            "values": self.values,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IsotonicCalibration:
        return cls(
            breakpoints=list(data.get("breakpoints", [])),
            values=list(data.get("values", [])),
        )

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: str | Path) -> IsotonicCalibration:
        return cls.from_dict(json.loads(Path(path).read_text()))


@dataclass
class PlattCalibration:
    """Platt's sigmoid calibration: σ(a * x + b).

    Fit via simple gradient descent on log loss.
    """

    a: float = 1.0
    b: float = 0.0

    @classmethod
    def fit(
        cls,
        pairs: Sequence[tuple[float, bool]],
        *,
        lr: float = 0.1,
        epochs: int = 200,
    ) -> PlattCalibration:
        """Fit a sigmoid to (confidence, was_correct) pairs."""
        if not pairs:
            return cls()

        a, b = 1.0, 0.0
        for _ in range(epochs):
            grad_a = 0.0
            grad_b = 0.0
            for x, y in pairs:
                p = _sigmoid(a * x + b)
                err = p - int(y)
                grad_a += err * x
                grad_b += err
            n = len(pairs)
            a -= lr * grad_a / n
            b -= lr * grad_b / n

        return cls(a=a, b=b)

    def transform(self, raw_confidence: float) -> float:
        return _clip(_sigmoid(self.a * raw_confidence + self.b))

    def transform_many(self, values: Sequence[float]) -> list[float]:
        return [self.transform(v) for v in values]

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "platt", "a": self.a, "b": self.b}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlattCalibration:
        return cls(a=data.get("a", 1.0), b=data.get("b", 0.0))

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: str | Path) -> PlattCalibration:
        return cls.from_dict(json.loads(Path(path).read_text()))
