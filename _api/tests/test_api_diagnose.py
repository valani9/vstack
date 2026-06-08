"""Tests for the ``POST /v1/diagnose`` endpoint.

The endpoint wraps :func:`vstack.diagnose.diagnose`. These tests use
synthetic patterns registered into the diagnose registry so the
endpoint exercises real wire shapes without needing an LLM. Validation
guards (unknown recipe, unknown pattern, recipe+patterns mutex, bad
shape) are tested via the 400 path; the timeout + 502 paths are
covered by the existing analyzer-level tests since they share the
same middleware stack.
"""

from __future__ import annotations

import sys
import types

import pytest
from fastapi.testclient import TestClient

import vstack.api as api
from vstack.diagnose.registry import PatternInfo


def _stub_pattern(slug: str, pattern_id: int, severity: str = "high") -> PatternInfo:
    """Register a synthetic vstack pattern that always emits one
    finding at the requested severity. Returns the PatternInfo so the
    test can put it in vstack.diagnose.PATTERNS for the duration of
    the test.
    """
    module_name = f"_test_api_diagnose_synth.{slug}"
    cls_name = f"{slug.title()}Analyzer"
    mod = types.ModuleType(module_name)

    class _Analyzer:
        def __init__(self, *, llm_client=None, mode="standard"):
            self.client = llm_client
            self.mode = mode

        def run(self, trace):  # noqa: ARG002
            return types.SimpleNamespace(
                findings=[
                    {
                        "severity": severity,
                        "title": f"finding from {slug}",
                        "evidence": "synthetic",
                    }
                ]
            )

    _Analyzer.__name__ = cls_name
    setattr(mod, cls_name, _Analyzer)
    sys.modules[module_name] = mod

    return PatternInfo(
        name=slug,
        module=module_name,
        analyzer=cls_name,
        analyzer_async=None,
        shapes=("individual",),
        module_id=9,
        pattern_id=pattern_id,
        summary="api diagnose test pattern",
    )


@pytest.fixture
def stub_factory():
    """Stub LLM client that's never actually invoked by the synthetic
    analyzers (they emit findings without calling the client), but the
    endpoint requires a resolvable factory."""

    def _make():
        return types.SimpleNamespace()  # any object works

    return _make


@pytest.fixture
def client(stub_factory):
    app = api.build_app(llm_client_factory=stub_factory)
    return TestClient(app)


def _register_synth_patterns(*patterns: PatternInfo):
    """Add synthetic patterns into the diagnose registry. Returns a
    callable that removes them again."""
    from vstack.diagnose import PATTERNS as DIAGNOSE_PATTERNS

    for p in patterns:
        DIAGNOSE_PATTERNS[p.name] = p

    def _cleanup():
        for p in patterns:
            DIAGNOSE_PATTERNS.pop(p.name, None)

    return _cleanup


# --- happy path ------------------------------------------------------


def test_diagnose_returns_ranked_findings(client: TestClient) -> None:
    p_high = _stub_pattern("apidiaghigh", pattern_id=801, severity="high")
    p_low = _stub_pattern("apidiaglow", pattern_id=802, severity="low")
    cleanup = _register_synth_patterns(p_high, p_low)
    try:
        r = client.post(
            "/v1/diagnose",
            json={
                "trace": {"goal": "test goal", "steps": []},
                "patterns": [p_high.name, p_low.name],
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["shape"] == "individual"
        assert len(body["findings"]) == 2
        # High severity ranks first.
        assert body["findings"][0]["severity"] == "high"
        assert body["findings"][1]["severity"] == "low"
        # Per-pattern summary lists both.
        pp_names = {entry["pattern"] for entry in body["per_pattern"]}
        assert pp_names == {p_high.name, p_low.name}
        # Cost envelope is present even when no LLM calls happened.
        assert body["cost"]["llm_calls"] == 0
    finally:
        cleanup()


def test_diagnose_truncates_with_top_param(client: TestClient) -> None:
    p1 = _stub_pattern("apidiagt1", pattern_id=811, severity="critical")
    p2 = _stub_pattern("apidiagt2", pattern_id=812, severity="high")
    p3 = _stub_pattern("apidiagt3", pattern_id=813, severity="medium")
    cleanup = _register_synth_patterns(p1, p2, p3)
    try:
        r = client.post(
            "/v1/diagnose",
            json={
                "trace": {"goal": "test", "steps": []},
                "patterns": [p1.name, p2.name, p3.name],
                "top": 2,
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert len(body["findings"]) == 2
        # Per-pattern still shows all 3 (truncation only applies to
        # the merged findings list).
        assert len(body["per_pattern"]) == 3
    finally:
        cleanup()


# --- validation errors ------------------------------------------------


def test_diagnose_rejects_unknown_recipe(client: TestClient) -> None:
    r = client.post(
        "/v1/diagnose",
        json={"trace": {"goal": "x", "steps": []}, "recipe": "no_such_recipe"},
    )
    assert r.status_code == 400
    body = r.json()
    assert body["detail"]["error"] == "validation_error"
    assert "no_such_recipe" in body["detail"]["message"]


def test_diagnose_rejects_unknown_pattern(client: TestClient) -> None:
    r = client.post(
        "/v1/diagnose",
        json={
            "trace": {"goal": "x", "steps": []},
            "patterns": ["totally_not_a_pattern"],
        },
    )
    assert r.status_code == 400
    body = r.json()
    assert body["detail"]["error"] == "validation_error"


def test_diagnose_rejects_recipe_and_patterns_together(client: TestClient) -> None:
    from vstack.diagnose import RECIPES as DIAGNOSE_RECIPES

    sample_recipe = next(iter(DIAGNOSE_RECIPES))
    r = client.post(
        "/v1/diagnose",
        json={
            "trace": {"goal": "x", "steps": []},
            "recipe": sample_recipe,
            "patterns": ["lencioni"],
        },
    )
    assert r.status_code == 400
    body = r.json()
    assert body["detail"]["error"] == "validation_error"
    assert "mutually exclusive" in body["detail"]["message"]


def test_diagnose_rejects_unknown_shape(client: TestClient) -> None:
    r = client.post(
        "/v1/diagnose",
        json={
            "trace": {"goal": "x", "steps": []},
            "shape": "outer_space",
        },
    )
    assert r.status_code == 400
    body = r.json()
    assert body["detail"]["error"] == "validation_error"


def test_diagnose_rejects_missing_trace(client: TestClient) -> None:
    # FastAPI / Pydantic catches this at the body-parse layer -> 422.
    r = client.post("/v1/diagnose", json={})
    assert r.status_code == 422


# --- openapi documentation ------------------------------------------


def test_diagnose_appears_in_openapi(client: TestClient) -> None:
    r = client.get("/openapi.json")
    assert r.status_code == 200
    spec = r.json()
    assert "/v1/diagnose" in spec["paths"]
    op = spec["paths"]["/v1/diagnose"]["post"]
    # FastAPI-generated operationId; we just confirm presence.
    assert "operationId" in op
    # The response shape is the DiagnoseResponseEnvelope schema.
    response_schema = op["responses"]["200"]["content"]["application/json"]["schema"]
    assert "$ref" in response_schema
    assert "DiagnoseResponseEnvelope" in response_schema["$ref"]
