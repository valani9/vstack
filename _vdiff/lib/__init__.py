"""vstack.vdiff — compare two diagnose reports.

The vdiff module produces a structured diff between two
DiagnoseReport instances (or their dict-serialized forms). Useful
for:

  - Regression testing: compare a new pattern version's output
    against a baseline.
  - Pre-deploy validation: compare current production output
    against last release's output.
  - A/B testing: compare two LLM models on the same trace.

Quick start
-----------

    from vstack.vdiff import diff_reports

    before = diagnose(trace=trace, llm_client=old_client)
    after = diagnose(trace=trace, llm_client=new_client)

    delta = diff_reports(before, after)
    print(delta.to_markdown())
    print(delta.is_regression(threshold=0.2))
"""

from __future__ import annotations

from ._diff import (
    FindingDiff,
    ReportDelta,
    diff_reports,
)

__all__ = [
    "FindingDiff",
    "ReportDelta",
    "diff_reports",
]
