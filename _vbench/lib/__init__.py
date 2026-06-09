"""vstack.vbench — in-process benchmark runner for vstack patterns.

Distinct from ``vstack.benchmarks`` (which runs against external
agent-task suites), ``vstack.vbench`` measures the *pattern
runtime itself*: latency, token use, finding stability across runs,
and confidence calibration regression vs a baseline.

Use cases
---------

* **Pattern regression testing.** A new pattern release shouldn't
  silently get slower or noisier; vbench surfaces both.
* **Pre-release performance gates.** Block a release if p95 latency
  exceeds threshold.
* **Cross-model comparison.** Same trace, multiple LLM clients;
  vbench tabulates results.

Quick start
-----------

    from vstack.vbench import (
        BenchHarness,
        BenchResult,
        compare_results,
    )
    from vstack.trace_zoo import get_trace
    from vstack.aar.clients import StubClient

    harness = BenchHarness(
        traces=[get_trace("stuck_in_loop"), get_trace("hallucinated_citation")],
        patterns=["lewin", "aar"],
        repetitions=3,
    )

    result = harness.run(llm_client=StubClient())
    print(result.to_markdown())

    # Compare against a baseline.
    baseline = BenchResult.load("baselines/bench-v0.27.json")
    print(compare_results(baseline, result).to_markdown())
"""

from __future__ import annotations

from ._bench import (
    BenchHarness,
    BenchResult,
    BenchRun,
    Statistics,
    compare_results,
)

__all__ = [
    "BenchHarness",
    "BenchResult",
    "BenchRun",
    "Statistics",
    "compare_results",
]
