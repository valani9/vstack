"""Hugging Face smolagents tool bindings.

smolagents' ``Tool`` is class-based: each tool declares ``name``,
``description``, ``inputs`` (a dict of typed params), ``output_type``,
and a ``forward`` method. We build one ``Tool`` subclass per pattern.
Each tool takes a single ``trace`` object (the agent trace to analyze,
whose fields match the pattern's input schema) plus an optional
``mode``, and returns the detection as a dict.

No smolagents import is required until you call ``as_smolagents_tools``;
install with ``pip install 'valanistack[smolagents]'``.

::

    from smolagents import CodeAgent, InferenceClientModel
    from vstack.adapters.smolagents import as_smolagents_tools

    agent = CodeAgent(tools=as_smolagents_tools(), model=InferenceClientModel())
"""

from __future__ import annotations

from typing import Any, Callable

from ._base import (
    PatternToolSpec,
    list_pattern_tool_specs,
    require_module,
    run_pattern_dispatch,
)

__all__ = ["as_smolagents_tools"]


def as_smolagents_tools(
    *,
    llm_client_factory: Callable[[], Any] | None = None,
    specs: list[PatternToolSpec] | None = None,
) -> list[Any]:
    """Return one smolagents ``Tool`` instance per pattern.

    Raises :class:`~vstack.adapters.AdapterImportError` (via
    ``require_module``) if smolagents isn't installed.
    """
    smolagents = require_module("smolagents", extras_hint="smolagents")
    tool_base = smolagents.Tool
    specs = specs or list_pattern_tool_specs()
    return [_build_tool(spec, llm_client_factory, tool_base) for spec in specs]


def _build_tool(
    spec: PatternToolSpec,
    llm_client_factory: Callable[[], Any] | None,
    tool_base: type[Any],
) -> Any:
    pattern = spec.pattern

    def forward(self: Any, trace: dict[str, Any], mode: str | None = None) -> dict[str, Any]:
        args = dict(trace or {})
        if mode:
            args["mode"] = mode
        return run_pattern_dispatch(pattern, args, llm_client_factory=llm_client_factory)

    inputs = {
        "trace": {
            "type": "object",
            "description": (
                f"The agent trace to analyze. Its fields match the {spec.friendly} input schema."
            ),
        },
        "mode": {
            "type": "string",
            "description": f"Analysis depth — one of: {', '.join(spec.mode_values)}.",
            "nullable": True,
        },
    }

    cls = type(
        f"Vstack{_camel(spec.pattern_name)}Tool",
        (tool_base,),
        {
            "name": spec.name,
            "description": spec.description,
            "inputs": inputs,
            "output_type": "object",
            "forward": forward,
        },
    )
    return cls()


def _camel(snake: str) -> str:
    return "".join(part.capitalize() for part in snake.split("_"))
