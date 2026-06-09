"""Scorecard comparison — compute the delta between two scorecards
for drift detection across releases.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ._compute import DimensionName, ScoreCard
from ._grade import Grade, score_to_grade, trend_arrow


@dataclass
class DimensionDelta:
    """A single dimension's change between two scorecards."""

    name: DimensionName
    score_before: float
    score_after: float
    grade_before: Grade
    grade_after: Grade

    @property
    def delta(self) -> float:
        return self.score_after - self.score_before

    @property
    def grade_changed(self) -> bool:
        return self.grade_before.letter != self.grade_after.letter

    @property
    def is_regression(self) -> bool:
        return self.score_after + 5 < self.score_before

    @property
    def is_improvement(self) -> bool:
        return self.score_after > self.score_before + 5

    @property
    def trend(self) -> str:
        return trend_arrow(self.delta)


@dataclass
class ScoreCardComparison:
    """Full comparison of two scorecards.

    Useful for:
      - CI gates on scorecard regression.
      - Quarterly review of fleet trend.
      - Pre-release validation against a previous-release baseline.
    """

    before: ScoreCard
    after: ScoreCard
    dimension_deltas: dict[DimensionName, DimensionDelta]
    new_patterns: list[str] = field(default_factory=list)
    removed_patterns: list[str] = field(default_factory=list)

    @property
    def overall_score_before(self) -> float:
        return self.before.overall_score

    @property
    def overall_score_after(self) -> float:
        return self.after.overall_score

    @property
    def overall_delta(self) -> float:
        return self.overall_score_after - self.overall_score_before

    @property
    def overall_grade_before(self) -> Grade:
        return self.before.overall_grade

    @property
    def overall_grade_after(self) -> Grade:
        return self.after.overall_grade

    @property
    def has_regression(self) -> bool:
        return any(d.is_regression for d in self.dimension_deltas.values())

    @property
    def has_improvement(self) -> bool:
        return any(d.is_improvement for d in self.dimension_deltas.values())

    @property
    def regressed_dimensions(self) -> list[DimensionDelta]:
        return [d for d in self.dimension_deltas.values() if d.is_regression]

    @property
    def improved_dimensions(self) -> list[DimensionDelta]:
        return [d for d in self.dimension_deltas.values() if d.is_improvement]

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_before": self.overall_score_before,
            "overall_after": self.overall_score_after,
            "overall_delta": self.overall_delta,
            "overall_grade_before": self.overall_grade_before.letter,
            "overall_grade_after": self.overall_grade_after.letter,
            "has_regression": self.has_regression,
            "has_improvement": self.has_improvement,
            "dimension_deltas": {
                name: {
                    "score_before": d.score_before,
                    "score_after": d.score_after,
                    "delta": d.delta,
                    "grade_before": d.grade_before.letter,
                    "grade_after": d.grade_after.letter,
                    "grade_changed": d.grade_changed,
                    "trend": d.trend,
                }
                for name, d in self.dimension_deltas.items()
            },
            "new_patterns": self.new_patterns,
            "removed_patterns": self.removed_patterns,
        }

    def to_markdown(self) -> str:
        lines = ["# Scorecard Comparison", ""]
        lines.append(
            f"**Overall**: {self.overall_grade_before.letter} "
            f"({self.overall_score_before:.1f}) → "
            f"{self.overall_grade_after.letter} "
            f"({self.overall_score_after:.1f}) "
            f"{trend_arrow(self.overall_delta)} {self.overall_delta:+.1f}"
        )
        lines.append("")

        if self.has_regression:
            lines.append("## ⚠️ Regressions")
            for d in self.regressed_dimensions:
                lines.append(
                    f"- **{d.name}**: {d.grade_before.letter} → "
                    f"{d.grade_after.letter} ({d.delta:+.1f})"
                )
            lines.append("")

        if self.has_improvement:
            lines.append("## ✓ Improvements")
            for d in self.improved_dimensions:
                lines.append(
                    f"- **{d.name}**: {d.grade_before.letter} → "
                    f"{d.grade_after.letter} ({d.delta:+.1f})"
                )
            lines.append("")

        lines.append("## All dimensions")
        lines.append("")
        lines.append("| Dimension     | Before | After  | Delta   | Trend |")
        lines.append("|---------------|--------|--------|---------|-------|")
        for name in ("reasoning", "coordination", "trust", "workload", "culture"):
            d = self.dimension_deltas.get(name)
            if d is None:
                continue
            lines.append(
                f"| {name:13s} | "
                f"{d.grade_before.letter:6s} | "
                f"{d.grade_after.letter:6s} | "
                f"{d.delta:+6.1f}  | {d.trend}     |"
            )
        return "\n".join(lines)


def compare_scorecards(before: ScoreCard, after: ScoreCard) -> ScoreCardComparison:
    """Compute the delta between two scorecards."""
    dimension_deltas: dict[DimensionName, DimensionDelta] = {}
    for name in ("reasoning", "coordination", "trust", "workload", "culture"):
        b = before.get_dimension(name)
        a = after.get_dimension(name)
        if b is None or a is None:
            continue
        dimension_deltas[name] = DimensionDelta(
            name=name,
            score_before=b.score,
            score_after=a.score,
            grade_before=b.grade,
            grade_after=a.grade,
        )

    before_patterns = {p.pattern for p in before.pattern_contributions}
    after_patterns = {p.pattern for p in after.pattern_contributions}

    return ScoreCardComparison(
        before=before,
        after=after,
        dimension_deltas=dimension_deltas,
        new_patterns=sorted(after_patterns - before_patterns),
        removed_patterns=sorted(before_patterns - after_patterns),
    )


def is_blocking_regression(
    comparison: ScoreCardComparison,
    *,
    grade_threshold: str = "C",
    score_threshold: float = 10.0,
) -> bool:
    """Return True if the comparison shows a regression worth blocking
    on (e.g., for a CI gate).

    A regression is blocking if EITHER:
      - Overall score dropped by ``score_threshold`` or more, OR
      - Any dimension dropped to a grade worse than ``grade_threshold``.
    """
    threshold_grade_obj = score_to_grade(_grade_letter_to_score(grade_threshold))

    if comparison.overall_delta < -score_threshold:
        return True

    for d in comparison.dimension_deltas.values():
        if d.grade_after.gpa_value < threshold_grade_obj.gpa_value:
            if d.grade_before.gpa_value >= threshold_grade_obj.gpa_value:
                # Was above threshold, now below.
                return True

    return False


def _grade_letter_to_score(letter: str) -> float:
    """Approximate inverse of score_to_grade for threshold computation."""
    mapping = {
        "A+": 95.0,
        "A": 90.0,
        "A-": 87.0,
        "B+": 83.0,
        "B": 80.0,
        "B-": 77.0,
        "C+": 73.0,
        "C": 70.0,
        "C-": 67.0,
        "D+": 63.0,
        "D": 60.0,
        "D-": 57.0,
        "F": 0.0,
    }
    return mapping.get(letter, 70.0)
