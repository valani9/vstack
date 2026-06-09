"""The diagnose() runner: executes a bundle of vstack patterns against
one trace and merges their findings into a single ranked report.

Design notes
------------

1. We do NOT enforce a single Result schema on every pattern. Patterns
   ship their own analyzer classes with their own return types. The
   runner runs each analyzer's main entry point, then normalizes
   whatever comes back into a small :class:`Finding` dataclass via
   each pattern's adapter (``_adapters/lib`` already has one per
   pattern). When no adapter is available the runner falls back to
   reflecting on common attribute names ("score", "severity",
   "findings", "summary"), so adding a new pattern works without code
   changes here.

2. Patterns execute serially in the sync ``diagnose()`` because some
   pattern clients (Anthropic, OpenAI) are not safe to call concurrently
   from a single key without rate-limit coordination. Concurrent
   execution is available via ``diagnose_async()`` which uses each
   pattern's published async variant + asyncio.gather, with caller
   responsible for client concurrency.

3. Each pattern's failure is isolated. If one analyzer raises, the
   runner records the exception in the report's ``errors`` list and
   continues with the rest. A user debugging a misbehaving agent does
   not want one broken pattern to wipe out the other six findings.

4. Findings are ranked by severity (highest first), then by pattern
   id (lowest first), so reports read top-down in the order a human
   debugger would want to act on them.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

from .adapters import Finding, extract_findings
from .registry import (
    ALL_SHAPES,
    PATTERNS,
    PatternInfo,
    TraceShape,
    iter_bundle,
    resolve_pattern,
)

log = logging.getLogger("vstack.diagnose")


# Finding is defined in adapters.py to avoid a circular import; it is
# re-exported from this module so existing callers continue to work
# (``from vstack.diagnose.runner import Finding``).


@dataclass
class PatternResult:
    """The raw result of one pattern execution + the extracted findings.

    The runner keeps the raw ``result`` object around so a caller who
    wants pattern-specific richness (e.g., the full Lencioni pyramid
    breakdown) can still get at it without re-running the analyzer.
    ``findings`` is the normalized, ranking-ready form.
    """

    pattern: str
    info: PatternInfo
    result: Any = None
    findings: list[Finding] = field(default_factory=list)
    error: str | None = None
    elapsed_seconds: float = 0.0


@dataclass
class CostSummary:
    """Aggregate token + latency stats collected during one ``diagnose()``
    run.

    Populated by the runner from the telemetry events that participating
    patterns emit. Patterns that don't emit telemetry simply don't
    contribute, and the summary still reflects the patterns that did.

    Fields
    ------
    llm_calls: total number of LLM calls observed across the bundle.
    input_tokens / output_tokens / total_tokens: token totals.
    elapsed_ms: cumulative LLM latency in milliseconds.
    by_pattern: per-pattern breakdown for tooling. Each entry has
        the same field names (minus ``by_pattern``).
    by_model: per-model breakdown. Useful when one bundle hits multiple
        providers / model tiers.
    """

    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    elapsed_ms: float = 0.0
    by_pattern: dict[str, dict[str, float]] = field(default_factory=dict)
    by_model: dict[str, dict[str, float]] = field(default_factory=dict)


@dataclass
class DiagnoseReport:
    """The cross-pattern report ``diagnose()`` returns.

    Field ``per_pattern`` preserves the order in which patterns ran.
    Field ``findings`` is the merged + ranked view (highest severity
    first) and is what most users will read. ``errors`` lists pattern
    failures by pattern name with the exception message. ``cost`` is
    a :class:`CostSummary` aggregating LLM-call telemetry; populated
    when participating patterns emit telemetry events, empty otherwise.
    """

    shape: str
    per_pattern: list[PatternResult] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)
    cost: CostSummary = field(default_factory=CostSummary)
    # Populated only when diagnose() was called with cache=True.
    # Otherwise None so callers can tell whether caching was on at all.
    cache_stats: Any = None

    def top(self, k: int = 5) -> list[Finding]:
        """Return the top-k findings by severity rank."""
        return self.findings[:k]

    def to_html(self, *, report_id: str = "run", title: str | None = None) -> str:
        """Render the report as a self-contained HTML dashboard.

        Delegates to :func:`vstack.dashboard.render_report`. Open the
        returned HTML in any browser; no server needed. For a live
        multi-report view, use the ``vstack-dashboard serve`` CLI.
        """
        from vstack.dashboard import DashboardConfig, render_report

        cfg = DashboardConfig(title=title) if title else None
        return render_report(self, config=cfg, report_id=report_id)

    def to_markdown(self) -> str:
        """Render the report as a single self-contained Markdown
        document. The format is opinionated: an overview line, the
        top-3 findings as a numbered list, then a per-pattern section
        for full traceability."""
        lines: list[str] = []
        lines.append(f"# vstack diagnose -- {self.shape} trace")
        lines.append("")
        lines.append(
            f"Ran {len(self.per_pattern)} patterns; "
            f"surfaced {len(self.findings)} findings, "
            f"{len(self.errors)} pattern errors."
        )
        lines.append("")
        if self.findings:
            lines.append("## Top findings")
            for i, f in enumerate(self.top(5), 1):
                lines.append(f"{i}. **[{f.severity}]** `{f.pattern}` -- {f.title}")
                if f.evidence:
                    lines.append(f"   - evidence: {f.evidence}")
                if f.intervention:
                    lines.append(f"   - intervention: {f.intervention}")
            lines.append("")
        if self.cost.llm_calls > 0:
            lines.append("## Cost summary")
            lines.append(
                f"- {self.cost.llm_calls} LLM call(s); "
                f"{self.cost.input_tokens} in / "
                f"{self.cost.output_tokens} out tokens "
                f"({self.cost.total_tokens} total); "
                f"{self.cost.elapsed_ms:.0f} ms cumulative latency."
            )
            if self.cache_stats is not None:
                lines.append(
                    f"- Cache: {self.cache_stats.hits} hit(s) of "
                    f"{self.cache_stats.total_lookups} lookups "
                    f"({self.cache_stats.hit_rate:.0%} hit rate, "
                    f"{self.cache_stats.bytes_saved} bytes saved)."
                )
            if self.cost.by_pattern:
                lines.append("")
                lines.append("### By pattern")
                for name, stats in self.cost.by_pattern.items():
                    lines.append(
                        f"- `{name}`: {int(stats['llm_calls'])} call(s), "
                        f"{int(stats['total_tokens'])} tok, "
                        f"{stats['elapsed_ms']:.0f} ms"
                    )
            lines.append("")
        if self.errors:
            lines.append("## Pattern errors")
            for name, msg in self.errors.items():
                lines.append(f"- `{name}`: {msg}")
            lines.append("")
        return "\n".join(lines)


# --- normalization ----------------------------------------------------

# Findings extraction is delegated to :mod:`vstack.diagnose.adapters`.
# The runner used to ship its own reflective ``_coerce_findings`` that
# only knew about the generic ``findings`` / ``top_findings`` attribute
# names; that was lossy for most patterns (Lencioni's five dysfunctions
# collapsed to one Finding, etc.). The smart extractor in adapters.py
# walks the pattern-specific field-name inventory, then per-item field
# names, surfacing all N evidence items as their own Findings.
#
# A backward-compatible alias for the old name is preserved below so
# external code that imported ``_coerce_findings`` still works.

_coerce_findings = extract_findings


# --- pattern execution ------------------------------------------------


def _resolve_trace_shape(trace: Any, override: TraceShape | None) -> TraceShape:
    """Decide which trace shape we're dealing with.

    Order: explicit override > attribute introspection > fallback.
    Multi-agent traces carry an ``agents`` list; single-agent traces
    carry a ``steps`` list. Org traces carry an ``org_chart`` or are
    forced via override.
    """
    if override is not None:
        if override not in ALL_SHAPES:
            raise ValueError(f"unknown trace shape {override!r}; expected one of {ALL_SHAPES}")
        return override
    if hasattr(trace, "agents") and getattr(trace, "agents"):
        return "team"
    if hasattr(trace, "steps"):
        return "individual"
    if hasattr(trace, "org_chart") or hasattr(trace, "structure_matrix"):
        return "org"
    log.warning(
        "could not infer trace shape from %s; defaulting to 'team'",
        type(trace).__name__,
    )
    return "team"


def _normalize_bundle(
    bundle: Sequence[str | PatternInfo] | None, shape: TraceShape
) -> tuple[PatternInfo, ...]:
    if bundle is None:
        return iter_bundle(shape)
    out: list[PatternInfo] = []
    for item in bundle:
        if isinstance(item, PatternInfo):
            out.append(item)
            continue
        if item not in PATTERNS:
            raise ValueError(f"unknown pattern {item!r}; known: {sorted(PATTERNS)}")
        out.append(PATTERNS[item])
    return tuple(out)


def _call_analyzer(analyzer_obj: Any, trace: Any) -> Any:
    """Call whichever entry point the analyzer exposes. Patterns
    standardized on a few names (``run``, ``analyze``, ``generate``,
    ``__call__``). We try them in order and pick the first one that
    exists. If none exist we raise so the user sees the misconfiguration
    immediately instead of getting an empty report.
    """
    for name in ("run", "analyze", "generate", "audit", "detect", "diagnose"):
        method: Callable[..., Any] | None = getattr(analyzer_obj, name, None)
        if callable(method):
            return method(trace)
    if callable(analyzer_obj):
        return analyzer_obj(trace)
    raise TypeError(
        f"analyzer {type(analyzer_obj).__name__} does not expose a known "
        f"entry point (run/analyze/generate/audit/detect/diagnose/__call__)"
    )


async def _call_analyzer_async(analyzer_obj: Any, trace: Any) -> Any:
    for name in ("run", "analyze", "generate", "audit", "detect", "diagnose"):
        method: Callable[..., Any] | None = getattr(analyzer_obj, name, None)
        if callable(method):
            res = method(trace)
            if asyncio.iscoroutine(res):
                return await res
            return res
    if callable(analyzer_obj):
        res = analyzer_obj(trace)
        if asyncio.iscoroutine(res):
            return await res
        return res
    raise TypeError(
        f"async analyzer {type(analyzer_obj).__name__} does not expose a known entry point"
    )


# --- public api -------------------------------------------------------


def diagnose(
    trace: Any,
    *,
    llm_client: Any | None = None,
    shape: TraceShape | None = None,
    patterns: Sequence[str | PatternInfo] | None = None,
    recipe: str | None = None,
    mode: str = "standard",
    analyzer_kwargs: dict[str, dict[str, Any]] | None = None,
    cache: bool = False,
) -> DiagnoseReport:
    """Run a curated bundle of patterns against ``trace`` and return a
    ranked findings report.

    Parameters
    ----------
    trace
        Any vstack trace object. The runner infers the shape
        (``individual`` / ``team`` / ``org``) from attribute presence.
    llm_client
        An LLM client conforming to the
        :class:`vstack.aar.LLMClient` protocol. The same client is
        passed to every analyzer in the bundle.
    shape
        Override the inferred trace shape.
    patterns
        Override the default bundle. Each item is either a pattern slug
        from :data:`PATTERNS` or a :class:`PatternInfo` instance.
    mode
        Pipeline mode forwarded to analyzers that accept a ``mode=``
        kwarg (``quick`` / ``standard`` / ``forensic``). Patterns that
        do not accept it ignore it via :func:`analyzer_kwargs`.
    analyzer_kwargs
        Per-pattern keyword overrides. Maps pattern slug to a dict of
        kwargs passed to that pattern's analyzer constructor in
        addition to ``llm_client`` and ``mode``.

    recipe
        Named recipe from :data:`vstack.diagnose.RECIPES`. When passed
        in, the recipe's pattern list is used (and its shape is the
        default ``shape``). Explicit ``patterns=`` still wins if both
        are supplied.

    Returns
    -------
    :class:`DiagnoseReport`
    """
    if recipe is not None and patterns is None:
        from .recipes import RECIPES

        if recipe not in RECIPES:
            raise ValueError(f"unknown recipe {recipe!r}; known: {sorted(RECIPES)}")
        rec = RECIPES[recipe]
        patterns = rec.patterns
        if shape is None:
            shape = rec.shape
    inferred_shape = _resolve_trace_shape(trace, shape)
    bundle = _normalize_bundle(patterns, inferred_shape)
    overrides = dict(analyzer_kwargs or {})

    cache_wrapper: Any | None = None
    if cache and llm_client is not None:
        from .cache import CachingLLMClient

        cache_wrapper = CachingLLMClient(inner=llm_client)
        effective_client = cache_wrapper
    else:
        effective_client = llm_client

    report = DiagnoseReport(shape=inferred_shape)
    sink, restore_sink = _install_telemetry_sink()
    for info in bundle:
        result = PatternResult(pattern=info.name, info=info)
        try:
            classes = resolve_pattern(info)
            cls = classes["analyzer"]
            if cls is None:
                raise ImportError(f"pattern {info.name!r} has no main analyzer class")
            ctor_kwargs: dict[str, Any] = {}
            if effective_client is not None:
                ctor_kwargs["llm_client"] = effective_client
            # Some analyzers want llm_client positional; we always pass
            # it as a kwarg and rely on the constructor to map it.
            ctor_kwargs.update(overrides.get(info.name, {}))
            if "mode" in cls.__init__.__code__.co_varnames:  # type: ignore[attr-defined]
                ctor_kwargs.setdefault("mode", mode)
            import time

            t0 = time.time()
            try:
                inst = cls(**ctor_kwargs)
            except TypeError:
                # Fallback for analyzers that take llm_client positional.
                if effective_client is not None:
                    inst = cls(
                        effective_client,
                        **{k: v for k, v in ctor_kwargs.items() if k != "llm_client"},
                    )
                else:
                    raise
            result.result = _call_analyzer(inst, trace)
            result.findings = _coerce_findings(info.name, result.result)
            result.elapsed_seconds = time.time() - t0
        except Exception as exc:  # one bad pattern doesn't kill the report
            log.warning("pattern %s failed: %s", info.name, exc)
            result.error = str(exc)
            report.errors[info.name] = str(exc)
        report.per_pattern.append(result)

    _merge_and_rank(report)
    _aggregate_cost(report, sink)
    if cache_wrapper is not None:
        report.cache_stats = cache_wrapper.stats
    restore_sink()
    return report


async def diagnose_async(
    trace: Any,
    *,
    llm_client: Any | None = None,
    shape: TraceShape | None = None,
    patterns: Sequence[str | PatternInfo] | None = None,
    recipe: str | None = None,
    mode: str = "standard",
    analyzer_kwargs: dict[str, dict[str, Any]] | None = None,
    concurrency: int = 4,
    cache: bool = False,
) -> DiagnoseReport:
    """Async variant of :func:`diagnose`. Runs the bundle's async
    analyzers concurrently with a configurable max-in-flight bound
    (``concurrency``). Caller is responsible for any LLM-client
    rate-limit coordination."""
    if recipe is not None and patterns is None:
        from .recipes import RECIPES

        if recipe not in RECIPES:
            raise ValueError(f"unknown recipe {recipe!r}; known: {sorted(RECIPES)}")
        rec = RECIPES[recipe]
        patterns = rec.patterns
        if shape is None:
            shape = rec.shape
    inferred_shape = _resolve_trace_shape(trace, shape)
    bundle = _normalize_bundle(patterns, inferred_shape)
    overrides = dict(analyzer_kwargs or {})
    sem = asyncio.Semaphore(max(1, concurrency))

    cache_wrapper: Any | None = None
    if cache and llm_client is not None:
        from .cache import CachingLLMClient

        cache_wrapper = CachingLLMClient(inner=llm_client)
        effective_client = cache_wrapper
    else:
        effective_client = llm_client

    report = DiagnoseReport(shape=inferred_shape)

    async def _run_one(info: PatternInfo) -> PatternResult:
        result = PatternResult(pattern=info.name, info=info)
        async with sem:
            try:
                classes = resolve_pattern(info)
                cls = classes["analyzer_async"] or classes["analyzer"]
                if cls is None:
                    raise ImportError(f"pattern {info.name!r} has no analyzer class")
                ctor_kwargs: dict[str, Any] = {}
                if effective_client is not None:
                    ctor_kwargs["llm_client"] = effective_client
                ctor_kwargs.update(overrides.get(info.name, {}))
                if "mode" in cls.__init__.__code__.co_varnames:  # type: ignore[attr-defined]
                    ctor_kwargs.setdefault("mode", mode)
                import time

                t0 = time.time()
                try:
                    inst = cls(**ctor_kwargs)
                except TypeError:
                    if effective_client is not None:
                        inst = cls(
                            effective_client,
                            **{k: v for k, v in ctor_kwargs.items() if k != "llm_client"},
                        )
                    else:
                        raise
                result.result = await _call_analyzer_async(inst, trace)
                result.findings = _coerce_findings(info.name, result.result)
                result.elapsed_seconds = time.time() - t0
            except Exception as exc:
                log.warning("pattern %s failed: %s", info.name, exc)
                result.error = str(exc)
        return result

    sink, restore_sink = _install_telemetry_sink()
    try:
        tasks = [_run_one(info) for info in bundle]
        per_pattern = await asyncio.gather(*tasks)
    finally:
        restore_sink()
    report.per_pattern = list(per_pattern)
    for r in report.per_pattern:
        if r.error:
            report.errors[r.pattern] = r.error
    _merge_and_rank(report)
    _aggregate_cost(report, sink)
    if cache_wrapper is not None:
        report.cache_stats = cache_wrapper.stats
    return report


def _merge_and_rank(report: DiagnoseReport) -> None:
    """Flatten every per-pattern findings list into the report-level
    ``findings`` list, sorted by (severity rank desc, pattern id asc).
    Mutates ``report`` in place."""
    flat: list[Finding] = []
    for pr in report.per_pattern:
        flat.extend(pr.findings)
    pattern_id = {info.name: info.pattern_id for info in PATTERNS.values()}
    flat.sort(
        key=lambda f: (
            -f.severity_rank(),
            pattern_id.get(f.pattern, 9999),
        )
    )
    report.findings = flat


def _install_telemetry_sink() -> tuple[Any, Callable[[], None]]:
    """Install an in-memory telemetry sink for the duration of one
    diagnose call. Returns the sink + a restore callable that the
    caller invokes when the run is done.

    Importing the telemetry layer is best-effort; older installs that
    pre-date :mod:`vstack.aar._telemetry` will get a no-op sink that
    silently swallows events. The diagnose() flow still works in that
    case, the cost summary just stays empty.
    """
    try:
        from vstack.aar import (  # type: ignore[attr-defined]
            InMemoryTelemetrySink,
            get_default_sink,
            set_default_sink,
        )
    except ImportError:

        class _Stub:
            events: list[Any] = []

        return _Stub(), lambda: None

    previous = get_default_sink()
    sink = InMemoryTelemetrySink()
    set_default_sink(sink)

    def _restore() -> None:
        set_default_sink(previous)

    return sink, _restore


def _aggregate_cost(report: DiagnoseReport, sink: Any) -> None:
    """Aggregate telemetry events from ``sink`` into the report's
    cost summary. Designed to never raise: any malformed event is
    silently skipped. A patternless event (one without
    ``event.pattern`` set) contributes to the totals but not to the
    per-pattern breakdown.
    """
    events = getattr(sink, "events", None) or []
    summary = report.cost
    for event in events:
        if getattr(event, "event_type", None) != "llm_call":
            continue
        in_t = int(getattr(event, "input_tokens", 0) or 0)
        out_t = int(getattr(event, "output_tokens", 0) or 0)
        tot_t = int(getattr(event, "total_tokens", 0) or 0) or (in_t + out_t)
        elapsed = float(getattr(event, "elapsed_ms", 0.0) or 0.0)
        summary.llm_calls += 1
        summary.input_tokens += in_t
        summary.output_tokens += out_t
        summary.total_tokens += tot_t
        summary.elapsed_ms += elapsed
        pattern = getattr(event, "pattern", None)
        if pattern:
            bucket = summary.by_pattern.setdefault(
                pattern,
                {
                    "llm_calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "elapsed_ms": 0.0,
                },
            )
            bucket["llm_calls"] = float(bucket["llm_calls"]) + 1
            bucket["input_tokens"] = float(bucket["input_tokens"]) + in_t
            bucket["output_tokens"] = float(bucket["output_tokens"]) + out_t
            bucket["total_tokens"] = float(bucket["total_tokens"]) + tot_t
            bucket["elapsed_ms"] = float(bucket["elapsed_ms"]) + elapsed
        model = getattr(event, "model", None)
        if model:
            bucket = summary.by_model.setdefault(
                model,
                {
                    "llm_calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "elapsed_ms": 0.0,
                },
            )
            bucket["llm_calls"] = float(bucket["llm_calls"]) + 1
            bucket["input_tokens"] = float(bucket["input_tokens"]) + in_t
            bucket["output_tokens"] = float(bucket["output_tokens"]) + out_t
            bucket["total_tokens"] = float(bucket["total_tokens"]) + tot_t
            bucket["elapsed_ms"] = float(bucket["elapsed_ms"]) + elapsed
