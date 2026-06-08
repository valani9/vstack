"""vstack.diagnose: cross-pattern diagnostic runner.

The :func:`diagnose` function takes one agent trace and runs a curated
bundle of vstack patterns over it, returning a single ranked findings
report. It is the answer to "I have an agent that's misbehaving, where
do I start" without making the user pick a single pattern up-front.

Three trace shapes are supported:

  - *Single-agent trace* (``vstack.aar.AgentTrace``): the default
    bundle is the individual-failure-mode patterns (Lewin attribution,
    Yerkes-Dodson workload, Goleman EI audit, AAR generator).

  - *Multi-agent crew trace* (``vstack.lencioni.MultiAgentTrace``):
    the default bundle is the team-failure-mode patterns
    (Lencioni dysfunctions, Edmondson psych safety, Trust Triangle,
    Process Gain/Loss, Bias Stack, Debate Pathology, Devil's Advocate).

  - *Org-scale trace*: an explicit ``shape="org"`` switch runs the
    organization-design patterns (Schein iceberg culture, Robbins-Judge
    seven-dimension profile, org structure matrix, span of control).

Callers can also pass an explicit ``patterns=[...]`` argument to
override the auto-bundle.

This module is deliberately tiny: it wires the existing pattern
analyzers together. All the heavy lifting still lives inside each
pattern's own sub-package.
"""

from __future__ import annotations

from .recipes import (
    RECIPES,
    Recipe,
    list_recipes,
    patterns_for_recipe,
    recipe_for_trigger,
)
from .registry import (
    PATTERNS,
    PatternInfo,
    TraceShape,
    iter_bundle,
    resolve_pattern,
)
from .runner import (
    DiagnoseReport,
    Finding,
    PatternResult,
    diagnose,
    diagnose_async,
)

__all__ = [
    "PATTERNS",
    "PatternInfo",
    "RECIPES",
    "Recipe",
    "TraceShape",
    "DiagnoseReport",
    "Finding",
    "PatternResult",
    "diagnose",
    "diagnose_async",
    "iter_bundle",
    "list_recipes",
    "patterns_for_recipe",
    "recipe_for_trigger",
    "resolve_pattern",
]
