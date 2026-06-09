"""Tests for the cost-tracking layer of vstack.diagnose.

The runner installs an in-memory telemetry sink for the duration of a
diagnose() call. Any pattern analyzer that calls
``vstack.aar.record_llm_call`` during that window contributes to the
report's ``CostSummary``. We verify three behaviors:

  1. A clean run with no telemetry produces an empty (but well-formed)
     CostSummary.
  2. Simulated telemetry events from inside a fake analyzer flow into
     the summary (counts + per-pattern + per-model breakdowns).
  3. The previously-installed sink is restored after the run so we
     don't leave global state mutated for the next caller.
"""

from __future__ import annotations

import sys
import types

from vstack.diagnose import CostSummary, diagnose
from vstack.diagnose.registry import PatternInfo

from vstack.aar import (  # type: ignore[attr-defined]
    InMemoryTelemetrySink,
    get_default_sink,
    record_llm_call,
    set_default_sink,
)


def _make_fake_pattern_emitting_telemetry(slug: str, pattern_id: int) -> PatternInfo:
    """Synthetic analyzer that fires one ``record_llm_call`` event with
    deterministic token + latency values when ``run()`` is invoked."""
    module_name = f"_test_cost_synth.{slug}"
    cls_name = f"{slug.title()}Analyzer"
    mod = types.ModuleType(module_name)

    class _Analyzer:
        def __init__(self, *, llm_client=None, mode="standard") -> None:
            self.llm_client = llm_client
            self.mode = mode

        def run(self, trace):  # noqa: ARG002
            # Pretend the analyzer made one LLM call.
            record_llm_call(
                pattern=slug,
                model="fake-model-mini",
                input_tokens=120,
                output_tokens=40,
                total_tokens=160,
                elapsed_ms=22.0,
            )
            return types.SimpleNamespace(findings=[{"severity": "low", "title": f"{slug} smoke"}])

    _Analyzer.__name__ = cls_name
    setattr(mod, cls_name, _Analyzer)
    sys.modules[module_name] = mod

    return PatternInfo(
        name=slug,
        module=module_name,
        analyzer=cls_name,
        analyzer_async=None,
        shapes=("individual",),
        module_id=9,
        pattern_id=pattern_id,
        summary="test pattern that emits telemetry",
    )


class _Trace:
    """Minimal individual-shape trace stub."""

    goal = "test"
    steps = ()


def test_empty_cost_summary_when_no_telemetry() -> None:
    """When no pattern emits telemetry, the report still has a
    well-formed (empty) CostSummary."""

    # Build a tiny synthetic pattern that returns findings but does NOT
    # emit telemetry, so the sink sees zero events.
    mod = types.ModuleType("_test_cost_synth.silent")

    class _Silent:
        def __init__(self, *, llm_client=None, mode="standard") -> None:
            pass

        def run(self, trace):  # noqa: ARG002
            return types.SimpleNamespace(findings=[])

    mod.SilentAnalyzer = _Silent  # type: ignore[attr-defined]
    sys.modules["_test_cost_synth.silent"] = mod

    info = PatternInfo(
        name="silent",
        module="_test_cost_synth.silent",
        analyzer="SilentAnalyzer",
        analyzer_async=None,
        shapes=("individual",),
        module_id=9,
        pattern_id=199,
        summary="silent test pattern",
    )
    report = diagnose(_Trace(), patterns=[info])

    assert isinstance(report.cost, CostSummary)
    assert report.cost.llm_calls == 0
    assert report.cost.total_tokens == 0
    assert report.cost.by_pattern == {}
    assert report.cost.by_model == {}


def test_cost_summary_aggregates_telemetry_events() -> None:
    a = _make_fake_pattern_emitting_telemetry("costa", pattern_id=210)
    b = _make_fake_pattern_emitting_telemetry("costb", pattern_id=211)
    report = diagnose(_Trace(), patterns=[a, b])

    # Two patterns each emitted one event -> 2 calls total.
    assert report.cost.llm_calls == 2
    assert report.cost.input_tokens == 240
    assert report.cost.output_tokens == 80
    assert report.cost.total_tokens == 320
    assert report.cost.elapsed_ms == 44.0

    # Per-pattern breakdown shows one call each.
    assert set(report.cost.by_pattern) == {"costa", "costb"}
    assert report.cost.by_pattern["costa"]["llm_calls"] == 1.0
    assert report.cost.by_pattern["costa"]["total_tokens"] == 160.0

    # Per-model breakdown collapses both calls under the shared model.
    assert "fake-model-mini" in report.cost.by_model
    assert report.cost.by_model["fake-model-mini"]["llm_calls"] == 2.0
    assert report.cost.by_model["fake-model-mini"]["total_tokens"] == 320.0


def test_runner_restores_previous_sink() -> None:
    """The runner installs its own sink for the duration of the run,
    then restores whatever sink was previously active. We verify by
    installing a tagged sentinel sink, running diagnose(), and
    checking the sentinel comes back."""
    sentinel = InMemoryTelemetrySink()
    sentinel.tag = "pre-run-sentinel"  # type: ignore[attr-defined]
    previous = get_default_sink()
    set_default_sink(sentinel)
    try:
        info = _make_fake_pattern_emitting_telemetry("costc", pattern_id=212)
        report = diagnose(_Trace(), patterns=[info])
        assert report.cost.llm_calls == 1
        assert get_default_sink() is sentinel
    finally:
        set_default_sink(previous)


def test_markdown_render_includes_cost_section_when_present() -> None:
    info = _make_fake_pattern_emitting_telemetry("costd", pattern_id=213)
    report = diagnose(_Trace(), patterns=[info])
    md = report.to_markdown()
    assert "Cost summary" in md
    assert "fake-model-mini" not in md  # By-model breakdown is in by_model
    # We at least show the per-pattern bucket.
    assert "costd" in md


def test_markdown_render_skips_cost_section_when_empty() -> None:
    # The silent pattern from the first test emits no telemetry.
    mod = sys.modules.get("_test_cost_synth.silent")
    if mod is None:
        # Pytest may execute tests in parallel; re-build if needed.
        test_empty_cost_summary_when_no_telemetry()
        mod = sys.modules["_test_cost_synth.silent"]
    info = PatternInfo(
        name="silent",
        module="_test_cost_synth.silent",
        analyzer="SilentAnalyzer",
        analyzer_async=None,
        shapes=("individual",),
        module_id=9,
        pattern_id=199,
        summary="silent test pattern",
    )
    report = diagnose(_Trace(), patterns=[info])
    md = report.to_markdown()
    assert "Cost summary" not in md
