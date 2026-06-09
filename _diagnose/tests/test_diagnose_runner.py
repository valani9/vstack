"""Tests for the vstack.diagnose runner.

These tests build fake pattern analyzers in-memory and pass them in
via ``patterns=[PatternInfo(...)]``, so the suite does not depend on
the real pattern sub-packages and does not need an LLM client. They
exercise the four behaviors that matter:

  1. The runner calls each analyzer's entry point and collects the
     result.
  2. One pattern raising does not break the report.
  3. Findings are merged, ranked by severity, and the
     ``DiagnoseReport.to_markdown()`` renderer is well-formed.
  4. The async variant runs analyzers concurrently and returns the
     same merged report shape as the sync variant.
"""

from __future__ import annotations

import asyncio
import sys
import types
from dataclasses import dataclass

import pytest

from vstack.diagnose import (
    DiagnoseReport,
    Finding,
    PATTERNS,
    PatternResult,
    diagnose,
    diagnose_async,
)
from vstack.diagnose.registry import PatternInfo


# --- helpers ---------------------------------------------------------


def _make_fake_module(module_name: str, cls_name: str, async_cls_name: str | None = None) -> None:
    """Register a synthetic module under ``module_name`` exposing one
    analyzer class (with optional async variant). The runner uses
    importlib.import_module, so sys.modules registration is enough.
    """
    mod = types.ModuleType(module_name)

    class _Analyzer:
        def __init__(self, *, llm_client=None, mode="standard"):
            self.llm_client = llm_client
            self.mode = mode

        def run(self, trace):
            return types.SimpleNamespace(
                findings=[
                    {
                        "severity": "medium",
                        "title": f"fake finding from {cls_name}",
                        "evidence": f"trace.goal={getattr(trace, 'goal', None)!r}",
                        "intervention": "no-op (test analyzer)",
                    }
                ]
            )

    _Analyzer.__name__ = cls_name
    setattr(mod, cls_name, _Analyzer)

    if async_cls_name:

        class _AsyncAnalyzer:
            def __init__(self, *, llm_client=None, mode="standard"):
                self.llm_client = llm_client
                self.mode = mode

            async def run(self, trace):
                return types.SimpleNamespace(
                    findings=[
                        {
                            "severity": "high",
                            "title": f"async finding from {async_cls_name}",
                        }
                    ]
                )

        _AsyncAnalyzer.__name__ = async_cls_name
        setattr(mod, async_cls_name, _AsyncAnalyzer)

    sys.modules[module_name] = mod


def _make_pattern(
    slug: str,
    pattern_id: int = 99,
    shapes=("individual",),
    summary: str = "test pattern",
) -> PatternInfo:
    return PatternInfo(
        name=slug,
        module=f"_test_runner_synth.{slug}",
        analyzer=f"{slug.title()}Analyzer",
        analyzer_async=f"{slug.title()}AnalyzerAsync",
        shapes=shapes,
        module_id=9,
        pattern_id=pattern_id,
        summary=summary,
    )


def _setup_fake_pattern(info: PatternInfo) -> None:
    _make_fake_module(info.module, info.analyzer or "X", info.analyzer_async)


@dataclass
class FakeTrace:
    """A trace with both ``steps`` (single-agent) and ``goal`` so the
    runner's shape inference picks 'individual'."""

    goal: str = "fake goal"
    steps: tuple = ()


@dataclass
class FakeCrew:
    """Multi-agent trace: ``agents`` populated triggers 'team' shape."""

    goal: str = "fake crew goal"
    agents: tuple = ("alpha", "beta")
    messages: tuple = ()


# --- sync runner -----------------------------------------------------


def test_runner_collects_findings() -> None:
    info = _make_pattern("alpha", pattern_id=101)
    _setup_fake_pattern(info)
    report = diagnose(FakeTrace(), patterns=[info])
    assert report.shape == "individual"
    assert len(report.per_pattern) == 1
    pr = report.per_pattern[0]
    assert isinstance(pr, PatternResult)
    assert pr.error is None
    assert len(pr.findings) == 1
    assert pr.findings[0].pattern == "alpha"
    assert pr.findings[0].severity == "medium"


def test_runner_ranks_findings_by_severity() -> None:
    high = _make_pattern("highpat", pattern_id=110)
    low = _make_pattern("lowpat", pattern_id=111)
    _setup_fake_pattern(high)
    _setup_fake_pattern(low)

    # Mutate the synthetic analyzers to emit different severities.
    sys.modules[high.module].HighpatAnalyzer.run = (  # type: ignore[attr-defined]
        lambda self, trace: types.SimpleNamespace(findings=[{"severity": "high", "title": "H"}])
    )
    sys.modules[low.module].LowpatAnalyzer.run = (  # type: ignore[attr-defined]
        lambda self, trace: types.SimpleNamespace(findings=[{"severity": "low", "title": "L"}])
    )

    report = diagnose(FakeTrace(), patterns=[low, high])
    assert [f.severity for f in report.findings] == ["high", "low"]


def test_runner_isolates_pattern_errors() -> None:
    ok = _make_pattern("okpat", pattern_id=120)
    broken = _make_pattern("brokenpat", pattern_id=121)
    _setup_fake_pattern(ok)
    _setup_fake_pattern(broken)

    def _boom(self, trace):
        raise RuntimeError("simulated pattern crash")

    sys.modules[broken.module].BrokenpatAnalyzer.run = _boom  # type: ignore[attr-defined]

    report = diagnose(FakeTrace(), patterns=[ok, broken])
    assert len(report.per_pattern) == 2
    assert "brokenpat" in report.errors
    assert "simulated pattern crash" in report.errors["brokenpat"]
    # The OK pattern still landed a finding.
    assert any(p.pattern == "okpat" for p in report.findings)


def test_runner_renders_markdown_well_formed() -> None:
    info = _make_pattern("md", pattern_id=130)
    _setup_fake_pattern(info)
    report = diagnose(FakeTrace(), patterns=[info])
    md = report.to_markdown()
    assert "# vstack diagnose" in md
    assert "Top findings" in md
    assert "md" in md  # pattern slug appears


def test_explicit_shape_overrides_inference() -> None:
    info = _make_pattern("forceteam", pattern_id=140, shapes=("team",))
    _setup_fake_pattern(info)
    # FakeTrace would normally infer 'individual' but we force 'team'.
    report = diagnose(FakeTrace(), patterns=[info], shape="team")
    assert report.shape == "team"


def test_unknown_pattern_string_raises() -> None:
    with pytest.raises(ValueError):
        diagnose(FakeTrace(), patterns=["does_not_exist"])


def test_known_pattern_string_works() -> None:
    # Use one real pattern slug from PATTERNS but pre-replace its
    # module with a fake one so it does not import the real heavy
    # implementation. We pick "lewin" because it's the simplest
    # individual-mode pattern.
    real = PATTERNS["lewin"]
    fake = _make_pattern("lewinteststub", pattern_id=141)
    _setup_fake_pattern(fake)
    sys.modules[real.module] = sys.modules[fake.module]
    try:
        # Override the analyzer class name lookup to match our fake.
        sys.modules[real.module].LewinAttributionDetector = (  # type: ignore[attr-defined]
            sys.modules[fake.module].LewinteststubAnalyzer  # type: ignore[attr-defined]
        )
        report = diagnose(FakeTrace(), patterns=["lewin"])
        assert any(p.pattern == "lewin" for p in report.per_pattern)
    finally:
        # Restore so subsequent tests don't see the swap.
        del sys.modules[real.module]


# --- async runner ----------------------------------------------------


def test_async_runner_concurrent() -> None:
    a = _make_pattern("asynca", pattern_id=150)
    b = _make_pattern("asyncb", pattern_id=151)
    _setup_fake_pattern(a)
    _setup_fake_pattern(b)

    report = asyncio.run(diagnose_async(FakeTrace(), patterns=[a, b]))
    assert isinstance(report, DiagnoseReport)
    assert len(report.per_pattern) == 2
    # Async analyzers produced "high" severity findings per the helper.
    assert any(f.severity == "high" for f in report.findings)


# --- Finding helper API ----------------------------------------------


def test_finding_severity_rank_monotonic() -> None:
    assert (
        Finding(pattern="x", severity="critical", title="t").severity_rank()
        > Finding(pattern="x", severity="medium", title="t").severity_rank()
    )
    assert Finding(pattern="x", severity="none", title="t").severity_rank() == 0
