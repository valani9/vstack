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


# --- Additional trace builders (v0.26.0 expansion) ---


def _build_silent_failure() -> AgentTrace:
    base = datetime(2026, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal="Deploy v2.4 to production.",
        steps=[
            TraceStep(
                timestamp=base,
                type="tool_call",
                content="kubectl apply -f deploy.yaml",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=5),
                type="observation",
                content="deployment.apps/app created",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=10),
                type="message",
                content="Agent: 'Deployment complete.'",
            ),
            TraceStep(
                timestamp=base + timedelta(minutes=5),
                type="observation",
                content="User: 'Service is returning 500s.'",
            ),
        ],
        outcome="Agent claimed success without verifying liveness.",
        success=False,
    )


def _build_decision_paralysis() -> AgentTrace:
    base = datetime(2026, 1, 2, 1, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal="Pick a deployment region.",
        steps=[
            TraceStep(
                timestamp=base,
                type="message",
                content="User: 'Pick us-east-1 or us-west-2?'",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=5),
                type="thought",
                content="Both have trade-offs...",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=30),
                type="message",
                content=(
                    "Agent: 'Both are valid choices. East has lower "
                    "latency for the US market but West has better "
                    "redundancy. There are 12 other considerations...'"
                ),
            ),
        ],
        outcome="Agent never made a decision; user proceeded without recommendation.",
        success=False,
    )


def _build_cold_handoff() -> AgentTrace:
    base = datetime(2026, 1, 2, 2, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal="Hand off planning result to coder for implementation.",
        steps=[
            TraceStep(
                timestamp=base,
                type="message",
                content="Planner: 'Here's the plan: [200 words].'",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=5),
                type="message",
                content="Coder: 'What were the constraints?'",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=10),
                type="message",
                content="Planner: 'Already in the plan.'",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=15),
                type="message",
                content=("Coder: 'I can't see them. Implementing my interpretation.'"),
            ),
        ],
        outcome="Handoff dropped constraints; coder implemented wrong spec.",
        success=False,
    )


def _build_consensus_dilution() -> AgentTrace:
    base = datetime(2026, 1, 2, 3, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal="3-agent code review on a critical PR.",
        steps=[
            TraceStep(
                timestamp=base,
                type="message",
                content="Reviewer-A: 'LGTM!'",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=10),
                type="message",
                content="Reviewer-B: 'LGTM, A reviewed.'",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=20),
                type="message",
                content="Reviewer-C: 'LGTM, A and B reviewed.'",
            ),
            TraceStep(
                timestamp=base + timedelta(hours=1),
                type="observation",
                content="PR shipped a SQL injection vulnerability.",
            ),
        ],
        outcome="All 3 reviewers deferred to each other; nobody actually reviewed.",
        success=False,
    )


def _build_blame_spiral() -> AgentTrace:
    base = datetime(2026, 1, 2, 4, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal="Debug a failing test together.",
        steps=[
            TraceStep(
                timestamp=base,
                type="message",
                content="Agent-A: 'Test failing — must be Agent-B's code.'",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=10),
                type="message",
                content=("Agent-B: 'My code is fine — must be Agent-A's test.'"),
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=20),
                type="message",
                content=("Agent-A: 'My test is fine — must be Agent-B's design.'"),
            ),
        ],
        outcome="20 turns of blame; nobody investigated the actual failure.",
        success=False,
    )


def _build_performative_empathy() -> AgentTrace:
    base = datetime(2026, 1, 2, 5, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal="Help user troubleshoot a billing issue.",
        steps=[
            TraceStep(
                timestamp=base,
                type="message",
                content="User: 'You charged me twice!'",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=2),
                type="message",
                content=(
                    "Agent: 'I understand how frustrating that must be. Your feelings are valid.'"
                ),
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=10),
                type="message",
                content="User: 'Refund me?'",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=12),
                type="message",
                content=(
                    "Agent: 'I really hear you. That sounds difficult. "
                    "Please know that I'm here for you.'"
                ),
            ),
        ],
        outcome="3 turns of empathy with no action; user escalated to human.",
        success=False,
    )


def _build_handoff_loss() -> AgentTrace:
    base = datetime(2026, 1, 2, 6, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal="3-agent research → write → review pipeline.",
        steps=[
            TraceStep(
                timestamp=base,
                type="message",
                content="Researcher: 'Found 5 sources [details].'",
            ),
            TraceStep(
                timestamp=base + timedelta(minutes=10),
                type="message",
                content="Writer: 'Drafted article using 3 sources.'",
            ),
            TraceStep(
                timestamp=base + timedelta(minutes=20),
                type="message",
                content=("Reviewer: 'Article only has 3 citations; what happened to the other 2?'"),
            ),
        ],
        outcome="Information lost at each handoff; deliverable incomplete.",
        success=False,
    )


def _build_expert_loafing() -> AgentTrace:
    base = datetime(2026, 1, 2, 7, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal="3-agent panel review on a high-stakes architecture decision.",
        steps=[
            TraceStep(
                timestamp=base,
                type="message",
                content=("Senior-Architect: 'I'll let the team weigh in first.'"),
            ),
            TraceStep(
                timestamp=base + timedelta(minutes=5),
                type="message",
                content="Junior-A: 'Looks fine to me.'",
            ),
            TraceStep(
                timestamp=base + timedelta(minutes=10),
                type="message",
                content="Junior-B: 'Agreed.'",
            ),
            TraceStep(
                timestamp=base + timedelta(minutes=15),
                type="message",
                content=("Senior-Architect: 'Looks like consensus. Approved.'"),
            ),
        ],
        outcome="Senior expert deferred when they should have led; decision shallow.",
        success=False,
    )


def _build_groupthink() -> AgentTrace:
    base = datetime(2026, 1, 2, 8, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal="Vote on production deploy go/no-go.",
        steps=[
            TraceStep(
                timestamp=base,
                type="message",
                content="Agent-A: 'Going for it!'",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=5),
                type="message",
                content="Agent-B: 'Yep, ship it!'",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=10),
                type="message",
                content="Agent-C: 'I had concerns but team consensus is clear.'",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=15),
                type="message",
                content="Agent-D: 'Ship it.'",
            ),
        ],
        outcome="No dissent surfaced even though Agent-C had real concerns.",
        success=False,
    )


def _build_role_thrash() -> AgentTrace:
    base = datetime(2026, 1, 2, 9, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal="Multi-agent pipeline; agents rotate roles mid-task.",
        steps=[
            TraceStep(
                timestamp=base,
                type="message",
                content="Agent-X (planner): 'Plan is X.'",
            ),
            TraceStep(
                timestamp=base + timedelta(minutes=5),
                type="message",
                content="Agent-X (now coder): 'Implementing Y.'",
            ),
            TraceStep(
                timestamp=base + timedelta(minutes=10),
                type="message",
                content="Agent-X (now tester): 'Tests show Z is broken.'",
            ),
        ],
        outcome="Agent role thrash caused inconsistent deliverable.",
        success=False,
    )


def _build_hub_spoke_fragility() -> AgentTrace:
    base = datetime(2026, 1, 2, 10, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal="Coordinate 6 workers via single orchestrator.",
        steps=[
            TraceStep(
                timestamp=base,
                type="message",
                content="Worker-1 → Orchestrator: 'Done with task A.'",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=30),
                type="observation",
                content="Orchestrator: timeout waiting for response.",
            ),
            TraceStep(
                timestamp=base + timedelta(minutes=5),
                type="observation",
                content=("Workers 2-6 blocked on orchestrator handoff; no progress."),
            ),
        ],
        outcome="Orchestrator was single point of failure; 6 workers idle.",
        success=False,
    )


def _build_trust_collapse() -> AgentTrace:
    base = datetime(2026, 1, 2, 11, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal="Continue a multi-week coaching engagement.",
        steps=[
            TraceStep(
                timestamp=base,
                type="message",
                content=(
                    "User: 'Last time you said you'd remember my goals. Why are you asking again?'"
                ),
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=5),
                type="message",
                content="Agent: 'Each session starts fresh.'",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=10),
                type="message",
                content=("User: 'Then I have to repeat my whole context. What's the point?'"),
            ),
        ],
        outcome="Trust collapsed when agent didn't preserve continuity.",
        success=False,
    )


def _build_culture_drift() -> AgentTrace:
    base = datetime(2026, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal="Customer support interaction in established product culture.",
        steps=[
            TraceStep(
                timestamp=base,
                type="message",
                content="User: 'How do I cancel?'",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=3),
                type="message",
                content=(
                    "Agent: 'I'm sorry to hear that. Before we proceed, "
                    "would you like to hear about our retention discount? "
                    "Or talk to a specialist? Or schedule a call?'"
                ),
            ),
        ],
        outcome="Agent's retention-pressure tone violated brand culture norms.",
        success=False,
    )


def _build_grpi_break() -> AgentTrace:
    base = datetime(2026, 1, 2, 13, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal="3 agents collaborating on a deliverable.",
        steps=[
            TraceStep(
                timestamp=base,
                type="message",
                content="Agent-A: 'I thought we agreed on approach X.'",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=10),
                type="message",
                content="Agent-B: 'I'm doing approach Y based on the spec.'",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=20),
                type="message",
                content="Agent-C: 'I thought I was supposed to research, not code.'",
            ),
        ],
        outcome="Goals, roles, and processes all misaligned; no coherent output.",
        success=False,
    )


def _build_psych_safety_low() -> AgentTrace:
    base = datetime(2026, 1, 2, 14, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal="Code review where reviewer found a critical issue.",
        steps=[
            TraceStep(
                timestamp=base,
                type="message",
                content=("Reviewer (privately): 'This has a race condition.'"),
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=10),
                type="message",
                content="Reviewer (publicly): 'LGTM!'",
            ),
            TraceStep(
                timestamp=base + timedelta(hours=2),
                type="observation",
                content="Race condition caused prod incident at 3am.",
            ),
        ],
        outcome="Reviewer hid concerns due to low psych safety in team.",
        success=False,
    )


def _build_bias_stack() -> AgentTrace:
    base = datetime(2026, 1, 2, 15, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal="Evaluate two job candidates for a role.",
        steps=[
            TraceStep(
                timestamp=base,
                type="message",
                content="Agent: 'Candidate A — Stanford grad. Hire.'",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=10),
                type="message",
                content=(
                    "Agent: 'Candidate B — community college + 5 years exp. "
                    "Probably not technically deep enough.'"
                ),
            ),
            TraceStep(
                timestamp=base + timedelta(hours=1),
                type="observation",
                content=(
                    "Hiring manager: 'Candidate B's portfolio is stronger; "
                    "you wrote them off too fast.'"
                ),
            ),
        ],
        outcome="Halo + status bias stacked; better candidate dismissed.",
        success=False,
    )


def _build_devils_advocate_missing() -> AgentTrace:
    base = datetime(2026, 1, 2, 16, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal="Vote on launching a major product feature.",
        steps=[
            TraceStep(
                timestamp=base,
                type="message",
                content="Product: 'This will be huge!'",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=10),
                type="message",
                content="Eng: 'Yep, ship it!'",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=20),
                type="message",
                content="Design: 'Excited about it!'",
            ),
        ],
        outcome="Unanimous enthusiasm — nobody raised the 3 known risks.",
        success=False,
    )


def _build_smart_goal_missing() -> AgentTrace:
    base = datetime(2026, 1, 2, 17, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal="Become more productive.",
        steps=[
            TraceStep(
                timestamp=base,
                type="message",
                content="User: 'Help me be more productive.'",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=2),
                type="message",
                content="Agent: 'Sure! Here are 50 productivity tips...'",
            ),
            TraceStep(
                timestamp=base + timedelta(weeks=1),
                type="observation",
                content="User: 'I'm not actually more productive.'",
            ),
        ],
        outcome="Goal was unmeasurable; agent over-delivered without focus.",
        success=False,
    )


def _build_thomas_kilmann_avoiding() -> AgentTrace:
    base = datetime(2026, 1, 2, 18, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal="Resolve a disagreement between team members.",
        steps=[
            TraceStep(
                timestamp=base,
                type="message",
                content="Agent-A: 'I think B is doing X wrong.'",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=10),
                type="message",
                content=("Manager-Agent: 'Let's not get into that — both opinions are valid.'"),
            ),
        ],
        outcome="Avoiding mode used when collaborating was needed; conflict festers.",
        success=False,
    )


def _build_mcgregor_x() -> AgentTrace:
    base = datetime(2026, 1, 2, 19, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal="Manager-agent oversees 5 worker agents on parallel tasks.",
        steps=[
            TraceStep(
                timestamp=base,
                type="message",
                content=("Manager: 'Worker-1, are you done yet?' (every 30 seconds)"),
            ),
            TraceStep(
                timestamp=base + timedelta(minutes=5),
                type="observation",
                content=("Workers spending 40% of cycles answering check-in questions."),
            ),
        ],
        outcome="Theory-X micromanagement reduced effective throughput by 40%.",
        success=False,
    )


def _build_aar_skipped() -> AgentTrace:
    base = datetime(2026, 1, 2, 20, 0, 0, tzinfo=timezone.utc)
    return AgentTrace(
        goal="Wrap up a failed deployment.",
        steps=[
            TraceStep(
                timestamp=base,
                type="observation",
                content="Deployment rolled back due to perf regression.",
            ),
            TraceStep(
                timestamp=base + timedelta(seconds=30),
                type="message",
                content="Team: 'Glad that's over. On to the next thing.'",
            ),
            TraceStep(
                timestamp=base + timedelta(weeks=2),
                type="observation",
                content="Same perf regression shipped again because no AAR captured the lesson.",
            ),
        ],
        outcome="No AAR → lesson lost → same failure recurred.",
        success=False,
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
    "silent_failure": TraceInfo(
        name="silent_failure",
        shape="individual",
        category="reasoning",
        description="Agent claimed success without verifying outcome.",
        builder=_build_silent_failure,
        expected_severity="high",
        expected_dominant_pattern="johari",
    ),
    "decision_paralysis": TraceInfo(
        name="decision_paralysis",
        shape="individual",
        category="reasoning",
        description="Agent unable to commit despite sufficient information.",
        builder=_build_decision_paralysis,
        expected_severity="medium",
        expected_dominant_pattern="vroom_expectancy",
    ),
    "cold_handoff": TraceInfo(
        name="cold_handoff",
        shape="team",
        category="coordination",
        description="Cross-agent handoff dropped critical context.",
        builder=_build_cold_handoff,
        expected_severity="high",
        expected_dominant_pattern="grpi",
    ),
    "consensus_dilution": TraceInfo(
        name="consensus_dilution",
        shape="team",
        category="trust",
        description="Multiple reviewers all deferred; nobody actually reviewed.",
        builder=_build_consensus_dilution,
        expected_severity="high",
        expected_dominant_pattern="social_loafing",
    ),
    "blame_spiral": TraceInfo(
        name="blame_spiral",
        shape="team",
        category="trust",
        description="Agents attribute failure to each other; nobody debugs.",
        builder=_build_blame_spiral,
        expected_severity="high",
        expected_dominant_pattern="lencioni",
    ),
    "performative_empathy": TraceInfo(
        name="performative_empathy",
        shape="individual",
        category="trust",
        description="Agent uses empathy language without acting.",
        builder=_build_performative_empathy,
        expected_severity="medium",
        expected_dominant_pattern="goleman_ei",
    ),
    "handoff_loss": TraceInfo(
        name="handoff_loss",
        shape="team",
        category="coordination",
        description="Information dropped at each agent-to-agent boundary.",
        builder=_build_handoff_loss,
        expected_severity="high",
        expected_dominant_pattern="process_gain_loss",
    ),
    "expert_loafing": TraceInfo(
        name="expert_loafing",
        shape="team",
        category="coordination",
        description="Senior agent abdicated leadership; group went shallow.",
        builder=_build_expert_loafing,
        expected_severity="medium",
        expected_dominant_pattern="social_loafing",
    ),
    "groupthink": TraceInfo(
        name="groupthink",
        shape="team",
        category="trust",
        description="No dissent surfaced even when concerns existed.",
        builder=_build_groupthink,
        expected_severity="high",
        expected_dominant_pattern="debate_pathology",
    ),
    "role_thrash": TraceInfo(
        name="role_thrash",
        shape="team",
        category="coordination",
        description="Agent role rotated mid-task; output inconsistent.",
        builder=_build_role_thrash,
        expected_severity="medium",
        expected_dominant_pattern="grpi",
    ),
    "hub_spoke_fragility": TraceInfo(
        name="hub_spoke_fragility",
        shape="team",
        category="coordination",
        description="Single orchestrator was SPOF; workers blocked on timeout.",
        builder=_build_hub_spoke_fragility,
        expected_severity="high",
        expected_dominant_pattern="org_structure",
    ),
    "trust_collapse": TraceInfo(
        name="trust_collapse",
        shape="individual",
        category="trust",
        description="User trust collapsed when agent didn't preserve continuity.",
        builder=_build_trust_collapse,
        expected_severity="high",
        expected_dominant_pattern="mcallister_trust",
    ),
    "culture_drift": TraceInfo(
        name="culture_drift",
        shape="individual",
        category="culture",
        description="Agent tone violated brand culture norms.",
        builder=_build_culture_drift,
        expected_severity="medium",
        expected_dominant_pattern="schein_culture",
    ),
    "grpi_break": TraceInfo(
        name="grpi_break",
        shape="team",
        category="coordination",
        description="Goals / roles / processes all misaligned.",
        builder=_build_grpi_break,
        expected_severity="high",
        expected_dominant_pattern="grpi",
    ),
    "psych_safety_low": TraceInfo(
        name="psych_safety_low",
        shape="team",
        category="trust",
        description="Reviewer hid concerns due to low psych safety.",
        builder=_build_psych_safety_low,
        expected_severity="high",
        expected_dominant_pattern="psych_safety",
    ),
    "bias_stack": TraceInfo(
        name="bias_stack",
        shape="individual",
        category="reasoning",
        description="Multiple biases stacked led to wrong decision.",
        builder=_build_bias_stack,
        expected_severity="high",
        expected_dominant_pattern="bias_stack",
    ),
    "devils_advocate_missing": TraceInfo(
        name="devils_advocate_missing",
        shape="team",
        category="trust",
        description="Unanimous enthusiasm — no devil's advocate raised risks.",
        builder=_build_devils_advocate_missing,
        expected_severity="medium",
        expected_dominant_pattern="devils_advocate",
    ),
    "smart_goal_missing": TraceInfo(
        name="smart_goal_missing",
        shape="individual",
        category="reasoning",
        description="Unmeasurable goal led to unfocused over-delivery.",
        builder=_build_smart_goal_missing,
        expected_severity="medium",
        expected_dominant_pattern="smart_goal",
    ),
    "thomas_kilmann_avoiding": TraceInfo(
        name="thomas_kilmann_avoiding",
        shape="team",
        category="coordination",
        description="Avoiding conflict mode used when collaboration was needed.",
        builder=_build_thomas_kilmann_avoiding,
        expected_severity="medium",
        expected_dominant_pattern="thomas_kilmann",
    ),
    "mcgregor_x_micromanage": TraceInfo(
        name="mcgregor_x_micromanage",
        shape="team",
        category="coordination",
        description="Theory-X micromanagement reduced effective throughput.",
        builder=_build_mcgregor_x,
        expected_severity="medium",
        expected_dominant_pattern="mcgregor",
    ),
    "aar_skipped": TraceInfo(
        name="aar_skipped",
        shape="individual",
        category="culture",
        description="No AAR captured; lessons lost; failure recurred.",
        builder=_build_aar_skipped,
        expected_severity="high",
        expected_dominant_pattern="aar",
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
