"""Tests for the calibration module."""

from __future__ import annotations

from pathlib import Path


from vstack.calibrate import (
    IsotonicCalibration,
    PlattCalibration,
    evaluate_calibration,
)


class TestEvaluateCalibration:
    def test_empty_returns_zeros(self):
        metrics = evaluate_calibration([])
        assert metrics.brier_score == 0.0
        assert metrics.log_loss == 0.0

    def test_perfect_predictions_low_brier(self):
        pairs = [(1.0, True), (0.0, False)] * 50
        metrics = evaluate_calibration(pairs)
        assert metrics.brier_score < 0.01

    def test_terrible_predictions_high_brier(self):
        pairs = [(1.0, False), (0.0, True)] * 50
        metrics = evaluate_calibration(pairs)
        assert metrics.brier_score > 0.9

    def test_calibrated_50_50_has_low_ece(self):
        # Confidence = 0.5 for all; half right.
        pairs = [(0.5, True)] * 50 + [(0.5, False)] * 50
        metrics = evaluate_calibration(pairs)
        assert metrics.expected_calibration_error < 0.05

    def test_overconfident_high_ece(self):
        # All 0.9 confidence; only 30% correct.
        pairs = [(0.9, True)] * 30 + [(0.9, False)] * 70
        metrics = evaluate_calibration(pairs)
        assert metrics.expected_calibration_error > 0.3

    def test_to_dict(self):
        metrics = evaluate_calibration([(0.5, True)] * 10)
        data = metrics.to_dict()
        assert "brier_score" in data
        assert "log_loss" in data
        assert "expected_calibration_error" in data


class TestIsotonicCalibration:
    def test_empty_pairs_returns_identity(self):
        cal = IsotonicCalibration.fit([])
        # Empty curve — transform returns clipped input.
        assert cal.transform(0.5) == 0.5

    def test_monotonic(self):
        pairs = [
            (0.1, False),
            (0.2, False),
            (0.3, True),
            (0.5, True),
            (0.7, True),
            (0.9, True),
        ]
        cal = IsotonicCalibration.fit(pairs)

        # Curve should be monotonic.
        xs = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
        ys = [cal.transform(x) for x in xs]
        for i in range(len(ys) - 1):
            assert ys[i] <= ys[i + 1] + 1e-9

    def test_clipping(self):
        pairs = [(0.5, True), (0.5, False)]
        cal = IsotonicCalibration.fit(pairs)
        # Outside breakpoints — clipped.
        assert 0.0 <= cal.transform(-1.0) <= 1.0
        assert 0.0 <= cal.transform(2.0) <= 1.0

    def test_transform_many(self):
        pairs = [(0.1, False), (0.9, True)] * 10
        cal = IsotonicCalibration.fit(pairs)
        results = cal.transform_many([0.0, 0.5, 1.0])
        assert len(results) == 3

    def test_save_load_roundtrip(self, tmp_path: Path):
        pairs = [(0.1, False), (0.5, True), (0.9, True)] * 5
        cal = IsotonicCalibration.fit(pairs)
        path = tmp_path / "cal.json"
        cal.save(path)
        loaded = IsotonicCalibration.load(path)

        # Transformations should match.
        for x in (0.0, 0.3, 0.7, 1.0):
            assert abs(cal.transform(x) - loaded.transform(x)) < 1e-9

    def test_to_dict_kind_isotonic(self):
        cal = IsotonicCalibration.fit([(0.5, True)] * 10)
        data = cal.to_dict()
        assert data["kind"] == "isotonic"

    def test_overconfident_curve_pulls_down(self):
        # Mixed: high-confidence ones only 30% correct; low ones 5%.
        pairs = (
            [(0.95, True)] * 30
            + [(0.95, False)] * 70  # 30% at 0.95
            + [(0.10, True)] * 5
            + [(0.10, False)] * 95  # 5% at 0.10
        )
        cal = IsotonicCalibration.fit(pairs)
        # Calibrated value at 0.95 should be much lower (closer to 0.3).
        assert cal.transform(0.95) < 0.5


class TestPlattCalibration:
    def test_empty_pairs(self):
        cal = PlattCalibration.fit([])
        # Default params should still produce valid output.
        result = cal.transform(0.5)
        assert 0.0 <= result <= 1.0

    def test_fits_overconfident(self):
        pairs = [(0.9, True)] * 30 + [(0.9, False)] * 70
        cal = PlattCalibration.fit(pairs, epochs=500)
        # Overconfident calibration should pull 0.9 down.
        assert cal.transform(0.9) < 0.8

    def test_transform_returns_probability(self):
        cal = PlattCalibration()
        assert 0.0 <= cal.transform(0.5) <= 1.0
        assert 0.0 <= cal.transform(-100) <= 1.0
        assert 0.0 <= cal.transform(100) <= 1.0

    def test_transform_many(self):
        cal = PlattCalibration()
        results = cal.transform_many([0.0, 0.5, 1.0])
        assert len(results) == 3

    def test_save_load_roundtrip(self, tmp_path: Path):
        pairs = [(0.1, False), (0.5, True), (0.9, True)] * 10
        cal = PlattCalibration.fit(pairs)
        path = tmp_path / "cal.json"
        cal.save(path)
        loaded = PlattCalibration.load(path)
        assert abs(cal.a - loaded.a) < 1e-9
        assert abs(cal.b - loaded.b) < 1e-9

    def test_to_dict_kind_platt(self):
        cal = PlattCalibration()
        data = cal.to_dict()
        assert data["kind"] == "platt"


class TestCalibrationReducesECE:
    def test_isotonic_reduces_ece_on_overconfident(self):
        # Synthesize overconfident eval set.
        pairs = (
            [(0.95, True)] * 20
            + [(0.95, False)] * 80  # 20% correct at 0.95
            + [(0.50, True)] * 50
            + [(0.50, False)] * 50  # 50% correct at 0.50
            + [(0.10, True)] * 10
            + [(0.10, False)] * 90  # 10% correct at 0.10
        )
        cal = IsotonicCalibration.fit(pairs)

        # Raw ECE.
        raw_metrics = evaluate_calibration(pairs)

        # Calibrated ECE.
        calibrated_pairs = [(cal.transform(c), y) for c, y in pairs]
        cal_metrics = evaluate_calibration(calibrated_pairs)

        # Calibration should reduce ECE.
        assert cal_metrics.expected_calibration_error < raw_metrics.expected_calibration_error
