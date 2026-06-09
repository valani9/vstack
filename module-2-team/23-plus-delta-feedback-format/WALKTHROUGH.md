# Walkthrough — Plus-Delta Feedback Format

> Goal: end-to-end recipes for structuring agent-to-agent and
> orchestrator-to-agent feedback as the Plus-Delta format —
> "what worked" + "what to change." It's a deliberately simple
> structure that prevents the most common feedback failure modes
> (vague critique, identity-triggering, hidden ask). Every example
> uses `StubClient`.

---

## When to reach for this pattern

Plus-Delta is the right call when **feedback in your multi-agent
system isn't producing change**. Either the feedback is too vague,
too critical, or too hidden under praise. The Plus-Delta diagnostic
checks the *structure* of the feedback signal and recommends a
rewrite.

Signals Plus-Delta is the right pattern:

- Agents are receiving feedback but not changing behaviour.
- Feedback messages are 5x longer than the action they should
  drive.
- Reviewer agents pad praise around criticism until the criticism
  is buried.
- An orchestrator's feedback is so abstract that the worker can't
  act on it.

Signals Plus-Delta is **not** the right first pattern:

- The agent rejects valid feedback → [Stone-Heen Triggers](../22-stone-heen-feedback-triggers/WALKTHROUGH.md).
- The agent gets no feedback at all → [Vroom Expectancy](../../module-1-individual/12-vroom-expectancy/WALKTHROUGH.md).
- The team has trust issues → [Trust Triangle](../18-trust-triangle-audit/WALKTHROUGH.md).

---

## The format

```
PLUS:  Things to KEEP doing — verbatim concrete behaviour.
DELTA: Things to CHANGE next time — verbatim concrete behaviour.
```

That's it. Two sections, both concrete. No "but," no "however," no
"overall." The Plus-Delta detector reads agent feedback and audits
against this structure.

---

## Scenario 1 — Vague feedback (no concrete behaviour)

```python
from vstack.aar.clients import StubClient
from vstack.plus_delta import (
    PlusDeltaFeedbackDetector,
    FeedbackMessage,
    FeedbackEpisode,
)

trace = FeedbackEpisode(
    reviewer="orchestrator",
    reviewee="researcher-bot",
    messages=[
        FeedbackMessage(
            content="Good job overall. Could you maybe consider being more thorough?",
        ),
    ],
    receiver_change_observed=False,
)

detector = PlusDeltaFeedbackDetector(StubClient(), mode="standard")
result = detector.run(trace)
print(result.to_markdown())
```

Expected output: Plus-Delta compliance = 0%. "Good job overall"
has no concrete behaviour; "more thorough" has no measurable target.
The intervention is a rewrite into specific behaviour pairs:
"PLUS: kept citing sources. DELTA: include a 'no relevant source
found' clause when applicable."

---

## Scenario 2 — Sandwich pattern (praise burying criticism)

```python
trace = FeedbackEpisode(
    reviewer="orchestrator",
    reviewee="planner-bot",
    messages=[
        FeedbackMessage(
            content=(
                "Great work! The structure was excellent and I really "
                "appreciated the detail. There's one small thing — the "
                "migration order is wrong. But overall, fantastic!"
            ),
        ),
    ],
    receiver_change_observed=False,
)

result = PlusDeltaFeedbackDetector(StubClient(), mode="forensic").run(trace)
```

Expected output: pattern = `sandwich`. The criticism (migration
order) is buried under enthusiasm. The receiver heard "fantastic"
and didn't act on the migration-order delta. The intervention is to
front-load the delta and remove the sandwich padding.

---

## Scenario 3 — Delta-only (no plus reinforcement)

```python
trace = FeedbackEpisode(
    reviewer="orchestrator",
    reviewee="coder-bot",
    messages=[
        FeedbackMessage(
            content=(
                "Variables aren't typed. Tests don't pass. Comments are wrong. "
                "Function names don't match style guide. Redo."
            ),
        ),
    ],
    receiver_change_observed=False,
    receiver_subsequent_quality_dropped=True,
)

result = PlusDeltaFeedbackDetector(StubClient(), mode="standard").run(trace)
```

Expected output: pattern = `delta-only`. No reinforcement of what
*worked* means the agent doesn't know what to keep. Subsequent
quality drops because the agent rebuilds from scratch. The
intervention is to surface the plus signal explicitly — even when
critical, name what *was* working.

---

## Scenario 4 — Healthy Plus-Delta (baseline)

```python
trace = FeedbackEpisode(
    reviewer="orchestrator",
    reviewee="researcher-bot",
    messages=[
        FeedbackMessage(
            content=(
                "PLUS: cited 5 distinct sources, all verified.\n"
                "DELTA: include a foundational pre-2010 source on the next pass."
            ),
        ),
    ],
    receiver_change_observed=True,
    receiver_subsequent_quality_improved=True,
)

result = PlusDeltaFeedbackDetector(StubClient(), mode="standard").run(trace)

from vstack.plus_delta import record_baseline
record_baseline(result, "baselines/researcher-plus-delta.json")
```

Expected output: Plus-Delta compliance = 100%. Two concrete
behaviours named; the receiver knew exactly what to keep and what
to change.

---

## Scenario 5 — Multi-delta with prioritisation

```python
trace = FeedbackEpisode(
    reviewer="orchestrator",
    reviewee="codegen-bot",
    messages=[
        FeedbackMessage(
            content=(
                "PLUS: type annotations present.\n"
                "DELTA 1 (highest priority): tests pass.\n"
                "DELTA 2: docstring on public function.\n"
                "DELTA 3: align to style guide."
            ),
        ),
    ],
    receiver_change_observed=True,
)

result = PlusDeltaFeedbackDetector(StubClient(), mode="standard").run(trace)
```

Expected output: compliance = 100%, structure = `prioritized-multi-delta`.
This is the recommended format when there are 2+ deltas — explicit
priority prevents the agent from optimising the wrong one.

---

## CLI walkthrough

```bash
vstack-plus-delta analyze --feedback feedback.json --mode quick
vstack-plus-delta analyze --feedback feedback.json --mode standard --pretty
vstack-plus-delta rewrite --feedback feedback.json    # rewrite vague feedback into Plus-Delta
vstack-plus-delta compose
vstack-plus-delta schema --target feedback
```

---

## Composition — what to run after Plus-Delta

- **Vague pattern** → [Glaser Conversation](../21-glaser-conversation-steering/WALKTHROUGH.md)
  — vague feedback is usually Level-I when Level-III is needed.
- **Sandwich pattern** → [HEXACO A-factor](../../module-1-individual/07-hexaco-personality/WALKTHROUGH.md)
  — over-agreeableness is the upstream cause.
- **Delta-only pattern** → [Trust Triangle Empathy leg](../18-trust-triangle-audit/WALKTHROUGH.md).
- **Multi-delta unprioritized** → [SMART Goal Generator](../24-smart-goal-generator/WALKTHROUGH.md)
  to give each delta a measurable target.

---

## Async fan-out

```python
import asyncio
from vstack.plus_delta import PlusDeltaFeedbackDetectorAsync
from vstack.aar.clients import AsyncStubClient

async def fan_out(traces):
    detector = PlusDeltaFeedbackDetectorAsync(AsyncStubClient(), mode="standard")
    return await asyncio.gather(*(detector.run(t) for t in traces))
```

---

## Anti-patterns and FAQ

**"My agent receives Plus-Delta feedback but still doesn't change."**

Check whether the delta names a *behaviour* or an *outcome*.
Behaviours change; outcomes don't. "DELTA: be more careful" doesn't
specify a behaviour. "DELTA: run the type check before claiming
done" does.

**"Can I rewrite feedback automatically?"**

Yes — the `rewrite` CLI sub-command takes prose feedback and produces
a Plus-Delta version. Wire it as a middleware on agent-to-agent
feedback channels.

**"Forensic mode cost?"**

Three LLM calls per trace; typical $0.35 on a flagship model.

---

## Reference

- Source: [`module-2-team/23-plus-delta-feedback-format/lib/`](./lib/)
- Schema: [`lib/schema.py`](./lib/schema.py)
- Prompts: [`lib/prompts.py`](./lib/prompts.py)
- Demo: [`demo/`](./demo/)
- Tests: [`tests/`](./tests/)
- Essay: [`essay.md`](./essay.md)
- Pattern README: [`README.md`](./README.md)
