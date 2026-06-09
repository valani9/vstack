"""vstack.aggregate — cross-report aggregation utilities.

Aggregate findings across many reports for fleet-level analysis:

  - Top-N patterns by frequency.
  - Severity distribution.
  - Per-agent finding counts.
  - Co-occurrence: which pattern pairs appear together?
  - Trend: severity rate over time.

Quick start
-----------

    from vstack.aggregate import (
        aggregate_reports,
        top_n_patterns,
        cooccurrence_matrix,
    )

    summary = aggregate_reports(reports)
    print(summary.total_findings, summary.unique_patterns)

    top = top_n_patterns(reports, n=5)
    for pattern, count in top:
        print(pattern, count)
"""

from __future__ import annotations

from ._aggregate import (
    AggregateSummary,
    PatternStats,
    aggregate_reports,
    cooccurrence_matrix,
    severity_distribution,
    top_n_agents,
    top_n_patterns,
)

__all__ = [
    "AggregateSummary",
    "PatternStats",
    "aggregate_reports",
    "cooccurrence_matrix",
    "severity_distribution",
    "top_n_agents",
    "top_n_patterns",
]
