"""Tests for the trace_diff module."""

from __future__ import annotations


from vstack.trace_diff import StepDiff, diff_traces


def _step(type_="thought", content="x"):
    return {"type": type_, "content": content}


def _trace(steps=None, goal="goal", outcome="outcome", success=True):
    return {
        "goal": goal,
        "steps": steps or [],
        "outcome": outcome,
        "success": success,
    }


class TestNoChange:
    def test_identical_traces(self):
        t = _trace(steps=[_step("thought", "a"), _step("tool_call", "b")])
        delta = diff_traces(t, t)
        assert len(delta.unchanged_steps) == 2
        assert len(delta.changed_steps) == 0
        assert len(delta.added_steps) == 0
        assert len(delta.removed_steps) == 0
        assert not delta.is_regression()
        assert not delta.is_recovery()


class TestAddRemove:
    def test_added_step(self):
        before = _trace(steps=[_step("thought", "a")])
        after = _trace(steps=[_step("thought", "a"), _step("tool_call", "b")])
        delta = diff_traces(before, after)
        assert len(delta.added_steps) == 1
        assert delta.added_steps[0].after_type == "tool_call"

    def test_removed_step(self):
        before = _trace(steps=[_step("thought", "a"), _step("tool_call", "b")])
        after = _trace(steps=[_step("thought", "a")])
        delta = diff_traces(before, after)
        assert len(delta.removed_steps) == 1
        assert delta.removed_steps[0].before_type == "tool_call"


class TestChange:
    def test_content_changed(self):
        before = _trace(steps=[_step("thought", "old")])
        after = _trace(steps=[_step("thought", "new")])
        delta = diff_traces(before, after)
        assert len(delta.changed_steps) == 1
        cd = delta.changed_steps[0]
        assert cd.content_changed

    def test_type_changed(self):
        before = _trace(steps=[_step("thought", "a")])
        after = _trace(steps=[_step("observation", "a")])
        delta = diff_traces(before, after)
        assert len(delta.changed_steps) == 1
        cd = delta.changed_steps[0]
        assert cd.type_changed


class TestTraceProperties:
    def test_goal_changed(self):
        before = _trace(goal="old")
        after = _trace(goal="new")
        delta = diff_traces(before, after)
        assert delta.goal_changed

    def test_outcome_changed(self):
        before = _trace(outcome="old")
        after = _trace(outcome="new")
        delta = diff_traces(before, after)
        assert delta.outcome_changed

    def test_success_unchanged(self):
        before = _trace(success=True)
        after = _trace(success=True)
        delta = diff_traces(before, after)
        assert not delta.success_flipped

    def test_regression(self):
        before = _trace(success=True)
        after = _trace(success=False)
        delta = diff_traces(before, after)
        assert delta.is_regression()
        assert not delta.is_recovery()

    def test_recovery(self):
        before = _trace(success=False)
        after = _trace(success=True)
        delta = diff_traces(before, after)
        assert delta.is_recovery()
        assert not delta.is_regression()


class TestStepCount:
    def test_count_delta(self):
        before = _trace(steps=[_step()])
        after = _trace(steps=[_step(), _step()])
        delta = diff_traces(before, after)
        assert delta.step_count_delta == 1

    def test_negative_count_delta(self):
        before = _trace(steps=[_step(), _step(), _step()])
        after = _trace(steps=[_step()])
        delta = diff_traces(before, after)
        assert delta.step_count_delta == -2


class TestSummaryAndMarkdown:
    def test_summary_returns_string(self):
        before = _trace(steps=[_step()])
        after = _trace(steps=[_step(), _step()])
        delta = diff_traces(before, after)
        summary = delta.summary()
        assert "steps:" in summary

    def test_to_markdown_runs(self):
        before = _trace(steps=[_step("thought", "a")])
        after = _trace(steps=[_step("observation", "a")], success=False)
        delta = diff_traces(before, after)
        md = delta.to_markdown()
        assert "# Trace Delta" in md
        assert "REGRESSION" in md

    def test_markdown_added_section(self):
        before = _trace()
        after = _trace(steps=[_step("thought", "new")])
        delta = diff_traces(before, after)
        md = delta.to_markdown()
        assert "Added Steps" in md

    def test_markdown_removed_section(self):
        before = _trace(steps=[_step("thought", "old")])
        after = _trace()
        delta = diff_traces(before, after)
        md = delta.to_markdown()
        assert "Removed Steps" in md


class TestSerialization:
    def test_to_dict(self):
        before = _trace(steps=[_step()])
        after = _trace(steps=[_step(), _step()])
        delta = diff_traces(before, after)
        data = delta.to_dict()
        assert "step_count_before" in data
        assert "step_count_after" in data
        assert "added" in data

    def test_stepdiff_to_dict(self):
        d = StepDiff(
            kind="changed",
            before_index=0,
            after_index=0,
            before_type="thought",
            after_type="observation",
        )
        data = d.to_dict()
        assert data["kind"] == "changed"
        assert data["type_changed"] is True


class TestComplexAlignment:
    def test_insertion_in_middle(self):
        before = _trace(
            steps=[
                _step("thought", "a"),
                _step("tool_call", "c"),
            ]
        )
        after = _trace(
            steps=[
                _step("thought", "a"),
                _step("observation", "b"),  # inserted
                _step("tool_call", "c"),
            ]
        )
        delta = diff_traces(before, after)
        assert len(delta.added_steps) == 1
        assert delta.added_steps[0].after_type == "observation"

    def test_deletion_in_middle(self):
        before = _trace(
            steps=[
                _step("thought", "a"),
                _step("observation", "b"),
                _step("tool_call", "c"),
            ]
        )
        after = _trace(
            steps=[
                _step("thought", "a"),
                _step("tool_call", "c"),
            ]
        )
        delta = diff_traces(before, after)
        assert len(delta.removed_steps) == 1
        assert delta.removed_steps[0].before_type == "observation"
