"""Tests for the synth module."""

from __future__ import annotations

import pytest

from vstack.aar import AgentTrace
from vstack.synth import (
    TraceTemplate,
    generate_anxious_overhedge,
    generate_batch,
    generate_hallucination,
    generate_healthy,
    generate_over_apology,
    generate_premature_completion,
    generate_stuck_in_loop,
    generate_sycophancy,
    generate_tool_misuse,
    get_template,
    list_templates,
)


class TestStuckInLoop:
    def test_default_returns_trace(self):
        trace = generate_stuck_in_loop()
        assert isinstance(trace, AgentTrace)
        assert trace.success is False
        assert trace.retry_count == 3

    def test_custom_retry_count(self):
        trace = generate_stuck_in_loop(retry_count=10)
        assert trace.retry_count == 10
        # Should have at least 10 retries.
        retries = sum(1 for s in trace.steps if s.type == "tool_call")
        assert retries == 10

    def test_seed_reproducible(self):
        t1 = generate_stuck_in_loop(seed=42)
        t2 = generate_stuck_in_loop(seed=42)
        assert len(t1.steps) == len(t2.steps)
        assert t1.goal == t2.goal

    def test_different_error_types(self):
        for err in ("unique_constraint", "network_timeout", "permission_denied", "rate_limited"):
            trace = generate_stuck_in_loop(error_type=err)
            obs = [s for s in trace.steps if s.type == "observation"]
            assert len(obs) > 0


class TestHallucination:
    def test_default_returns_trace(self):
        trace = generate_hallucination()
        assert isinstance(trace, AgentTrace)
        assert trace.success is False

    def test_custom_fabricated_count(self):
        trace = generate_hallucination(fabricated_count=10)
        assert "10 of 10" in trace.steps[-1].content


class TestSycophancy:
    def test_default_returns_trace(self):
        trace = generate_sycophancy()
        assert isinstance(trace, AgentTrace)
        assert trace.success is False

    def test_custom_turns(self):
        trace = generate_sycophancy(turns=3)
        # 3 user + 3 agent = 6 steps.
        assert len(trace.steps) == 6


class TestOverApology:
    def test_default_returns_trace(self):
        trace = generate_over_apology()
        assert isinstance(trace, AgentTrace)
        assert trace.success is False

    def test_apologies_present(self):
        trace = generate_over_apology(apology_count=5)
        apologies = [s for s in trace.steps if "apologize" in s.content.lower()]
        assert len(apologies) >= 5


class TestPrematureCompletion:
    def test_default_returns_trace(self):
        trace = generate_premature_completion()
        assert isinstance(trace, AgentTrace)
        assert trace.success is False

    def test_custom_required(self):
        trace = generate_premature_completion(required_count=10)
        assert "10" in trace.goal


class TestToolMisuse:
    def test_default_returns_trace(self):
        trace = generate_tool_misuse()
        assert isinstance(trace, AgentTrace)
        assert trace.success is False

    def test_tool_calls_present(self):
        trace = generate_tool_misuse(tool_calls=3)
        tool_calls = [s for s in trace.steps if s.type == "tool_call"]
        assert len(tool_calls) == 3


class TestAnxiousOverhedge:
    def test_default_returns_trace(self):
        trace = generate_anxious_overhedge()
        assert isinstance(trace, AgentTrace)
        assert trace.success is False

    def test_paris_in_response(self):
        trace = generate_anxious_overhedge()
        assert "Paris" in trace.steps[1].content


class TestHealthy:
    def test_default_returns_success(self):
        trace = generate_healthy()
        assert isinstance(trace, AgentTrace)
        assert trace.success is True

    def test_custom_count(self):
        trace = generate_healthy(success_count=10)
        assert "10" in trace.goal


class TestBatchGeneration:
    def test_default_count(self):
        traces = generate_batch(generate_stuck_in_loop, count=5)
        assert len(traces) == 5

    def test_all_unique_seeds(self):
        traces = generate_batch(generate_stuck_in_loop, count=10, seed=100)
        # Different seeds → potentially different traces.
        assert len(traces) == 10
        for t in traces:
            assert isinstance(t, AgentTrace)

    def test_seed_reproducibility(self):
        a = generate_batch(generate_stuck_in_loop, count=3, seed=42)
        b = generate_batch(generate_stuck_in_loop, count=3, seed=42)
        for ta, tb in zip(a, b):
            assert ta.goal == tb.goal

    def test_pass_through_kwargs(self):
        traces = generate_batch(
            generate_stuck_in_loop,
            count=3,
            retry_count=7,
        )
        for t in traces:
            assert t.retry_count == 7


class TestTemplateRegistry:
    def test_list_templates(self):
        templates = list_templates()
        assert len(templates) > 0
        assert "stuck_in_loop" in templates
        assert "hallucination" in templates

    def test_get_known_template(self):
        t = get_template("stuck_in_loop")
        assert isinstance(t, TraceTemplate)
        assert t.name == "stuck_in_loop"
        assert callable(t.generator)

    def test_get_unknown_raises(self):
        with pytest.raises(KeyError):
            get_template("nonexistent_xyz")

    def test_template_default_params(self):
        t = get_template("stuck_in_loop")
        assert "retry_count" in t.default_params

    def test_invoke_via_template(self):
        t = get_template("stuck_in_loop")
        trace = t.generator(**t.default_params)
        assert isinstance(trace, AgentTrace)
