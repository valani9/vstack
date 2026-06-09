"""FastAPI dashboard server.

Exposes a small multi-page HTML dashboard backed by an in-memory store
of ingested :class:`vstack.diagnose.DiagnoseReport` payloads. Designed
to run alongside ``vstack-api`` (or against any external service that
posts diagnose reports).

Routes:

  GET  /                       — overview table of all ingested reports
  GET  /runs                   — alias for /
  GET  /runs/{report_id}       — per-report dashboard (charts + tables)
  GET  /patterns               — pattern catalog browser
  GET  /recipes                — recipe catalog browser
  POST /v1/reports             — ingest a new report (JSON body)
  GET  /healthz                — liveness probe
  GET  /v1/reports             — list ingested reports as JSON

The store is in-memory; restarts wipe the catalog. For persistence,
front the server with a real cache backend or wire a database
(:class:`ReportStore` is intentionally pluggable).
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Any

from fastapi import Body, FastAPI, HTTPException, Path
from fastapi.responses import HTMLResponse, JSONResponse

from .render import (
    DashboardConfig,
    render_report,
    render_reports_overview,
)


# ---------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------


class ReportStore:
    """In-memory LRU-ish report store.

    Keeps the last ``maxsize`` reports keyed by report_id. Thread-safe
    under a single Python GIL via a lock; not designed for cross-process
    coordination.
    """

    def __init__(self, maxsize: int = 100) -> None:
        self._maxsize = maxsize
        self._lock = threading.Lock()
        self._items: OrderedDict[str, dict[str, Any]] = OrderedDict()

    def put(self, report_id: str, payload: dict[str, Any]) -> None:
        with self._lock:
            if report_id in self._items:
                self._items.move_to_end(report_id)
            self._items[report_id] = payload
            while len(self._items) > self._maxsize:
                self._items.popitem(last=False)

    def get(self, report_id: str) -> dict[str, Any] | None:
        with self._lock:
            return self._items.get(report_id)

    def all(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._items.values())

    def all_ids(self) -> list[str]:
        with self._lock:
            return list(self._items)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


# Module-level default store, used by the FastAPI app factory.
_DEFAULT_STORE = ReportStore(maxsize=200)


# ---------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------


def build_app(
    *,
    store: ReportStore | None = None,
    config: DashboardConfig | None = None,
) -> FastAPI:
    """Construct the dashboard FastAPI app.

    Parameters
    ----------
    store
        Custom :class:`ReportStore` (defaults to the module-level in-memory
        store).
    config
        Custom :class:`DashboardConfig` (defaults to the standard styling).
    """
    store = store or _DEFAULT_STORE
    cfg = config or DashboardConfig()
    app = FastAPI(title="vstack-dashboard", version="0.1.0")

    @app.get("/", response_class=HTMLResponse)
    def home() -> HTMLResponse:
        with_ids = [
            {**payload, "report_id": payload.get("report_id") or rid}
            for rid, payload in zip(store.all_ids(), store.all())
        ]
        return HTMLResponse(content=render_reports_overview(with_ids, config=cfg))

    @app.get("/runs", response_class=HTMLResponse)
    def runs() -> HTMLResponse:
        return home()

    @app.get("/runs/{report_id}", response_class=HTMLResponse)
    def run_detail(report_id: str = Path(...)) -> HTMLResponse:
        payload = store.get(report_id)
        if payload is None:
            raise HTTPException(status_code=404, detail=f"Unknown report {report_id!r}")
        return HTMLResponse(content=render_report(payload, config=cfg, report_id=report_id))

    @app.get("/patterns", response_class=HTMLResponse)
    def patterns_index() -> HTMLResponse:
        try:
            from vstack.diagnose import PATTERNS
        except ImportError:
            return HTMLResponse("vstack.diagnose not installed", status_code=503)

        rows = []
        for name in sorted(PATTERNS):
            info = PATTERNS[name]
            rows.append(
                f"<tr class='border-t border-[#232842] hover:bg-[#1a1f36]'>"
                f"<td class='py-3 pl-6 pr-3 font-mono text-sm accent'>{name}</td>"
                f"<td class='px-3 py-3 text-sm'>{', '.join(info.shapes)}</td>"
                f"<td class='px-3 py-3 text-gray-300'>{info.summary}</td>"
                f"</tr>"
            )
        body = (
            f"<section class='max-w-7xl mx-auto px-6 pt-10 pb-4'>"
            f"<h1 class='text-3xl font-semibold'>Pattern catalog</h1>"
            f"<p class='text-gray-400 mt-2'>{len(PATTERNS)} patterns shipped.</p>"
            f"</section>"
            f"<main class='max-w-7xl mx-auto px-6 pb-16'>"
            f"<div class='panel p-0 overflow-hidden'>"
            f"<table class='w-full'><thead class='bg-[#1a1f36] text-left text-xs uppercase tracking-wider text-gray-400'>"
            f"<tr><th class='py-3 pl-6 pr-3 font-medium'>Pattern</th>"
            f"<th class='px-3 py-3 font-medium'>Shapes</th>"
            f"<th class='px-3 py-3 font-medium'>Summary</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table></div></main>"
        )
        from .render import _head, _layout, _nav  # type: ignore[attr-defined]

        return HTMLResponse(content=_layout(head=_head(cfg), body=_nav(cfg) + body))

    @app.get("/recipes", response_class=HTMLResponse)
    def recipes_index() -> HTMLResponse:
        try:
            from vstack.diagnose import RECIPES, list_recipes_by_cluster
        except ImportError:
            return HTMLResponse("vstack.diagnose not installed", status_code=503)

        sections: list[str] = []
        for cluster, recipes in list_recipes_by_cluster().items():
            rows = []
            for r in recipes:
                triggers = f"<span class='text-xs text-gray-500'>{', '.join(r.triggers[:3])}</span>"
                rows.append(
                    f"<tr class='border-t border-[#232842] hover:bg-[#1a1f36]'>"
                    f"<td class='py-3 pl-6 pr-3 font-mono text-sm accent'>{r.name}</td>"
                    f"<td class='px-3 py-3 text-sm'>{r.shape}</td>"
                    f"<td class='px-3 py-3 text-gray-300'>{r.description}<br/>{triggers}</td>"
                    f"<td class='px-3 py-3 text-xs font-mono text-gray-500 text-right pr-6'>{', '.join(r.patterns[:4])}</td>"
                    f"</tr>"
                )
            sections.append(
                f"<h2 class='text-xl font-semibold mt-8 mb-3 capitalize'>{cluster}</h2>"
                f"<div class='panel p-0 overflow-hidden'>"
                f"<table class='w-full'><thead class='bg-[#1a1f36] text-left text-xs uppercase tracking-wider text-gray-400'>"
                f"<tr><th class='py-3 pl-6 pr-3 font-medium'>Recipe</th>"
                f"<th class='px-3 py-3 font-medium'>Shape</th>"
                f"<th class='px-3 py-3 font-medium'>Description / Triggers</th>"
                f"<th class='px-3 py-3 font-medium text-right pr-6'>Patterns</th></tr></thead>"
                f"<tbody>{''.join(rows)}</tbody></table></div>"
            )
        body = (
            f"<section class='max-w-7xl mx-auto px-6 pt-10 pb-4'>"
            f"<h1 class='text-3xl font-semibold'>Recipe catalog</h1>"
            f"<p class='text-gray-400 mt-2'>{len(RECIPES)} named recipes across 5 thematic clusters.</p>"
            f"</section>"
            f"<main class='max-w-7xl mx-auto px-6 pb-16'>{''.join(sections)}</main>"
        )
        from .render import _head, _layout, _nav  # type: ignore[attr-defined]

        return HTMLResponse(content=_layout(head=_head(cfg), body=_nav(cfg) + body))

    @app.post("/v1/reports")
    def ingest_report(payload: dict[str, Any] = Body(...)) -> JSONResponse:
        report_id = payload.get("report_id") or _autogen_id(store)
        payload.setdefault("report_id", report_id)
        store.put(report_id, payload)
        return JSONResponse(content={"report_id": report_id, "url": f"/runs/{report_id}"})

    @app.get("/v1/reports")
    def list_reports() -> JSONResponse:
        return JSONResponse(
            content={
                "count": len(store.all_ids()),
                "report_ids": store.all_ids(),
            }
        )

    @app.get("/healthz")
    def healthz() -> JSONResponse:
        return JSONResponse(content={"status": "ok", "reports": len(store.all_ids())})

    return app


def _autogen_id(store: ReportStore) -> str:
    """Generate a short sequential report id."""
    n = len(store.all_ids()) + 1
    return f"run-{n:04d}"


# Convenient module-level app for `uvicorn vstack.dashboard.server:app`
app = build_app()
