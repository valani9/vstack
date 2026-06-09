"""Tests for the streaming module."""

from __future__ import annotations

import json

import pytest

from vstack.streaming import Event, EventStream, SSEStreamWriter


class TestEventStream:
    def test_emit_records(self):
        stream = EventStream()
        stream.emit("test_event", key="value")
        events = stream.events()
        assert len(events) == 1
        assert events[0].kind == "test_event"
        assert events[0].payload["key"] == "value"

    def test_emit_returns_event(self):
        stream = EventStream()
        e = stream.emit("test", foo="bar")
        assert isinstance(e, Event)
        assert e.kind == "test"

    def test_run_lifecycle(self):
        stream = EventStream()
        stream.run_started(recipe="stuck_in_loop", pattern_count=3)
        stream.pattern_started("lewin")
        stream.finding_emitted("lewin", "high", "Stuck loop")
        stream.pattern_completed("lewin", duration_ms=100)
        stream.run_completed(findings_count=1)

        kinds = [e.kind for e in stream.events()]
        assert "run_started" in kinds
        assert "pattern_started" in kinds
        assert "finding_emitted" in kinds
        assert "pattern_completed" in kinds
        assert "run_completed" in kinds

    def test_listener_fires_on_kind(self):
        stream = EventStream()
        received = []

        def listener(event):
            received.append(event)

        stream.add_listener("finding_emitted", listener)
        stream.finding_emitted("lewin", "high", "test")
        stream.pattern_started("lewin")

        # Only the finding event should reach the listener.
        assert len(received) == 1
        assert received[0].kind == "finding_emitted"

    def test_wildcard_listener_fires_on_all(self):
        stream = EventStream()
        received = []

        stream.add_listener("*", lambda e: received.append(e))
        stream.emit("a")
        stream.emit("b")
        stream.emit("c")

        assert len(received) == 3

    def test_decorator_register(self):
        stream = EventStream()
        received = []

        @stream.on("finding_emitted")
        def on_finding(event):
            received.append(event)

        stream.finding_emitted("a", "low", "x")
        assert len(received) == 1

    def test_remove_listener(self):
        stream = EventStream()
        received = []

        def listener(event):
            received.append(event)

        stream.add_listener("test", listener)
        stream.emit("test")
        stream.remove_listener("test", listener)
        stream.emit("test")

        # Only first emit should have been received.
        assert len(received) == 1

    def test_listener_exception_swallowed(self):
        """A listener raising shouldn't break the emission."""
        stream = EventStream()

        def bad_listener(event):
            raise ValueError("oops")

        stream.add_listener("test", bad_listener)
        # Should not raise.
        stream.emit("test")

    def test_filter_events(self):
        stream = EventStream()
        stream.emit("a")
        stream.emit("b")
        stream.emit("a")
        stream.emit("c")

        a_events = stream.filter_events("a")
        assert len(a_events) == 2

    def test_buffer_caps_oldest_dropped(self):
        stream = EventStream(max_buffer=3)
        stream.emit("1")
        stream.emit("2")
        stream.emit("3")
        stream.emit("4")
        events = stream.events()
        # Oldest dropped.
        assert len(events) == 3
        assert events[0].kind == "2"

    def test_close(self):
        stream = EventStream()
        assert not stream.closed
        stream.close()
        assert stream.closed

    def test_error_event(self):
        stream = EventStream()
        stream.error(message="something failed", pattern="lewin")
        events = stream.filter_events("error")
        assert len(events) == 1
        assert events[0].payload["message"] == "something failed"


class TestEventProperties:
    def test_pattern_property(self):
        e = Event(kind="test", timestamp=0.0, payload={"pattern": "lewin"})
        assert e.pattern == "lewin"

    def test_severity_property(self):
        e = Event(kind="test", timestamp=0.0, payload={"severity": "high"})
        assert e.severity == "high"

    def test_title_property(self):
        e = Event(kind="test", timestamp=0.0, payload={"title": "x"})
        assert e.title == "x"

    def test_missing_properties_return_none(self):
        e = Event(kind="test", timestamp=0.0)
        assert e.pattern is None
        assert e.severity is None

    def test_to_dict(self):
        e = Event(kind="test", timestamp=1.0, payload={"foo": "bar"})
        data = e.to_dict()
        assert data["kind"] == "test"
        assert data["timestamp"] == 1.0
        assert data["foo"] == "bar"


class TestSSEWriter:
    def test_format_event(self):
        stream = EventStream()
        writer = SSEStreamWriter(stream)
        event = Event(kind="test", timestamp=1.0, payload={"a": 1})
        formatted = writer.format_event(event)
        assert "event: test" in formatted
        assert "data:" in formatted
        # Should end with double newline (SSE separator).
        assert formatted.endswith("\n\n")

    def test_all_buffered(self):
        stream = EventStream()
        stream.emit("a")
        stream.emit("b")

        writer = SSEStreamWriter(stream)
        text = writer.all_buffered()
        assert "event: a" in text
        assert "event: b" in text

    def test_data_parses_as_json(self):
        stream = EventStream()
        writer = SSEStreamWriter(stream)
        event = Event(kind="test", timestamp=1.0, payload={"foo": "bar", "n": 42})
        formatted = writer.format_event(event)
        # Find the data line and parse.
        for line in formatted.split("\n"):
            if line.startswith("data: "):
                data = json.loads(line[6:])
                assert data["foo"] == "bar"
                assert data["n"] == 42
                break
        else:
            pytest.fail("No data line found")
