"""Snippet extraction + rendering."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


_STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "of",
    "in",
    "to",
    "for",
    "on",
    "with",
    "at",
    "by",
    "from",
    "as",
    "this",
    "that",
    "these",
    "those",
    "it",
    "its",
    "what",
    "which",
    "agent",
    "trace",
    "step",
    "user",
    "system",
}


def _get_steps(trace: Any) -> list[Any]:
    if isinstance(trace, dict):
        return list(trace.get("steps", []))
    if hasattr(trace, "steps"):
        return list(trace.steps)
    return []


def _step_field(step: Any, field: str, default: Any = "") -> Any:
    if isinstance(step, dict):
        return step.get(field, default)
    return getattr(step, field, default)


def _tokenize(text: str) -> set[str]:
    """Lowercase tokenize; drop stopwords + tokens <= 2 chars."""
    if not text:
        return set()
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9_]+", text.lower())
    return {t for t in tokens if len(t) > 2 and t not in _STOPWORDS}


@dataclass
class SnippetStep:
    """One step within a snippet (preserves index for context)."""

    index: int
    type: str
    content: str
    is_relevant: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "type": self.type,
            "content": self.content,
            "is_relevant": self.is_relevant,
        }


@dataclass
class Snippet:
    """Extracted snippet of a trace."""

    finding_title: str
    steps: list[SnippetStep] = field(default_factory=list)
    total_steps_in_trace: int = 0
    omitted_steps_before: int = 0
    omitted_steps_after: int = 0
    relevant_indices: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_title": self.finding_title,
            "steps": [s.to_dict() for s in self.steps],
            "total_steps_in_trace": self.total_steps_in_trace,
            "omitted_steps_before": self.omitted_steps_before,
            "omitted_steps_after": self.omitted_steps_after,
            "relevant_indices": list(self.relevant_indices),
        }


def find_relevant_steps(
    trace: Any,
    finding: dict[str, Any],
    *,
    max_steps: int = 3,
) -> list[int]:
    """Heuristic: token-overlap between finding text and step content.

    Returns up to ``max_steps`` indices sorted by relevance score.
    """
    finding_text = " ".join(str(finding.get(k, "")) for k in ("title", "intervention", "pattern"))
    finding_tokens = _tokenize(finding_text)

    steps = _get_steps(trace)
    if not steps or not finding_tokens:
        return []

    scored = []
    for i, step in enumerate(steps):
        content = str(_step_field(step, "content", ""))
        step_tokens = _tokenize(content)
        overlap = len(finding_tokens & step_tokens)
        if overlap > 0:
            scored.append((i, overlap))

    # Sort by overlap desc, then index asc.
    scored.sort(key=lambda x: (-x[1], x[0]))
    return [i for i, _ in scored[:max_steps]]


def extract_snippet(
    trace: Any,
    finding: dict[str, Any],
    *,
    context_steps: int = 2,
    max_total_steps: int = 10,
) -> Snippet:
    """Extract a snippet centered on the most-relevant steps.

    Args:
        trace: AgentTrace (dict or pydantic).
        finding: a finding dict with at least 'title' and 'intervention'.
        context_steps: how many neighbor steps on each side of relevant steps.
        max_total_steps: cap on total snippet length.
    """
    steps = _get_steps(trace)
    total = len(steps)
    finding_title = str(finding.get("title", "")) or "Finding"

    relevant_indices = find_relevant_steps(trace, finding)

    if not steps:
        return Snippet(finding_title=finding_title, total_steps_in_trace=0)

    if not relevant_indices:
        # Fall back: take first/last steps for context.
        n = min(max_total_steps, total)
        snippet_steps = []
        for i in range(n):
            step = steps[i]
            snippet_steps.append(
                SnippetStep(
                    index=i,
                    type=str(_step_field(step, "type", "")),
                    content=str(_step_field(step, "content", "")),
                    is_relevant=False,
                )
            )
        return Snippet(
            finding_title=finding_title,
            steps=snippet_steps,
            total_steps_in_trace=total,
            omitted_steps_after=max(0, total - n),
        )

    # Expand each relevant index by context_steps.
    keep = set()
    for idx in relevant_indices:
        for offset in range(-context_steps, context_steps + 1):
            j = idx + offset
            if 0 <= j < total:
                keep.add(j)

    # Trim to max_total_steps if needed.
    if len(keep) > max_total_steps:
        # Keep the highest-relevance indices first, then their immediate context.
        keep = set()
        for idx in relevant_indices:
            keep.add(idx)
            if len(keep) >= max_total_steps:
                break
        # Fill remaining budget with neighbors.
        remaining = max_total_steps - len(keep)
        if remaining > 0:
            for idx in relevant_indices:
                for offset in range(1, context_steps + 1):
                    if remaining <= 0:
                        break
                    for j in (idx - offset, idx + offset):
                        if 0 <= j < total and j not in keep:
                            keep.add(j)
                            remaining -= 1
                            if remaining <= 0:
                                break

    sorted_indices = sorted(keep)
    omitted_before = sorted_indices[0] if sorted_indices else 0
    omitted_after = total - 1 - sorted_indices[-1] if sorted_indices else 0

    snippet_steps = []
    for i in sorted_indices:
        step = steps[i]
        snippet_steps.append(
            SnippetStep(
                index=i,
                type=str(_step_field(step, "type", "")),
                content=str(_step_field(step, "content", "")),
                is_relevant=i in set(relevant_indices),
            )
        )

    return Snippet(
        finding_title=finding_title,
        steps=snippet_steps,
        total_steps_in_trace=total,
        omitted_steps_before=omitted_before,
        omitted_steps_after=max(0, omitted_after),
        relevant_indices=list(relevant_indices),
    )


def summarize_steps(content: str, *, head_chars: int = 100, tail_chars: int = 50) -> str:
    """Elide long step content."""
    if len(content) <= head_chars + tail_chars + 5:
        return content
    return f"{content[:head_chars]}…{content[-tail_chars:]}"


def render_snippet(snippet: Snippet) -> str:
    """Render the snippet as markdown."""
    lines = [f"### Snippet: {snippet.finding_title}", ""]
    if snippet.total_steps_in_trace == 0:
        lines.append("_No steps in trace._")
        return "\n".join(lines)

    if snippet.omitted_steps_before > 0:
        lines.append(f"_… {snippet.omitted_steps_before} earlier step(s) omitted_")
        lines.append("")

    for s in snippet.steps:
        marker = "**→**" if s.is_relevant else "   "
        content = summarize_steps(s.content, head_chars=200, tail_chars=80)
        lines.append(f"{marker} `[{s.index}][{s.type}]` {content}")

    if snippet.omitted_steps_after > 0:
        lines.append("")
        lines.append(f"_… {snippet.omitted_steps_after} later step(s) omitted_")

    return "\n".join(lines)
