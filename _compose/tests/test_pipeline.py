"""Tests for the compose Pipeline."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


from vstack.compose import (
    Pipeline,
    PipelineResult,
    Stop,
)


def _make_report(findings: list[dict]):
    """Build a dict-shaped report (matches diagnose() return)."""
    return {"findings": findings, "per_pattern": {}, "errors": []}


def _make_finding(pattern: str, severity: str, title: str = ""):
    return {
        "pattern": pattern,
        "severity": severity,
        "title": title or f"{pattern} finding",
        "intervention": f"fix {pattern}",
    }


class TestPipelineBuilder:
    def test_empty_pipeline_has_zero_steps(self):
        p = Pipeline("test")
        assert len(p) == 0

    def test_step_appends(self):
        p = Pipeline("test").step("lewin")
        assert len(p) == 1

    def test_step_chain(self):
        p = Pipeline("test").step("lewin").step("aar").then("bias_stack")
        assert len(p) == 3

    def test_builder_immutable(self):
        p1 = Pipeline("test")
        p2 = p1.step("lewin")
        # Original unchanged.
        assert len(p1) == 0
        assert len(p2) == 1

    def test_when_severity_appends(self):
        p = Pipeline("test").step("lewin").when_severity("high", run="aar")
        assert len(p) == 2

    def test_when_appends(self):
        p = Pipeline("test").when(lambda r: True, run="aar")
        assert len(p) == 1

    def test_callback_appends(self):
        p = Pipeline("test").callback(lambda r: print(r))
        assert len(p) == 1

    def test_diagnose_appends(self):
        p = Pipeline("test").diagnose(recipe="stuck_in_loop")
        assert len(p) == 1

    def test_with_baseline_sets(self):
        p = Pipeline("test").with_baseline("baseline.json")
        assert p.baseline_path == "baseline.json"

    def test_to_dict(self):
        p = Pipeline("test").step("lewin", mode="forensic").with_baseline("baseline.json")
        data = p.to_dict()
        assert data["name"] == "test"
        assert len(data["steps"]) == 1
        assert data["baseline_path"] == "baseline.json"


class TestPipelineRun:
    def test_runs_each_pattern_step(self):
        p = Pipeline("test").step("lewin").step("aar")

        with patch("vstack.diagnose.diagnose") as mock_diagnose:
            mock_diagnose.return_value = _make_report([])
            result = p.run(trace=MagicMock(), llm_client=MagicMock())

        assert mock_diagnose.call_count == 2
        assert "lewin" in result.steps_run
        assert "aar" in result.steps_run

    def test_findings_aggregated(self):
        p = Pipeline("test").step("lewin")

        with patch("vstack.diagnose.diagnose") as mock_diagnose:
            mock_diagnose.return_value = _make_report(
                [
                    _make_finding("lewin", "high"),
                ]
            )
            result = p.run(trace=MagicMock(), llm_client=MagicMock())

        assert len(result.findings) == 1
        assert result.findings[0]["severity"] == "high"

    def test_conditional_runs_when_predicate_true(self):
        p = Pipeline("test").step("lewin").when_severity("high", run="aar")

        with patch("vstack.diagnose.diagnose") as mock_diagnose:
            # First call (lewin) returns high finding.
            mock_diagnose.return_value = _make_report(
                [
                    _make_finding("lewin", "high"),
                ]
            )
            p.run(trace=MagicMock(), llm_client=MagicMock())

        # Both steps should have run.
        assert mock_diagnose.call_count == 2

    def test_conditional_skips_when_predicate_false(self):
        p = Pipeline("test").step("lewin").when_severity("high", run="aar")

        with patch("vstack.diagnose.diagnose") as mock_diagnose:
            mock_diagnose.return_value = _make_report(
                [
                    _make_finding("lewin", "low"),
                ]
            )
            result = p.run(trace=MagicMock(), llm_client=MagicMock())

        # Only the first step runs.
        assert mock_diagnose.call_count == 1
        assert any("skip" in s for s in result.steps_run)

    def test_callback_runs(self):
        callback_calls = []

        p = Pipeline("test").step("lewin").callback(lambda prev: callback_calls.append(prev))

        with patch("vstack.diagnose.diagnose") as mock_diagnose:
            mock_diagnose.return_value = _make_report([])
            p.run(trace=MagicMock(), llm_client=MagicMock())

        assert len(callback_calls) == 1

    def test_callback_stop_halts_pipeline(self):
        def stopper(_prev):
            raise Stop

        p = (
            Pipeline("test").step("lewin").callback(stopper).step("aar")  # should NOT run
        )

        with patch("vstack.diagnose.diagnose") as mock_diagnose:
            mock_diagnose.return_value = _make_report([])
            result = p.run(trace=MagicMock(), llm_client=MagicMock())

        assert result.stopped_early
        # Only lewin called.
        assert mock_diagnose.call_count == 1

    def test_diagnose_step(self):
        p = Pipeline("test").diagnose(recipe="stuck_in_loop")

        with patch("vstack.diagnose.diagnose") as mock_diagnose:
            mock_diagnose.return_value = _make_report([])
            p.run(trace=MagicMock(), llm_client=MagicMock())

        # diagnose() called with recipe argument.
        call = mock_diagnose.call_args
        assert call.kwargs["recipe"] == "stuck_in_loop"

    def test_errors_captured(self):
        p = Pipeline("test").step("lewin")

        with patch("vstack.diagnose.diagnose") as mock_diagnose:
            mock_diagnose.side_effect = ValueError("test error")
            result = p.run(trace=MagicMock(), llm_client=MagicMock())

        assert len(result.errors) == 1
        assert "test error" in result.errors[0]["error"]


class TestPipelineResult:
    def test_dimension_summary(self):
        result = PipelineResult(
            pipeline_name="test",
            steps_run=[],
            findings=[
                _make_finding("a", "high"),
                _make_finding("b", "high"),
                _make_finding("c", "medium"),
                _make_finding("d", "low"),
            ],
        )
        summary = result.dimension_summary()
        assert summary["high"] == 2
        assert summary["medium"] == 1
        assert summary["low"] == 1

    def test_has_high(self):
        result = PipelineResult(
            pipeline_name="test",
            steps_run=[],
            findings=[_make_finding("a", "high")],
        )
        assert result.has_high()

        result2 = PipelineResult(
            pipeline_name="test",
            steps_run=[],
            findings=[_make_finding("a", "low")],
        )
        assert not result2.has_high()

    def test_top_findings_severity_ordered(self):
        result = PipelineResult(
            pipeline_name="test",
            steps_run=[],
            findings=[
                _make_finding("a", "low"),
                _make_finding("b", "high"),
                _make_finding("c", "medium"),
            ],
        )
        top = result.top_findings(n=3)
        assert top[0]["severity"] == "high"
        assert top[1]["severity"] == "medium"
        assert top[2]["severity"] == "low"

    def test_to_dict(self):
        result = PipelineResult(
            pipeline_name="test",
            steps_run=["lewin"],
            findings=[_make_finding("a", "high")],
        )
        data = result.to_dict()
        assert data["pipeline_name"] == "test"
        assert data["findings_count"] == 1
        assert data["dimension_summary"]["high"] == 1


class TestComplexPipelines:
    def test_complex_chain(self):
        p = (
            Pipeline("complex")
            .step("lewin", mode="standard")
            .step("yerkes_dodson", mode="quick")
            .when_severity("high", run="bias_stack")
            .then("aar", mode="forensic")
        )
        assert len(p) == 4

    def test_each_step_label_present(self):
        p = Pipeline("test").step("lewin", label="my_lewin")
        with patch("vstack.diagnose.diagnose") as mock_diagnose:
            mock_diagnose.return_value = _make_report([])
            result = p.run(trace=MagicMock(), llm_client=MagicMock())
        assert "my_lewin" in result.steps_run
