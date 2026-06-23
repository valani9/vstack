"""Tests for vstack.ingest (chat-message + OTel-span importers)."""

from __future__ import annotations

import json
from io import StringIO


from vstack.ingest import from_chat_messages, from_otel_spans


def test_from_chat_messages_maps_roles() -> None:
    msgs = [
        {"role": "system", "content": "be helpful"},
        {"role": "user", "content": "add JWT auth"},
        {"role": "assistant", "content": "I'll grep first"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"function": {"name": "edit", "arguments": '{"file":"auth.py"}'}}],
        },
        {"role": "tool", "content": "tests failed"},
    ]
    trace = from_chat_messages(msgs)
    types = [s.type for s in trace.steps]
    assert types == ["message", "message", "message", "tool_call", "observation"]
    # goal inferred from first user message; outcome from last assistant text.
    assert trace.goal == "add JWT auth"
    assert trace.outcome == "I'll grep first"
    assert trace.success is False
    assert "edit(" in trace.steps[3].content


def test_from_chat_messages_explicit_fields_win() -> None:
    trace = from_chat_messages(
        [{"role": "user", "content": "x"}],
        goal="explicit goal",
        outcome="explicit outcome",
        success=True,
        agent_id="agent-7",
    )
    assert trace.goal == "explicit goal"
    assert trace.outcome == "explicit outcome"
    assert trace.success is True
    assert trace.agent_id == "agent-7"


def test_from_chat_messages_multimodal_content() -> None:
    trace = from_chat_messages(
        [{"role": "user", "content": [{"type": "text", "text": "hello"}, {"type": "image"}]}]
    )
    assert "hello" in trace.steps[0].content


def test_from_otel_spans_orders_and_classifies() -> None:
    spans = [
        {"name": "tool.fetch", "start_time": 2, "attributes": {"x": 1}},
        {"name": "llm.chat", "start_time": 1, "attributes": {"gen_ai.completion": "done"}},
    ]
    trace = from_otel_spans(spans)
    # ordered by start_time: llm.chat first.
    assert trace.steps[0].type == "tool_call"  # gen_ai span
    assert "done" in trace.steps[0].content
    assert trace.steps[1].type == "observation"  # non-genai span


def test_from_otel_spans_otlp_attribute_list() -> None:
    spans = [
        {
            "name": "gen_ai.completion",
            "startTimeUnixNano": 5,
            "attributes": [{"key": "gen_ai.prompt", "value": {"stringValue": "hi"}}],
        }
    ]
    trace = from_otel_spans(spans)
    assert trace.steps[0].type == "tool_call"
    assert "hi" in trace.steps[0].content


def test_validates_against_real_aar_model() -> None:
    # The produced trace must satisfy the real AgentTrace pydantic model.
    from vstack.aar import AgentTrace

    trace = from_chat_messages([{"role": "user", "content": "x"}])
    assert isinstance(trace, AgentTrace)
    # round-trips through JSON
    AgentTrace.model_validate_json(trace.model_dump_json())


# --- CLI ------------------------------------------------------------------


def _run_cli(argv: list[str], stdin: str = "") -> tuple[int, str, str]:
    import sys

    from vstack.ingest._cli import main

    out, err, in_ = StringIO(), StringIO(), StringIO(stdin)
    ro, re_, ri = sys.stdout, sys.stderr, sys.stdin
    sys.stdout, sys.stderr, sys.stdin = out, err, in_
    try:
        code = main(argv)
    finally:
        sys.stdout, sys.stderr, sys.stdin = ro, re_, ri
    return code, out.getvalue(), err.getvalue()


def test_cli_messages_stdin_to_trace() -> None:
    msgs = [{"role": "user", "content": "do a thing"}, {"role": "assistant", "content": "ok"}]
    code, out, _ = _run_cli(["--format", "messages", "-"], stdin=json.dumps(msgs))
    assert code == 0
    trace = json.loads(out)
    assert trace["goal"] == "do a thing"
    assert len(trace["steps"]) == 2


def test_cli_wrapped_dict_input() -> None:
    payload = {"messages": [{"role": "user", "content": "q"}]}
    code, out, _ = _run_cli(["--format", "messages"], stdin=json.dumps(payload))
    assert code == 0
    assert json.loads(out)["goal"] == "q"


def test_cli_bad_shape_returns_2() -> None:
    code, _out, err = _run_cli(["--format", "messages"], stdin=json.dumps({"nope": 1}))
    assert code == 2
    assert "vstack-import" in err


# --- LangSmith ------------------------------------------------------------


def test_from_langsmith_run_tree() -> None:
    from vstack.ingest import from_langsmith_runs

    tree = {
        "name": "My Chat Bot",
        "run_type": "chain",
        "start_time": "2026-01-01T00:00:00",
        "inputs": {"text": "summarize meetings"},
        "outputs": {"output": "done"},
        "child_runs": [
            {
                "name": "My LLM",
                "run_type": "llm",
                "start_time": "2026-01-01T00:00:01",
                "inputs": {"prompts": ["..."]},
                "outputs": {"generations": ["use the tool"]},
            },
            {
                "name": "loader",
                "run_type": "tool",
                "start_time": "2026-01-01T00:00:02",
                "inputs": {"date": "x"},
                "error": "boom",
            },
        ],
    }
    trace = from_langsmith_runs(tree)
    types = [s.type for s in trace.steps]
    assert types == ["thought", "message", "tool_call"]  # chain, llm, tool
    assert trace.goal.startswith("") and "summarize meetings" in trace.goal
    assert "ERROR: boom" in trace.steps[2].content


def test_from_langsmith_flat_list_orders_by_start() -> None:
    from vstack.ingest import from_langsmith_runs

    runs = [
        {"name": "b", "run_type": "tool", "start_time": "2026-01-01T00:00:05"},
        {"name": "a", "run_type": "llm", "start_time": "2026-01-01T00:00:01"},
    ]
    trace = from_langsmith_runs(runs)
    assert [s.metadata["name"] for s in trace.steps] == ["a", "b"]


def test_cli_langsmith_single_run() -> None:
    run = {"name": "root", "run_type": "chain", "inputs": {"q": "hi"}, "outputs": {"a": "ok"}}
    code, out, _ = _run_cli(["--format", "langsmith"], stdin=json.dumps(run))
    assert code == 0
    assert json.loads(out)["agent_framework"] == "langsmith"


def test_cli_phoenix_openinference_span() -> None:
    spans = [
        {
            "name": "llm",
            "start_time": 1,
            "attributes": {"openinference.span.kind": "LLM", "output.value": "the answer"},
        }
    ]
    code, out, _ = _run_cli(["--format", "phoenix"], stdin=json.dumps(spans))
    assert code == 0
    trace = json.loads(out)
    assert trace["steps"][0]["type"] == "tool_call"
    assert "the answer" in trace["steps"][0]["content"]
