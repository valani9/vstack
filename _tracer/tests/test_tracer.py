"""Tests for the tracer module."""

from __future__ import annotations


from vstack.aar import AgentTrace
from vstack.tracer import StepRecord, Tracer


class TestTracerRecording:
    def test_empty_tracer(self):
        t = Tracer(goal="test")
        assert t.step_count() == 0

    def test_thought(self):
        t = Tracer().thought("think")
        assert t.step_count() == 1
        assert t.records()[0].kind == "thought"
        assert t.records()[0].content == "think"

    def test_tool_call_with_args(self):
        t = Tracer().tool_call("db_query", "SELECT 1")
        assert t.records()[0].kind == "tool_call"
        assert "db_query" in t.records()[0].content
        assert "SELECT 1" in t.records()[0].content

    def test_tool_call_no_args(self):
        t = Tracer().tool_call("ping")
        assert t.records()[0].content == "ping"

    def test_observation(self):
        t = Tracer().observation("result")
        assert t.records()[0].kind == "observation"

    def test_message(self):
        t = Tracer().message("hi")
        assert t.records()[0].kind == "message"

    def test_decision(self):
        t = Tracer().decision("commit")
        assert t.records()[0].kind == "decision"

    def test_chained_recording(self):
        t = (
            Tracer(goal="task")
            .thought("starting")
            .tool_call("read_file", "x.txt")
            .observation("contents")
            .decision("done")
        )
        assert t.step_count() == 4
        kinds = [r.kind for r in t.records()]
        assert kinds == ["thought", "tool_call", "observation", "decision"]


class TestFinalize:
    def test_finalize_returns_agent_trace(self):
        t = Tracer(goal="task")
        t.thought("starting")
        trace = t.finalize(outcome="done", success=True)
        assert isinstance(trace, AgentTrace)
        assert trace.goal == "task"
        assert trace.success is True
        assert trace.outcome == "done"

    def test_steps_preserved_in_trace(self):
        t = Tracer().thought("a").tool_call("b").observation("c")
        trace = t.finalize(outcome="x", success=True)
        assert len(trace.steps) == 3
        assert trace.steps[0].type == "thought"
        assert trace.steps[1].type == "tool_call"

    def test_finalize_can_be_called_via_property(self):
        t = Tracer(goal="task")
        t.thought("hi")
        t.set_outcome("done", success=True)
        trace = t.trace
        assert isinstance(trace, AgentTrace)


class TestContextManager:
    def test_context_manager_works(self):
        with Tracer(goal="ctx") as t:
            t.thought("hi")
        assert t.trace.goal == "ctx"
        assert len(t.trace.steps) == 1

    def test_exception_marks_failure(self):
        try:
            with Tracer(goal="ctx") as t:
                t.thought("about to fail")
                raise ValueError("oops")
        except ValueError:
            pass
        assert t.trace.success is False
        assert "oops" in t.trace.outcome


class TestSetters:
    def test_set_outcome(self):
        t = Tracer().set_outcome("done", success=True)
        assert t._outcome == "done"
        assert t._success is True

    def test_set_retry_count(self):
        t = Tracer().set_retry_count(5)
        assert t._retry_count == 5

    def test_finalize_uses_set_outcome(self):
        t = Tracer(goal="x")
        t.set_outcome("yes", success=True)
        trace = t.finalize()
        assert trace.outcome == "yes"


class TestStepRecord:
    def test_dataclass_fields(self):
        from datetime import datetime, timezone

        r = StepRecord(
            kind="thought",
            content="hi",
            timestamp=datetime.now(timezone.utc),
        )
        assert r.kind == "thought"


class TestClear:
    def test_clear_resets(self):
        t = Tracer().thought("a").thought("b")
        assert t.step_count() == 2
        t.clear()
        assert t.step_count() == 0


class TestTraceFinalization:
    def test_trace_with_steps(self):
        t = Tracer(goal="x").thought("a")
        trace = t.finalize(outcome="ok", success=True)
        assert len(trace.steps) == 1
        # The step's timestamp should be a valid datetime.
        from datetime import datetime

        assert isinstance(trace.steps[0].timestamp, datetime)
