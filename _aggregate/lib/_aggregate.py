"""Cross-report aggregation."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any


def _get_findings(report: Any) -> list[Any]:
    if isinstance(report, dict):
        return list(report.get("findings", []))
    if hasattr(report, "findings"):
        return list(report.findings)
    if isinstance(report, list):
        return list(report)
    return []


def _f(finding: Any, field: str, default: Any = "") -> Any:
    if isinstance(finding, dict):
        return finding.get(field, default)
    return getattr(finding, field, default)


@dataclass
class PatternStats:
    """Per-pattern aggregate stats."""

    pattern: str
    total: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0

    @property
    def severity_score(self) -> float:
        """Weighted severity (high=3, med=2, low=1)."""
        return self.high * 3 + self.medium * 2 + self.low

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern": self.pattern,
            "total": self.total,
            "high": self.high,
            "medium": self.medium,
            "low": self.low,
            "severity_score": self.severity_score,
        }


@dataclass
class AggregateSummary:
    """Cross-report summary."""

    total_reports: int = 0
    total_findings: int = 0
    unique_patterns: int = 0
    pattern_stats: dict[str, PatternStats] = field(default_factory=dict)
    severity_counts: dict[str, int] = field(default_factory=dict)
    agent_counts: dict[str, int] = field(default_factory=dict)

    def top_patterns(self, n: int = 10) -> list[PatternStats]:
        items = sorted(
            self.pattern_stats.values(),
            key=lambda p: (-p.total, -p.severity_score, p.pattern),
        )
        return items[:n]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_reports": self.total_reports,
            "total_findings": self.total_findings,
            "unique_patterns": self.unique_patterns,
            "pattern_stats": {k: v.to_dict() for k, v in self.pattern_stats.items()},
            "severity_counts": dict(self.severity_counts),
            "agent_counts": dict(self.agent_counts),
        }


def aggregate_reports(
    reports: list[Any],
    *,
    agent_id_extractor: Any = None,
) -> AggregateSummary:
    """Cross-report aggregation.

    Args:
        reports: list of report objects (dict or attr-style).
        agent_id_extractor: callable(report) → str. Default: pulls
            'agent_id' from the report dict.
    """
    summary = AggregateSummary(total_reports=len(reports))

    if agent_id_extractor is None:

        def agent_id_extractor(r: Any) -> str:
            if isinstance(r, dict):
                return str(r.get("agent_id", "unknown"))
            return str(getattr(r, "agent_id", "unknown"))

    for report in reports:
        findings = _get_findings(report)
        agent = agent_id_extractor(report)

        for finding in findings:
            pattern = str(_f(finding, "pattern", "unknown"))
            severity = str(_f(finding, "severity", "low"))

            stats = summary.pattern_stats.setdefault(pattern, PatternStats(pattern=pattern))
            stats.total += 1
            if severity == "high":
                stats.high += 1
            elif severity == "medium":
                stats.medium += 1
            else:
                stats.low += 1

            summary.severity_counts[severity] = summary.severity_counts.get(severity, 0) + 1
            summary.agent_counts[agent] = summary.agent_counts.get(agent, 0) + 1
            summary.total_findings += 1

    summary.unique_patterns = len(summary.pattern_stats)
    return summary


def top_n_patterns(reports: list[Any], n: int = 10) -> list[tuple[str, int]]:
    """Return [(pattern, count)] for the top-N patterns by frequency."""
    counter: Counter[str] = Counter()
    for report in reports:
        for finding in _get_findings(report):
            pattern = str(_f(finding, "pattern", "unknown"))
            counter[pattern] += 1
    return counter.most_common(n)


def top_n_agents(
    reports: list[Any],
    *,
    n: int = 10,
    severity: str | None = None,
) -> list[tuple[str, int]]:
    """Return [(agent_id, finding_count)] for the noisiest agents.

    If ``severity`` is given, only count findings of that severity.
    """
    counter: Counter[str] = Counter()
    for report in reports:
        agent = "unknown"
        if isinstance(report, dict):
            agent = str(report.get("agent_id", "unknown"))
        elif hasattr(report, "agent_id"):
            agent = str(report.agent_id)

        for finding in _get_findings(report):
            if severity is not None and _f(finding, "severity") != severity:
                continue
            counter[agent] += 1
    return counter.most_common(n)


def severity_distribution(reports: list[Any]) -> dict[str, int]:
    """Count of findings per severity bucket."""
    dist: dict[str, int] = {"high": 0, "medium": 0, "low": 0}
    for report in reports:
        for finding in _get_findings(report):
            severity = str(_f(finding, "severity", "low"))
            dist[severity] = dist.get(severity, 0) + 1
    return dist


def cooccurrence_matrix(reports: list[Any]) -> dict[tuple[str, str], int]:
    """Count co-occurrence of pattern pairs within the same report.

    Returns a dict keyed by (pattern_a, pattern_b) where a < b
    (tuples ordered canonically). Value = number of reports in
    which both patterns appeared.
    """
    matrix: dict[tuple[str, str], int] = {}
    for report in reports:
        patterns = set()
        for finding in _get_findings(report):
            patterns.add(str(_f(finding, "pattern", "unknown")))
        # All pairs.
        plist = sorted(patterns)
        for i, a in enumerate(plist):
            for b in plist[i + 1 :]:
                key = (a, b)
                matrix[key] = matrix.get(key, 0) + 1
    return matrix
