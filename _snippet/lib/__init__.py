"""vstack.snippet — minimal trace excerpts for findings.

The snippet module extracts the most-relevant slice of a trace for
each finding — useful for embedding in alerts, PR comments, or
issue bodies without dumping the entire trace.

  - `extract_snippet()`: pull N steps around the relevant step(s).
  - `summarize_steps()`: collapse long steps to head/tail with elision.
  - `find_relevant_steps()`: heuristic for which steps a finding
    references (via keyword overlap with the finding's title /
    intervention).
  - `render_snippet()`: format as markdown.

Quick start
-----------

    from vstack.snippet import extract_snippet, render_snippet

    snippet = extract_snippet(
        trace=trace,
        finding=finding,
        context_steps=2,
    )
    print(render_snippet(snippet))
"""

from __future__ import annotations

from ._snippet import (
    Snippet,
    SnippetStep,
    extract_snippet,
    find_relevant_steps,
    render_snippet,
    summarize_steps,
)

__all__ = [
    "Snippet",
    "SnippetStep",
    "extract_snippet",
    "find_relevant_steps",
    "render_snippet",
    "summarize_steps",
]
