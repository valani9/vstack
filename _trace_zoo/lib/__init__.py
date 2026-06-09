"""vstack.trace_zoo — canonical library of synthetic agent traces.

The trace zoo is a curated catalog of named, ready-to-run agent
traces covering every failure mode in the recipe catalog. Each
trace has:

  - **A canonical name** matching the recipe it triggers.
  - **A failure shape** (individual / team / org).
  - **A stable schema** that won't change between vstack releases.
  - **Test coverage** verifying the trace round-trips and is valid
    for at least one pattern.

Use cases
---------

* **Scaffold a first diagnosis** — fetch a canonical trace and run
  ``diagnose()`` against it; you get realistic findings without
  building your own trace from scratch.
* **Unit-test pattern integrations** — call sites that need a known
  trace shape can fetch from the zoo instead of building bespoke
  fixtures.
* **Onboarding** — new users can browse the catalog to learn the
  trace shape per failure mode.

Quick start
-----------

    from vstack.trace_zoo import get_trace, list_traces

    # Fetch by name:
    trace = get_trace("stuck_in_loop")

    # Browse the catalog:
    for name, info in list_traces():
        print(name, info.shape, info.description)

    # Diagnose against a zoo trace:
    from vstack import diagnose
    from vstack.aar.clients import StubClient
    report = diagnose(trace=trace, llm_client=StubClient())

CLI
---

    vstack-trace-zoo list
    vstack-trace-zoo show stuck_in_loop
    vstack-trace-zoo get stuck_in_loop > trace.json
    vstack-trace-zoo categories
"""

from __future__ import annotations

from ._catalog import (
    CATALOG,
    TraceCategory,
    TraceInfo,
    get_trace,
    get_trace_info,
    list_traces,
    list_traces_by_category,
    list_traces_by_shape,
)
from ._cli import main as _cli_main

__all__ = [
    "CATALOG",
    "TraceCategory",
    "TraceInfo",
    "_cli_main",
    "get_trace",
    "get_trace_info",
    "list_traces",
    "list_traces_by_category",
    "list_traces_by_shape",
]
