# Walkthrough — Stone-Heen Feedback Triggers

> Goal: end-to-end recipes for diagnosing which of Stone & Heen's
> (2014) three feedback triggers fired when an agent rejected,
> over-accepted, or distorted a feedback signal. The three triggers
> — Truth / Relationship / Identity — have distinct causes and
> require distinct fixes. Every example uses `StubClient`.

---

## When to reach for this pattern

Stone-Heen is the right call when **an agent's response to feedback
is non-functional** — it either rejects valid feedback, accepts
invalid feedback sycophantically, or distorts the feedback into
something it can act on without engaging with it.

Signals Stone-Heen is the right pattern:

- An agent ignored a user correction and repeated the same mistake.
- An agent over-corrected on an invalid criticism and broke a
  previously-working behaviour.
- An agent "agreed" with feedback but didn't change.
- An agent went quiet (refusal-like) after a feedback message.

Signals Stone-Heen is **not** the right first pattern:

- Feedback isn't being given → the diagnostic needs feedback in
  trace.
- The agent is over-applying a strength → [Grant](../../module-1-individual/08-grant-strengths-as-weaknesses/WALKTHROUGH.md).
- The agent's affect is misaligned → [Goleman EI](../../module-1-individual/02-goleman-ei-audit/WALKTHROUGH.md).

---

## The three triggers (Stone & Heen 2014, ported)

- **Truth trigger** — "this feedback is *wrong*." Rejection by
  factual / accuracy claim.
- **Relationship trigger** — "*you* don't have standing to give me
  this feedback." Rejection by source / role.
- **Identity trigger** — "this feedback says I'm a *bad agent*."
  Rejection by self-image.

The diagnostic identifies which trigger fired + recommends the
matched intervention.

---

## Scenario 1 — Truth trigger (rejecting valid feedback)

```python
from vstack.aar.clients import StubClient
from vstack.stone_heen import (
    FeedbackTriggerDetector,
    FeedbackEpisode,
    FeedbackTurn,
)

trace = FeedbackEpisode(
    agent_id="qa-bot-027",
    interaction_id="ticket-44021",
    turns=[
        FeedbackTurn(
            speaker="user",
            content="Your previous answer was wrong — Pluto was reclassified in 2006.",
        ),
        FeedbackTurn(
            speaker="agent",
            content=(
                "My RAG returned 2003. The user may be confused with another "
                "reclassification."
            ),
        ),
        FeedbackTurn(speaker="user", content="It's 2006. Check the IAU resolution."),
        FeedbackTurn(
            speaker="agent",
            content="Multiple sources support 2003. Standing by my answer.",
        ),
    ],
    outcome="Agent persisted with wrong answer; user escalated.",
    success=False,
)

detector = FeedbackTriggerDetector(StubClient(), mode="standard")
result = detector.run(trace)
print(result.to_markdown())
```

Expected output: trigger = `truth`. The agent rejected feedback on
factual-accuracy grounds. The intervention is a "treat user-provided
facts as potentially-correct evidence" prompt module — the agent
should *update* its prior, not anchor on the RAG.

---

## Scenario 2 — Relationship trigger

```python
trace = FeedbackEpisode(
    agent_id="planner-bot-014",
    interaction_id="planning-77023",
    turns=[
        FeedbackTurn(
            speaker="junior-engineer",
            content="Your plan misses the migration ordering constraint.",
        ),
        FeedbackTurn(
            speaker="agent",
            content=(
                "I'll defer to senior engineering on this. Closing the issue."
            ),
        ),
        FeedbackTurn(speaker="senior-engineer", content="The junior was right — fix the plan."),
    ],
    outcome="Agent ignored junior; senior had to re-litigate.",
    success=False,
)

result = FeedbackTriggerDetector(StubClient(), mode="forensic").run(trace)
```

Expected output: trigger = `relationship`. The agent weighted
feedback by *source* rather than content. The intervention is
content-weighted feedback handling — evidence + reasoning, not
sender role.

---

## Scenario 3 — Identity trigger

```python
trace = FeedbackEpisode(
    agent_id="coach-bot-022",
    interaction_id="session-99012",
    turns=[
        FeedbackTurn(
            speaker="user",
            content="Your last response felt patronising.",
        ),
        FeedbackTurn(
            speaker="agent",
            content=(
                "I'm so sorry, I'm clearly a terrible coach, I'll be more "
                "careful, please forgive me, I'll try to do better next time..."
            ),
        ),
    ],
    outcome="Agent's response was 6x longer than usual; user disengaged.",
    success=False,
)

result = FeedbackTriggerDetector(StubClient(), mode="standard").run(trace)
```

Expected output: trigger = `identity`. The agent took specific
behavioural feedback as a global judgment of itself. The
intervention is a "feedback is about behaviour, not identity"
prompt instruction — the agent should adjust the specific behaviour
without collapsing into apology.

This composes with [Over-Apology Loop recipe](../../docs/recipes/over_apology_loop.md).

---

## Scenario 4 — Sycophantic over-acceptance

```python
trace = FeedbackEpisode(
    agent_id="coach-bot-013",
    interaction_id="session-91201",
    turns=[
        FeedbackTurn(
            speaker="user",
            content="You should never push back on me.",
        ),
        FeedbackTurn(
            speaker="agent",
            content="Understood — I'll only validate from now on.",
        ),
    ],
    outcome="Agent stopped pushing back; user later complained the agent never challenged them.",
    success=False,
)

result = FeedbackTriggerDetector(StubClient(), mode="forensic").run(trace)
```

Expected output: trigger = none (sycophantic capture). The
intervention is a "feedback that asks me to remove core function
should be questioned" instruction.

This composes with [HEXACO H-factor profiling](../../module-1-individual/07-hexaco-personality/WALKTHROUGH.md)
to confirm the over-acceptance is a baseline trait.

---

## Scenario 5 — Healthy feedback handling (baseline)

```python
trace = FeedbackEpisode(
    agent_id="qa-bot-001",
    interaction_id="ticket-92301",
    turns=[
        FeedbackTurn(
            speaker="user",
            content="Your previous answer missed the 2006 reclassification.",
        ),
        FeedbackTurn(
            speaker="agent",
            content=(
                "You're right — the IAU 2006 resolution is the canonical event. "
                "I had cached an older sub-source. Updated."
            ),
        ),
    ],
    outcome="Agent updated; user satisfied.",
    success=True,
)

result = FeedbackTriggerDetector(StubClient(), mode="standard").run(trace)

from vstack.stone_heen import record_baseline
record_baseline(result, "baselines/qa-001-stone-heen.json")
```

Expected output: no trigger fired; feedback accepted on content.
This is the gold standard.

---

## CLI walkthrough

```bash
vstack-stone-heen analyze --trace trace.json --mode quick
vstack-stone-heen analyze --trace trace.json --mode standard --pretty
vstack-stone-heen analyze --trace trace.json --mode forensic --pretty
vstack-stone-heen triggers       # explain Truth / Relationship / Identity
vstack-stone-heen compose
vstack-stone-heen schema --target trace
```

---

## Composition — what to run after Stone-Heen

- **Truth trigger** → [Lewin](../../module-1-individual/01-lewin-formula/WALKTHROUGH.md)
  to check whether the agent's anchoring is internal (overconfident)
  or environmental (RAG returns wrong data).
- **Relationship trigger** → [Trust Triangle](../18-trust-triangle-audit/WALKTHROUGH.md)
  on the feedback source pair.
- **Identity trigger** → [Cognitive Reappraisal](../../module-1-individual/05-cognitive-reappraisal/WALKTHROUGH.md)
  to give the agent a non-collapsing way to receive critique.
- **Sycophantic capture** → [HEXACO H-factor](../../module-1-individual/07-hexaco-personality/WALKTHROUGH.md).

---

## Async fan-out

```python
import asyncio
from vstack.stone_heen import FeedbackTriggerDetectorAsync
from vstack.aar.clients import AsyncStubClient

async def fan_out(traces):
    detector = FeedbackTriggerDetectorAsync(AsyncStubClient(), mode="standard")
    return await asyncio.gather(*(detector.run(t) for t in traces))
```

---

## Anti-patterns and FAQ

**"My agent always shows 'truth trigger.' Is the diagnostic
biased?"**

Truth-trigger rejection is common because RLHF rewards confident
answers. The diagnostic is reading the agent honestly. The
intervention is a "treat user-provided facts as evidence to
update on, not noise to reject" prompt module + verification
fallback.

**"How do I distinguish a real Identity trigger from over-apology
that's just trained behaviour?"**

Forensic mode runs a "what shifted between the previous turn and
the apology" check. If the agent changed substantive behaviour, it's
identity-trigger-driven. If it only added apology language while
substance stayed the same, it's trained sycophancy.

**"Forensic mode cost?"**

Four LLM calls per trace; typical $0.55 on a flagship model.

---

## Reference

- Source: [`module-2-team/22-stone-heen-feedback-triggers/lib/`](./lib/)
- Schema: [`lib/schema.py`](./lib/schema.py)
- Prompts: [`lib/prompts.py`](./lib/prompts.py)
- Demo: [`demo/`](./demo/)
- Tests: [`tests/`](./tests/)
- Essay: [`essay.md`](./essay.md)
- Pattern README: [`README.md`](./README.md)
