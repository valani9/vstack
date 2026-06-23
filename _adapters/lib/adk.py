"""Google Agent Development Kit (ADK) tool bindings.

ADK wraps a Python function as a tool via ``FunctionTool(func=...)``; it
reads the function's name, type hints, and docstring to build the schema.
We return one ``FunctionTool`` per pattern, each taking the agent
``trace`` (a dict whose fields match the pattern's input schema) plus an
optional ``mode`` and returning the detection as a dict.

Framework-gated; install with ``pip install 'valanistack[adk]'``::

    from google.adk.agents import Agent
    from vstack.adapters.adk import as_adk_tools

    agent = Agent(name="diagnostician", model="gemini-2.0-flash",
                  tools=as_adk_tools())
"""

from __future__ import annotations

from typing import Any, Callable

from ._base import (
    PatternToolSpec,
    list_pattern_tool_specs,
    require_module,
    run_pattern_dispatch,
)

__all__ = ["as_adk_tools"]


def as_adk_tools(
    *,
    llm_client_factory: Callable[[], Any] | None = None,
    specs: list[PatternToolSpec] | None = None,
) -> list[Any]:
    """Return one ADK ``FunctionTool`` per pattern.

    Raises :class:`~vstack.adapters.AdapterImportError` (via
    ``require_module``) if google-adk isn't installed.
    """
    function_tool_mod = require_module("google.adk.tools.function_tool", extras_hint="adk")
    function_tool = function_tool_mod.FunctionTool
    specs = specs or list_pattern_tool_specs()
    return [function_tool(func=_build_callable(spec, llm_client_factory)) for spec in specs]


def _build_callable(
    spec: PatternToolSpec,
    llm_client_factory: Callable[[], Any] | None,
) -> Callable[..., dict[str, Any]]:
    pattern = spec.pattern

    def tool(trace: dict[str, Any], mode: str = "standard") -> dict[str, Any]:
        args = dict(trace or {})
        if mode:
            args["mode"] = mode
        return run_pattern_dispatch(pattern, args, llm_client_factory=llm_client_factory)

    tool.__name__ = spec.name
    tool.__qualname__ = spec.name
    tool.__doc__ = (
        f"{spec.description}\n\n"
        f"Args:\n"
        f"    trace: The agent trace to analyze (fields match the "
        f"{spec.friendly} input schema).\n"
        f"    mode: Analysis depth ({', '.join(spec.mode_values)}). "
        f"Defaults to 'standard'.\n\n"
        f"Returns:\n"
        f"    dict: The {spec.friendly} detection."
    )
    return tool
