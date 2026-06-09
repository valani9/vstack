"""vstack.dashboard: HTML report generator + live FastAPI dashboard.

This is the visible-surface analog of what an observability product
like superlog (https://superlog.sh) ships for OTEL data: a polished,
multi-panel dashboard for the diagnose pipeline's findings, costs,
and pattern run history.

Two surfaces:

  - :func:`render_report` / :meth:`DiagnoseReport.to_html` -- takes
    one :class:`vstack.diagnose.DiagnoseReport` and emits a single
    self-contained HTML file. Open in any browser; no server needed.

  - :func:`build_app` -- a small FastAPI app that ingests one or more
    serialized reports (JSON) and serves an interactive multi-page
    dashboard with Chart.js panels. ``vstack-dashboard serve --port
    8001`` is the convenience entry point.

The HTML template is dark-mode + responsive, modeled after the
superlog hero screenshot: stacked area chart for findings by severity
over time, line charts for cost-by-pattern, pattern run history
table, and a top-findings panel with severity badges.

Both surfaces are pure-Python so they install with the base wheel;
the FastAPI variant just requires the existing ``[anthropic]`` /
``[fastapi]`` extras already present for the API server.
"""

from __future__ import annotations

from .render import (
    BadgeStyle,
    DashboardConfig,
    render_report,
    render_reports_overview,
)
from .server import build_app

__all__ = [
    "BadgeStyle",
    "DashboardConfig",
    "build_app",
    "render_report",
    "render_reports_overview",
]
