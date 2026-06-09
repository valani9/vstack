"""Event stream + SSE writer."""

from __future__ import annotations

import json
import queue
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator


@dataclass
class Event:
    """A single event emitted by the stream."""

    kind: str
    """Event kind: run_started / pattern_started / finding_emitted /
    pattern_completed / run_completed / error."""

    timestamp: float
    payload: dict[str, Any] = field(default_factory=dict)

    @property
    def pattern(self) -> str | None:
        return self.payload.get("pattern")

    @property
    def severity(self) -> str | None:
        return self.payload.get("severity")

    @property
    def title(self) -> str | None:
        return self.payload.get("title")

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "timestamp": self.timestamp,
            **self.payload,
        }


class EventStream:
    """An in-process event stream for diagnose() runs.

    Listeners can subscribe to specific event kinds. The stream
    also buffers events for iteration after the run completes.
    """

    def __init__(self, *, max_buffer: int = 1000):
        self._listeners: dict[str, list[Callable[[Event], None]]] = {}
        self._events: list[Event] = []
        self._queue: queue.Queue[Event] = queue.Queue(maxsize=max_buffer)
        self._closed = False
        self._max_buffer = max_buffer

    def on(self, kind: str) -> Callable[[Callable[[Event], None]], Callable[[Event], None]]:
        """Decorator: register a listener for an event kind."""

        def decorator(fn: Callable[[Event], None]) -> Callable[[Event], None]:
            self._listeners.setdefault(kind, []).append(fn)
            return fn

        return decorator

    def add_listener(self, kind: str, fn: Callable[[Event], None]) -> None:
        self._listeners.setdefault(kind, []).append(fn)

    def remove_listener(self, kind: str, fn: Callable[[Event], None]) -> None:
        if kind in self._listeners:
            try:
                self._listeners[kind].remove(fn)
            except ValueError:
                pass

    def emit(self, kind: str, **payload: Any) -> Event:
        """Emit an event of the given kind with payload."""
        event = Event(
            kind=kind,
            timestamp=time.time(),
            payload=dict(payload),
        )
        self._events.append(event)
        if len(self._events) > self._max_buffer:
            self._events = self._events[-self._max_buffer :]

        # Notify per-kind listeners.
        for listener in self._listeners.get(kind, []):
            try:
                listener(event)
            except Exception:
                pass

        # Notify wildcard listeners.
        for listener in self._listeners.get("*", []):
            try:
                listener(event)
            except Exception:
                pass

        # Enqueue for streaming consumers.
        try:
            self._queue.put_nowait(event)
        except queue.Full:
            # Drop the oldest event.
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(event)
            except queue.Empty:
                pass

        return event

    def run_started(
        self,
        *,
        recipe: str | None = None,
        pattern_count: int | None = None,
        shape: str | None = None,
        run_id: str | None = None,
    ) -> Event:
        return self.emit(
            "run_started",
            recipe=recipe,
            pattern_count=pattern_count,
            shape=shape,
            run_id=run_id,
        )

    def pattern_started(self, pattern: str, *, mode: str = "standard") -> Event:
        return self.emit("pattern_started", pattern=pattern, mode=mode)

    def finding_emitted(
        self,
        pattern: str,
        severity: str,
        title: str,
        *,
        intervention: str = "",
        confidence: float | None = None,
    ) -> Event:
        return self.emit(
            "finding_emitted",
            pattern=pattern,
            severity=severity,
            title=title,
            intervention=intervention,
            confidence=confidence,
        )

    def pattern_completed(self, pattern: str, *, duration_ms: int = 0) -> Event:
        return self.emit("pattern_completed", pattern=pattern, duration_ms=duration_ms)

    def run_completed(self, *, findings_count: int = 0, duration_ms: int = 0) -> Event:
        return self.emit(
            "run_completed",
            findings_count=findings_count,
            duration_ms=duration_ms,
        )

    def error(self, *, message: str, pattern: str | None = None) -> Event:
        return self.emit("error", message=message, pattern=pattern)

    def close(self) -> None:
        self._closed = True

    @property
    def closed(self) -> bool:
        return self._closed

    def events(self) -> list[Event]:
        """Return all buffered events."""
        return list(self._events)

    def filter_events(self, kind: str) -> list[Event]:
        return [e for e in self._events if e.kind == kind]

    def iter_queue(self, *, timeout: float = 0.1) -> Iterator[Event]:
        """Yield events as they're enqueued. Stops when closed."""
        while not self._closed or not self._queue.empty():
            try:
                yield self._queue.get(timeout=timeout)
            except queue.Empty:
                continue


class SSEStreamWriter:
    """Convert an EventStream into Server-Sent Events lines."""

    def __init__(self, stream: EventStream):
        self.stream = stream

    def format_event(self, event: Event) -> str:
        """Format a single event as an SSE block."""
        data = json.dumps(event.to_dict(), default=str)
        return f"event: {event.kind}\ndata: {data}\n\n"

    def iter_sse(self) -> Iterator[str]:
        """Iterate the stream's queue as SSE-formatted strings."""
        for event in self.stream.iter_queue():
            yield self.format_event(event)
            if event.kind == "run_completed":
                break

    def all_buffered(self) -> str:
        """Format all buffered events as a single SSE string."""
        return "".join(self.format_event(e) for e in self.stream.events())
