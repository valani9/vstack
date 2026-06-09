# Tutorial 7 — Deploying the vstack Dashboard

> Goal: stand up the vstack HTML dashboard in production. Covers
> rendering, serving, embedding, and integrating with the diagnose
> pipeline.

---

## What you'll build

By the end of this tutorial you'll have:

1. A static HTML report you can email or save.
2. A long-running FastAPI dashboard server you can browse.
3. A wired-up pipeline that captures every production run + renders
   a dashboard automatically.

---

## Part 1 — Static HTML rendering

The simplest dashboard surface: render a `DiagnoseReport` to a
single self-contained HTML file.

### Setup

```bash
pip install valanistack
```

The dashboard module is bundled in vstack — no extras needed.

### Render

```python
from vstack import diagnose
from vstack.aar import AgentTrace, TraceStep
from vstack.aar.clients import StubClient
from vstack.dashboard import render_report

trace = AgentTrace(
    goal="...",
    steps=[
        TraceStep(type="thought", content="..."),
        TraceStep(type="tool_call", content="..."),
        TraceStep(type="observation", content="..."),
    ],
    outcome="...",
    success=False,
)

report = diagnose(trace=trace, llm_client=StubClient())
html = render_report(report)

with open("report.html", "w") as f:
    f.write(html)
```

Open `report.html` in any browser. The HTML is self-contained —
all CSS + JS is inlined via Tailwind CDN + Chart.js CDN — and
renders identically across browsers.

### Configure

```python
from vstack.dashboard import render_report, DashboardConfig

config = DashboardConfig(
    title="Production Run 2026-06-09",
    badge_style="severity-tinted",
    chart_height=320,
)
html = render_report(report, config=config)
```

### Multi-report overview

If you have many reports, render an overview page that links to each:

```python
from vstack.dashboard import render_reports_overview

reports = [report1, report2, report3]
overview_html = render_reports_overview(
    reports=reports,
    title="Production Runs This Week",
)

with open("index.html", "w") as f:
    f.write(overview_html)
```

The overview page shows a sparkline + severity counts per report.

---

## Part 2 — FastAPI dashboard server

For interactive browsing, run the dashboard as a long-running
FastAPI server. Reports persist in-memory (or in a backing store)
and are browsable via routes.

### Launch

```bash
vstack-dashboard serve --port 7878
# or:
python -m vstack.dashboard serve --port 7878
```

Browse `http://localhost:7878`.

### Routes

| Route                       | Purpose                                          |
|-----------------------------|--------------------------------------------------|
| `GET /`                     | Overview of all stored reports                  |
| `GET /runs`                 | List runs (paginated)                            |
| `GET /runs/{report_id}`     | Single report's full HTML render                |
| `GET /patterns`             | Per-pattern explorer                             |
| `GET /recipes`              | Recipe catalog browser                           |
| `POST /v1/reports`          | Submit a new report                              |
| `GET /v1/reports`           | List report IDs (JSON)                           |
| `GET /healthz`              | Liveness check                                   |

### Submit a report

```python
import requests
from vstack import diagnose

report = diagnose(trace=..., llm_client=...)

response = requests.post(
    "http://localhost:7878/v1/reports",
    json={"report_id": "run-001", "report": report.model_dump()},
)
print(response.json())
# {"status": "stored", "url": "/runs/run-001"}
```

### Persistence

By default the dashboard uses an in-memory LRU-ish store with
capacity 1000. For persistence, configure a backing store via env:

```bash
VSTACK_DASHBOARD_STORE=filesystem
VSTACK_DASHBOARD_STORE_PATH=/var/lib/vstack-dashboard

vstack-dashboard serve --port 7878
```

Reports persist as JSON under the configured path. The server
loads them at startup.

---

## Part 3 — Wired-up production pipeline

For a full production pipeline that captures every run and
renders a dashboard automatically:

```python
from vstack import diagnose
from vstack.aar import AgentTrace
from vstack.dashboard import render_report
import requests

DASHBOARD_URL = "http://dashboard.internal:7878"


def diagnosed_production_run(agent_call_fn, **kwargs):
    """Wraps any agent function with vstack diagnostics + dashboard."""
    trace_id = generate_id()

    # Run the production agent.
    result, trace = agent_call_fn(**kwargs)

    # Diagnose.
    report = diagnose(trace=trace, llm_client=llm)

    # Submit to dashboard.
    submit_to_dashboard(trace_id, report)

    return result


def submit_to_dashboard(report_id: str, report) -> None:
    """POST the report to the dashboard server."""
    try:
        response = requests.post(
            f"{DASHBOARD_URL}/v1/reports",
            json={"report_id": report_id, "report": report.model_dump()},
            timeout=5,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        # Dashboard submission is best-effort; don't fail production.
        logger.warning("Dashboard submission failed: %s", exc)
```

### Severity-triggered alerts

```python
def submit_to_dashboard_with_alerts(report_id: str, report) -> None:
    """Submit + alert on high-severity findings."""
    submit_to_dashboard(report_id, report)

    high = [f for f in report.findings if f.severity == "high"]
    if high:
        send_alert(
            channel="#agent-alerts",
            text=f"High-severity findings in run {report_id}: {len(high)}",
            dashboard_url=f"{DASHBOARD_URL}/runs/{report_id}",
        )
```

---

## Embedding the dashboard

### In a Jupyter notebook

```python
from IPython.display import HTML
from vstack.dashboard import render_report

html = render_report(report)
HTML(html)
```

### In Streamlit

```python
import streamlit as st
from vstack.dashboard import render_report

html = render_report(report)
st.components.v1.html(html, height=900, scrolling=True)
```

### In a Slack message

```python
# Render as image (requires headless Chrome / Playwright).
from playwright.sync_api import sync_playwright
from vstack.dashboard import render_report

html = render_report(report)
with open("/tmp/report.html", "w") as f:
    f.write(html)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("file:///tmp/report.html")
    page.screenshot(path="/tmp/report.png", full_page=True)
    browser.close()

# Then send the PNG via Slack API.
```

---

## Production deployment checklist

- [ ] Dashboard server behind reverse proxy with TLS.
- [ ] Persistence backing store configured (`VSTACK_DASHBOARD_STORE`).
- [ ] Backup policy for the backing store.
- [ ] Auth in front of POST endpoints (the in-process auth is for
      sketch only; use your gateway).
- [ ] Rate limit on POST endpoints if exposed to user-facing
      agents.
- [ ] Monitoring for the `/healthz` endpoint.
- [ ] Log aggregation for the JSON access logs.
- [ ] Retention policy for old reports (filesystem store grows
      unbounded by default).

---

## Troubleshooting

### Dashboard renders blank

The dashboard uses Tailwind CDN + Chart.js CDN. If the rendered
HTML loads in a browser with no network access, charts won't render.
For air-gapped deployments, use the `bundle_assets=True` mode:

```python
html = render_report(report, config=DashboardConfig(bundle_assets=True))
```

This inlines Tailwind and Chart.js into the HTML output. The
file is bigger (~250KB instead of 20KB) but self-contained.

### Charts wrong colour

The dashboard auto-detects the user's prefers-color-scheme. Force
a theme with:

```python
config = DashboardConfig(theme="dark")  # or "light"
html = render_report(report, config=config)
```

### Custom CSS

```python
config = DashboardConfig(custom_css="""
    body { font-family: 'Inter', sans-serif; }
    .severity-high { background: #b91c1c; }
""")
```

---

## See also

- Tutorial 6: FastAPI deployment
- Surface reference: `docs/surfaces/dashboard.md`
- Source: `_dashboard/lib/`
