"""vstack.streaming — SSE-friendly event stream for live diagnoses.

The streaming module emits incremental events as a diagnose() run
progresses, so downstream consumers (dashboards, CLIs, terminals)
can render findings as they appear instead of waiting for the
whole report.

Events
------

  - ``run_started``: at the start of a diagnose() call.
  - ``pattern_started``: when a pattern begins.
  - ``finding_emitted``: each finding as it's produced.
  - ``pattern_completed``: when a pattern finishes.
  - ``run_completed``: full report ready.
  - ``error``: any exception bubbled up.

Quick start
-----------

    from vstack.streaming import EventStream

    stream = EventStream()

    @stream.on("finding_emitted")
    def on_finding(event):
        print(f"  [{event.severity}] {event.pattern}: {event.title}")

    # Wire to your runner:
    stream.run_started(recipe="stuck_in_loop")
    stream.pattern_started("lewin")
    stream.finding_emitted("lewin", "high", "Stuck loop detected")
    stream.pattern_completed("lewin", duration_ms=1234)
    stream.run_completed(findings_count=3)

SSE
---

The ``SSEStreamWriter`` converts events to Server-Sent Events
format for HTTP streaming:

    writer = SSEStreamWriter(stream)
    for line in writer.iter_sse():
        yield line.encode("utf-8")
"""

from __future__ import annotations

from ._stream import (
    Event,
    EventStream,
    SSEStreamWriter,
)

__all__ = [
    "Event",
    "EventStream",
    "SSEStreamWriter",
]
