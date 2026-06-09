"""Trace template registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class TraceTemplate:
    """A registered template for trace generation."""

    name: str
    description: str
    generator: Callable[..., Any]
    default_params: dict[str, Any] = field(default_factory=dict)


_REGISTRY: dict[str, TraceTemplate] = {}


def register_template(template: TraceTemplate) -> None:
    """Register a new trace template (callable can be invoked later)."""
    _REGISTRY[template.name] = template


def get_template(name: str) -> TraceTemplate:
    if name not in _REGISTRY:
        raise KeyError(f"Unknown template: {name}")
    return _REGISTRY[name]


def list_templates() -> list[str]:
    return sorted(_REGISTRY.keys())
