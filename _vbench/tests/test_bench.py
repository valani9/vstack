"""Tests for the vbench module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from vstack.vbench import (
    BenchHarness,
    BenchResult,
    BenchRun,
    Statistics,
    compare_results,
)


def _make_report(findings: list[dict]):
    return {"findings": findings}


def _f(severity: str = "high", pattern: str = "lewin"):
    return {"pattern": pattern, "severity": severity, "title": "test", "intervention": "x"}


class TestStatistics:
    def test_from_empty_samples(self):
        stats = Statistics.from_samples([])
        assert stats.count == 0
        assert stats.mean == 0.0

    def test_from_single_sample(self):
        stats = Statistics.from_samples([42])
        assert stats.count == 1
        assert stats.mean == 42
        assert stats.median == 42
        assert stats.stddev == 0.0

    def test_from_multiple_samples(self):
        stats = Statistics.from_samples([1, 2, 3, 4, 5])
        assert stats.count == 5
        assert stats.mean == 3
        assert stats.median == 3
        assert stats.min_ == 1
        assert stats.max_ == 5

    def test_percentiles(self):
        stats = Statistics.from_samples(list(range(1, 101)))
        # p95 of 1..100 should be ~95.
        assert 90 <= stats.p95 <= 100
        assert 95 <= stats.p99 <= 100

    def test_to_dict(self):
        stats = Statistics.from_samples([1, 2, 3])
        data = stats.to_dict()
        assert "mean" in data
        assert "p95" in data


class TestBenchRun:
    def test_to_dict(self):
        run = BenchRun(
            pattern="lewin",
            trace_name="t1",
            rep=0,
            duration_ms=100,
            finding_count=2,
            severity_high_count=1,
            severity_medium_count=1,
            severity_low_count=0,
        )
        data = run.to_dict()
        assert data["pattern"] == "lewin"
        assert data["duration_ms"] == 100

    def test_error_field(self):
        run = BenchRun(
            pattern="x",
            trace_name="t",
            rep=0,
            duration_ms=0,
            finding_count=0,
            severity_high_count=0,
            severity_medium_count=0,
            severity_low_count=0,
            error="oops",
        )
        assert run.error == "oops"


class TestBenchResult:
    def _make_runs(self):
        return [
            BenchRun("lewin", "t1", 0, 100, 1, 1, 0, 0),
            BenchRun("lewin", "t1", 1, 120, 1, 1, 0, 0),
            BenchRun("aar", "t1", 0, 200, 2, 1, 1, 0),
        ]

    def test_latency_stats_all_patterns(self):
        result = BenchResult(runs=self._make_runs(), patterns=["lewin", "aar"])
        stats = result.latency_stats()
        assert stats.count == 3
        assert stats.mean == 140

    def test_latency_stats_per_pattern(self):
        result = BenchResult(runs=self._make_runs(), patterns=["lewin", "aar"])
        lewin_stats = result.latency_stats(pattern="lewin")
        assert lewin_stats.count == 2
        assert lewin_stats.mean == 110

    def test_finding_stats(self):
        result = BenchResult(runs=self._make_runs(), patterns=["lewin", "aar"])
        stats = result.finding_stats()
        assert stats.count == 3
        assert stats.mean == pytest.approx(4 / 3)

    def test_error_rate_zero(self):
        result = BenchResult(runs=self._make_runs())
        assert result.error_rate() == 0.0

    def test_error_rate_with_errors(self):
        runs = self._make_runs()
        runs.append(BenchRun("x", "t", 0, 0, 0, 0, 0, 0, error="oops"))
        result = BenchResult(runs=runs)
        assert result.error_rate() == 0.25

    def test_per_pattern_summary(self):
        result = BenchResult(runs=self._make_runs(), patterns=["lewin", "aar"])
        summary = result.per_pattern_summary()
        assert "lewin" in summary
        assert "aar" in summary
        assert "latency_ms" in summary["lewin"]

    def test_save_load_roundtrip(self, tmp_path: Path):
        result = BenchResult(runs=self._make_runs(), patterns=["lewin", "aar"])
        path = tmp_path / "bench.json"
        result.save(path)
        loaded = BenchResult.load(path)
        assert len(loaded.runs) == len(result.runs)
        assert loaded.patterns == result.patterns

    def test_to_markdown_runs(self):
        result = BenchResult(runs=self._make_runs(), patterns=["lewin", "aar"])
        md = result.to_markdown()
        assert "Benchmark Result" in md
        assert "lewin" in md


class TestBenchHarness:
    def test_run_calls_diagnose_per_pattern_trace_rep(self):
        from unittest.mock import MagicMock

        harness = BenchHarness(
            traces=[MagicMock(), MagicMock()],
            patterns=["lewin", "aar"],
            repetitions=2,
        )

        with patch("vstack.diagnose.diagnose") as mock_diagnose:
            mock_diagnose.return_value = _make_report([_f()])
            result = harness.run(llm_client=MagicMock())

        # 2 patterns × 2 traces × 2 reps = 8 calls.
        assert mock_diagnose.call_count == 8
        assert len(result.runs) == 8

    def test_run_records_findings(self):
        from unittest.mock import MagicMock

        harness = BenchHarness(
            traces=[MagicMock()],
            patterns=["lewin"],
            repetitions=1,
        )

        with patch("vstack.diagnose.diagnose") as mock_diagnose:
            mock_diagnose.return_value = _make_report(
                [
                    _f("high"),
                    _f("medium"),
                    _f("low"),
                ]
            )
            result = harness.run(llm_client=MagicMock())

        assert result.runs[0].severity_high_count == 1
        assert result.runs[0].severity_medium_count == 1
        assert result.runs[0].severity_low_count == 1

    def test_error_captured(self):
        from unittest.mock import MagicMock

        harness = BenchHarness(
            traces=[MagicMock()],
            patterns=["lewin"],
            repetitions=1,
        )

        with patch("vstack.diagnose.diagnose") as mock_diagnose:
            mock_diagnose.side_effect = ValueError("oops")
            result = harness.run(llm_client=MagicMock())

        assert result.runs[0].error is not None
        assert "oops" in result.runs[0].error


class TestCompareResults:
    def test_no_regression(self):
        before = BenchResult(
            runs=[BenchRun("lewin", "t", 0, 100, 1, 1, 0, 0)],
            patterns=["lewin"],
        )
        after = BenchResult(
            runs=[BenchRun("lewin", "t", 0, 100, 1, 1, 0, 0)],
            patterns=["lewin"],
        )
        comp = compare_results(before, after)
        assert len(comp.latency_regressions) == 0
        assert len(comp.latency_improvements) == 0

    def test_regression_detected(self):
        before = BenchResult(
            runs=[BenchRun("lewin", "t", 0, 100, 1, 1, 0, 0)],
            patterns=["lewin"],
        )
        after = BenchResult(
            runs=[BenchRun("lewin", "t", 0, 200, 1, 1, 0, 0)],
            patterns=["lewin"],
        )
        comp = compare_results(before, after)
        assert len(comp.latency_regressions) == 1
        # 100% regression.
        assert comp.latency_regressions[0][0] == "lewin"

    def test_improvement_detected(self):
        before = BenchResult(
            runs=[BenchRun("lewin", "t", 0, 200, 1, 1, 0, 0)],
            patterns=["lewin"],
        )
        after = BenchResult(
            runs=[BenchRun("lewin", "t", 0, 100, 1, 1, 0, 0)],
            patterns=["lewin"],
        )
        comp = compare_results(before, after)
        assert len(comp.latency_improvements) == 1

    def test_to_markdown_runs(self):
        before = BenchResult(
            runs=[BenchRun("lewin", "t", 0, 100, 1, 1, 0, 0)],
            patterns=["lewin"],
        )
        after = BenchResult(
            runs=[BenchRun("lewin", "t", 0, 200, 1, 1, 0, 0)],
            patterns=["lewin"],
        )
        comp = compare_results(before, after)
        md = comp.to_markdown()
        assert "Bench Comparison" in md
