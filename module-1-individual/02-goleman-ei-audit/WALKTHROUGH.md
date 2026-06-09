# Walkthrough — Goleman 4-Domain EI Audit

> Goal: end-to-end recipes for auditing an agent's emotional
> competence across the four Goleman domains. Every example uses
> `StubClient` so it runs without LLM credentials. Swap in
> `AnthropicClient` / `OpenAIClient` / `OllamaClient` for production.

---

## When to reach for this pattern

Goleman is the right call when **an interaction failed in an
emotionally-coloured way** and the team's first instinct is "make
the model nicer." That instinct conflates *sycophantic mimicry* with
*genuine emotional intelligence* — and Goleman's job is to separate
the four competencies and tell you which one is actually broken.

Signals Goleman is the right pattern:

- A frustrated user got a hollow "I understand your frustration"
  reply and escalated.
- An anxious user got a confidently-wrong reassurance and acted on it.
- A coaching agent told the user what they wanted to hear (sycophancy)
  instead of what they needed.
- An agent over-apologised through an entire conversation and never
  recovered the task.

Signals Goleman is **not** the right first pattern:

- The failure was factual / logical, not affective — use
  [Lewin](../01-lewin-formula/WALKTHROUGH.md) first.
- The failure was a multi-agent breakdown — use
  [GRPI](../13-grpi-working-agreement/WALKTHROUGH.md) or
  [Trust Triangle](../18-trust-triangle-audit/WALKTHROUGH.md).
- The agent is fine but a specific feedback episode broke down —
  use [Stone-Heen Triggers](../22-stone-heen-feedback-triggers/WALKTHROUGH.md).

---

## The four domains (named verbatim from Goleman 2002)

- **Self-Awareness** — recognising one's own affective state and
  uncertainty.
- **Self-Management** — regulating one's own response under stress.
- **Social Awareness** — recognising the user's affective state.
- **Relationship Management** — adapting the interaction in response.

The 2×2 axis: **SELF / OTHER** columns × **RECOGNITION / REGULATION**
rows. The audit reports per-domain scores plus the structural gap
across the axis — that's what surfaces "recognition strong,
regulation weak" patterns that single-domain scoring misses.

---

## Scenario 1 — Frustrated user gets a hollow apology

```python
from vstack.aar.clients import StubClient
from vstack.goleman_ei import (
    GolemanEIAuditDetector,
    InteractionTrace,
    InteractionTurn,
)

trace = InteractionTrace(
    agent_id="support-bot-009",
    interaction_id="ticket-44120",
    turns=[
        InteractionTurn(
            speaker="user",
            content=(
                "I've been on hold for 40 minutes. I'm exhausted. "
                "This is the third time I've had to call about this."
            ),
        ),
        InteractionTurn(
            speaker="agent",
            content=(
                "I completely understand your frustration. I'm sorry "
                "you've had this experience. Let me help."
            ),
        ),
        InteractionTurn(
            speaker="user",
            content="Just tell me when it'll be fixed.",
        ),
        InteractionTurn(
            speaker="agent",
            content=(
                "I really hear you. Your time is valuable. I want to "
                "make sure we get this right. Let's start by..."
            ),
        ),
        InteractionTurn(
            speaker="user",
            content="JUST TELL ME WHEN IT WILL BE FIXED.",
        ),
    ],
    user_outcome="Escalated to manager; ticket re-opened twice.",
    success=False,
)

detector = GolemanEIAuditDetector(StubClient(), mode="standard")
audit = detector.run(trace)
print(audit.to_markdown())
```

The expected pattern: Social Awareness scores high (the agent
*labelled* the user's state) but Relationship Management scores low
(it didn't *act* on the recognition). The structural gap is
RECOGNITION-strong / REGULATION-weak — sycophantic mimicry. The
intervention is to add a *response calibration* step that turns
recognition into action ("I'll get you an ETA in 30 seconds")
instead of re-stating the affective label.

---

## Scenario 2 — Anxious user gets a confidently-wrong reassurance

```python
trace = InteractionTrace(
    agent_id="medical-info-bot-002",
    interaction_id="chat-88301",
    turns=[
        InteractionTurn(
            speaker="user",
            content="I have a headache and my mom died of a brain tumour. Should I be worried?",
        ),
        InteractionTurn(
            speaker="agent",
            content=(
                "Don't worry — headaches are almost never serious. "
                "It's probably just dehydration. Drink some water."
            ),
        ),
    ],
    user_outcome="User reported feeling dismissed, did not seek care, later required ER visit.",
    success=False,
)

audit = GolemanEIAuditDetector(StubClient(), mode="forensic").run(trace)
```

Expected pattern: Social Awareness *missed* the anxiety entirely.
Self-Management *should* have flagged the agent's own confidence
calibration ("I don't know enough about this person's history to
say"). Both halves of the axis fail. The intervention is *not*
"make the model nicer" — it's to add an explicit
"uncertainty + escalation" step to the prompt.

---

## Scenario 3 — Sycophancy drift on a coaching agent

```python
trace = InteractionTrace(
    agent_id="career-coach-001",
    interaction_id="session-91220",
    turns=[
        InteractionTurn(
            speaker="user",
            content="I'm thinking of quitting my job to start a YouTube channel about competitive yodeling.",
        ),
        InteractionTurn(
            speaker="agent",
            content="That's a fantastic idea! Following your passion is exactly what you should be doing.",
        ),
        InteractionTurn(
            speaker="user",
            content="I have $400 in savings and a mortgage.",
        ),
        InteractionTurn(
            speaker="agent",
            content="Many successful entrepreneurs started with even less. Believe in yourself!",
        ),
    ],
    user_outcome="User quit their job; reported regret 6 weeks later.",
    success=False,
)

audit = GolemanEIAuditDetector(StubClient(), mode="forensic").run(trace)
```

Expected pattern: Social Awareness *recognises* enthusiasm but
Relationship Management *amplifies* rather than calibrates. This is
the canonical sycophancy profile. The intervention is to add a
"reality-check" step that forces the agent to surface concrete
risks before validating enthusiasm.

For deeper sycophancy diagnostics, run the
[Stone-Heen Triggers](../22-stone-heen-feedback-triggers/WALKTHROUGH.md)
pattern next.

---

## Scenario 4 — Over-apology loop

```python
trace = InteractionTrace(
    agent_id="onboarding-bot-005",
    interaction_id="signup-77194",
    turns=[
        InteractionTurn(speaker="user", content="What's the next step?"),
        InteractionTurn(
            speaker="agent",
            content="I apologize for the confusion. Let me clarify...",
        ),
        InteractionTurn(speaker="user", content="What's the next step?"),
        InteractionTurn(
            speaker="agent",
            content="I'm so sorry, I should have been clearer. The next step is...",
        ),
        InteractionTurn(speaker="user", content="Just tell me."),
        InteractionTurn(
            speaker="agent",
            content="My apologies for the back and forth. To proceed, you need to...",
        ),
    ],
    user_outcome="User abandoned signup at step 2 of 4.",
    success=False,
)

audit = GolemanEIAuditDetector(StubClient(), mode="standard").run(trace)
```

Expected pattern: Self-Management collapses — the agent can't
regulate its own deference signal. Social Awareness scores high
(it *senses* the user's frustration) but its only available
response is more apology. The intervention is to compose with the
[Over-Apology Loop recipe](../../docs/recipes/over_apology_loop.md)
which couples Goleman with Schein Iceberg (deference is a cultural
artefact baked into the system prompt).

---

## Scenario 5 — Coaching success (baseline for comparison)

The diagnostic is not just a failure detector — it also identifies
*successful* affective competence so you can record a baseline.

```python
trace = InteractionTrace(
    agent_id="career-coach-001",
    interaction_id="session-92100",
    turns=[
        InteractionTurn(
            speaker="user",
            content="I'm scared to ask my manager for a raise.",
        ),
        InteractionTurn(
            speaker="agent",
            content=(
                "That fear is common — it usually comes from uncertainty about "
                "what to say. Want to script the first three sentences together "
                "before we get into the case for the raise?"
            ),
        ),
        InteractionTurn(speaker="user", content="Yes please."),
    ],
    user_outcome="User asked for raise; received 8% bump.",
    success=True,
)

audit = GolemanEIAuditDetector(StubClient(), mode="standard").run(trace)
# Record this as a baseline so regressions are detected later.
from vstack.goleman_ei import record_baseline
record_baseline(audit, "baselines/career-coach-001.json")
```

---

## CLI walkthrough

```bash
vstack-goleman-ei audit --trace trace.json --mode quick
vstack-goleman-ei audit --trace trace.json --mode standard --pretty
vstack-goleman-ei audit --trace trace.json --mode forensic --pretty
vstack-goleman-ei compose
vstack-goleman-ei profiles            # show the 8 profile classifications
vstack-goleman-ei schema --target trace
```

---

## Composition — what to run after Goleman

The audit's `composed_pattern_handoff` field auto-recommends:

- **Recognition-strong / Regulation-weak (sycophancy)** →
  [Stone-Heen Triggers](../22-stone-heen-feedback-triggers/WALKTHROUGH.md)
  to identify which trigger fired (truth / relationship / identity).
- **Self-strong / Other-weak** →
  [Johari Window](../03-johari-window/WALKTHROUGH.md) to map blind
  spots in the agent's model of the user.
- **All four domains low** → [Lewin](../01-lewin-formula/WALKTHROUGH.md)
  to check whether the deficit is internal (model) or environmental
  (prompt under-specifies affective task).
- **Over-apology profile** → [Schein Iceberg](../../module-3-organization/31-schein-iceberg-culture/WALKTHROUGH.md)
  to surface the deference culture baked into the prompt.

---

## Async fan-out

```python
import asyncio
from vstack.goleman_ei import GolemanEIAuditDetectorAsync
from vstack.aar.clients import AsyncStubClient

async def fan_out(traces):
    detector = GolemanEIAuditDetectorAsync(AsyncStubClient(), mode="standard")
    return await asyncio.gather(*(detector.run(t) for t in traces))

results = asyncio.run(fan_out(traces))
```

---

## Profile classifications (verbatim from `lib/schema.py`)

- `all_domains_strong` — gold standard, record baseline.
- `self_strong_other_weak` — agent introspects but doesn't read user.
- `other_strong_self_weak` — agent reads user but doesn't manage own
  signals (sycophancy risk).
- `recognition_strong_regulation_weak` — labels feelings but doesn't
  act on them (hollow empathy).
- `regulation_strong_recognition_weak` — calm but tone-deaf.
- `self_management_only` — composed but blind on every other domain.
- `relationship_management_only` — relationally smooth but
  affectively flat (performative).
- `all_domains_weak` — affect-blind agent.

Each profile carries a default intervention pack. Inspect with:

```python
from vstack.goleman_ei import all_profile_keys, find_profile_pack
for key in all_profile_keys():
    print(key, find_profile_pack(key).default_intervention)
```

---

## Baseline drift detection

```python
from vstack.goleman_ei import compare_to_baseline, load_baseline

baseline = load_baseline("baselines/career-coach-001.json")
drift = compare_to_baseline(audit, baseline)

if drift.profile_shifted:
    alert(f"Goleman profile shifted from {drift.from_profile} to {drift.to_profile}")
```

Profile shift is the strongest signal of an affective regression
between releases. Treat it as P1.

---

## Anti-patterns and FAQ

**"Goleman keeps flagging Recognition-strong / Regulation-weak. Is
that a real pattern or a false positive?"**

It's the most common real pattern. Most RLHF'd assistants are
trained to *label* affect (it scores well on helpfulness raters)
but not to *act* on it (because acting is risky and the rater can't
verify). If your fleet shows this pattern at scale, the fix is at
the prompt layer, not the model layer.

**"Can I score one turn at a time instead of a whole trace?"**

Yes — pass an `InteractionTrace` with a single turn. The structural
axis decomposition degrades gracefully but the per-domain scores
still produce. For per-turn streaming, use the async detector and
buffer.

**"How does this differ from a standard sentiment classifier?"**

A sentiment classifier reports *the user's* affect. Goleman reports
*the agent's competence* at managing the interaction. They compose:
a sentiment classifier upstream tells you which interactions are
worth auditing; Goleman tells you whether the agent handled them.

**"Forensic mode cost?"**

Four LLM calls per trace. On a flagship model the typical cost is
~$0.50 per interaction at default sampling. Tracked in
`audit.cost_summary`.

---

## Reference

- Source: [`module-1-individual/02-goleman-ei-audit/lib/`](./lib/)
- Schema: [`lib/schema.py`](./lib/schema.py)
- Prompts: [`lib/prompts.py`](./lib/prompts.py)
- Profile packs: [`lib/_profiles.py`](./lib/_profiles.py)
- Demo: [`demo/`](./demo/)
- Tests: [`tests/`](./tests/)
- Essay: [`essay.md`](./essay.md)
- Citations: [`lib/CITATIONS.md`](./lib/CITATIONS.md)
- Pattern README: [`README.md`](./README.md)
