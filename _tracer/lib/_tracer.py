"""Inline tracer for live agent instrumentation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import TracebackType
from typing import Any, Literal

from vstack.aar import AgentTrace, TraceStep

# Mirrors the Literal accepted by TraceStep.type.
StepKind = Literal["tool_call", "message", "decision", "observation", "thought"]


@dataclass
class StepRecord:
    """A recorded step before conversion to TraceStep."""

    kind: StepKind  # thought / tool_call / observation / message / decision
    content: str
    timestamp: datetime
    extra: dict[str, Any] = field(default_factory=dict)


class Tracer:
    """Fluent recorder for building agent traces.

    Usage as context manager (recommended):

        with Tracer(goal="task") as t:
            t.thought("...")
            t.tool_call("name", "args")

    Or imperatively:

        t = Tracer(goal="task")
        t.thought("...")
        ...
        trace = t.finalize(outcome="...", success=True)
    """

    def __init__(
        self,
        *,
        goal: str = "",
        agent_id: str | None = None,
        model_name: str | None = None,
    ):
        self.goal = goal
        self.agent_id = agent_id
        self.model_name = model_name
        self._records: list[StepRecord] = []
        self._outcome: str = ""
        self._success: bool = True
        self._retry_count: int = 0
        self._finalized_trace: AgentTrace | None = None

    def _now(self) -> datetime:
        return datetime.now(tz=timezone.utc)

    def thought(self, content: str, **extra: Any) -> Tracer:
        self._records.append(
            StepRecord(
                kind="thought",
                content=content,
                timestamp=self._now(),
                extra=dict(extra),
            )
        )
        return self

    def tool_call(self, tool: str, args: str = "", **extra: Any) -> Tracer:
        content = f"{tool}({args})" if args else tool
        self._records.append(
            StepRecord(
                kind="tool_call",
                content=content,
                timestamp=self._now(),
                extra={"tool": tool, "args": args, **extra},
            )
        )
        return self

    def observation(self, content: str, **extra: Any) -> Tracer:
        self._records.append(
            StepRecord(
                kind="observation",
                content=content,
                timestamp=self._now(),
                extra=dict(extra),
            )
        )
        return self

    def message(self, content: str, **extra: Any) -> Tracer:
        self._records.append(
            StepRecord(
                kind="message",
                content=content,
                timestamp=self._now(),
                extra=dict(extra),
            )
        )
        return self

    def decision(self, content: str, **extra: Any) -> Tracer:
        self._records.append(
            StepRecord(
                kind="decision",
                content=content,
                timestamp=self._now(),
                extra=dict(extra),
            )
        )
        return self

    def set_outcome(self, outcome: str, *, success: bool = True) -> Tracer:
        self._outcome = outcome
        self._success = success
        return self

    def set_retry_count(self, count: int) -> Tracer:
        self._retry_count = count
        return self

    def finalize(
        self,
        *,
        outcome: str | None = None,
        success: bool | None = None,
    ) -> AgentTrace:
        """Build the final AgentTrace from the recorded steps."""
        if outcome is not None:
            self._outcome = outcome
        if success is not None:
            self._success = success

        steps = [
            TraceStep(
                timestamp=r.timestamp,
                type=r.kind,
                content=r.content,
            )
            for r in self._records
        ]

        trace = AgentTrace(
            goal=self.goal,
            steps=steps,
            outcome=self._outcome,
            success=self._success,
            retry_count=self._retry_count,
        )
        self._finalized_trace = trace
        return trace

    @property
    def trace(self) -> AgentTrace:
        if self._finalized_trace is None:
            return self.finalize()
        return self._finalized_trace

    def records(self) -> list[StepRecord]:
        """Return the recorded steps (mutable copy)."""
        return list(self._records)

    def step_count(self) -> int:
        return len(self._records)

    def clear(self) -> None:
        self._records.clear()
        self._finalized_trace = None

    # Context manager support.
    def __enter__(self) -> Tracer:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            self._outcome = self._outcome or f"Exception: {exc_val}"
            self._success = False
        self.finalize()
