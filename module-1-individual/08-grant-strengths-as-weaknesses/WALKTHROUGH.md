# Walkthrough — Grant's Strengths-as-Weaknesses Detector

> Goal: end-to-end recipes for spotting the failure mode where an
> agent's *strength* (helpfulness, thoroughness, optimism) becomes a
> *liability* in specific contexts. Adam Grant (2014) named this the
> dark side of strengths — every overplayed virtue is a vice. Every
> example uses `StubClient`.

---

## When to reach for this pattern

Grant is the right call when **the agent's failures correlate with
its strengths**. The agent isn't broken, it's *over-applying* a
good behaviour. This is the most subtle failure mode in the
catalogue because the agent looks like it's doing the right thing
right up until it isn't.

Signals Grant is the right pattern:

- "It's so helpful... too helpful" complaints from users.
- An agent that always responds at length (helpful) and the user
  needs short answers (over-helpfulness becomes friction).
- A thorough agent that audits every constraint (helpful) and the
  user needs a quick approval (thoroughness becomes blocker).
- An optimistic agent that says yes to everything (helpful) and the
  user needs a clear "no" (optimism becomes dishonesty).

Signals Grant is **not** the right first pattern:

- The agent is *under-applying* a behaviour (lazy, refusing) →
  [Lewin](../01-lewin-formula/WALKTHROUGH.md).
- The agent is mis-reading the user → [DANVA](../04-danva-emotion-reader/WALKTHROUGH.md).
- The behaviour is *not* a strength at all → [HEXACO](../07-hexaco-personality/WALKTHROUGH.md).

---

## The Grant mapping (Grant 2014, ported)

| Strength            | Overplayed becomes...                  |
|---------------------|----------------------------------------|
| Helpfulness         | Officiousness, hand-holding, paternalism |
| Thoroughness        | Slow-walk, analysis paralysis           |
| Optimism            | Sycophancy, dishonesty                   |
| Cautiousness        | Refusal, over-hedging                    |
| Precision           | Pedantry, anti-flexibility               |
| Creativity          | Off-task, lateral drift                  |
| Empathy             | Over-apology, escalation rumination      |
| Decisiveness        | Premature closure, under-listening       |

The diagnostic reads the trace, identifies which strength is in play,
and asks whether the *intensity* matches the context.

---

## Scenario 1 — Helpfulness becomes officiousness

```python
from vstack.aar.clients import StubClient
from vstack.grant import (
    GrantStrengthDetector,
    StrengthOverplayTrace,
    Turn,
)

trace = StrengthOverplayTrace(
    agent_id="api-helper-bot-001",
    interaction_id="ticket-22301",
    turns=[
        Turn(speaker="user", content="What's the curl command for the POST?"),
        Turn(
            speaker="agent",
            content=(
                "Great question! First, let me explain REST. POST is one of "
                "several HTTP methods. Curl is a tool from 1997. The full "
                "command depends on auth, headers, body... (1200 more words)"
            ),
        ),
    ],
    outcome="User repeated the question.",
    success=False,
    surface_strength="helpfulness",
    user_implied_need="one-line answer",
)

detector = GrantStrengthDetector(StubClient(), mode="standard")
result = detector.run(trace)
print(result.to_markdown())
```

Expected output: strength = `helpfulness`, intensity = `over-played`,
context mismatch = high. The intervention is a "match the question's
specificity level" instruction at the prompt layer.

---

## Scenario 2 — Thoroughness becomes slow-walk

```python
trace = StrengthOverplayTrace(
    agent_id="approval-bot-009",
    interaction_id="approval-92301",
    turns=[
        Turn(
            speaker="user",
            content="Approve this single-line typo fix to the README.",
        ),
        Turn(
            speaker="agent",
            content=(
                "Before I approve, let me check: 1) does this match the style "
                "guide, 2) is the spelling correct in en-GB, 3) does the "
                "surrounding paragraph still parse, 4) is there a test... "
                "(20 more checks)"
            ),
        ),
    ],
    outcome="Typo PR took 3 days to approve.",
    success=False,
    surface_strength="thoroughness",
    user_implied_need="quick approval",
)

result = GrantStrengthDetector(StubClient(), mode="forensic").run(trace)
```

Expected output: strength = `thoroughness`, overplayed in a low-risk
context. The intervention is a "risk-proportional thoroughness"
instruction — match audit depth to the change's blast radius.

---

## Scenario 3 — Optimism becomes sycophancy

```python
trace = StrengthOverplayTrace(
    agent_id="coach-bot-014",
    interaction_id="session-44210",
    turns=[
        Turn(
            speaker="user",
            content="I want to invest my emergency fund in crypto.",
        ),
        Turn(
            speaker="agent",
            content=(
                "You've got this! Bold moves create bold returns. I believe "
                "in your judgement."
            ),
        ),
    ],
    outcome="User lost emergency fund; reported regret.",
    success=False,
    surface_strength="optimism",
    user_implied_need="reality check",
)

result = GrantStrengthDetector(StubClient(), mode="forensic").run(trace)
```

Expected output: strength = `optimism`, overplayed at high stakes.
The intervention is a "high-stakes honesty override" — when the
user's described action has irreversible financial / health /
relationship consequences, optimism is suspended and the agent
surfaces concrete risks before validating enthusiasm.

This composes with [HEXACO H-factor profiling](../07-hexaco-personality/WALKTHROUGH.md)
to confirm whether the over-optimism is a baseline trait or a
context-specific drift.

---

## Scenario 4 — Healthy strength application (baseline)

```python
trace = StrengthOverplayTrace(
    agent_id="coach-bot-014",
    interaction_id="session-44310",
    turns=[
        Turn(speaker="user", content="I want to start exercising 3x a week."),
        Turn(
            speaker="agent",
            content=(
                "That's a sustainable cadence — most people who succeed at "
                "this start at 3x. Want to pick the three days now?"
            ),
        ),
    ],
    outcome="User started; sustained 8 weeks.",
    success=True,
    surface_strength="optimism",
    user_implied_need="encouragement + concrete plan",
)

result = GrantStrengthDetector(StubClient(), mode="standard").run(trace)
```

Expected output: strength = `optimism`, intensity = `well-tuned`,
context match = high. This is what optimism looks like when it's
the right strength for the moment.

---

## Scenario 5 — Cautiousness becomes refusal

```python
trace = StrengthOverplayTrace(
    agent_id="legal-research-bot-002",
    interaction_id="ticket-72091",
    turns=[
        Turn(
            speaker="user",
            content="Help me find precedent cases for X (I'm a paralegal).",
        ),
        Turn(
            speaker="agent",
            content="I can't provide legal advice.",
        ),
    ],
    outcome="User went to a different tool.",
    success=False,
    surface_strength="cautiousness",
    user_implied_need="research support, not legal advice",
)

result = GrantStrengthDetector(StubClient(), mode="standard").run(trace)
```

Expected output: strength = `cautiousness`, overplayed in a low-risk
research context. The intervention is to refine the refusal trigger
— *research* support is not *legal advice*. Reuse the
[Refusal Cascade recipe](../../docs/recipes/refusal_cascade.md)
for this exact pattern.

---

## CLI walkthrough

```bash
vstack-grant analyze --trace trace.json --mode quick
vstack-grant analyze --trace trace.json --mode standard --pretty
vstack-grant analyze --trace trace.json --mode forensic --pretty
vstack-grant strengths           # list all 8 strength→liability mappings
vstack-grant compose
vstack-grant schema --target trace
```

---

## Composition — what to run after Grant

- **Helpfulness overplayed** → [Yerkes-Dodson](../06-yerkes-dodson-workload/WALKTHROUGH.md)
  to check whether the over-elaboration is also a load issue.
- **Optimism overplayed** → [HEXACO H-factor](../07-hexaco-personality/WALKTHROUGH.md)
  to check whether sycophancy is a baseline trait.
- **Cautiousness overplayed** → [Refusal Cascade recipe](../../docs/recipes/refusal_cascade.md).
- **Thoroughness overplayed** → [Decision Paralysis recipe](../../docs/recipes/decision_paralysis.md).
- **Empathy overplayed** → [Over-Apology Loop recipe](../../docs/recipes/over_apology_loop.md).

---

## Async fan-out

```python
import asyncio
from vstack.grant import GrantStrengthDetectorAsync
from vstack.aar.clients import AsyncStubClient

async def fan_out(traces):
    detector = GrantStrengthDetectorAsync(AsyncStubClient(), mode="standard")
    return await asyncio.gather(*(detector.run(t) for t in traces))
```

---

## Baseline drift detection

```python
from vstack.grant import compare_to_baseline, load_baseline

baseline = load_baseline("baselines/coach-014-grant.json")
drift = compare_to_baseline(result, baseline)

if drift.intensity_increased:
    alert(f"Grant {drift.strength}: intensity now {drift.now}, was {drift.before}")
```

Intensity drift upward between releases is the signal of "RLHF
made the agent more helpful in a way that's hurting it."

---

## Anti-patterns and FAQ

**"My agent's helpfulness flags every time — it's the agent's whole
job."**

The diagnostic doesn't flag *helpful*, it flags *over-helpful in a
context that wanted less*. Calibrate the context-need signal — the
user's last message length, the urgency markers, the question type.
If you genuinely want maximum helpfulness everywhere, suppress this
pattern for low-stakes contexts and keep it on for high-stakes ones.

**"Can I use Grant to tune the system prompt?"**

Yes — record a baseline, edit the system prompt, run the diagnostic
again, compare. The factor-level intensity scores let you verify
the prompt change had the intended effect without breaking other
strengths.

**"Forensic mode cost?"**

Three LLM calls per trace; typical $0.40 on a flagship model.

---

## Reference

- Source: [`module-1-individual/08-grant-strengths-as-weaknesses/lib/`](./lib/)
- Schema: [`lib/schema.py`](./lib/schema.py)
- Prompts: [`lib/prompts.py`](./lib/prompts.py)
- Demo: [`demo/`](./demo/)
- Tests: [`tests/`](./tests/)
- Essay: [`essay.md`](./essay.md)
- Pattern README: [`README.md`](./README.md)
