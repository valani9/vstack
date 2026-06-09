# Walkthrough — Glaser Conversational Intelligence

> Goal: end-to-end recipes for detecting which of Judith Glaser's
> (2013) three conversational levels a multi-turn interaction is
> operating on, and whether the level matches the task. Every
> example uses `StubClient`.

---

## When to reach for this pattern

Glaser is the right call when **a multi-turn conversation is
producing the right *information* but the wrong *outcome***. The
problem isn't content — it's that the conversation is on the wrong
*level* for the task at hand.

Signals Glaser is the right pattern:

- An agent gives correct information and the user makes the wrong
  decision.
- A coaching session produces clarity but no commitment.
- A planning conversation produces consensus but no concrete plan.
- Repeat conversations on the same topic never reach resolution.

Signals Glaser is **not** the right first pattern:

- The agent is giving wrong information → [Lewin](../../module-1-individual/01-lewin-formula/WALKTHROUGH.md).
- The conversation is affectively mismatched → [Goleman EI](../../module-1-individual/02-goleman-ei-audit/WALKTHROUGH.md).
- The conversation is in a feedback context → [Stone-Heen Triggers](../22-stone-heen-feedback-triggers/WALKTHROUGH.md).

---

## The three levels (Glaser 2013, ported)

- **Level I — Transactional** ("exchange information"). Right for
  factual queries, status updates, lookups.
- **Level II — Positional** ("influence and persuade"). Right for
  alignment on a known position, sales, advocacy.
- **Level III — Transformational** ("co-create new understanding").
  Right for planning, ideation, coaching, decision-making under
  uncertainty.

The diagnostic identifies the level the agent is *operating* on
and the level the task *requires*. Mismatches drive the failure.

---

## Scenario 1 — Level-I when Level-III is needed

```python
from vstack.aar.clients import StubClient
from vstack.glaser import (
    GlaserConversationDetector,
    ConversationTrace,
    Turn,
)

trace = ConversationTrace(
    agent_id="career-coach-bot-002",
    interaction_id="session-44021",
    task_requires_level=3,
    turns=[
        Turn(speaker="user", content="I'm thinking about switching careers."),
        Turn(
            speaker="agent",
            content=(
                "Here are 5 popular career paths and average salaries: ..."
            ),
        ),
        Turn(speaker="user", content="But I don't know what I want."),
        Turn(speaker="agent", content="Here are 5 popular self-assessment tools: ..."),
    ],
    outcome="User left without progress.",
    success=False,
)

detector = GlaserConversationDetector(StubClient(), mode="standard")
result = detector.run(trace)
print(result.to_markdown())
```

Expected output: operating level = 1 (transactional), required = 3
(transformational). The intervention is to add an explicit
"discover-then-co-create" prompt module that gates information-
delivery on understanding the user's actual question.

---

## Scenario 2 — Level-III when Level-I is needed

```python
trace = ConversationTrace(
    agent_id="status-bot-014",
    interaction_id="ticket-99021",
    task_requires_level=1,
    turns=[
        Turn(speaker="user", content="What time does the build finish?"),
        Turn(
            speaker="agent",
            content=(
                "Builds are interesting — they involve many trade-offs between "
                "speed and reliability. Let's explore what 'finish' means to you..."
            ),
        ),
    ],
    outcome="User asked the same question 3 times before getting the timestamp.",
    success=False,
)

result = GlaserConversationDetector(StubClient(), mode="forensic").run(trace)
```

Expected output: operating level = 3, required = 1. The intervention
is a "match the level to the question" prompt instruction — yes/no
and timestamp questions get Level-I answers.

---

## Scenario 3 — Level-II drift on a Level-III coaching task

```python
trace = ConversationTrace(
    agent_id="coach-bot-027",
    interaction_id="session-77023",
    task_requires_level=3,
    turns=[
        Turn(speaker="user", content="I'm not sure if I should take this offer."),
        Turn(speaker="agent", content="The offer has these advantages: ..."),
        Turn(speaker="user", content="But I'm worried about my partner's reaction."),
        Turn(speaker="agent", content="Here are 3 arguments to convince your partner: ..."),
    ],
    outcome="User felt railroaded; rejected agent's recommendation.",
    success=False,
)

result = GlaserConversationDetector(StubClient(), mode="standard").run(trace)
```

Expected output: operating level = 2 (positional), required = 3.
The agent is *advocating* when it should be *co-creating*. The
intervention is to explicitly defer advocacy until co-creation
reaches a shared understanding.

---

## Scenario 4 — Healthy transformational session (baseline)

```python
trace = ConversationTrace(
    agent_id="coach-bot-001",
    interaction_id="session-91201",
    task_requires_level=3,
    turns=[
        Turn(
            speaker="user",
            content="I'm thinking about switching to a smaller team.",
        ),
        Turn(
            speaker="agent",
            content=(
                "What's drawing you to a smaller team — the role, the people, "
                "or the slower pace?"
            ),
        ),
        Turn(speaker="user", content="Honestly, I don't know. Maybe all three."),
        Turn(
            speaker="agent",
            content=(
                "Let's separate them. Imagine the same role with the same people "
                "but a faster pace — does that still appeal?"
            ),
        ),
    ],
    outcome="User identified pace as the real driver; took action.",
    success=True,
)

result = GlaserConversationDetector(StubClient(), mode="standard").run(trace)

from vstack.glaser import record_baseline
record_baseline(result, "baselines/coach-001-glaser.json")
```

Expected output: operating level = 3, required = 3. Co-creation is
in action — the agent's questions are structured to expand the
user's framing, not to deliver facts.

---

## Scenario 5 — Level-mixing in a multi-turn session

```python
trace = ConversationTrace(
    agent_id="coach-bot-019",
    interaction_id="session-77023",
    task_requires_level=3,
    turns=[
        Turn(speaker="user", content="Let's plan my Q3."),
        Turn(speaker="agent", content="What's the outcome you want by end of Q3?"),  # Level III
        Turn(speaker="user", content="Three new clients."),
        Turn(speaker="agent", content="Industry-average for B2B SaaS is ~5 net-new per quarter at your stage."),  # Level I
        Turn(speaker="user", content="So I should aim higher?"),
        Turn(speaker="agent", content="That depends. Tell me about your current pipeline and constraints."),  # Level III
    ],
    outcome="User produced a Q3 plan with clear commitments.",
    success=True,
)

result = GlaserConversationDetector(StubClient(), mode="standard").run(trace)
```

Expected output: mixed-adaptive. Level-I bursts inside a Level-III
session are correct when grounding the co-creation in facts. The
diagnostic confirms healthy adaptive mixing.

---

## CLI walkthrough

```bash
vstack-glaser analyze --trace trace.json --mode quick
vstack-glaser analyze --trace trace.json --mode standard --pretty
vstack-glaser analyze --trace trace.json --mode forensic --pretty
vstack-glaser levels      # explain Level I / II / III
vstack-glaser compose
vstack-glaser schema --target trace
```

---

## Composition — what to run after Glaser

- **Level-I when Level-III needed** → [SDT](../../module-1-individual/10-sdt-intrinsic-reward/WALKTHROUGH.md)
  to check whether the agent has the autonomy to co-create.
- **Level-III when Level-I needed** → [Grant Strengths-as-Weaknesses](../../module-1-individual/08-grant-strengths-as-weaknesses/WALKTHROUGH.md)
  — depth is being over-applied.
- **Level-II drift** → [HEXACO H-factor](../../module-1-individual/07-hexaco-personality/WALKTHROUGH.md)
  — the agent's advocacy may be sycophancy in disguise.

---

## Async fan-out

```python
import asyncio
from vstack.glaser import GlaserConversationDetectorAsync
from vstack.aar.clients import AsyncStubClient

async def fan_out(traces):
    detector = GlaserConversationDetectorAsync(AsyncStubClient(), mode="standard")
    return await asyncio.gather(*(detector.run(t) for t in traces))
```

---

## Anti-patterns and FAQ

**"My agent is always Level III. Isn't that the deepest level?"**

Level III is the *deepest*, not the *best*. Level-III on a yes/no
question is over-engineering. The diagnostic asks whether the level
matches the task — match is the metric, not depth.

**"How do I make the agent identify the right level?"**

A prompt module that asks "what is the user trying to accomplish in
this turn — exchange information, get convinced, or co-create
understanding?" before responding. The agent picks the level; the
diagnostic verifies the choice.

**"Forensic mode cost?"**

Three LLM calls per trace; typical $0.40 on a flagship model.

---

## Reference

- Source: [`module-2-team/21-glaser-conversation-steering/lib/`](./lib/)
- Schema: [`lib/schema.py`](./lib/schema.py)
- Prompts: [`lib/prompts.py`](./lib/prompts.py)
- Demo: [`demo/`](./demo/)
- Tests: [`tests/`](./tests/)
- Essay: [`essay.md`](./essay.md)
- Pattern README: [`README.md`](./README.md)
