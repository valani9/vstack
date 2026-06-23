"""AWS Strands Agents tool bindings.

Strands turns a Python function into a tool with its ``@tool`` decorator,
reading the function's name, type hints, and docstring (the ``Args:``
section) to build the tool spec. We return one decorated tool per
pattern, each taking the agent ``trace`` (a dict whose fields match the
pattern's input schema) plus an optional ``mode`` and returning the
detection as a dict.

Framework-gated; install with ``pip install 'valanistack[strands]'``::

    from strands import Agent
    from vstack.adapters.strands import as_strands_tools

    agent = Agent(tools=as_strands_tools())
"""

from __future__ import annotations

from typing import Any, Callable

from ._base import (
    PatternToolSpec,
    list_pattern_tool_specs,
    require_module,
    run_pattern_dispatch,
)

__all__ = ["as_strands_tools"]


def as_strands_tools(
    *,
    llm_client_factory: Callable[[], Any] | None = None,
    specs: list[PatternToolSpec] | None = None,
) -> list[Any]:
    """Return one Strands ``@tool``-decorated callable per pattern.

    Raises :class:`~vstack.adapters.AdapterImportError` (via
    ``require_module``) if strands-agents isn't installed.
    """
    strands = require_module("strands", extras_hint="strands")
    tool_decorator = strands.tool
    specs = specs or list_pattern_tool_specs()
    return [tool_decorator(_build_callable(spec, llm_client_factory)) for spec in specs]


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
