"""Tests for the cross-pattern ``vstack_diagnose`` MCP tool.

These exercise the tool's input schema, validation guards, and the
end-to-end dispatch path. The patterns themselves are mocked via
sys.modules registration so the test does not require an LLM
client and so each pattern's analyzer is deterministic.

Behaviors under test:

  1. list_tools includes ``vstack_diagnose`` alongside the 34
     per-pattern tools.
  2. The diagnose tool's input schema declares the expected
     parameters (trace, shape, recipe, patterns, mode, model, cache,
     top), with ``trace`` required.
  3. Dispatching with a synthetic trace + explicit patterns list runs
     the runner and surfaces the report JSON.
  4. Invalid recipe / unknown pattern / both-recipe-and-patterns
     yield structured validation errors.
"""

from __future__ import annotations

import asyncio
import json
import sys
import types
from typing import Any

import pytest
from mcp.types import CallToolRequest, CallToolRequestParams, ListToolsRequest

from vstack.diagnose.registry import PatternInfo
from vstack.mcp._server import (
    DIAGNOSE_TOOL_NAME,
    _build_diagnose_tool,
    _dispatch_diagnose_call,
    build_server,
)


# --- helpers ---------------------------------------------------------


def _run(coro):
    return asyncio.run(coro)


def _invoke_handler(server, request_cls, params=None):
    handler = server.request_handlers[request_cls]
    method_default = request_cls.model_fields["method"].default
    if params is None:
        request = request_cls.model_construct(method=method_default, params=None)
    else:
        request = request_cls(method=method_default, params=params)
    return _run(handler(request))


def _stub_pattern(slug: str, pattern_id: int, severity: str = "high") -> PatternInfo:
    """Register a synthetic vstack pattern that always emits one
    finding at the requested severity. Returns the PatternInfo for
    passing into the diagnose call."""
    module_name = f"_test_mcp_diagnose_synth.{slug}"
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
        summary="diagnose mcp test pattern",
    )


# --- schema + listing ------------------------------------------------


@pytest.fixture
def server():
    return build_server()


def test_list_tools_includes_diagnose(server) -> None:
    result = _invoke_handler(server, ListToolsRequest)
    names = {t.name for t in result.root.tools}
    assert DIAGNOSE_TOOL_NAME in names


def test_diagnose_tool_schema_has_expected_fields() -> None:
    tool = _build_diagnose_tool()
    schema = tool.inputSchema
    assert schema["type"] == "object"
    props = schema["properties"]
    assert set(["trace", "shape", "recipe", "patterns", "mode", "model", "cache", "top"]).issubset(
        props.keys()
    )
    # Trace is required; the rest are optional.
    assert schema["required"] == ["trace"]
    # Mode enum mirrors the runner's mode literal set.
    assert set(props["mode"]["enum"]) == {"quick", "standard", "forensic"}
    # Shape enum covers all three trace shapes.
    assert set(props["shape"]["enum"]) == {"individual", "team", "org"}
    # Pattern enum is populated and includes a known pattern.
    assert "lencioni" in props["patterns"]["items"]["enum"]
    # Recipe enum is populated.
    assert len(props["recipe"]["enum"]) >= 1


# --- dispatch --------------------------------------------------------


def test_dispatch_runs_synthetic_pattern() -> None:
    """An end-to-end call with two synthetic patterns produces a
    DiagnoseReport JSON with both findings ranked."""
    p1 = _stub_pattern("synthhigh", pattern_id=901, severity="high")
    p2 = _stub_pattern("synthlow", pattern_id=902, severity="low")

    # The patterns list must contain pattern slugs from the diagnose
    # registry; we pass PatternInfo instances directly through the
    # runner's `patterns=[PatternInfo(...)]` API by going through the
    # MCP arg path. Since MCP only accepts strings, we'll route via
    # the registered PATTERNS dict for this test. The simpler path is
    # to call _dispatch_diagnose_call without strict pattern enums.
    #
    # We monkey-patch the diagnose enum check by passing PatternInfo
    # via the runner directly. But the MCP layer enforces that
    # `patterns` is a list of strings. So instead, register the
    # synthetic patterns into the diagnose PATTERNS dict for the
    # duration of the test.

    from vstack.diagnose import PATTERNS as DIAGNOSE_PATTERNS

    try:
        DIAGNOSE_PATTERNS[p1.name] = p1
        DIAGNOSE_PATTERNS[p2.name] = p2

        # Patch resolve_llm_client to skip the real-client requirement
        # since synthetic analyzers do not actually need an LLM.
        from vstack.mcp import _server as mcp_server

        class _DummyClient:
            pass

        original = mcp_server.resolve_llm_client
        mcp_server.resolve_llm_client = lambda: _DummyClient()
        try:
            response = _dispatch_diagnose_call(
                {
                    "trace": {"goal": "test goal", "steps": []},
                    "patterns": [p1.name, p2.name],
                }
            )
        finally:
            mcp_server.resolve_llm_client = original
    finally:
        DIAGNOSE_PATTERNS.pop(p1.name, None)
        DIAGNOSE_PATTERNS.pop(p2.name, None)

    assert len(response) == 1
    body = json.loads(response[0].text)
    assert body["shape"] == "individual"
    assert len(body["findings"]) == 2
    # High severity ranks first per the runner's merge-and-rank sort.
    assert body["findings"][0]["severity"] == "high"
    assert body["findings"][1]["severity"] == "low"
    # Per-pattern summary lists both patterns + their elapsed time.
    pp_names = {entry["pattern"] for entry in body["per_pattern"]}
    assert pp_names == {p1.name, p2.name}


# --- validation errors ------------------------------------------------


def test_dispatch_rejects_missing_trace() -> None:
    response = _dispatch_diagnose_call({})
    body = json.loads(response[0].text)
    assert body.get("error") == "validation_error"


def test_dispatch_rejects_unknown_recipe() -> None:
    response = _dispatch_diagnose_call(
        {"trace": {"goal": "x", "steps": []}, "recipe": "no_such_recipe"}
    )
    body = json.loads(response[0].text)
    assert body.get("error") == "validation_error"
    assert "no_such_recipe" in body.get("message", "")


def test_dispatch_rejects_unknown_pattern_in_list() -> None:
    response = _dispatch_diagnose_call(
        {
            "trace": {"goal": "x", "steps": []},
            "patterns": ["totally_not_a_pattern"],
        }
    )
    body = json.loads(response[0].text)
    assert body.get("error") == "validation_error"


def test_dispatch_rejects_recipe_and_patterns_together() -> None:
    from vstack.diagnose import RECIPES as DIAGNOSE_RECIPES

    sample_recipe = next(iter(DIAGNOSE_RECIPES))
    response = _dispatch_diagnose_call(
        {
            "trace": {"goal": "x", "steps": []},
            "recipe": sample_recipe,
            "patterns": ["lencioni"],
        }
    )
    body = json.loads(response[0].text)
    assert body.get("error") == "validation_error"
    assert "mutually exclusive" in body.get("message", "")
