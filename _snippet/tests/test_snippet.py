"""Tests for the snippet module."""

from __future__ import annotations


from vstack.snippet import (
    Snippet,
    SnippetStep,
    extract_snippet,
    find_relevant_steps,
    render_snippet,
    summarize_steps,
)


def _trace(steps):
    return {"goal": "g", "outcome": "o", "steps": steps, "success": False}


def _step(type_="thought", content="x"):
    return {"type": type_, "content": content}


class TestSummarizeSteps:
    def test_short_content_unchanged(self):
        assert summarize_steps("hello world") == "hello world"

    def test_long_content_elided(self):
        long_text = "a" * 500
        result = summarize_steps(long_text, head_chars=100, tail_chars=50)
        assert len(result) < 500
        assert "…" in result

    def test_keeps_head_and_tail(self):
        text = "START_" + "x" * 200 + "_END"
        result = summarize_steps(text, head_chars=20, tail_chars=20)
        assert "START_" in result
        assert "_END" in result


class TestFindRelevantSteps:
    def test_no_overlap_returns_empty(self):
        trace = _trace([_step(content="hello world")])
        finding = {"title": "completely unrelated phrase"}
        # "hello", "world", "completely", "unrelated", "phrase" are tokens.
        # No overlap.
        result = find_relevant_steps(trace, finding)
        assert result == []

    def test_token_overlap_finds_step(self):
        trace = _trace(
            [
                _step(content="reading the manual carefully"),
                _step(content="executing the migration"),
            ]
        )
        finding = {"title": "migration reading issue"}
        result = find_relevant_steps(trace, finding)
        assert len(result) > 0

    def test_higher_overlap_ranks_higher(self):
        trace = _trace(
            [
                _step(content="random text"),
                _step(content="migration migration migration database database"),
                _step(content="single migration mention"),
            ]
        )
        finding = {"title": "migration database problem"}
        result = find_relevant_steps(trace, finding)
        # Step 1 has the most overlap.
        assert result[0] == 1

    def test_max_steps_caps_results(self):
        trace = _trace([_step(content="migration") for _ in range(10)])
        finding = {"title": "migration"}
        result = find_relevant_steps(trace, finding, max_steps=3)
        assert len(result) <= 3

    def test_empty_trace(self):
        trace = _trace([])
        result = find_relevant_steps(trace, {"title": "x"})
        assert result == []


class TestExtractSnippet:
    def test_empty_trace(self):
        s = extract_snippet(_trace([]), {"title": "x"})
        assert s.total_steps_in_trace == 0
        assert len(s.steps) == 0

    def test_no_relevant_falls_back_to_first_steps(self):
        trace = _trace(
            [
                _step(content="a"),
                _step(content="b"),
                _step(content="c"),
            ]
        )
        finding = {"title": "xyz unrelated"}
        s = extract_snippet(trace, finding, max_total_steps=10)
        # No relevant, so fall back to first N.
        assert len(s.steps) > 0

    def test_context_steps_included(self):
        trace = _trace(
            [
                _step(content="alpha"),  # 0
                _step(content="beta"),  # 1
                _step(content="critical migration step"),  # 2 - relevant
                _step(content="delta"),  # 3
                _step(content="epsilon"),  # 4
            ]
        )
        finding = {"title": "critical migration"}
        s = extract_snippet(trace, finding, context_steps=1)
        indices = [step.index for step in s.steps]
        # Should include 1, 2, 3 (relevant + 1 context).
        assert 2 in indices
        assert 1 in indices
        assert 3 in indices

    def test_relevant_marked(self):
        trace = _trace(
            [
                _step(content="alpha"),
                _step(content="critical migration step"),
                _step(content="delta"),
            ]
        )
        finding = {"title": "critical migration"}
        s = extract_snippet(trace, finding, context_steps=1)
        relevant = [step for step in s.steps if step.is_relevant]
        assert len(relevant) >= 1
        assert relevant[0].index == 1

    def test_omitted_counts(self):
        trace = _trace([_step(content=f"step{i}") for i in range(10)])
        # Relevance only on step 5.
        finding = {"title": "step5"}
        s = extract_snippet(trace, finding, context_steps=1)
        assert s.omitted_steps_before > 0 or s.omitted_steps_after > 0

    def test_max_total_steps_respected(self):
        trace = _trace([_step(content="migration") for _ in range(20)])
        finding = {"title": "migration"}
        s = extract_snippet(trace, finding, context_steps=5, max_total_steps=8)
        assert len(s.steps) <= 8


class TestRenderSnippet:
    def test_empty_snippet(self):
        s = Snippet(finding_title="Test")
        md = render_snippet(s)
        assert "Test" in md
        assert "No steps" in md

    def test_renders_steps(self):
        s = Snippet(
            finding_title="Test",
            steps=[
                SnippetStep(index=0, type="thought", content="hello", is_relevant=True),
            ],
            total_steps_in_trace=1,
        )
        md = render_snippet(s)
        assert "hello" in md
        assert "thought" in md
        assert "→" in md  # relevant marker

    def test_omission_notes_rendered(self):
        s = Snippet(
            finding_title="Test",
            steps=[SnippetStep(index=2, type="x", content="y")],
            total_steps_in_trace=10,
            omitted_steps_before=2,
            omitted_steps_after=7,
        )
        md = render_snippet(s)
        assert "2 earlier" in md
        assert "7 later" in md


class TestSnippetSerialization:
    def test_to_dict(self):
        s = Snippet(
            finding_title="Test",
            steps=[SnippetStep(index=0, type="thought", content="hello")],
            total_steps_in_trace=5,
        )
        data = s.to_dict()
        assert data["finding_title"] == "Test"
        assert data["total_steps_in_trace"] == 5
        assert len(data["steps"]) == 1
