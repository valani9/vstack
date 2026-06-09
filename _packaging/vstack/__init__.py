"""vstack: organizational behavior, practiced on AI agents.

A library of 34 diagnostic patterns drawn from organizational behavior,
social psychology, and group dynamics, each one rewritten for the domain
of AI agents rather than human teams. Patterns ship as independent
sub-packages under the ``vstack.*`` namespace and share a common
LLM-client + retry + JSON-parsing core in :mod:`vstack.aar`.

Public API surface (this module)
--------------------------------

Two curated entry points are exposed directly from the top-level
``vstack`` package:

  - :func:`vstack.diagnose` runs a curated bundle of patterns against
    one agent (or multi-agent crew) trace and returns a single ranked
    findings report. The default bundle is task-aware: a single-agent
    trace runs the individual-failure-mode patterns; a multi-agent trace
    runs the team-failure-mode patterns; an org-scale trace runs the
    org-design patterns. You can also pass an explicit bundle.

  - :data:`vstack.PATTERNS` is a registry mapping every shipped pattern
    name to its main analyzer class, its async variant, and the
    sub-package it lives in. Useful for tooling that wants to enumerate
    all patterns without importing each one by hand.

Quick start (curated API)
-------------------------

    from vstack.diagnose import diagnose, PATTERNS
    from vstack.aar import AgentTrace, TraceStep
    from vstack.aar.clients import AnthropicClient

    trace = AgentTrace(
        goal="Refactor the auth module to use JWTs",
        steps=[TraceStep(...)],
        outcome="Created tokens but broke session middleware",
        success=False,
    )

    report = diagnose(trace, llm_client=AnthropicClient())
    print(report.to_markdown())

    # Enumerate every shipped pattern + its main analyzer class:
    for name, info in PATTERNS.items():
        print(name, "->", info.analyzer)

Quick start (single-pattern API)
--------------------------------

Each pattern is still importable directly via its dedicated sub-package
and remains the supported way to use a single pattern in production:

    from vstack.aar import AARAnalyzer
    from vstack.aar.clients import AnthropicClient
    aar = AARAnalyzer(AnthropicClient()).run(trace)

Public API stability
--------------------

Every sub-package exposes its public surface via its own ``__all__``.
Symbols not listed in ``__all__`` are private and may change in any
release. Symbols in ``__all__`` follow this stability promise:

  - ``0.x.y`` releases: breaking changes permitted in ``minor`` bumps
    (``0.0.x`` -> ``0.1.0``). Patch bumps (``0.x.y`` -> ``0.x.(y+1)``)
    are non-breaking.
  - ``1.x.y`` and later: SemVer. Breaking changes only on ``major``.
    Deprecations are warned for one minor release before removal.

See ``PATTERNS.md`` for the full pattern index and per-pattern import paths.
"""

from __future__ import annotations

__version__ = "0.32.0"

# The diagnose() function and PATTERNS registry are lazy-imported below
# so that ``import vstack`` itself stays cheap. Pattern sub-packages
# carry their own LLM-client dependencies and we don't want to pay for
# any of them unless the user actually calls into the diagnostic
# pipeline. The names are exposed via __getattr__ (PEP 562).

__all__ = ["__version__", "diagnose", "PATTERNS"]


def __getattr__(name: str):
    if name == "diagnose":
        from .diagnose import diagnose as _diagnose

        return _diagnose
    if name == "PATTERNS":
        from .diagnose import PATTERNS as _patterns

        return _patterns
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(list(globals().keys()) + list(__all__)))
