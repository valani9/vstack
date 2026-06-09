"""Letter-grade scale and score-to-grade mapping.

The grade scale is fixed at module level so all scorecards across
a fleet use the same calibration. Users who want a custom scale
should construct a ``ScoreCardConfig`` with their own
``grade_scale=``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

GradeLetter = Literal[
    "A+",
    "A",
    "A-",
    "B+",
    "B",
    "B-",
    "C+",
    "C",
    "C-",
    "D+",
    "D",
    "D-",
    "F",
]


@dataclass(frozen=True)
class Grade:
    """A letter grade with an associated numeric range.

    The numeric score is on a 0-100 scale where:
      - 95-100 = A+
      - 90-94  = A
      - 87-89  = A-
      - 83-86  = B+
      - 80-82  = B
      - 77-79  = B-
      - 73-76  = C+
      - 70-72  = C
      - 67-69  = C-
      - 63-66  = D+
      - 60-62  = D
      - 57-59  = D-
      - 0-56   = F
    """

    letter: GradeLetter
    min_score: int
    max_score: int

    def __str__(self) -> str:
        return self.letter

    @property
    def is_failing(self) -> bool:
        return self.letter == "F"

    @property
    def is_passing(self) -> bool:
        return self.letter != "F"

    @property
    def gpa_value(self) -> float:
        """Standard US 4-point GPA scale."""
        return {
            "A+": 4.0,
            "A": 4.0,
            "A-": 3.7,
            "B+": 3.3,
            "B": 3.0,
            "B-": 2.7,
            "C+": 2.3,
            "C": 2.0,
            "C-": 1.7,
            "D+": 1.3,
            "D": 1.0,
            "D-": 0.7,
            "F": 0.0,
        }[self.letter]


GRADE_SCALE: list[Grade] = [
    Grade("A+", 95, 100),
    Grade("A", 90, 94),
    Grade("A-", 87, 89),
    Grade("B+", 83, 86),
    Grade("B", 80, 82),
    Grade("B-", 77, 79),
    Grade("C+", 73, 76),
    Grade("C", 70, 72),
    Grade("C-", 67, 69),
    Grade("D+", 63, 66),
    Grade("D", 60, 62),
    Grade("D-", 57, 59),
    Grade("F", 0, 56),
]


def score_to_grade(score: float, scale: list[Grade] | None = None) -> Grade:
    """Map a numeric score (0-100) to a letter Grade.

    Scores below 0 are clamped to F; scores above 100 are clamped
    to A+. ``scale`` defaults to :data:`GRADE_SCALE`.
    """
    grades = scale if scale is not None else GRADE_SCALE
    clamped = max(0, min(100, int(round(score))))

    for grade in grades:
        if grade.min_score <= clamped <= grade.max_score:
            return grade

    # Should be unreachable given the scale covers 0-100.
    return grades[-1]


def grade_to_color(grade: Grade) -> str:
    """Return a hex colour suitable for HTML rendering."""
    if grade.letter.startswith("A"):
        return "#15803d"  # green
    if grade.letter.startswith("B"):
        return "#65a30d"  # lime
    if grade.letter.startswith("C"):
        return "#ca8a04"  # amber
    if grade.letter.startswith("D"):
        return "#ea580c"  # orange
    return "#b91c1c"  # red


def grade_to_emoji(grade: Grade) -> str:
    """Return an emoji suitable for terminal rendering."""
    if grade.letter.startswith("A"):
        return "🟢"
    if grade.letter.startswith("B"):
        return "🟡"
    if grade.letter.startswith("C"):
        return "🟠"
    if grade.letter.startswith("D"):
        return "🔴"
    return "⚫"


def trend_arrow(delta: float) -> str:
    """Return an arrow indicating the direction of change."""
    if delta > 5:
        return "↗"  # improving
    if delta < -5:
        return "↘"  # regressing
    return "→"  # stable


def gpa_to_letter(gpa: float) -> str:
    """Inverse of Grade.gpa_value — approximates a letter from a GPA."""
    if gpa >= 3.95:
        return "A+"
    if gpa >= 3.85:
        return "A"
    if gpa >= 3.5:
        return "A-"
    if gpa >= 3.15:
        return "B+"
    if gpa >= 2.85:
        return "B"
    if gpa >= 2.5:
        return "B-"
    if gpa >= 2.15:
        return "C+"
    if gpa >= 1.85:
        return "C"
    if gpa >= 1.5:
        return "C-"
    if gpa >= 1.15:
        return "D+"
    if gpa >= 0.85:
        return "D"
    if gpa >= 0.5:
        return "D-"
    return "F"
