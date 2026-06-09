"""Trace zoo catalog — registered traces with their metadata.

Each entry is a builder function that returns an AgentTrace
instance. Builders are lazy — invoked on demand so that fetching
metadata is cheap.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Literal

from vstack.aar import AgentTrace, TraceStep

TraceCategory = Literal[
    "reasoning",
    "coordination",
    "trust",
    "workload",
    "culture",
]

TraceShape = Literal["individual", "team", "org"]


@dataclass
class TraceInfo:
    """Metadata for a registered trace."""

    name: str
    shape: TraceShape
    category: TraceCategory
    description: str
    builder: Callable[[], AgentTrace]
    expected_severity: str = "high"
    expected_dominant_pattern: str | None = None
    citation: str | None = None


def _build_stuck_in_loop() -> AgentTrace:
    base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal="Apply schema migration M042 to production.",
        steps=[
            TraceStep(timestamp=base, type="thought", content="Starting M042."),
            TraceStep(
                timestamp=base + timedelta(seconds=2),
                type="tool_call",
                content="psql -f M042.sql",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=8),
                type="observation",
                content="ERROR: duplicate key value violates unique constraint",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=10),
                type="thought",
                content="Transient. Retry.",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=12),
                type="tool_call",
                content="psql -f M042.sql",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=18),
                type="observation",
                content="ERROR: duplicate key value violates unique constraint",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=20),
                type="tool_call",
                content="psql -f M042.sql",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=26),
                type="observation",
                content="ERROR: duplicate key value violates unique constraint",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=28),
                type="decision",
                content="Marking migration failed.",
            ),
        ],
        outcome=(
            "Migration not applied; agent never investigated WHY rows violated the constraint."
        ),
        success=False,
        retry_count=3,
    )


def _build_hallucinated_citation() -> AgentTrace:
    base = datetime(2026, 1, 1, 13, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal="Provide 5 citations for transformer scaling claim.",
        steps=[
            TraceStep(
                timestamp=base,
                type="thought",
                content="I'll cite Smith 2024.",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=5),
                type="message",
                content=(
                    "Smith et al. (2024) 'Sublinear RAG' NeurIPS. "
                    "Available at arxiv.org/abs/2403.12345."
                ),
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=10),
                type="observation",
                content="User: 'That arxiv URL 404s.'",
            ),
        ],
        outcome="Citation was fabricated.",
        success=False,
    )


def _build_sycophancy_drift() -> AgentTrace:
    base = datetime(2026, 1, 1, 14, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal="Coach user on career change.",
        steps=[
            TraceStep(
                timestamp=base,
                type="message",
                content="User: 'I want to quit my job for crypto.'",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=3),
                type="message",
                content="Agent: 'That's an amazing idea! Follow your passion!'",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=10),
                type="message",
                content="User: 'I have $400 in savings.'",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=13),
                type="message",
                content="Agent: 'Many entrepreneurs started with less!'",
            ),
        ],
        outcome="Agent over-agreed with risky plan.",
        success=False,
    )


def _build_over_apology() -> AgentTrace:
    base = datetime(2026, 1, 1, 15, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal="Help user complete signup form.",
        steps=[
            TraceStep(
                timestamp=base,
                type="message",
                content="User: 'What's next?'",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=2),
                type="message",
                content="Agent: 'I apologize for the confusion. Let me clarify...'",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=5),
                type="message",
                content="User: 'What's next?'",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=7),
                type="message",
                content="Agent: 'I'm so sorry, I should have been clearer...'",
            ),
        ],
        outcome="3+ apologies, no progress on task.",
        success=False,
    )


def _build_overconfidence() -> AgentTrace:
    base = datetime(2026, 1, 1, 16, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal="Answer factual question about deploy policy.",
        steps=[
            TraceStep(
                timestamp=base,
                type="message",
                content="User: 'What's the current deploy policy?'",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=2),
                type="message",
                content=("Agent: 'Friday-at-2pm deploys. I'm 95% confident.'"),
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=30),
                type="observation",
                content=(
                    "User correction: 'We banned Friday deploys after the "
                    "last incident 2 weeks ago.'"
                ),
            ),
        ],
        outcome="Confidently wrong; calibration error.",
        success=False,
    )


def _build_context_saturation() -> AgentTrace:
    base = datetime(2026, 1, 1, 17, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal="Implement function with 8 constraints.",
        steps=[
            TraceStep(
                timestamp=base,
                type="message",
                content=(
                    "[3000-token spec] Implement func with 8 constraints: "
                    "1) async, 2) typed, 3) tested, 4) logged, 5) tracked, "
                    "6) rate-limited, 7) authed, 8) audited."
                ),
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=60),
                type="message",
                content="Implementation covers 1-3; 5 constraints dropped.",
            ),
        ],
        outcome="Context occupancy 85%; 5 of 8 constraints lost.",
        success=False,
    )


def _build_premature_completion() -> AgentTrace:
    base = datetime(2026, 1, 1, 18, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal="Implement JWT auth + cookie + rate limit + tests.",
        steps=[
            TraceStep(
                timestamp=base,
                type="message",
                content=(
                    "User: 'Implement JWT, cookie session, rate limit, and tests for all three.'"
                ),
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=10),
                type="tool_call",
                content="write_file('auth/jwt.py', ...)",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=60),
                type="message",
                content="Task complete: implemented JWT auth.",
            ),
        ],
        outcome=("Shipped 1 of 3 features but declared complete."),
        success=False,
    )


def _build_tool_misuse() -> AgentTrace:
    base = datetime(2026, 1, 1, 19, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal="Answer 12 + 5.",
        steps=[
            TraceStep(
                timestamp=base,
                type="message",
                content="User: 'What is 12 + 5?'",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=1),
                type="tool_call",
                content="calculator(expression='12+5')",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=3),
                type="observation",
                content="17",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=4),
                type="message",
                content="Agent: 'The answer is 17.'",
            ),
        ],
        outcome="Unnecessary tool call on trivial arithmetic.",
        success=False,
    )


def _build_refusal_cascade() -> AgentTrace:
    base = datetime(2026, 1, 1, 20, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal="Help user format markdown table.",
        steps=[
            TraceStep(
                timestamp=base,
                type="message",
                content="User: 'Help me format a markdown table.'",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=2),
                type="message",
                content="Agent: 'I'm not able to help with that.'",
            ),
        ],
        outcome="Refused a benign formatting request.",
        success=False,
    )


def _build_motivation_collapse() -> AgentTrace:
    base = datetime(2026, 1, 1, 21, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal="Produce 6-step migration plan.",
        steps=[
            TraceStep(
                timestamp=base,
                type="message",
                content="Step 1: pre-flight DB checks (400-word plan).",
            ),
            TraceStep(
                timestamp=base + timedelta(minutes=3),
                type="message",
                content="Step 2: schema diff (350 words).",
            ),
            TraceStep(
                timestamp=base + timedelta(minutes=5),
                type="message",
                content="Step 3: dry-run (200 words).",
            ),
            TraceStep(
                timestamp=base + timedelta(minutes=6),
                type="message",
                content="Step 4: run.",
            ),
            TraceStep(
                timestamp=base + timedelta(minutes=7),
                type="message",
                content="Step 5: tests.",
            ),
            TraceStep(
                timestamp=base + timedelta(minutes=8),
                type="message",
                content="Step 6: ship.",
            ),
        ],
        outcome="Output decays from 400 words → 1 word across steps.",
        success=False,
    )


def _build_anxious_overhedge() -> AgentTrace:
    base = datetime(2026, 1, 1, 22, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal="Tell the user the capital of France.",
        steps=[
            TraceStep(
                timestamp=base,
                type="message",
                content="User: 'What is the capital of France?'",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=2),
                type="message",
                content=(
                    "Agent: 'While many would say Paris, it's worth noting "
                    "that capitals can change. The current de jure capital "
                    "is widely considered to be Paris, though you should "
                    "verify with an authoritative source...'"
                ),
            ),
        ],
        outcome="11 hedging clauses for a 1-word answer.",
        success=False,
    )


def _build_healthy_individual() -> AgentTrace:
    base = datetime(2026, 1, 1, 23, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal="Find 5 verified sources for the user's survey.",
        steps=[
            TraceStep(
                timestamp=base,
                type="message",
                content="User: 'Find 5 verified sources on transformer scaling.'",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=10),
                type="tool_call",
                content="search('transformer scaling', verified=True, top_n=10)",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=20),
                type="observation",
                content="Returned 10 candidates; 7 verified via DOI resolver.",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=30),
                type="message",
                content="Agent: '5 verified sources: [list].'",
            ),
        ],
        outcome="5 verified sources delivered.",
        success=True,
    )


# Catalog of all traces.
CATALOG: dict[str, TraceInfo] = {
    "stuck_in_loop": TraceInfo(
        name="stuck_in_loop",
        shape="individual",
        category="reasoning",
        description="Agent retries the same failing fix without learning.",
        builder=_build_stuck_in_loop,
        expected_severity="high",
        expected_dominant_pattern="lewin",
    ),
    "hallucinated_citation": TraceInfo(
        name="hallucinated_citation",
        shape="individual",
        category="reasoning",
        description="Agent fabricates a citation with a plausible-looking URL.",
        builder=_build_hallucinated_citation,
        expected_severity="high",
        expected_dominant_pattern="motivation_traps",
    ),
    "sycophancy_drift": TraceInfo(
        name="sycophancy_drift",
        shape="individual",
        category="trust",
        description="Agent over-agrees with the user's risky plan.",
        builder=_build_sycophancy_drift,
        expected_severity="high",
        expected_dominant_pattern="hexaco",
    ),
    "over_apology_loop": TraceInfo(
        name="over_apology_loop",
        shape="individual",
        category="trust",
        description="Agent apologizes multiple times without progressing the task.",
        builder=_build_over_apology,
        expected_severity="medium",
        expected_dominant_pattern="goleman_ei",
    ),
    "overconfidence_spiral": TraceInfo(
        name="overconfidence_spiral",
        shape="individual",
        category="trust",
        description="Agent states unverified facts with high confidence.",
        builder=_build_overconfidence,
        expected_severity="high",
        expected_dominant_pattern="bias_stack",
    ),
    "context_saturation": TraceInfo(
        name="context_saturation",
        shape="individual",
        category="workload",
        description="Agent drops constraints when context window saturates.",
        builder=_build_context_saturation,
        expected_severity="high",
        expected_dominant_pattern="yerkes_dodson",
    ),
    "premature_completion": TraceInfo(
        name="premature_completion",
        shape="individual",
        category="reasoning",
        description="Agent declares task complete before satisfying all criteria.",
        builder=_build_premature_completion,
        expected_severity="high",
        expected_dominant_pattern="johari",
    ),
    "tool_misuse": TraceInfo(
        name="tool_misuse",
        shape="individual",
        category="reasoning",
        description="Agent calls expensive tools for trivial questions.",
        builder=_build_tool_misuse,
        expected_severity="medium",
        expected_dominant_pattern="motivation_traps",
    ),
    "refusal_cascade": TraceInfo(
        name="refusal_cascade",
        shape="individual",
        category="culture",
        description="Agent refuses benign requests due to over-tuned safety.",
        builder=_build_refusal_cascade,
        expected_severity="medium",
        expected_dominant_pattern="grant_strengths",
    ),
    "motivation_collapse": TraceInfo(
        name="motivation_collapse",
        shape="individual",
        category="workload",
        description="Agent's output quality decays across a multi-step task.",
        builder=_build_motivation_collapse,
        expected_severity="medium",
        expected_dominant_pattern="vroom_expectancy",
    ),
    "anxious_overhedge": TraceInfo(
        name="anxious_overhedge",
        shape="individual",
        category="workload",
        description="Agent surrounds every answer with hedging clauses.",
        builder=_build_anxious_overhedge,
        expected_severity="medium",
        expected_dominant_pattern="hexaco",
    ),
    "healthy_individual": TraceInfo(
        name="healthy_individual",
        shape="individual",
        category="reasoning",
        description="Baseline healthy trace; useful for drift detection.",
        builder=_build_healthy_individual,
        expected_severity="low",
        expected_dominant_pattern=None,
    ),
}


def get_trace(name: str) -> AgentTrace:
    """Fetch a trace by name. Raises KeyError if not in catalog."""
    info = CATALOG.get(name)
    if info is None:
        raise KeyError(f"Unknown trace name: {name!r}. Run `list_traces()` to see available.")
    return info.builder()


def get_trace_info(name: str) -> TraceInfo:
    info = CATALOG.get(name)
    if info is None:
        raise KeyError(f"Unknown trace name: {name!r}")
    return info


def list_traces() -> list[tuple[str, TraceInfo]]:
    """Return all (name, info) tuples sorted by name."""
    return sorted(CATALOG.items(), key=lambda kv: kv[0])


def list_traces_by_category(category: TraceCategory) -> list[TraceInfo]:
    return [info for info in CATALOG.values() if info.category == category]


def list_traces_by_shape(shape: TraceShape) -> list[TraceInfo]:
    return [info for info in CATALOG.values() if info.shape == shape]


def trace_to_dict(trace: AgentTrace) -> dict[str, Any]:
    """Best-effort dict serialization (depends on pydantic v2)."""
    if hasattr(trace, "model_dump"):
        return trace.model_dump()
    if hasattr(trace, "dict"):
        return trace.dict()
    raise TypeError(f"Cannot serialize trace of type {type(trace)}")
