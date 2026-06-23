"""Agno tool bindings.

Agno accepts plain Python functions as tools — it reads each function's
name, type hints, and docstring to build the tool schema. We return one
callable per pattern, each taking the agent ``trace`` (a dict whose
fields match the pattern's input schema) plus an optional ``mode`` and
returning the detection as a dict.

No Agno import is required to USE these callables (they're pure Python),
so this adapter has no install gate — pass them straight to ``Agent``::

    from agno.agent import Agent
    from vstack.adapters.agno import as_agno_tools

    agent = Agent(model=..., tools=as_agno_tools())
"""

from __future__ import annotations

from typing import Any, Callable

from ._base import (
    PatternToolSpec,
    list_pattern_tool_specs,
    run_pattern_dispatch,
)

__all__ = ["as_agno_tools"]


def as_agno_tools(
    *,
    llm_client_factory: Callable[[], Any] | None = None,
    specs: list[PatternToolSpec] | None = None,
) -> list[Callable[..., dict[str, Any]]]:
    """Return ``[callable, ...]`` — one Agno tool function per pattern.

    Each callable's ``__name__`` is the tool name (``vstack_<pattern>``)
    and its ``__doc__`` carries the description + an ``Args:`` section so
    Agno introspects it correctly.
    """
    specs = specs or list_pattern_tool_specs()
    return [_build_callable(spec, llm_client_factory) for spec in specs]


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
        f"    The {spec.friendly} detection as a dict."
    )
    return tool
