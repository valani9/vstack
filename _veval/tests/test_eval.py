"""Tests for the veval module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch


from vstack.veval import (
    EvalCase,
    EvalHarness,
    EvalResult,
    EvalRun,
    compute_metrics,
)


class TestEvalCase:
    def test_positive_case(self):
        case = EvalCase(trace=None, expected_severity="high")
        assert case.is_positive()

    def test_negative_case(self):
        case = EvalCase(trace=None, expected_severity="none")
        assert not case.is_positive()


class TestEvalRun:
    def test_tp(self):
        run = EvalRun(
            case_id="x",
            expected_severity="high",
            predicted_severity="high",
            expected_positive=True,
            predicted_positive=True,
        )
        assert run.is_tp
        assert run.is_correct

    def test_fp(self):
        run = EvalRun(
            case_id="x",
            expected_severity="none",
            predicted_severity="high",
            expected_positive=False,
            predicted_positive=True,
        )
        assert run.is_fp

    def test_fn(self):
        run = EvalRun(
            case_id="x",
            expected_severity="high",
            predicted_severity="none",
            expected_positive=True,
            predicted_positive=False,
        )
        assert run.is_fn

    def test_tn(self):
        run = EvalRun(
            case_id="x",
            expected_severity="none",
            predicted_severity="none",
            expected_positive=False,
            predicted_positive=False,
        )
        assert run.is_tn


class TestComputeMetrics:
    def test_perfect_classifier(self):
        runs = [
            EvalRun("a", "high", "high", True, True),
            EvalRun("b", "none", "none", False, False),
        ]
        result = EvalResult(runs=runs)
        metrics = compute_metrics(result)
        assert metrics.accuracy == 1.0
        assert metrics.precision == 1.0
        assert metrics.recall == 1.0
        assert metrics.f1 == 1.0

    def test_random_classifier(self):
        runs = [
            EvalRun("a", "high", "high", True, True),
            EvalRun("b", "high", "none", True, False),
            EvalRun("c", "none", "high", False, True),
            EvalRun("d", "none", "none", False, False),
        ]
        result = EvalResult(runs=runs)
        metrics = compute_metrics(result)
        assert metrics.accuracy == 0.5
        assert metrics.precision == 0.5  # 1 tp / (1 tp + 1 fp)
        assert metrics.recall == 0.5  # 1 tp / (1 tp + 1 fn)
        assert metrics.f1 == 0.5

    def test_all_predicted_positive(self):
        runs = [
            EvalRun("a", "high", "high", True, True),
            EvalRun("b", "none", "high", False, True),
        ]
        result = EvalResult(runs=runs)
        metrics = compute_metrics(result)
        assert metrics.precision == 0.5
        assert metrics.recall == 1.0

    def test_no_predicted_positive(self):
        runs = [
            EvalRun("a", "high", "none", True, False),
            EvalRun("b", "high", "none", True, False),
        ]
        result = EvalResult(runs=runs)
        metrics = compute_metrics(result)
        # tp+fp = 0 → precision = 0
        assert metrics.precision == 0.0
        assert metrics.recall == 0.0
        assert metrics.f1 == 0.0

    def test_empty_result(self):
        result = EvalResult(runs=[])
        metrics = compute_metrics(result)
        assert metrics.n_cases == 0
        assert metrics.precision == 0.0

    def test_confusion_matrix_counts(self):
        runs = [
            EvalRun("a", "high", "high", True, True),  # tp
            EvalRun("b", "high", "high", True, True),  # tp
            EvalRun("c", "none", "high", False, True),  # fp
            EvalRun("d", "high", "none", True, False),  # fn
            EvalRun("e", "none", "none", False, False),  # tn
        ]
        result = EvalResult(runs=runs)
        metrics = compute_metrics(result)
        assert metrics.confusion.tp == 2
        assert metrics.confusion.fp == 1
        assert metrics.confusion.fn == 1
        assert metrics.confusion.tn == 1


class TestEvalHarness:
    def _make_trace(self):
        from datetime import datetime, timezone
        from vstack.aar import AgentTrace, TraceStep

        return AgentTrace(
            goal="test",
            steps=[
                TraceStep(
                    timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
                    type="thought",
                    content="x",
                )
            ],
            outcome="x",
            success=False,
        )

    def test_run_against_mock_pattern(self):
        cases = [
            EvalCase(
                trace=self._make_trace(),
                expected_severity="high",
                case_id="case-1",
            ),
        ]

        harness = EvalHarness(cases=cases, pattern="lewin")

        with patch("vstack.diagnose.diagnose") as mock_diagnose:
            mock_diagnose.return_value = {"findings": [{"pattern": "lewin", "severity": "high"}]}
            result = harness.run(llm_client=MagicMock())

        assert len(result.runs) == 1
        assert result.runs[0].is_tp

    def test_error_during_diagnose_creates_error_run(self):
        cases = [
            EvalCase(
                trace=self._make_trace(),
                expected_severity="high",
            ),
        ]

        harness = EvalHarness(cases=cases, pattern="lewin")

        with patch("vstack.diagnose.diagnose") as mock_diagnose:
            mock_diagnose.side_effect = ValueError("oops")
            result = harness.run(llm_client=MagicMock())

        assert result.runs[0].predicted_severity == "error"


class TestSerialization:
    def test_save_load_roundtrip(self, tmp_path: Path):
        result = EvalResult(
            runs=[
                EvalRun("a", "high", "high", True, True),
                EvalRun("b", "none", "none", False, False),
            ],
            pattern="lewin",
        )
        path = tmp_path / "result.json"
        result.save(path)
        loaded = EvalResult.load(path)
        assert loaded.pattern == "lewin"
        assert len(loaded.runs) == 2

    def test_to_dict(self):
        result = EvalResult(
            runs=[EvalRun("a", "high", "high", True, True)],
            pattern="lewin",
        )
        data = result.to_dict()
        assert data["pattern"] == "lewin"
        assert data["n_runs"] == 1

    def test_eval_run_to_dict(self):
        run = EvalRun("a", "high", "low", True, True)
        data = run.to_dict()
        assert data["case_id"] == "a"
        assert data["is_correct"] is False

    def test_metrics_to_dict(self):
        runs = [EvalRun("a", "high", "high", True, True)]
        result = EvalResult(runs=runs)
        data = result.metrics().to_dict()
        assert "precision" in data
        assert "confusion" in data


class TestEvalResultMetricsMethod:
    def test_metrics_returns_eval_metrics(self):
        runs = [EvalRun("a", "high", "high", True, True)]
        result = EvalResult(runs=runs)
        m = result.metrics()
        assert m.f1 > 0
