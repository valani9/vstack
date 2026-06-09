"""vstack.export — export findings to CSV, Markdown, JSON, Jira, GitHub.

The export module converts DiagnoseReports and finding lists into
formats suitable for downstream consumers:

  - **CSV** — for spreadsheet analysis.
  - **Markdown** — for documentation / PR comments.
  - **JSON** — for API responses.
  - **Jira ADF** — Atlassian Document Format for Jira issue body.
  - **GitHub comment** — markdown sized for a PR comment.

Quick start
-----------

    from vstack.export import (
        export_csv,
        export_markdown,
        export_jira,
        export_github_comment,
    )

    csv_text = export_csv(report)
    md_text = export_markdown(report, title="Run 2026-06-09")
    jira_payload = export_jira(report)
    pr_comment = export_github_comment(report, max_chars=8000)
"""

from __future__ import annotations

from ._export import (
    export_csv,
    export_github_comment,
    export_jira,
    export_json,
    export_markdown,
)

__all__ = [
    "export_csv",
    "export_github_comment",
    "export_jira",
    "export_json",
    "export_markdown",
]
