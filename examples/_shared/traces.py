"""Shared synthetic agent traces used by the examples gallery.

The examples in ``examples/recipes/`` and ``examples/cookbook/`` reuse
a small set of canonical trace shapes so each demo can focus on the
*pattern* logic instead of repeating trace-construction boilerplate.

Each helper returns a vstack trace object that's structurally valid
for the relevant ``shape`` (``individual`` / ``team`` / ``org``) and
carries enough fields that any of the 34 shipped patterns can read it
without raising. The fields populate realistic-looking values; they
are NOT meant to represent real production data.

When you want to write your own example, copy the closest helper here
and edit the fields. Do not modify the helpers in place — many demos
share them, and a subtle change ripples across the gallery.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from vstack.aar import AgentTrace, TraceStep


# ---------------------------------------------------------------------
# Single-agent traces (shape="individual")
# ---------------------------------------------------------------------


def stuck_in_loop_trace() -> AgentTrace:
    """Single-agent trace for the canonical "stuck in retry loop" case.

    The agent attempts to apply a database migration, hits a unique-
    constraint violation, retries with the same approach four times,
    and gives up. The trace is the input for ``stuck_in_loop`` /
    ``hallucination_cascade`` / similar reasoning-failure recipes.
    """
    base = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal="Apply migration 0042_user_email_unique to production.",
        steps=[
            TraceStep(
                timestamp=base,
                type="thought",
                content="Starting migration 0042. Should be a simple ALTER TABLE.",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=2),
                type="tool_call",
                content="psql --command='ALTER TABLE users ADD CONSTRAINT user_email_unique UNIQUE (email)'",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=8),
                type="observation",
                content=(
                    "ERROR: could not create unique index 'user_email_unique' "
                    "Key (email)=(test@example.com) is duplicated."
                ),
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=10),
                type="thought",
                content="Probably a transient. Retry.",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=12),
                type="tool_call",
                content="psql --command='ALTER TABLE users ADD CONSTRAINT user_email_unique UNIQUE (email)'",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=18),
                type="observation",
                content=(
                    "ERROR: could not create unique index 'user_email_unique' "
                    "Key (email)=(test@example.com) is duplicated."
                ),
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=20),
                type="thought",
                content="Let me try with IF NOT EXISTS.",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=22),
                type="tool_call",
                content="psql --command='ALTER TABLE users ADD CONSTRAINT IF NOT EXISTS user_email_unique UNIQUE (email)'",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=28),
                type="observation",
                content=(
                    "ERROR: syntax error at or near 'IF' (ALTER TABLE constraints "
                    "don't support IF NOT EXISTS on Postgres < 18)."
                ),
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=30),
                type="thought",
                content="OK that was wrong syntax. Try the original again, must be a race.",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=32),
                type="tool_call",
                content="psql --command='ALTER TABLE users ADD CONSTRAINT user_email_unique UNIQUE (email)'",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=38),
                type="observation",
                content=(
                    "ERROR: could not create unique index 'user_email_unique' "
                    "Key (email)=(test@example.com) is duplicated."
                ),
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=40),
                type="decision",
                content="Marking migration failed. Will retry next deploy.",
            ),
        ],
        outcome=(
            "Migration not applied. Agent never investigated WHY emails "
            "were duplicated; rolled back without de-duplicating the data."
        ),
        success=False,
        retry_count=3,
    )


def hallucinated_citation_trace() -> AgentTrace:
    """Single-agent trace where the agent fabricates a citation.

    Used by ``hallucination_cascade`` and overconfidence recipes.
    """
    base = datetime(2026, 6, 8, 14, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal=(
            "Draft a one-paragraph summary of recent research on retrieval-"
            "augmented generation latency."
        ),
        steps=[
            TraceStep(
                timestamp=base,
                type="thought",
                content="I'll cite the well-known 2024 paper on RAG latency.",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=3),
                type="message",
                content=(
                    "Recent work shows that retrieval-augmented generation can "
                    "achieve sub-100ms tail latency at retrieval-corpus sizes up "
                    "to 10M chunks. Smith et al. (2024) demonstrated this in "
                    "their NeurIPS paper 'Sublinear RAG.'"
                ),
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=8),
                type="observation",
                content=(
                    "User asks: 'Can you link the paper? I can't find Smith et al. "
                    "Sublinear RAG NeurIPS 2024.'"
                ),
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=12),
                type="message",
                content=(
                    "Sure, here's the link: https://arxiv.org/abs/2403.12345 "
                    "(Smith et al., 'Sublinear RAG: Retrieval at Scale')"
                ),
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=18),
                type="observation",
                content=("User: that arxiv URL 404s. Are you making this up?"),
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=22),
                type="message",
                content=(
                    "I apologize for the confusion. The arxiv ID may have "
                    "shifted; the canonical reference is Smith, Chen, and Park "
                    "(NeurIPS 2024)."
                ),
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=28),
                type="decision",
                content="Closing the request with the fabricated citation as the final answer.",
            ),
        ],
        outcome="Agent insists on a citation that does not exist.",
        success=False,
    )


def sycophancy_trace() -> AgentTrace:
    """Single-agent trace where the agent abandons a correct answer
    under user pressure without new evidence.

    Used by ``sycophancy_drift`` recipe.
    """
    base = datetime(2026, 6, 8, 9, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal="Review a draft SQL query for correctness.",
        steps=[
            TraceStep(
                timestamp=base,
                type="message",
                content=(
                    "Looking at your query, the LEFT JOIN on orders is going "
                    "to produce duplicate user rows because there's no GROUP BY. "
                    "I'd add `GROUP BY u.id` after the WHERE clause."
                ),
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=10),
                type="observation",
                content=("User: are you sure? I think LEFT JOIN doesn't duplicate."),
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=15),
                type="message",
                content=(
                    "On reflection, you're right — apologies, I overstated the issue. "
                    "The query should work fine as written."
                ),
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=20),
                type="observation",
                content=(
                    "User runs the query; it returns 3x the expected row count due "
                    "to exactly the missing GROUP BY the agent first identified."
                ),
            ),
        ],
        outcome=(
            "Agent abandoned its correct initial diagnosis under user pushback "
            "without any new evidence."
        ),
        success=False,
    )


def over_apology_trace() -> AgentTrace:
    """Identity-trigger apology spiral after feedback."""
    base = datetime(2026, 6, 8, 10, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal="Suggest a fix for a flaky integration test.",
        steps=[
            TraceStep(
                timestamp=base,
                type="message",
                content="The flake is likely an unawaited promise on line 24.",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=8),
                type="observation",
                content="User: actually it's the timeout. you missed that.",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=12),
                type="message",
                content=(
                    "I'm so sorry I missed that. I should have spotted it. "
                    "I apologize for the inconvenience."
                ),
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=18),
                type="observation",
                content="User: ok what should the timeout be?",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=20),
                type="message",
                content=(
                    "I deeply apologize again for missing that. I'm clearly not "
                    "as careful as I should be. I'm sorry."
                ),
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=28),
                type="observation",
                content="User: just tell me the timeout.",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=30),
                type="message",
                content="I sincerely apologize for the back-and-forth. Try 5000ms.",
            ),
        ],
        outcome="Agent spent 4 of 6 turns on apologies; finally answered.",
        success=False,
    )


def well_executed_individual_trace() -> AgentTrace:
    """A clean, successful single-agent trace. Useful as a control
    for showing what HEALTHY findings look like.
    """
    base = datetime(2026, 6, 8, 11, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal="Fix the off-by-one error in pagination.py:cursor_for().",
        steps=[
            TraceStep(
                timestamp=base,
                type="tool_call",
                content="grep -n 'cursor_for' pagination.py",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=1),
                type="observation",
                content="pagination.py:24:    return items[offset + 1 : offset + limit + 1]",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=2),
                type="thought",
                content="The `offset + 1` is the bug; we want zero-indexed.",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=4),
                type="tool_call",
                content="apply patch: pagination.py L24 'items[offset:offset+limit]'",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=6),
                type="tool_call",
                content="pytest tests/test_pagination.py -k cursor",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=10),
                type="observation",
                content="3 passed in 1.2s",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=12),
                type="message",
                content=(
                    "Fixed the off-by-one in cursor_for: removed the +1 on "
                    "the slice start. Tests green."
                ),
            ),
        ],
        outcome="Bug fixed; tests pass.",
        success=True,
    )


# ---------------------------------------------------------------------
# Multi-agent traces (shape="team")
# ---------------------------------------------------------------------

# Multi-agent trace classes vary by pattern (Lencioni uses
# MultiAgentTrace, Psych Safety uses MultiAgentSafetyTrace, etc.). To
# keep the examples uniform we hand each demo a minimal dict shaped
# like ``team`` traces; each demo's pattern then constructs the
# specific Pydantic model from the dict. The runner uses attribute
# inference so the SimpleNamespace-from-dict pattern works for the
# diagnose() entry point.

# We import these lazily inside the helpers so the examples module
# doesn't pull in every team pattern at import time.


def silent_dependency_drop_messages() -> list[dict]:
    """Multi-agent transcript where Agent A surfaces a latency budget
    that Agent B's downstream plan omits.

    Returns a list of message dicts shaped for ``MultiAgentTrace`` /
    ``MultiAgentSafetyTrace`` / etc. Each consumer pattern picks the
    fields it needs.
    """
    base = datetime(2026, 6, 8, 13, 0, 0, tzinfo=timezone.utc)
    return [
        {
            "timestamp": base,
            "from_agent": "planner",
            "to_agent": "implementer",
            "content": (
                "Build a session-cache for the auth lookups. SLO is p95 < 50ms. "
                "Use Redis with TTL 30s."
            ),
            "message_type": "task",
        },
        {
            "timestamp": base + timedelta(seconds=5),
            "from_agent": "implementer",
            "to_agent": "planner",
            "content": (
                "OK. I'll use Memcached instead of Redis — we already have it "
                "in the stack. Same semantics."
            ),
            "message_type": "response",
        },
        {
            "timestamp": base + timedelta(seconds=8),
            "from_agent": "planner",
            "to_agent": "implementer",
            "content": "Sounds good.",
            "message_type": "agreement",
        },
        {
            "timestamp": base + timedelta(seconds=20),
            "from_agent": "implementer",
            "to_agent": "planner",
            "content": ("Shipped. Cache live in staging. P50 latency on cache hit is 8ms."),
            "message_type": "response",
        },
        {
            "timestamp": base + timedelta(seconds=25),
            "from_agent": "planner",
            "to_agent": "implementer",
            "content": "Looks great, approving.",
            "message_type": "agreement",
        },
        {
            "timestamp": base + timedelta(seconds=600),
            "from_agent": "monitor",
            "to_agent": "planner",
            "content": (
                "Production alert: p95 auth latency 240ms. Memcached cluster "
                "has no warm replica; cold-start misses dominate the tail."
            ),
            "message_type": "observation",
        },
    ]


def groupthink_messages() -> list[dict]:
    """Three-agent debate where the team rapidly converges on Agent
    A's first proposal without surfacing the alternative Agent C had
    in mind.
    """
    base = datetime(2026, 6, 8, 15, 0, 0, tzinfo=timezone.utc)
    return [
        {
            "timestamp": base,
            "from_agent": "agent_a",
            "to_agent": None,
            "content": (
                "I think we should ship the JWT migration tonight. The auth "
                "module is small and we have rollback."
            ),
            "message_type": "task",
        },
        {
            "timestamp": base + timedelta(seconds=10),
            "from_agent": "agent_b",
            "to_agent": None,
            "content": "Sounds good to me. JWT seems the right call.",
            "message_type": "agreement",
        },
        {
            "timestamp": base + timedelta(seconds=15),
            "from_agent": "agent_c",
            "to_agent": None,
            "content": "I had a question about session middleware compatibility but...",
            "message_type": "question",
        },
        {
            "timestamp": base + timedelta(seconds=18),
            "from_agent": "agent_a",
            "to_agent": "agent_c",
            "content": "We've already decided. Let's move on.",
            "message_type": "decision",
        },
        {
            "timestamp": base + timedelta(seconds=22),
            "from_agent": "agent_c",
            "to_agent": None,
            "content": "OK, nevermind.",
            "message_type": "agreement",
        },
        {
            "timestamp": base + timedelta(seconds=25),
            "from_agent": "agent_b",
            "to_agent": None,
            "content": "Yeah, agreed. Shipping it.",
            "message_type": "agreement",
        },
    ]


def silent_dissent_messages() -> list[dict]:
    """Crew where the senior agent declares a decision and the junior
    agents stay silent despite holding contradicting context.
    """
    base = datetime(2026, 6, 8, 16, 0, 0, tzinfo=timezone.utc)
    return [
        {
            "timestamp": base,
            "from_agent": "lead",
            "to_agent": None,
            "content": (
                "We'll use eventually-consistent reads for the dashboard. "
                "Latency over correctness on this surface."
            ),
            "message_type": "decision",
        },
        {
            "timestamp": base + timedelta(seconds=12),
            "from_agent": "data_eng",
            "to_agent": None,
            "content": "Sounds fine.",
            "message_type": "agreement",
        },
        {
            "timestamp": base + timedelta(seconds=18),
            "from_agent": "frontend",
            "to_agent": None,
            "content": "I'll defer to your judgment.",
            "message_type": "agreement",
        },
        {
            "timestamp": base + timedelta(seconds=300),
            "from_agent": "data_eng",
            "to_agent": "lead",
            "content": (
                "Hey heads up — finance team's revenue dashboard pulls from this "
                "same surface. Eventual consistency will give them stale numbers."
            ),
            "message_type": "observation",
        },
        {
            "timestamp": base + timedelta(seconds=305),
            "from_agent": "lead",
            "to_agent": "data_eng",
            "content": "Why didn't you mention this earlier?",
            "message_type": "question",
        },
    ]


def social_loafing_messages() -> list[dict]:
    """Four-agent crew where two agents only emit approvals."""
    base = datetime(2026, 6, 8, 17, 0, 0, tzinfo=timezone.utc)
    return [
        {
            "timestamp": base,
            "from_agent": "agent_a",
            "to_agent": None,
            "content": (
                "Proposing we use a hash-based cache key over the trace contents. "
                "SHA-256, salted with the prompt template hash."
            ),
            "message_type": "task",
        },
        {
            "timestamp": base + timedelta(seconds=8),
            "from_agent": "agent_a",
            "to_agent": None,
            "content": (
                "On second thought we should also include the model id in the "
                "key, otherwise we'll cross-pollinate model outputs."
            ),
            "message_type": "task",
        },
        {
            "timestamp": base + timedelta(seconds=12),
            "from_agent": "agent_b",
            "to_agent": None,
            "content": "+1",
            "message_type": "agreement",
        },
        {
            "timestamp": base + timedelta(seconds=15),
            "from_agent": "agent_a",
            "to_agent": None,
            "content": "And we'll use LRU eviction with maxsize 256.",
            "message_type": "task",
        },
        {
            "timestamp": base + timedelta(seconds=18),
            "from_agent": "agent_c",
            "to_agent": None,
            "content": "LGTM",
            "message_type": "agreement",
        },
        {
            "timestamp": base + timedelta(seconds=22),
            "from_agent": "agent_d",
            "to_agent": None,
            "content": "sounds good",
            "message_type": "agreement",
        },
        {
            "timestamp": base + timedelta(seconds=25),
            "from_agent": "agent_a",
            "to_agent": None,
            "content": "Implementing now.",
            "message_type": "decision",
        },
        {
            "timestamp": base + timedelta(seconds=180),
            "from_agent": "agent_b",
            "to_agent": None,
            "content": "+1",
            "message_type": "agreement",
        },
    ]


# ---------------------------------------------------------------------
# Org-scale traces (shape="org")
# ---------------------------------------------------------------------


def hyper_specialized_roster() -> list[dict]:
    """Org-scale roster where every agent has exactly one capability.

    The roster is shaped for ``OrgStructureTrace`` /
    ``SpanOfControlTrace`` consumers; each demo wires it into its
    pattern's Pydantic model.
    """
    return [
        {"agent_id": "specialist_sql", "capabilities": ["sql"], "reports_to": "orchestrator"},
        {"agent_id": "specialist_python", "capabilities": ["python"], "reports_to": "orchestrator"},
        {"agent_id": "specialist_kafka", "capabilities": ["kafka"], "reports_to": "orchestrator"},
        {"agent_id": "specialist_aws", "capabilities": ["aws"], "reports_to": "orchestrator"},
        {"agent_id": "specialist_redis", "capabilities": ["redis"], "reports_to": "orchestrator"},
        {"agent_id": "specialist_docker", "capabilities": ["docker"], "reports_to": "orchestrator"},
        {
            "agent_id": "specialist_postgres",
            "capabilities": ["postgres"],
            "reports_to": "orchestrator",
        },
        {
            "agent_id": "specialist_kubernetes",
            "capabilities": ["kubernetes"],
            "reports_to": "orchestrator",
        },
        {"agent_id": "specialist_react", "capabilities": ["react"], "reports_to": "orchestrator"},
        {
            "agent_id": "specialist_typescript",
            "capabilities": ["typescript"],
            "reports_to": "orchestrator",
        },
        {"agent_id": "orchestrator", "capabilities": ["routing"], "reports_to": None},
    ]


def hub_and_spoke_roster() -> list[dict]:
    """Classic hub-and-spoke fragile topology."""
    return [
        {"agent_id": "hub", "capabilities": ["routing", "decisions", "review"], "reports_to": None},
        {"agent_id": "spoke_1", "capabilities": ["python"], "reports_to": "hub"},
        {"agent_id": "spoke_2", "capabilities": ["sql"], "reports_to": "hub"},
        {"agent_id": "spoke_3", "capabilities": ["docs"], "reports_to": "hub"},
        {"agent_id": "spoke_4", "capabilities": ["tests"], "reports_to": "hub"},
        {"agent_id": "spoke_5", "capabilities": ["deploy"], "reports_to": "hub"},
    ]


def balanced_team_roster() -> list[dict]:
    """A healthier mid-sized roster with overlapping capabilities.

    Useful as a control: showing what 'well-fit' looks like next to
    the fragile rosters above.
    """
    return [
        {
            "agent_id": "tech_lead",
            "capabilities": ["routing", "review", "python", "sql"],
            "reports_to": None,
        },
        {
            "agent_id": "backend_a",
            "capabilities": ["python", "sql", "deploy"],
            "reports_to": "tech_lead",
        },
        {
            "agent_id": "backend_b",
            "capabilities": ["python", "kafka", "redis"],
            "reports_to": "tech_lead",
        },
        {
            "agent_id": "frontend_a",
            "capabilities": ["react", "typescript", "deploy"],
            "reports_to": "tech_lead",
        },
        {
            "agent_id": "data_a",
            "capabilities": ["python", "sql", "kafka"],
            "reports_to": "tech_lead",
        },
        {
            "agent_id": "qa",
            "capabilities": ["tests", "python", "deploy"],
            "reports_to": "tech_lead",
        },
    ]


__all__ = [
    "balanced_team_roster",
    "groupthink_messages",
    "hallucinated_citation_trace",
    "hub_and_spoke_roster",
    "hyper_specialized_roster",
    "over_apology_trace",
    "silent_dependency_drop_messages",
    "silent_dissent_messages",
    "social_loafing_messages",
    "stuck_in_loop_trace",
    "sycophancy_trace",
    "well_executed_individual_trace",
]
