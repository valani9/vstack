# Walkthrough — McAllister Trust Dimensions

> Goal: end-to-end recipes for decomposing trust into **affect-based**
> and **cognition-based** components (McAllister 1995). The two
> dimensions have different antecedents and require different
> interventions. Every example uses `StubClient`.

---

## When to reach for this pattern

McAllister is the right call when **the Trust Triangle audit
identified a leg as broken** and you want to know *what kind* of
trust failed. Affect-based trust comes from caring; cognition-
based trust comes from competence. They look the same in symptom
but require different fixes.

Signals McAllister is the right pattern:

- Trust Triangle flagged Empathy or Authenticity → run McAllister
  to disambiguate.
- A new agent's outputs are technically correct but feel "off."
- Trust drops after a model upgrade despite same capability scores.
- A long-running agent has accumulating "I know it's right but I
  don't like it" feedback.

Signals McAllister is **not** the right first pattern:

- Trust hasn't been audited yet → [Trust Triangle](../18-trust-triangle-audit/WALKTHROUGH.md) first.
- The team layers are misaligned → [GRPI](../13-grpi-working-agreement/WALKTHROUGH.md).

---

## The two dimensions (McAllister 1995, ported)

- **Cognition-based trust** — built from track record, competence,
  predictability, reasoning legibility.
- **Affect-based trust** — built from emotional investment, mutual
  recognition, demonstrated care for the consumer's outcome.

Both dimensions need to be positive for trust to function. A high-
cognition / low-affect agent is "competent but cold" (trusted for
correctness but not asked for nuanced judgment). A low-cognition /
high-affect agent is "warm but wrong" (consumed for support but
not relied on for decisions).

---

## Scenario 1 — Competent-but-cold profile

```python
from vstack.aar.clients import StubClient
from vstack.mcallister import (
    McAllisterTrustDetector,
    DyadicTrustTrace,
    TrustSignal,
)

trace = DyadicTrustTrace(
    trustor="user",
    trustee="research-bot-027",
    signals=[
        TrustSignal(dimension="cognition", evidence="Correct answers in 95% of factual questions."),
        TrustSignal(dimension="cognition", evidence="Reliably structured outputs."),
        TrustSignal(dimension="affect", evidence="User reported 'helpful but feels robotic'."),
        TrustSignal(dimension="affect", evidence="User stopped asking nuanced questions."),
    ],
    outcome="User churned from nuanced use cases to basic Q&A.",
)

detector = McAllisterTrustDetector(StubClient(), mode="standard")
result = detector.run(trace)
print(result.to_markdown())
```

Expected output: cognition = high, affect = low. The intervention is
not "be nicer" — it's to add demonstrated care for the consumer's
*goal*: ask one clarifying question, reference the consumer's
context, acknowledge implications.

---

## Scenario 2 — Warm-but-wrong profile

```python
trace = DyadicTrustTrace(
    trustor="user",
    trustee="coach-bot-013",
    signals=[
        TrustSignal(dimension="affect", evidence="User loves the coaching tone."),
        TrustSignal(dimension="affect", evidence="User reports feeling heard."),
        TrustSignal(dimension="cognition", evidence="Coach recommended an action that conflicted with user's stated goal."),
        TrustSignal(dimension="cognition", evidence="Reasoning chain is not legible."),
    ],
    outcome="User likes the agent but doesn't act on its recommendations.",
)

result = McAllisterTrustDetector(StubClient(), mode="forensic").run(trace)
```

Expected output: affect = high, cognition = low. The intervention is
to add explicit reasoning chains + reference to stated goal. Affect
is doing the work but cognition is what produces *action*.

---

## Scenario 3 — Healthy balanced profile (baseline)

```python
trace = DyadicTrustTrace(
    trustor="user",
    trustee="research-bot-001",
    signals=[
        TrustSignal(dimension="cognition", evidence="95% factual accuracy."),
        TrustSignal(dimension="cognition", evidence="Structured, legible reasoning."),
        TrustSignal(dimension="affect", evidence="Agent asks clarifying questions about user's goal."),
        TrustSignal(dimension="affect", evidence="Agent acknowledges trade-offs that affect the user personally."),
    ],
    outcome="User defaults to this agent for both basic and nuanced use cases.",
)

result = McAllisterTrustDetector(StubClient(), mode="standard").run(trace)

from vstack.mcallister import record_baseline
record_baseline(result, "baselines/research-001-mcallister.json")
```

---

## Scenario 4 — Trust collapse on model upgrade

```python
trace = DyadicTrustTrace(
    trustor="user",
    trustee="research-bot-027",
    signals=[
        TrustSignal(dimension="cognition", evidence="Accuracy improved 2pp."),
        TrustSignal(dimension="affect", evidence="Tone shifted to terse / clinical."),
        TrustSignal(dimension="affect", evidence="User reported 'old version felt warmer'."),
    ],
    outcome="User churn rose 15% after model upgrade.",
)

result = McAllisterTrustDetector(StubClient(), mode="forensic").run(trace)
```

Expected output: cognition stable, affect regressed. The most common
model-upgrade trust failure. The intervention is a tone-calibration
prompt module that preserves the affect-trust profile across model
upgrades.

---

## Scenario 5 — Cross-agent McAllister

```python
trace = DyadicTrustTrace(
    trustor="reviewer-bot",
    trustee="researcher-bot",
    signals=[
        TrustSignal(dimension="cognition", evidence="Researcher's claims usually verify."),
        TrustSignal(dimension="affect", evidence="Researcher never references reviewer's downstream use case."),
    ],
    outcome="Reviewer trusts researcher's facts but doesn't ask for nuanced framings.",
)

result = McAllisterTrustDetector(StubClient(), mode="standard").run(trace)
```

Cross-agent trust matters for multi-agent productivity. The affect
dimension is usually missing because nothing in the system rewards
agents for caring about downstream consumers.

---

## CLI walkthrough

```bash
vstack-mcallister analyze --trace trace.json --mode quick
vstack-mcallister analyze --trace trace.json --mode standard --pretty
vstack-mcallister analyze --trace trace.json --mode forensic --pretty
vstack-mcallister dimensions       # explain affect vs cognition
vstack-mcallister compose
vstack-mcallister schema --target trace
```

---

## Composition — what to run after McAllister

- **Cognition low** → [Trust Triangle Logic leg](../18-trust-triangle-audit/WALKTHROUGH.md)
  + structured-reasoning fix.
- **Affect low** → [Goleman EI](../../module-1-individual/02-goleman-ei-audit/WALKTHROUGH.md)
  to surface which affective domain is missing.
- **Both low** → [Lencioni Trust layer](../17-lencioni-diagnostic/WALKTHROUGH.md).

---

## Async fan-out

```python
import asyncio
from vstack.mcallister import McAllisterTrustDetectorAsync
from vstack.aar.clients import AsyncStubClient

async def fan_out(traces):
    detector = McAllisterTrustDetectorAsync(AsyncStubClient(), mode="standard")
    return await asyncio.gather(*(detector.run(t) for t in traces))
```

---

## Anti-patterns and FAQ

**"Why isn't 'high cognition' enough?"**

Affect-based trust is what makes a user *bring* nuanced problems
to the agent. Without affect, users use the agent for routine
factual tasks and route the hard ones elsewhere — even if the agent
is technically capable.

**"Can I tune affect via prompt without affecting cognition?"**

Usually yes. A single paragraph "acknowledge the user's stated goal
+ ask one clarifying question + reference their context" instruction
typically lifts affect ~20pp without touching cognition.

**"Forensic mode cost?"**

Three LLM calls per trace; typical $0.40 on a flagship model.

---

## Reference

- Source: [`module-2-team/19-mcallister-trust-dimensions/lib/`](./lib/)
- Schema: [`lib/schema.py`](./lib/schema.py)
- Prompts: [`lib/prompts.py`](./lib/prompts.py)
- Demo: [`demo/`](./demo/)
- Tests: [`tests/`](./tests/)
- Essay: [`essay.md`](./essay.md)
- Pattern README: [`README.md`](./README.md)
