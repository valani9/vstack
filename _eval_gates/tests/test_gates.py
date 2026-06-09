"""Tests for eval_gates module."""

from __future__ import annotations

from dataclasses import dataclass


from vstack.eval_gates import (
    BaselineComparisonGate,
    CustomGate,
    F1Gate,
    GateFailure,
    GateResult,
    GateSet,
    PrecisionGate,
    RecallGate,
    SeverityCountGate,
)


@dataclass
class _Metrics:
    f1: float = 0.0
    precision: float = 0.0
    recall: float = 0.0


def _r(findings, overall_score=None):
    d = {"findings": findings}
    if overall_score is not None:
        d["overall_score"] = overall_score
    return d


def _f(severity="high"):
    return {"pattern": "lewin", "severity": severity, "title": "x"}


class TestSeverityCountGate:
    def test_no_findings_passes(self):
        gate = SeverityCountGate(severity="high", max_count=0)
        assert gate.check(report=_r([])) is None

    def test_zero_high_passes_max_zero(self):
        gate = SeverityCountGate(severity="high", max_count=0)
        assert gate.check(report=_r([_f("low")])) is None

    def test_exceeds_max_fails(self):
        gate = SeverityCountGate(severity="high", max_count=0)
        failure = gate.check(report=_r([_f("high")]))
        assert failure is not None
        assert failure.observed == 1
        assert failure.threshold == 0

    def test_within_max_passes(self):
        gate = SeverityCountGate(severity="high", max_count=2)
        assert gate.check(report=_r([_f("high"), _f("high")])) is None

    def test_name_default(self):
        gate = SeverityCountGate(severity="high", max_count=3)
        assert "high" in gate.name
        assert "3" in gate.name


class TestF1Gate:
    def test_above_threshold_passes(self):
        gate = F1Gate(min_f1=0.7)
        assert gate.check(eval_metrics=_Metrics(f1=0.8)) is None

    def test_below_threshold_fails(self):
        gate = F1Gate(min_f1=0.7)
        failure = gate.check(eval_metrics=_Metrics(f1=0.5))
        assert failure is not None
        assert failure.observed == 0.5

    def test_no_metrics_passes(self):
        gate = F1Gate(min_f1=0.7)
        assert gate.check() is None


class TestPrecisionGate:
    def test_above_threshold_passes(self):
        gate = PrecisionGate(min_precision=0.5)
        assert gate.check(eval_metrics=_Metrics(precision=0.8)) is None

    def test_below_threshold_fails(self):
        gate = PrecisionGate(min_precision=0.7)
        failure = gate.check(eval_metrics=_Metrics(precision=0.3))
        assert failure is not None


class TestRecallGate:
    def test_above_threshold_passes(self):
        gate = RecallGate(min_recall=0.5)
        assert gate.check(eval_metrics=_Metrics(recall=0.6)) is None

    def test_below_threshold_fails(self):
        gate = RecallGate(min_recall=0.7)
        failure = gate.check(eval_metrics=_Metrics(recall=0.4))
        assert failure is not None


class TestBaselineComparisonGate:
    def test_no_inputs_passes(self):
        gate = BaselineComparisonGate()
        assert gate.check() is None

    def test_same_high_count_passes(self):
        gate = BaselineComparisonGate(max_new_high=0)
        baseline = _r([_f("high")])
        report = _r([_f("high")])
        assert gate.check(report=report, baseline=baseline) is None

    def test_new_high_fails(self):
        gate = BaselineComparisonGate(max_new_high=0)
        baseline = _r([])
        report = _r([_f("high")])
        failure = gate.check(report=report, baseline=baseline)
        assert failure is not None
        assert failure.observed == 1

    def test_score_drop_fails(self):
        gate = BaselineComparisonGate(max_score_drop=10.0)
        baseline = _r([], overall_score=100.0)
        report = _r([], overall_score=80.0)
        failure = gate.check(report=report, baseline=baseline)
        assert failure is not None
        assert failure.observed == 20.0

    def test_small_score_drop_passes(self):
        gate = BaselineComparisonGate(max_score_drop=10.0)
        baseline = _r([], overall_score=100.0)
        report = _r([], overall_score=95.0)
        assert gate.check(report=report, baseline=baseline) is None


class TestCustomGate:
    def test_predicate_returns_pass(self):
        gate = CustomGate(name_="custom", predicate=lambda **kw: None)
        assert gate.check() is None

    def test_predicate_returns_fail(self):
        def fail_pred(**kw):
            return GateFailure(gate_name="custom", reason="forced fail")

        gate = CustomGate(name_="custom", predicate=fail_pred)
        failure = gate.check()
        assert failure is not None
        assert failure.reason == "forced fail"


class TestGateSet:
    def test_empty_set_passes(self):
        gs = GateSet()
        result = gs.check()
        assert result.passed
        assert result.gates_checked == 0

    def test_all_pass(self):
        gs = GateSet(
            gates=[
                F1Gate(min_f1=0.5),
                PrecisionGate(min_precision=0.5),
            ]
        )
        result = gs.check(eval_metrics=_Metrics(f1=0.8, precision=0.9))
        assert result.passed
        assert len(result.failures) == 0

    def test_one_fails(self):
        gs = GateSet(
            gates=[
                F1Gate(min_f1=0.9),
                PrecisionGate(min_precision=0.5),
            ]
        )
        result = gs.check(eval_metrics=_Metrics(f1=0.7, precision=0.9))
        assert not result.passed
        assert len(result.failures) == 1

    def test_multiple_fail(self):
        gs = GateSet(
            gates=[
                F1Gate(min_f1=0.9),
                PrecisionGate(min_precision=0.9),
            ]
        )
        result = gs.check(eval_metrics=_Metrics(f1=0.5, precision=0.5))
        assert not result.passed
        assert len(result.failures) == 2

    def test_gate_raising_captured_as_failure(self):
        def bad_predicate(**_):
            raise RuntimeError("explosion")

        gs = GateSet(gates=[CustomGate(name_="bad", predicate=bad_predicate)])
        result = gs.check()
        assert not result.passed
        assert "explosion" in result.failures[0].reason

    def test_add_immutable(self):
        gs1 = GateSet()
        gs2 = gs1.add(F1Gate(min_f1=0.5))
        assert len(gs1.gates) == 0
        assert len(gs2.gates) == 1

    def test_exit_code(self):
        passing = GateResult(passed=True)
        failing = GateResult(passed=False)
        assert passing.exit_code() == 0
        assert failing.exit_code() == 1

    def test_to_dict(self):
        gs = GateSet(gates=[F1Gate(min_f1=0.5)])
        data = gs.to_dict()
        assert "gates" in data
        assert len(data["gates"]) == 1


class TestGateResultSerialization:
    def test_to_dict(self):
        result = GateResult(
            passed=False,
            failures=[GateFailure(gate_name="x", reason="r")],
            gates_checked=1,
        )
        data = result.to_dict()
        assert data["passed"] is False
        assert len(data["failures"]) == 1
