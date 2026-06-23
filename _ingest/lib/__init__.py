"""Import real-world traces into vstack's :class:`~vstack.aar.AgentTrace`.

Your agent runs already produce traces — as chat-completion message logs
(OpenAI / Anthropic style) or as OpenTelemetry spans. These converters turn
those into the canonical ``AgentTrace`` that every vstack pattern consumes, so
you can pipe real data straight into ``vstack-diagnose`` without hand-writing a
trace.

Public API:

* :func:`from_chat_messages` — a list of ``{role, content, tool_calls?}`` dicts.
* :func:`from_otel_spans` — a list of OpenTelemetry span dicts (best-effort,
  reads ``gen_ai.*`` attributes).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from vstack.aar import AgentTrace, TraceStep

__all__ = ["from_chat_messages", "from_otel_spans"]

_BASE_TS = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _coerce_content(content: Any) -> str:
    """Flatten a message ``content`` (str or multimodal list) to text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                parts.append(
                    str(block.get("text") or block.get("content") or block.get("type") or "")
                )
            else:
                parts.append(str(block))
        return "\n".join(p for p in parts if p)
    return str(content)


def _ts(index: int) -> datetime:
    return _BASE_TS + timedelta(seconds=index)


def from_chat_messages(
    messages: list[dict[str, Any]],
    *,
    goal: str = "",
    outcome: str = "",
    success: bool = False,
    agent_id: str | None = None,
    agent_framework: str = "chat",
    metadata: dict[str, Any] | None = None,
) -> AgentTrace:
    """Build an ``AgentTrace`` from chat-completion messages.

    Role → step mapping: ``system``/``user`` → ``message``; ``assistant``
    text → ``message`` and any ``tool_calls`` → ``tool_call``; ``tool`` →
    ``observation``. ``goal`` defaults to the first user message and
    ``outcome`` to the last assistant message when not given.
    """
    steps: list[TraceStep] = []
    idx = 0
    first_user = ""
    last_assistant = ""

    for msg in messages:
        role = str(msg.get("role", "")).lower()
        content = _coerce_content(msg.get("content"))
        tool_calls = msg.get("tool_calls") or []

        if role in ("system", "user", "developer"):
            if content:
                steps.append(TraceStep(timestamp=_ts(idx), type="message", content=content))
                idx += 1
            if role == "user" and content and not first_user:
                first_user = content
        elif role == "assistant":
            if content:
                steps.append(TraceStep(timestamp=_ts(idx), type="message", content=content))
                idx += 1
                last_assistant = content
            for call in tool_calls:
                fn = call.get("function", call) if isinstance(call, dict) else {}
                name = fn.get("name", "tool")
                args = fn.get("arguments", "")
                steps.append(
                    TraceStep(timestamp=_ts(idx), type="tool_call", content=f"{name}({args})")
                )
                idx += 1
        elif role == "tool":
            steps.append(
                TraceStep(
                    timestamp=_ts(idx), type="observation", content=content or "(tool result)"
                )
            )
            idx += 1
        elif content:
            steps.append(TraceStep(timestamp=_ts(idx), type="message", content=content))
            idx += 1

    return AgentTrace(
        agent_id=agent_id,
        agent_framework=agent_framework,
        goal=goal or first_user or "(goal not provided)",
        steps=steps,
        outcome=outcome or last_assistant or "(outcome not provided)",
        success=success,
        metadata=metadata or {},
    )


def _span_start(span: dict[str, Any]) -> Any:
    return span.get("start_time") or span.get("startTime") or span.get("startTimeUnixNano") or 0


def from_otel_spans(
    spans: list[dict[str, Any]],
    *,
    goal: str = "",
    outcome: str = "",
    success: bool = False,
    agent_id: str | None = None,
    agent_framework: str = "otel",
    metadata: dict[str, Any] | None = None,
) -> AgentTrace:
    """Build an ``AgentTrace`` from OpenTelemetry spans (best-effort).

    Spans are ordered by start time. Each span becomes a step: GenAI/LLM spans
    (a ``gen_ai.*`` attribute or an ``llm``/``chat`` name) → ``tool_call``;
    others → ``observation``. Reads ``attributes`` either as a dict or as a
    list of ``{key, value}`` (OTLP-JSON form).
    """
    ordered = sorted(spans, key=_span_start)
    steps: list[TraceStep] = []

    for i, span in enumerate(ordered):
        attrs = _otel_attrs(span)
        name = str(span.get("name", "span"))
        is_genai = name.lower().startswith(("llm", "chat", "gen_ai")) or any(
            k.startswith("gen_ai") for k in attrs
        )
        completion = (
            attrs.get("gen_ai.completion")
            or attrs.get("gen_ai.response.content")
            or attrs.get("llm.output")
        )
        prompt = attrs.get("gen_ai.prompt") or attrs.get("llm.input")
        detail = str(completion or prompt or "")
        content = f"{name}: {detail}" if detail else name
        steps.append(
            TraceStep(
                timestamp=_ts(i),
                type="tool_call" if is_genai else "observation",
                content=content,
                metadata={"span_name": name},
            )
        )

    return AgentTrace(
        agent_id=agent_id,
        agent_framework=agent_framework,
        goal=goal or "(goal not provided)",
        steps=steps,
        outcome=outcome or "(outcome not provided)",
        success=success,
        metadata=metadata or {},
    )


def _otel_attrs(span: dict[str, Any]) -> dict[str, Any]:
    raw = span.get("attributes", {})
    if isinstance(raw, dict):
        return raw
    out: dict[str, Any] = {}
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict) and "key" in item:
                val = item.get("value")
                if isinstance(val, dict):
                    val = next(iter(val.values()), val)
                out[str(item["key"])] = val
    return out
