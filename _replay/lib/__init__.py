"""vstack.replay — replay historical diagnose() runs from JSONL logs.

The replay module lets you re-run diagnostic analysis against
previously-captured traces without re-spending LLM calls. The
``ReplayClient`` matches the LLM client protocol and returns
canned responses from a JSONL file.

Use cases
---------

* **Regression testing.** Run a new pattern version against last
  week's traces without re-paying for LLM calls.
* **Pattern development.** Iterate locally against a fixed trace +
  response set; verify new logic doesn't change scoring on known
  cases.
* **CI gates.** Compare current pattern output against captured
  baseline using deterministic replay.

Quick start
-----------

    from vstack.replay import (
        ReplayClient,
        ReplayRecorder,
        load_run_log,
    )

    # First — record a production run to JSONL:
    recorder = ReplayRecorder("runs/2026-06-09.jsonl")
    client = recorder.wrap(AnthropicClient())

    from vstack.lewin import LewinAttributionDetector
    detector = LewinAttributionDetector(client)
    detector.run(trace)
    recorder.close()

    # Later — replay against the captured log:
    replay = ReplayClient.from_file("runs/2026-06-09.jsonl")
    detector = LewinAttributionDetector(replay)
    detector.run(trace)  # uses canned responses, no LLM calls

Format
------

The replay log is JSONL: one JSON object per LLM call. Each line:

    {
      "request_hash": "...",          # SHA256 of canonicalized messages
      "request": {"messages": [...], "model": "...", ...},
      "response": {"content": "...", "tokens_in": 1000, ...},
      "timestamp": "2026-06-09T12:34:56Z",
      "pattern": "lewin"               # optional metadata
    }
"""

from __future__ import annotations

from ._recorder import (
    ReplayRecorder,
)
from ._replay import (
    ReplayClient,
    ReplayEntry,
    ReplayMissError,
    load_run_log,
)

__all__ = [
    "ReplayClient",
    "ReplayEntry",
    "ReplayMissError",
    "ReplayRecorder",
    "load_run_log",
]
