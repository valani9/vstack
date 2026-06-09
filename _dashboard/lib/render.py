"""Render a :class:`DiagnoseReport` (or a list of them) as polished HTML.

The output is a self-contained HTML document modeled after the
superlog observability dashboard aesthetic: dark-mode (#0a0e1a base,
#15192c panels), saturated chart colors, sectioned panels with
sticky headers.

The HTML is fully inline -- no external assets except CDN-loaded
Chart.js (for the charts) and Tailwind (for the layout). Open the
file in any modern browser; it's also embeddable in iframes.

The renderer is pure-Python with no template engine dependency
(we hand-roll string concatenation to keep the dashboard module
zero-dep at install time).
"""

from __future__ import annotations

import html
import json
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence


# ---------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------

# Severity colors (matched to the 7-point scale in vstack.diagnose.registry).
_SEVERITY_COLORS: dict[str, str] = {
    "critical": "#ef4444",  # red-500
    "high": "#f97316",  # orange-500
    "medium": "#f59e0b",  # amber-500
    "moderate": "#facc15",  # yellow-400
    "low": "#84cc16",  # lime-500
    "trace": "#3b82f6",  # blue-500
    "none": "#6b7280",  # gray-500
}

_SEVERITY_BG: dict[str, str] = {
    "critical": "#7f1d1d",
    "high": "#7c2d12",
    "medium": "#78350f",
    "moderate": "#713f12",
    "low": "#365314",
    "trace": "#1e3a8a",
    "none": "#374151",
}

# Pattern accent palette (rotates through these for cost-by-pattern + findings-by-pattern).
_PATTERN_COLORS: tuple[str, ...] = (
    "#a78bfa",  # violet-400
    "#22d3ee",  # cyan-400
    "#f472b6",  # pink-400
    "#34d399",  # emerald-400
    "#fbbf24",  # amber-400
    "#60a5fa",  # blue-400
    "#fb7185",  # rose-400
    "#4ade80",  # green-400
    "#facc15",  # yellow-400
    "#c084fc",  # purple-400
)


# ---------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------


@dataclass
class BadgeStyle:
    """Styling for a severity badge in the findings table."""

    background: str
    foreground: str = "#ffffff"


@dataclass
class DashboardConfig:
    """Customization knobs for the dashboard renderer.

    Most consumers will just use the defaults; if you want to ship a
    branded variant (e.g., embedded in your internal docs site), pass
    a :class:`DashboardConfig` with overrides.
    """

    title: str = "vstack diagnose"
    subtitle: str = "Cross-pattern agent diagnostic dashboard"
    accent: str = "#a78bfa"  # primary accent color
    show_top_n_findings: int = 10
    show_per_pattern_table: bool = True
    show_cost_panel: bool = True
    show_history_panel: bool = True
    badge_styles: dict[str, BadgeStyle] = field(default_factory=dict)

    def badge_for(self, severity: str) -> BadgeStyle:
        if severity in self.badge_styles:
            return self.badge_styles[severity]
        bg = _SEVERITY_BG.get(severity, "#374151")
        fg = _SEVERITY_COLORS.get(severity, "#9ca3af")
        return BadgeStyle(background=bg, foreground=fg)


# ---------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------


def render_report(
    report: Any,
    *,
    config: DashboardConfig | None = None,
    report_id: str | None = None,
) -> str:
    """Render one DiagnoseReport as a self-contained HTML document.

    ``report`` may be a real :class:`vstack.diagnose.DiagnoseReport`
    instance, OR a dict / SimpleNamespace with the same fields. The
    renderer reads attributes / keys uniformly so the function works
    with both the structured object and a JSON-parsed payload.

    ``report_id`` is a human-readable label shown in the header. If
    omitted, defaults to "run".
    """
    cfg = config or DashboardConfig()
    return _layout(
        head=_head(cfg),
        body=_single_report_body(report, cfg, report_id or "run"),
    )


def render_reports_overview(
    reports: Sequence[Any],
    *,
    config: DashboardConfig | None = None,
) -> str:
    """Render an overview dashboard summarizing N reports.

    Used by the FastAPI ``GET /`` route to list every report that
    has been uploaded / ingested. Each row links to a per-report
    detail view (rendered via :func:`render_report`).
    """
    cfg = config or DashboardConfig()
    return _layout(
        head=_head(cfg),
        body=_overview_body(reports, cfg),
    )


# ---------------------------------------------------------------------
# Layout primitives
# ---------------------------------------------------------------------


def _layout(*, head: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
{head}
</head>
<body class="bg-[#0a0e1a] text-gray-100 min-h-screen font-sans antialiased">
{body}
</body>
</html>"""


def _head(cfg: DashboardConfig) -> str:
    return f"""<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{html.escape(cfg.title)}</title>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  body {{ font-family: 'Inter', system-ui, -apple-system, sans-serif; }}
  .panel {{
    background: #15192c;
    border: 1px solid #232842;
    border-radius: 0.75rem;
    padding: 1.5rem;
  }}
  .badge {{
    display: inline-block;
    padding: 0.125rem 0.5rem;
    border-radius: 0.375rem;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.025em;
    text-transform: uppercase;
  }}
  .accent {{ color: {cfg.accent}; }}
  .accent-bg {{ background-color: {cfg.accent}; }}
  table.findings tbody tr {{ border-top: 1px solid #232842; }}
  table.findings tbody tr:hover {{ background: #1a1f36; }}
  details summary {{ cursor: pointer; user-select: none; }}
  details summary::-webkit-details-marker {{ display: none; }}
  details[open] summary::after {{ content: ' ▾'; }}
  details:not([open]) summary::after {{ content: ' ▸'; }}
</style>"""


# ---------------------------------------------------------------------
# Single-report body
# ---------------------------------------------------------------------


def _single_report_body(report: Any, cfg: DashboardConfig, label: str) -> str:
    shape = _read(report, "shape", "individual")
    findings = list(_read(report, "findings", []))
    per_pattern = list(_read(report, "per_pattern", []))
    errors = dict(_read(report, "errors", {}))
    cost = _read(report, "cost", None)

    findings_by_severity = _bucket_by_severity(findings)
    findings_by_pattern = _bucket_by_pattern(findings)

    return (
        _nav(cfg)
        + _hero(cfg, label, shape, len(per_pattern), len(findings), len(errors))
        + '<main class="max-w-7xl mx-auto px-6 pb-16 space-y-6">'
        + _stats_strip(findings, per_pattern, errors, cost)
        + '<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">'
        + _severity_chart_panel(findings_by_severity)
        + _pattern_chart_panel(findings_by_pattern)
        + "</div>"
        + (_cost_panel(cost) if cfg.show_cost_panel and cost else "")
        + (_per_pattern_table_panel(per_pattern, errors) if cfg.show_per_pattern_table else "")
        + _top_findings_panel(findings, cfg)
        + (_errors_panel(errors) if errors else "")
        + "</main>"
    )


# ---------------------------------------------------------------------
# Overview body
# ---------------------------------------------------------------------


def _overview_body(reports: Sequence[Any], cfg: DashboardConfig) -> str:
    rows: list[str] = []
    for i, r in enumerate(reports):
        rid = _read(r, "report_id", f"run-{i + 1}")
        shape = _read(r, "shape", "?")
        n_findings = len(list(_read(r, "findings", [])))
        n_patterns = len(list(_read(r, "per_pattern", [])))
        n_errors = len(dict(_read(r, "errors", {})))
        top_sev = _top_severity(_read(r, "findings", []))
        badge = cfg.badge_for(top_sev)
        rows.append(
            f"""<tr class="border-t border-[#232842] hover:bg-[#1a1f36]">
              <td class="py-3 pl-6 pr-3">
                <a class="accent hover:underline" href="/runs/{html.escape(rid)}">{html.escape(rid)}</a>
              </td>
              <td class="px-3 py-3"><span class="badge"
                style="background:#1e3a8a;color:#bfdbfe;">{html.escape(shape)}</span></td>
              <td class="px-3 py-3">{n_patterns}</td>
              <td class="px-3 py-3">{n_findings}</td>
              <td class="px-3 py-3">
                <span class="badge"
                  style="background:{badge.background};color:{badge.foreground};"
                >{html.escape(top_sev)}</span>
              </td>
              <td class="px-3 py-3 text-right text-red-400 pr-6">{n_errors}</td>
            </tr>"""
        )

    if not rows:
        empty = """<tr><td colspan="6" class="py-12 text-center text-gray-500">
          No reports yet. Upload one via POST /v1/reports or use vstack-diagnose --json | vstack-dashboard ingest.
        </td></tr>"""
        rows.append(empty)

    return (
        _nav(cfg)
        + f"""
<section class="max-w-7xl mx-auto px-6 pt-10 pb-4">
  <h1 class="text-3xl font-semibold">All runs</h1>
  <p class="text-gray-400 mt-2">Browse every diagnose run ingested into the dashboard.</p>
</section>
<main class="max-w-7xl mx-auto px-6 pb-16">
  <div class="panel p-0 overflow-hidden">
    <table class="w-full">
      <thead class="bg-[#1a1f36] text-left text-xs uppercase tracking-wider text-gray-400">
        <tr>
          <th class="py-3 pl-6 pr-3 font-medium">Report</th>
          <th class="px-3 py-3 font-medium">Shape</th>
          <th class="px-3 py-3 font-medium">Patterns</th>
          <th class="px-3 py-3 font-medium">Findings</th>
          <th class="px-3 py-3 font-medium">Top severity</th>
          <th class="px-3 py-3 font-medium text-right pr-6">Errors</th>
        </tr>
      </thead>
      <tbody>{"".join(rows)}</tbody>
    </table>
  </div>
</main>"""
    )


# ---------------------------------------------------------------------
# Panels
# ---------------------------------------------------------------------


def _nav(cfg: DashboardConfig) -> str:
    return f"""<nav class="border-b border-[#232842] bg-[#0d1120]">
  <div class="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
    <div class="flex items-center gap-6">
      <a href="/" class="text-lg font-semibold flex items-center gap-2">
        <span class="accent-bg w-6 h-6 rounded-md inline-block"></span>
        <span>{html.escape(cfg.title)}</span>
      </a>
      <div class="hidden md:flex items-center gap-4 text-sm text-gray-400">
        <a href="/" class="hover:text-white">Overview</a>
        <a href="/runs" class="hover:text-white">Runs</a>
        <a href="/patterns" class="hover:text-white">Patterns</a>
        <a href="/recipes" class="hover:text-white">Recipes</a>
      </div>
    </div>
    <div class="text-xs text-gray-500">vstack {html.escape(cfg.subtitle)}</div>
  </div>
</nav>"""


def _hero(
    cfg: DashboardConfig,
    label: str,
    shape: str,
    n_patterns: int,
    n_findings: int,
    n_errors: int,
) -> str:
    return f"""<section class="max-w-7xl mx-auto px-6 pt-10 pb-2">
  <div class="text-xs text-gray-500 uppercase tracking-wider mb-2">
    <a href="/" class="hover:text-white">All runs</a> / {html.escape(label)}
  </div>
  <h1 class="text-3xl font-semibold">Run {html.escape(label)}</h1>
  <p class="text-gray-400 mt-2">
    <span class="badge" style="background:#1e3a8a;color:#bfdbfe;">{html.escape(shape)}</span>
    <span class="ml-2">{n_patterns} patterns ran, surfaced {n_findings} findings, {n_errors} pattern errors.</span>
  </p>
</section>"""


def _stats_strip(findings: list[Any], per_pattern: list[Any], errors: dict, cost: Any) -> str:
    sev_counts = _bucket_by_severity(findings)
    high_or_worse = sev_counts.get("critical", 0) + sev_counts.get("high", 0)

    llm_calls = _read(cost, "llm_calls", 0) if cost else 0
    total_tokens = _read(cost, "total_tokens", 0) if cost else 0
    elapsed_ms = _read(cost, "elapsed_ms", 0.0) if cost else 0.0

    return f"""<div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div class="panel">
        <div class="text-xs text-gray-400 uppercase tracking-wider">Patterns run</div>
        <div class="text-3xl font-semibold mt-2">{len(per_pattern)}</div>
      </div>
      <div class="panel">
        <div class="text-xs text-gray-400 uppercase tracking-wider">Findings</div>
        <div class="text-3xl font-semibold mt-2">
          {len(findings)}
          <span class="text-sm font-normal text-orange-400 ml-2">
            {high_or_worse} high+
          </span>
        </div>
      </div>
      <div class="panel">
        <div class="text-xs text-gray-400 uppercase tracking-wider">LLM calls / tokens</div>
        <div class="text-3xl font-semibold mt-2">{llm_calls}</div>
        <div class="text-xs text-gray-500 mt-1">{total_tokens:,} tokens · {elapsed_ms / 1000:.1f}s</div>
      </div>
      <div class="panel">
        <div class="text-xs text-gray-400 uppercase tracking-wider">Pattern errors</div>
        <div class="text-3xl font-semibold mt-2 {("text-red-400" if errors else "text-gray-500")}">
          {len(errors)}
        </div>
      </div>
    </div>"""


def _severity_chart_panel(by_sev: dict[str, int]) -> str:
    labels = ["critical", "high", "medium", "moderate", "low", "trace", "none"]
    data = [by_sev.get(s, 0) for s in labels]
    colors = [_SEVERITY_COLORS[s] for s in labels]
    cfg = {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "label": "Findings",
                    "data": data,
                    "backgroundColor": colors,
                    "borderRadius": 6,
                    "borderSkipped": False,
                }
            ],
        },
        "options": {
            "responsive": True,
            "plugins": {"legend": {"display": False}},
            "scales": {
                "y": {
                    "ticks": {"color": "#6b7280"},
                    "grid": {"color": "#232842"},
                },
                "x": {
                    "ticks": {"color": "#9ca3af"},
                    "grid": {"display": False},
                },
            },
        },
    }
    return _chart_panel("Findings by severity", "sev-chart", cfg)


def _pattern_chart_panel(by_pat: dict[str, int]) -> str:
    pairs = sorted(by_pat.items(), key=lambda kv: -kv[1])[:12]
    labels = [p for p, _ in pairs]
    data = [c for _, c in pairs]
    colors = [_PATTERN_COLORS[i % len(_PATTERN_COLORS)] for i in range(len(pairs))]
    cfg = {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "label": "Findings",
                    "data": data,
                    "backgroundColor": colors,
                    "borderRadius": 6,
                    "borderSkipped": False,
                }
            ],
        },
        "options": {
            "indexAxis": "y",
            "responsive": True,
            "plugins": {"legend": {"display": False}},
            "scales": {
                "y": {
                    "ticks": {"color": "#9ca3af"},
                    "grid": {"display": False},
                },
                "x": {
                    "ticks": {"color": "#6b7280"},
                    "grid": {"color": "#232842"},
                },
            },
        },
    }
    return _chart_panel("Top patterns by finding count", "pat-chart", cfg)


def _cost_panel(cost: Any) -> str:
    by_pattern = dict(_read(cost, "by_pattern", {}) or {})
    if not by_pattern:
        return ""

    labels = list(by_pattern.keys())
    tokens = [int(by_pattern[k].get("total_tokens", 0)) for k in labels]
    elapsed = [float(by_pattern[k].get("elapsed_ms", 0.0)) for k in labels]
    colors = [_PATTERN_COLORS[i % len(_PATTERN_COLORS)] for i in range(len(labels))]

    cfg = {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "label": "Tokens",
                    "data": tokens,
                    "backgroundColor": colors,
                    "borderRadius": 6,
                    "yAxisID": "y",
                },
                {
                    "label": "Elapsed (ms)",
                    "data": elapsed,
                    "type": "line",
                    "borderColor": "#22d3ee",
                    "backgroundColor": "rgba(34,211,238,0.1)",
                    "tension": 0.3,
                    "yAxisID": "y1",
                },
            ],
        },
        "options": {
            "responsive": True,
            "scales": {
                "y": {
                    "ticks": {"color": "#6b7280"},
                    "grid": {"color": "#232842"},
                    "position": "left",
                    "title": {"display": True, "text": "Tokens", "color": "#9ca3af"},
                },
                "y1": {
                    "ticks": {"color": "#6b7280"},
                    "grid": {"display": False},
                    "position": "right",
                    "title": {"display": True, "text": "Elapsed (ms)", "color": "#9ca3af"},
                },
                "x": {
                    "ticks": {"color": "#9ca3af"},
                    "grid": {"display": False},
                },
            },
            "plugins": {"legend": {"labels": {"color": "#9ca3af"}}},
        },
    }
    return _chart_panel("Cost by pattern", "cost-chart", cfg)


def _per_pattern_table_panel(per_pattern: list[Any], errors: dict) -> str:
    rows = []
    for pr in per_pattern:
        name = _read(pr, "pattern", "?")
        n_findings = _read(pr, "n_findings", 0)
        elapsed = float(_read(pr, "elapsed_seconds", 0.0))
        err = _read(pr, "error", None) or errors.get(name)
        if err:
            err_cell = f'<span class="text-red-400">⚠ {html.escape(str(err)[:80])}</span>'
        else:
            err_cell = '<span class="text-gray-600">—</span>'
        rows.append(
            f"""<tr class="border-t border-[#232842]">
              <td class="py-2 pl-6 pr-3 font-mono text-sm">{html.escape(name)}</td>
              <td class="px-3 py-2">{n_findings}</td>
              <td class="px-3 py-2">{elapsed:.2f}s</td>
              <td class="px-3 py-2 pr-6">{err_cell}</td>
            </tr>"""
        )
    return f"""<section class="panel p-0 overflow-hidden">
  <div class="px-6 py-4 border-b border-[#232842] flex items-center justify-between">
    <h2 class="text-base font-semibold">Per-pattern run summary</h2>
    <span class="text-xs text-gray-500">{len(per_pattern)} patterns</span>
  </div>
  <table class="w-full">
    <thead class="bg-[#1a1f36] text-left text-xs uppercase tracking-wider text-gray-400">
      <tr>
        <th class="py-3 pl-6 pr-3 font-medium">Pattern</th>
        <th class="px-3 py-3 font-medium">Findings</th>
        <th class="px-3 py-3 font-medium">Elapsed</th>
        <th class="px-3 py-3 pr-6 font-medium">Error</th>
      </tr>
    </thead>
    <tbody>{"".join(rows) or "<tr><td colspan='4' class='py-8 text-center text-gray-500'>No patterns ran.</td></tr>"}</tbody>
  </table>
</section>"""


def _top_findings_panel(findings: list[Any], cfg: DashboardConfig) -> str:
    rows = []
    for f in findings[: cfg.show_top_n_findings]:
        sev = str(_read(f, "severity", "trace"))
        title = str(_read(f, "title", ""))
        pattern = str(_read(f, "pattern", ""))
        evidence = str(_read(f, "evidence", ""))
        intervention = str(_read(f, "intervention", ""))
        badge = cfg.badge_for(sev)
        rows.append(
            f"""<tr>
              <td class="py-3 pl-6 pr-3 w-24">
                <span class="badge"
                  style="background:{badge.background};color:{badge.foreground};">
                  {html.escape(sev)}
                </span>
              </td>
              <td class="px-3 py-3 font-mono text-sm text-gray-400 w-44">{html.escape(pattern)}</td>
              <td class="px-3 py-3">
                <div class="font-medium">{html.escape(title[:140])}</div>
                {_evidence_block(evidence, intervention)}
              </td>
            </tr>"""
        )
    body = (
        "".join(rows)
        or "<tr><td colspan='3' class='py-8 text-center text-gray-500'>No findings surfaced.</td></tr>"
    )
    return f"""<section class="panel p-0 overflow-hidden">
  <div class="px-6 py-4 border-b border-[#232842] flex items-center justify-between">
    <h2 class="text-base font-semibold">Top findings</h2>
    <span class="text-xs text-gray-500">Showing top {min(cfg.show_top_n_findings, len(findings))} of {len(findings)}</span>
  </div>
  <table class="w-full findings">
    <tbody>{body}</tbody>
  </table>
</section>"""


def _evidence_block(evidence: str, intervention: str) -> str:
    if not evidence and not intervention:
        return ""
    bits = []
    if evidence:
        bits.append(
            f'<div class="text-xs text-gray-500 mt-1">evidence: <span class="text-gray-300">{html.escape(evidence[:200])}</span></div>'
        )
    if intervention:
        bits.append(
            f'<div class="text-xs text-gray-500 mt-1">intervention: <span class="text-gray-300">{html.escape(intervention[:200])}</span></div>'
        )
    return "".join(bits)


def _errors_panel(errors: dict) -> str:
    rows = []
    for pat, msg in errors.items():
        rows.append(
            f"""<tr>
              <td class="py-2 pl-6 pr-3 font-mono text-sm">{html.escape(str(pat))}</td>
              <td class="px-3 py-2 pr-6 text-red-400">{html.escape(str(msg)[:300])}</td>
            </tr>"""
        )
    return f"""<section class="panel p-0 overflow-hidden border-red-900">
  <div class="px-6 py-4 border-b border-[#232842]">
    <h2 class="text-base font-semibold text-red-400">Pattern errors</h2>
  </div>
  <table class="w-full">
    <tbody>{"".join(rows)}</tbody>
  </table>
</section>"""


def _chart_panel(title: str, canvas_id: str, chart_config: dict) -> str:
    config_json = json.dumps(chart_config)
    return f"""<section class="panel">
  <div class="flex items-center justify-between mb-4">
    <h2 class="text-base font-semibold">{html.escape(title)}</h2>
  </div>
  <div style="position:relative;height:260px;">
    <canvas id="{canvas_id}"></canvas>
  </div>
  <script>
    (function() {{
      const ctx = document.getElementById({json.dumps(canvas_id)});
      const cfg = {config_json};
      new Chart(ctx, cfg);
    }})();
  </script>
</section>"""


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _read(obj: Any, name: str, default: Any) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _bucket_by_severity(findings: Iterable[Any]) -> dict[str, int]:
    out: dict[str, int] = {}
    for f in findings:
        sev = str(_read(f, "severity", "trace"))
        out[sev] = out.get(sev, 0) + 1
    return out


def _bucket_by_pattern(findings: Iterable[Any]) -> dict[str, int]:
    out: dict[str, int] = {}
    for f in findings:
        pat = str(_read(f, "pattern", "?"))
        out[pat] = out.get(pat, 0) + 1
    return out


def _top_severity(findings: Iterable[Any]) -> str:
    order = ("critical", "high", "medium", "moderate", "low", "trace", "none")
    seen = {sev for sev in (_read(f, "severity", "trace") for f in findings)}
    for s in order:
        if s in seen:
            return s
    return "none"
