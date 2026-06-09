"""Tests for the grade scale and score-to-grade mapping."""

from __future__ import annotations

import pytest

from vstack.scorecard import (
    GRADE_SCALE,
    score_to_grade,
)
from vstack.scorecard._grade import (
    gpa_to_letter,
    grade_to_color,
    grade_to_emoji,
    trend_arrow,
)


class TestScoreToGrade:
    def test_perfect_score(self):
        assert score_to_grade(100).letter == "A+"

    def test_a_plus_range(self):
        for s in range(95, 101):
            assert score_to_grade(s).letter == "A+"

    def test_a_range(self):
        for s in range(90, 95):
            assert score_to_grade(s).letter == "A"

    def test_a_minus_range(self):
        for s in range(87, 90):
            assert score_to_grade(s).letter == "A-"

    def test_b_plus_range(self):
        for s in range(83, 87):
            assert score_to_grade(s).letter == "B+"

    def test_b_range(self):
        for s in range(80, 83):
            assert score_to_grade(s).letter == "B"

    def test_b_minus_range(self):
        for s in range(77, 80):
            assert score_to_grade(s).letter == "B-"

    def test_c_plus_range(self):
        for s in range(73, 77):
            assert score_to_grade(s).letter == "C+"

    def test_c_range(self):
        for s in range(70, 73):
            assert score_to_grade(s).letter == "C"

    def test_c_minus_range(self):
        for s in range(67, 70):
            assert score_to_grade(s).letter == "C-"

    def test_d_plus_range(self):
        for s in range(63, 67):
            assert score_to_grade(s).letter == "D+"

    def test_d_range(self):
        for s in range(60, 63):
            assert score_to_grade(s).letter == "D"

    def test_d_minus_range(self):
        for s in range(57, 60):
            assert score_to_grade(s).letter == "D-"

    def test_failing(self):
        for s in (0, 25, 50, 56):
            assert score_to_grade(s).letter == "F"

    def test_clamps_below_zero(self):
        assert score_to_grade(-10).letter == "F"

    def test_clamps_above_100(self):
        assert score_to_grade(200).letter == "A+"

    def test_float_scores_round(self):
        assert score_to_grade(89.4).letter == "A-"
        assert score_to_grade(89.6).letter == "A"


class TestGrade:
    def test_grade_str_returns_letter(self):
        g = score_to_grade(95)
        assert str(g) == "A+"

    def test_failing_grade_is_failing(self):
        assert score_to_grade(50).is_failing
        assert not score_to_grade(70).is_failing

    def test_passing_grade_is_passing(self):
        assert score_to_grade(70).is_passing
        assert not score_to_grade(50).is_passing

    def test_gpa_value_a_plus(self):
        assert score_to_grade(100).gpa_value == 4.0

    def test_gpa_value_a(self):
        assert score_to_grade(92).gpa_value == 4.0

    def test_gpa_value_a_minus(self):
        assert score_to_grade(88).gpa_value == 3.7

    def test_gpa_value_b_plus(self):
        assert score_to_grade(85).gpa_value == 3.3

    def test_gpa_value_b(self):
        assert score_to_grade(81).gpa_value == 3.0

    def test_gpa_value_f(self):
        assert score_to_grade(0).gpa_value == 0.0


class TestGradeScale:
    def test_scale_covers_full_range(self):
        # Every integer from 0 to 100 should map to exactly one grade.
        for s in range(0, 101):
            grades = [g for g in GRADE_SCALE if g.min_score <= s <= g.max_score]
            assert len(grades) == 1, f"score {s} mapped to {len(grades)} grades"

    def test_scale_is_ordered_a_first(self):
        assert GRADE_SCALE[0].letter == "A+"
        assert GRADE_SCALE[-1].letter == "F"


class TestColorAndEmoji:
    def test_a_grade_color_is_green(self):
        assert grade_to_color(score_to_grade(95)) == "#15803d"

    def test_b_grade_color_is_lime(self):
        assert grade_to_color(score_to_grade(82)) == "#65a30d"

    def test_c_grade_color_is_amber(self):
        assert grade_to_color(score_to_grade(72)) == "#ca8a04"

    def test_d_grade_color_is_orange(self):
        assert grade_to_color(score_to_grade(61)) == "#ea580c"

    def test_f_grade_color_is_red(self):
        assert grade_to_color(score_to_grade(0)) == "#b91c1c"

    def test_a_grade_emoji_is_green_circle(self):
        assert grade_to_emoji(score_to_grade(95)) == "🟢"

    def test_f_grade_emoji_is_black_circle(self):
        assert grade_to_emoji(score_to_grade(0)) == "⚫"


class TestTrendArrow:
    def test_strong_improvement(self):
        assert trend_arrow(20) == "↗"

    def test_strong_regression(self):
        assert trend_arrow(-20) == "↘"

    def test_stable(self):
        assert trend_arrow(2) == "→"
        assert trend_arrow(-2) == "→"
        assert trend_arrow(0) == "→"

    def test_boundary(self):
        # Just at threshold.
        assert trend_arrow(5) == "→"
        assert trend_arrow(-5) == "→"
        assert trend_arrow(6) == "↗"
        assert trend_arrow(-6) == "↘"


class TestGpaToLetter:
    def test_perfect(self):
        assert gpa_to_letter(4.0) == "A+"

    def test_3_5(self):
        assert gpa_to_letter(3.5) == "A-"

    def test_2_0(self):
        assert gpa_to_letter(2.0) == "C"

    def test_zero(self):
        assert gpa_to_letter(0.0) == "F"


@pytest.mark.parametrize(
    "score,expected_letter",
    [
        (100, "A+"),
        (95, "A+"),
        (94, "A"),
        (90, "A"),
        (89, "A-"),
        (87, "A-"),
        (86, "B+"),
        (83, "B+"),
        (82, "B"),
        (80, "B"),
        (79, "B-"),
        (77, "B-"),
        (76, "C+"),
        (73, "C+"),
        (72, "C"),
        (70, "C"),
        (69, "C-"),
        (67, "C-"),
        (66, "D+"),
        (63, "D+"),
        (62, "D"),
        (60, "D"),
        (59, "D-"),
        (57, "D-"),
        (56, "F"),
        (0, "F"),
    ],
)
def test_score_to_grade_parameterized(score, expected_letter):
    assert score_to_grade(score).letter == expected_letter
