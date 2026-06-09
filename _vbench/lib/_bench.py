"""Pattern benchmark harness — runs patterns and tabulates metrics."""

from __future__ import annotations

import json
import statistics
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence


@dataclass
class Statistics:
    """Summary statistics over a sample."""

    count: int
    mean: float
    median: float
    stddev: float
    p95: float
    p99: float
    min_: float
    max_: float

    @classmethod
    def from_samples(cls, samples: Sequence[float]) -> Statistics:
        if not samples:
            return cls(
                count=0,
                mean=0.0,
                median=0.0,
                stddev=0.0,
                p95=0.0,
                p99=0.0,
                min_=0.0,
                max_=0.0,
            )
        sorted_s = sorted(samples)
        n = len(sorted_s)
        return cls(
            count=n,
            mean=statistics.mean(samples),
            median=statistics.median(samples),
            stddev=statistics.stdev(samples) if n > 1 else 0.0,
            p95=_percentile(sorted_s, 0.95),
            p99=_percentile(sorted_s, 0.99),
            min_=min(samples),
            max_=max(samples),
        )

    def to_dict(self) -> dict[str, float]:
        return {
            "count": self.count,
            "mean": self.mean,
            "median": self.median,
            "stddev": self.stddev,
            "p95": self.p95,
            "p99": self.p99,
            "min": self.min_,
            "max": self.max_,
        }


def _percentile(sorted_samples: Sequence[float], p: float) -> float:
    if not sorted_samples:
        return 0.0
    n = len(sorted_samples)
    if n == 1:
        return sorted_samples[0]
    idx = max(0, min(n - 1, int(p * (n - 1))))
    return sorted_samples[idx]


@dataclass
class BenchRun:
    """A single (pattern, trace, rep) run."""

    pattern: str
    trace_name: str
    rep: int
    duration_ms: int
    finding_count: int
    severity_high_count: int
    severity_medium_count: int
    severity_low_count: int
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern": self.pattern,
            "trace_name": self.trace_name,
            "rep": self.rep,
            "duration_ms": self.duration_ms,
            "finding_count": self.finding_count,
            "severity_high_count": self.severity_high_count,
            "severity_medium_count": self.severity_medium_count,
            "severity_low_count": self.severity_low_count,
            "error": self.error,
        }


@dataclass
class BenchResult:
    """Aggregated benchmark result across all (pattern, trace, rep)."""

    runs: list[BenchRun] = field(default_factory=list)
    patterns: list[str] = field(default_factory=list)
    traces: list[str] = field(default_factory=list)
    repetitions: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)

    def latency_stats(self, *, pattern: str | None = None) -> Statistics:
        samples = [
            r.duration_ms
            for r in self.runs
            if r.error is None and (pattern is None or r.pattern == pattern)
        ]
        return Statistics.from_samples(samples)

    def finding_stats(self, *, pattern: str | None = None) -> Statistics:
        samples = [
            r.finding_count
            for r in self.runs
            if r.error is None and (pattern is None or r.pattern == pattern)
        ]
        return Statistics.from_samples(samples)

    def per_pattern_summary(self) -> dict[str, dict[str, Statistics]]:
        result: dict[str, dict[str, Statistics]] = {}
        for pattern in self.patterns:
            result[pattern] = {
                "latency_ms": self.latency_stats(pattern=pattern),
                "findings": self.finding_stats(pattern=pattern),
            }
        return result

    def error_rate(self) -> float:
        if not self.runs:
            return 0.0
        errors = sum(1 for r in self.runs if r.error is not None)
        return errors / len(self.runs)

    def to_dict(self) -> dict[str, Any]:
        return {
            "runs": [r.to_dict() for r in self.runs],
            "patterns": self.patterns,
            "traces": self.traces,
            "repetitions": self.repetitions,
            "error_rate": self.error_rate(),
            "per_pattern": {
                p: {k: v.to_dict() for k, v in stats.items()}
                for p, stats in self.per_pattern_summary().items()
            },
            "metadata": self.metadata,
        }

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: str | Path) -> BenchResult:
        data = json.loads(Path(path).read_text())
        runs = [
            BenchRun(
                pattern=r["pattern"],
                trace_name=r["trace_name"],
                rep=r["rep"],
                duration_ms=r["duration_ms"],
                finding_count=r["finding_count"],
                severity_high_count=r["severity_high_count"],
                severity_medium_count=r["severity_medium_count"],
                severity_low_count=r["severity_low_count"],
                error=r.get("error"),
            )
            for r in data.get("runs", [])
        ]
        return cls(
            runs=runs,
            patterns=data.get("patterns", []),
            traces=data.get("traces", []),
            repetitions=data.get("repetitions", 1),
            metadata=data.get("metadata", {}),
        )

    def to_markdown(self) -> str:
        lines = ["# Benchmark Result", ""]
        lines.append(f"**Runs**: {len(self.runs)}  |  **Error rate**: {self.error_rate():.1%}")
        lines.append("")
        lines.append("## Per-pattern latency (ms)")
        lines.append("")
        lines.append("| Pattern              | Count | Mean    | Median  | p95     | p99     |")
        lines.append("|----------------------|-------|---------|---------|---------|---------|")
        for pattern in self.patterns:
            stats = self.latency_stats(pattern=pattern)
            lines.append(
                f"| {pattern:20s} | {stats.count:5d} | "
                f"{stats.mean:7.1f} | {stats.median:7.1f} | "
                f"{stats.p95:7.1f} | {stats.p99:7.1f} |"
            )
        return "\n".join(lines)


class BenchHarness:
    """Runs patterns against traces; collects per-run metrics."""

    def __init__(
        self,
        *,
        traces: list[Any],
        patterns: list[str],
        repetitions: int = 1,
        trace_names: list[str] | None = None,
    ):
        self.traces = traces
        self.patterns = patterns
        self.repetitions = repetitions
        self.trace_names = trace_names or [
            getattr(t, "goal", "")[:30] or f"trace-{i}" for i, t in enumerate(traces)
        ]

    def run(
        self,
        *,
        llm_client: Any,
        mode: str = "standard",
    ) -> BenchResult:
        runs: list[BenchRun] = []

        for pattern in self.patterns:
            for trace_idx, trace in enumerate(self.traces):
                for rep in range(self.repetitions):
                    run = self._run_one(
                        pattern=pattern,
                        trace=trace,
                        trace_name=self.trace_names[trace_idx],
                        rep=rep,
                        llm_client=llm_client,
                        mode=mode,
                    )
                    runs.append(run)

        return BenchResult(
            runs=runs,
            patterns=list(self.patterns),
            traces=list(self.trace_names),
            repetitions=self.repetitions,
            metadata={"mode": mode},
        )

    def _run_one(
        self,
        *,
        pattern: str,
        trace: Any,
        trace_name: str,
        rep: int,
        llm_client: Any,
        mode: str,
    ) -> BenchRun:
        from vstack.diagnose import diagnose

        start = time.time()
        try:
            report = diagnose(
                trace=trace,
                llm_client=llm_client,
                patterns=[pattern],
                mode=mode,
            )
        except Exception as exc:
            return BenchRun(
                pattern=pattern,
                trace_name=trace_name,
                rep=rep,
                duration_ms=int((time.time() - start) * 1000),
                finding_count=0,
                severity_high_count=0,
                severity_medium_count=0,
                severity_low_count=0,
                error=str(exc),
            )
        duration_ms = int((time.time() - start) * 1000)

        findings = _get_findings(report)
        high = sum(1 for f in findings if _get_severity(f) == "high")
        med = sum(1 for f in findings if _get_severity(f) == "medium")
        low = sum(1 for f in findings if _get_severity(f) == "low")

        return BenchRun(
            pattern=pattern,
            trace_name=trace_name,
            rep=rep,
            duration_ms=duration_ms,
            finding_count=len(findings),
            severity_high_count=high,
            severity_medium_count=med,
            severity_low_count=low,
        )


def _get_findings(report: Any) -> list[Any]:
    if isinstance(report, dict):
        return list(report.get("findings", []))
    if hasattr(report, "findings"):
        return list(report.findings)
    return []


def _get_severity(finding: Any) -> str:
    if isinstance(finding, dict):
        return finding.get("severity", "low")
    return getattr(finding, "severity", "low")


@dataclass
class BenchComparison:
    """Delta between two benchmark results."""

    before: BenchResult
    after: BenchResult
    per_pattern_delta: dict[str, dict[str, float]] = field(default_factory=dict)

    @property
    def latency_regressions(self) -> list[tuple[str, float]]:
        """Patterns where p95 latency increased by > 20%."""
        return [
            (pattern, delta)
            for pattern, stats in self.per_pattern_delta.items()
            if (delta := stats.get("p95_pct", 0.0)) > 0.2
        ]

    @property
    def latency_improvements(self) -> list[tuple[str, float]]:
        return [
            (pattern, abs(delta))
            for pattern, stats in self.per_pattern_delta.items()
            if (delta := stats.get("p95_pct", 0.0)) < -0.2
        ]

    def to_markdown(self) -> str:
        lines = ["# Bench Comparison", ""]
        for pattern, stats in self.per_pattern_delta.items():
            delta = stats.get("p95_pct", 0.0)
            arrow = "↗" if delta > 0 else "↘" if delta < 0 else "→"
            lines.append(f"- **{pattern}**: p95 latency {arrow} {delta * 100:+.1f}%")
        return "\n".join(lines)


def compare_results(before: BenchResult, after: BenchResult) -> BenchComparison:
    """Compare two bench results pattern by pattern."""
    per_pattern: dict[str, dict[str, float]] = {}

    for pattern in set(before.patterns) | set(after.patterns):
        before_stats = before.latency_stats(pattern=pattern)
        after_stats = after.latency_stats(pattern=pattern)

        if before_stats.p95 == 0:
            p95_pct = 0.0
        else:
            p95_pct = (after_stats.p95 - before_stats.p95) / before_stats.p95

        per_pattern[pattern] = {
            "p95_before_ms": before_stats.p95,
            "p95_after_ms": after_stats.p95,
            "p95_pct": p95_pct,
            "mean_before_ms": before_stats.mean,
            "mean_after_ms": after_stats.mean,
        }

    return BenchComparison(
        before=before,
        after=after,
        per_pattern_delta=per_pattern,
    )
