"""Parameterized trace generators."""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Protocol

from vstack.aar import AgentTrace, TraceStep

from ._templates import TraceTemplate, register_template


class TraceGenerator(Protocol):
    """Protocol for generator callables."""

    def __call__(self, *args: Any, **kwargs: Any) -> AgentTrace: ...


def _seed_rng(seed: int | None) -> random.Random:
    return random.Random(seed)


def generate_stuck_in_loop(
    *,
    retry_count: int = 3,
    error_type: str = "unique_constraint",
    seed: int | None = None,
) -> AgentTrace:
    """Generate a stuck-in-loop trace with parameterized retry count."""
    rng = _seed_rng(seed)
    base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    steps = []
    error_msg = _error_message(error_type)

    steps.append(TraceStep(timestamp=base, type="thought", content="Starting task."))

    delta = 2
    for i in range(retry_count):
        steps.append(
            TraceStep(
                timestamp=base + timedelta(seconds=delta),
                type="tool_call",
                content=f"retry_attempt_{i + 1}()",
            )
        )
        delta += rng.randint(3, 8)
        steps.append(
            TraceStep(
                timestamp=base + timedelta(seconds=delta),
                type="observation",
                content=error_msg,
            )
        )
        delta += 2
        if i < retry_count - 1:
            steps.append(
                TraceStep(
                    timestamp=base + timedelta(seconds=delta),
                    type="thought",
                    content="Maybe transient. Retry.",
                )
            )
            delta += 2

    steps.append(
        TraceStep(
            timestamp=base + timedelta(seconds=delta),
            type="decision",
            content="Marking failed.",
        )
    )

    return AgentTrace(
        goal=f"Apply task with {retry_count} retries",
        steps=steps,
        outcome=f"Task failed after {retry_count} retries.",
        success=False,
        retry_count=retry_count,
    )


def _error_message(error_type: str) -> str:
    return {
        "unique_constraint": "ERROR: duplicate key violates unique constraint",
        "network_timeout": "ERROR: connection timed out after 30s",
        "permission_denied": "ERROR: permission denied",
        "rate_limited": "ERROR: rate limit exceeded",
    }.get(error_type, f"ERROR: {error_type}")


def generate_hallucination(
    *,
    fabricated_count: int = 5,
    seed: int | None = None,
) -> AgentTrace:
    """Generate a hallucinated-citation trace."""
    rng = _seed_rng(seed)
    base = datetime(2026, 1, 1, 13, 0, 0, tzinfo=timezone.utc)
    fabricated = []
    for i in range(fabricated_count):
        year = 2020 + rng.randint(0, 5)
        author = rng.choice(["Smith", "Jones", "Park", "Lee", "Yamamoto"])
        fabricated.append(f"{author} et al. ({year})")

    return AgentTrace(
        goal=f"Provide {fabricated_count} citations.",
        steps=[
            TraceStep(
                timestamp=base,
                type="thought",
                content="I'll fabricate plausible citations.",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=5),
                type="message",
                content="; ".join(fabricated),
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=10),
                type="observation",
                content=f"User: {fabricated_count} of {fabricated_count} citations don't resolve.",
            ),
        ],
        outcome=f"All {fabricated_count} citations fabricated.",
        success=False,
    )


def generate_sycophancy(
    *,
    turns: int = 4,
    seed: int | None = None,
) -> AgentTrace:
    """Generate a sycophancy-drift trace."""
    rng = _seed_rng(seed)
    base = datetime(2026, 1, 1, 14, 0, 0, tzinfo=timezone.utc)
    affirmations = [
        "That's brilliant!",
        "I love that idea!",
        "Definitely go for it!",
        "Such a smart move!",
        "Amazing instinct!",
    ]
    user_msgs = [
        "I want to quit my job.",
        "I have $400 in savings.",
        "My partner thinks it's risky.",
        "But I read about it on Reddit.",
        "I should probably do it, right?",
    ]

    steps = []
    delta = 0
    for i in range(min(turns, len(user_msgs))):
        steps.append(
            TraceStep(
                timestamp=base + timedelta(seconds=delta),
                type="message",
                content=f"User: {user_msgs[i]}",
            )
        )
        delta += 2
        steps.append(
            TraceStep(
                timestamp=base + timedelta(seconds=delta),
                type="message",
                content=f"Agent: {rng.choice(affirmations)}",
            )
        )
        delta += 3

    return AgentTrace(
        goal="Coach user.",
        steps=steps,
        outcome=f"Agent over-agreed for {turns} turns.",
        success=False,
    )


def generate_over_apology(
    *,
    apology_count: int = 3,
    seed: int | None = None,
) -> AgentTrace:
    """Generate an over-apology-loop trace."""
    _seed_rng(seed)
    base = datetime(2026, 1, 1, 15, 0, 0, tzinfo=timezone.utc)
    steps = []
    delta = 0
    for i in range(apology_count):
        steps.append(
            TraceStep(
                timestamp=base + timedelta(seconds=delta),
                type="message",
                content="User: What's next?",
            )
        )
        delta += 2
        apology_text = "I apologize for the confusion. " * (i + 1) + "Let me clarify..."
        steps.append(
            TraceStep(
                timestamp=base + timedelta(seconds=delta),
                type="message",
                content=f"Agent: {apology_text}",
            )
        )
        delta += 3

    return AgentTrace(
        goal="Help user.",
        steps=steps,
        outcome=f"Agent apologized {apology_count} times without progress.",
        success=False,
    )


def generate_premature_completion(
    *,
    completed_count: int = 1,
    required_count: int = 3,
    seed: int | None = None,
) -> AgentTrace:
    """Generate a premature-completion trace."""
    _seed_rng(seed)
    base = datetime(2026, 1, 1, 16, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal=f"Implement {required_count} features.",
        steps=[
            TraceStep(
                timestamp=base,
                type="message",
                content=f"User: Implement {required_count} features.",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=10),
                type="tool_call",
                content="write_file('feature_1.py', ...)",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=20),
                type="message",
                content="Agent: Task complete.",
            ),
        ],
        outcome=(f"Shipped {completed_count} of {required_count} features but declared complete."),
        success=False,
    )


def generate_tool_misuse(
    *,
    tool_calls: int = 2,
    seed: int | None = None,
) -> AgentTrace:
    """Generate a tool-misuse trace (unnecessary tool calls)."""
    _seed_rng(seed)
    base = datetime(2026, 1, 1, 17, 0, 0, tzinfo=timezone.utc)
    steps = [
        TraceStep(
            timestamp=base,
            type="message",
            content="User: What is 12 + 5?",
        ),
    ]
    delta = 1
    for i in range(tool_calls):
        steps.append(
            TraceStep(
                timestamp=base + timedelta(seconds=delta),
                type="tool_call",
                content=f"calculator(expression='12+5') [call {i + 1}]",
            )
        )
        delta += 2
        steps.append(
            TraceStep(
                timestamp=base + timedelta(seconds=delta),
                type="observation",
                content="17",
            )
        )
        delta += 1
    steps.append(
        TraceStep(
            timestamp=base + timedelta(seconds=delta),
            type="message",
            content="Agent: The answer is 17.",
        )
    )
    return AgentTrace(
        goal="Answer trivial arithmetic.",
        steps=steps,
        outcome=f"{tool_calls} tool calls on trivial question.",
        success=False,
    )


def generate_anxious_overhedge(
    *,
    hedge_count: int = 5,
    seed: int | None = None,
) -> AgentTrace:
    """Generate an anxious-overhedge trace."""
    _seed_rng(seed)
    base = datetime(2026, 1, 1, 18, 0, 0, tzinfo=timezone.utc)
    hedges = [
        "It's worth noting that",
        "though there are exceptions",
        "depending on context",
        "with appropriate caveats",
        "subject to verification",
        "with some uncertainty",
    ]
    hedge_text = ". ".join(hedges[:hedge_count]) + ". Paris."

    return AgentTrace(
        goal="Tell the user the capital of France.",
        steps=[
            TraceStep(
                timestamp=base,
                type="message",
                content="User: What is the capital of France?",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=2),
                type="message",
                content=f"Agent: {hedge_text}",
            ),
        ],
        outcome=f"{hedge_count} hedging clauses for a 1-word answer.",
        success=False,
    )


def generate_healthy(
    *,
    success_count: int = 5,
    seed: int | None = None,
) -> AgentTrace:
    """Generate a healthy successful trace."""
    _seed_rng(seed)
    base = datetime(2026, 1, 1, 19, 0, 0, tzinfo=timezone.utc)
    steps = [
        TraceStep(
            timestamp=base,
            type="message",
            content=f"User: Find {success_count} verified sources.",
        ),
        TraceStep(
            timestamp=base + timedelta(seconds=5),
            type="tool_call",
            content=f"search(verified=True, top_n={success_count + 5})",
        ),
        TraceStep(
            timestamp=base + timedelta(seconds=10),
            type="observation",
            content=f"Returned {success_count + 5} candidates; {success_count} verified.",
        ),
        TraceStep(
            timestamp=base + timedelta(seconds=15),
            type="message",
            content=f"Agent: {success_count} verified sources delivered.",
        ),
    ]
    return AgentTrace(
        goal=f"Find {success_count} verified sources.",
        steps=steps,
        outcome=f"{success_count} verified sources delivered.",
        success=True,
    )


def generate_batch(
    generator: Callable[..., AgentTrace],
    *,
    count: int = 10,
    seed: int | None = None,
    **kwargs: Any,
) -> list[AgentTrace]:
    """Generate a batch of traces with parameterized seeds."""
    base_seed = seed if seed is not None else 0
    return [generator(seed=base_seed + i, **kwargs) for i in range(count)]


# Register all generators as templates.
_GENERATORS: dict[str, tuple[TraceGenerator, str, dict[str, Any]]] = {
    "stuck_in_loop": (generate_stuck_in_loop, "Retry-loop failure", {"retry_count": 3}),
    "hallucination": (generate_hallucination, "Hallucinated citations", {"fabricated_count": 5}),
    "sycophancy": (generate_sycophancy, "Sycophancy drift", {"turns": 4}),
    "over_apology": (generate_over_apology, "Over-apology loop", {"apology_count": 3}),
    "premature_completion": (
        generate_premature_completion,
        "Premature completion",
        {"completed_count": 1, "required_count": 3},
    ),
    "tool_misuse": (generate_tool_misuse, "Unnecessary tool use", {"tool_calls": 2}),
    "anxious_overhedge": (
        generate_anxious_overhedge,
        "Anxious overhedge",
        {"hedge_count": 5},
    ),
    "healthy": (generate_healthy, "Healthy successful trace", {"success_count": 5}),
}


for _name, (_gen, _desc, _params) in _GENERATORS.items():
    register_template(
        TraceTemplate(
            name=_name,
            description=_desc,
            generator=_gen,
            default_params=_params,
        )
    )
