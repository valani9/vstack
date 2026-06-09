"""Tests for the FastAPI dashboard server."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from vstack.dashboard.server import ReportStore, build_app


def _sample_report() -> dict:
    return {
        "report_id": "test-1",
        "shape": "individual",
        "findings": [
            {
                "pattern": "lewin",
                "severity": "high",
                "title": "env locus",
                "evidence": "stale rag",
                "intervention": "refresh nightly",
            }
        ],
        "per_pattern": [
            {
                "pattern": "lewin",
                "n_findings": 1,
                "elapsed_seconds": 1.2,
                "error": None,
            }
        ],
        "errors": {},
        "cost": {
            "llm_calls": 1,
            "input_tokens": 500,
            "output_tokens": 200,
            "total_tokens": 700,
            "elapsed_ms": 1200,
            "by_pattern": {},
            "by_model": {},
        },
        "cache_stats": None,
    }


@pytest.fixture
def client():
    store = ReportStore(maxsize=10)
    app = build_app(store=store)
    return TestClient(app), store


def test_healthz(client) -> None:
    c, _ = client
    r = c.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_home_empty_state(client) -> None:
    c, _ = client
    r = c.get("/")
    assert r.status_code == 200
    assert "No reports yet" in r.text


def test_ingest_then_view(client) -> None:
    c, store = client
    r = c.post("/v1/reports", json=_sample_report())
    assert r.status_code == 200
    body = r.json()
    assert body["report_id"] == "test-1"
    assert body["url"] == "/runs/test-1"
    # Detail page
    r = c.get("/runs/test-1")
    assert r.status_code == 200
    assert "env locus" in r.text


def test_unknown_run_returns_404(client) -> None:
    c, _ = client
    r = c.get("/runs/nope")
    assert r.status_code == 404


def test_autogen_id_when_missing(client) -> None:
    c, _ = client
    payload = _sample_report()
    del payload["report_id"]
    r = c.post("/v1/reports", json=payload)
    assert r.status_code == 200
    assert r.json()["report_id"].startswith("run-")


def test_list_reports(client) -> None:
    c, _ = client
    c.post("/v1/reports", json=_sample_report())
    r = c.get("/v1/reports")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert "test-1" in body["report_ids"]


def test_patterns_index(client) -> None:
    c, _ = client
    r = c.get("/patterns")
    assert r.status_code == 200
    assert "Pattern catalog" in r.text
    # A known pattern slug should appear in the catalog
    assert "lewin" in r.text


def test_recipes_index(client) -> None:
    c, _ = client
    r = c.get("/recipes")
    assert r.status_code == 200
    assert "Recipe catalog" in r.text
    # A known recipe should appear
    assert "stuck_in_loop" in r.text


# --- ReportStore -----------------------------------------------------


def test_store_round_trip() -> None:
    store = ReportStore(maxsize=10)
    store.put("a", {"shape": "individual"})
    assert store.get("a") == {"shape": "individual"}
    assert store.get("missing") is None


def test_store_evicts_oldest_when_full() -> None:
    store = ReportStore(maxsize=2)
    store.put("a", {"v": 1})
    store.put("b", {"v": 2})
    store.put("c", {"v": 3})
    assert store.get("a") is None
    assert store.get("b") == {"v": 2}
    assert store.get("c") == {"v": 3}


def test_store_move_to_end_on_overwrite() -> None:
    store = ReportStore(maxsize=2)
    store.put("a", {"v": 1})
    store.put("b", {"v": 2})
    store.put("a", {"v": 11})  # bumps a to most-recent
    store.put("c", {"v": 3})  # should evict b, not a
    assert store.get("a") == {"v": 11}
    assert store.get("b") is None
    assert store.get("c") == {"v": 3}
