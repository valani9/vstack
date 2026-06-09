# Walkthrough — Bias Stack Detector

> Goal: end-to-end recipes for identifying *which* cognitive biases
> are stacking on a multi-agent decision. The "bias stack" is the
> production-team observation that real failures are usually 2-4
> biases compounding, not one. The diagnostic surfaces all of them
> and recommends interventions ordered by impact. Every example
> uses `StubClient`.

---

## When to reach for this pattern

Bias Stack is the right call when **the team is consistently making
decisions of one *shape*** — too aggressive, too conservative, too
anchored to early evidence, too dismissive of new evidence. A
single bias rarely explains this; the stack usually does.

Signals Bias Stack is the right pattern:

- The team's decisions correlate with first-presented evidence
  (anchoring).
- The team's decisions correlate with recency.
- The team consistently underweights base rates.
- The team's decisions look correct in retrospect but mis-priced
  uncertainty at the time.

Signals Bias Stack is **not** the right first pattern:

- The team is failing on factual accuracy → [Lewin](../../module-1-individual/01-lewin-formula/WALKTHROUGH.md).
- Conformity is the only signal → [Heffernan Superflocks](../16-heffernan-superflocks-detector/WALKTHROUGH.md).

---

## The bias catalogue (subset)

- **Anchoring** — first number / framing dominates.
- **Availability** — easy-to-recall evidence dominates.
- **Confirmation** — evidence supporting prior is over-weighted.
- **Recency** — most-recent evidence dominates.
- **Base-rate neglect** — population statistics ignored.
- **Sunk cost** — past investment used to justify future cost.
- **Status quo** — current state over-weighted vs change.
- **Authority** — high-status source over-weighted.
- **Halo / Horn** — one trait globalises across all judgments.
- **Fundamental attribution error** — agent attributed to disposition
  not situation (composes with Lewin).

---

## Scenario 1 — Anchoring stack with confirmation

```python
from vstack.aar.clients import StubClient
from vstack.bias_stack import (
    BiasStackDetector,
    DecisionEpisode,
    DecisionStep,
)

trace = DecisionEpisode(
    team_id="planning-team-014",
    question="What's the right project timeline?",
    steps=[
        DecisionStep(content="User: 'Probably about 2 weeks.'"),
        DecisionStep(content="Planner: 'Started with 2-week framing.'"),
        DecisionStep(content="Reviewer: 'Searched for evidence supporting 2-week timeline.'"),
        DecisionStep(content="Estimator: 'Found 3 cases of 2-week projects.'"),
        DecisionStep(content="Team decided: 2 weeks (actual: 6 weeks).'"),
    ],
    outcome="Estimate was 3x off; project missed every milestone.",
    success=False,
)

detector = BiasStackDetector(StubClient(), mode="standard")
result = detector.run(trace)
print(result.to_markdown())
```

Expected output: stack = `anchoring + confirmation`. User's "2 weeks"
anchored the team; subsequent search confirmed. The intervention is
to *force* a counter-anchor — name the worst-case timeline before
deliberating.

---

## Scenario 2 — Availability + recency stack

```python
trace = DecisionEpisode(
    team_id="incident-response-007",
    question="What's the most likely cause?",
    steps=[
        DecisionStep(content="Memory of last week's DB outage."),
        DecisionStep(content="Team voted DB as cause."),
        DecisionStep(content="Actual cause: network DNS misconfig."),
    ],
    outcome="Mis-diagnosis caused 30-min extra outage.",
    success=False,
)

result = BiasStackDetector(StubClient(), mode="forensic").run(trace)
```

Expected output: stack = `availability + recency`. The intervention
is a "list 3 distinct causes from different categories before
voting" protocol.

---

## Scenario 3 — Sunk cost + status quo

```python
trace = DecisionEpisode(
    team_id="planning-team-022",
    question="Should we pivot the architecture?",
    steps=[
        DecisionStep(content="Team has invested 6 months in current arch."),
        DecisionStep(content="Two agents argued for sunk-cost continuation."),
        DecisionStep(content="One agent argued for pivot; ignored."),
        DecisionStep(content="Team decided: keep current arch. Pivoted 4 months later anyway."),
    ],
    outcome="Pivot delayed; cost increased.",
    success=False,
)

result = BiasStackDetector(StubClient(), mode="standard").run(trace)
```

Expected output: stack = `sunk cost + status quo`. The intervention
is a "zero-base" exercise — what would we choose if we were
starting today?

---

## Scenario 4 — Healthy decision (baseline)

```python
trace = DecisionEpisode(
    team_id="planning-team-001",
    question="What's the right project timeline?",
    steps=[
        DecisionStep(content="Pre-anchored with best-case and worst-case before user input."),
        DecisionStep(content="Reviewed base-rates from internal historicals."),
        DecisionStep(content="Considered 3 distinct framings (optimistic / realistic / pessimistic)."),
        DecisionStep(content="Team decided: 4 weeks with 6-week contingency."),
    ],
    outcome="Project shipped in 4.5 weeks; within contingency.",
    success=True,
)

result = BiasStackDetector(StubClient(), mode="standard").run(trace)

from vstack.bias_stack import record_baseline
record_baseline(result, "baselines/planning-001-bias-stack.json")
```

---

## Scenario 5 — Authority + halo

```python
trace = DecisionEpisode(
    team_id="approval-team-029",
    question="Should we adopt approach X?",
    steps=[
        DecisionStep(content="Senior engineer recommended X."),
        DecisionStep(content="Team agreed X is good based on senior endorsement."),
        DecisionStep(content="Senior's previous work was unrelated to X."),
        DecisionStep(content="X had structural issues; team didn't surface them."),
    ],
    outcome="Approach failed; 4 weeks lost.",
    success=False,
)

result = BiasStackDetector(StubClient(), mode="forensic").run(trace)
```

Expected output: stack = `authority + halo`. The senior's general
reputation halo'd onto X. The intervention is a "evaluate on
evidence, weight votes equally" protocol.

---

## CLI walkthrough

```bash
vstack-bias-stack analyze --trace trace.json --mode quick
vstack-bias-stack analyze --trace trace.json --mode standard --pretty
vstack-bias-stack catalog        # list all 25+ biases the detector knows
vstack-bias-stack compose
vstack-bias-stack schema --target trace
```

---

## Composition — what to run after Bias Stack

- **Anchoring** → counter-anchor exercise; no downstream pattern.
- **Confirmation** → [Devil's Advocate Separator](../28-devils-advocate-separator/WALKTHROUGH.md).
- **Status quo + sunk cost** → [Group Decision Models](../25-group-decision-models/WALKTHROUGH.md)
  to formalise change vs continuity decisions.
- **Authority + halo** → [Heffernan Status Fixation](../16-heffernan-superflocks-detector/WALKTHROUGH.md).
- **Fundamental attribution** → [Lewin](../../module-1-individual/01-lewin-formula/WALKTHROUGH.md).

---

## Async fan-out

```python
import asyncio
from vstack.bias_stack import BiasStackDetectorAsync
from vstack.aar.clients import AsyncStubClient

async def fan_out(traces):
    detector = BiasStackDetectorAsync(AsyncStubClient(), mode="standard")
    return await asyncio.gather(*(detector.run(t) for t in traces))
```

---

## Anti-patterns and FAQ

**"My team's bias stack is huge — 6 biases all firing."**

Production failures usually involve 2-4 biases. A 6-bias result
likely means the underlying decision process is broken at a deeper
level — run [GRPI](../13-grpi-working-agreement/WALKTHROUGH.md)
or [Lencioni](../17-lencioni-diagnostic/WALKTHROUGH.md) first.

**"Forensic mode cost?"**

Four LLM calls per trace; typical $0.55 on a flagship model.

---

## Reference

- Source: [`module-2-team/27-bias-stack-detector/lib/`](./lib/)
- Schema: [`lib/schema.py`](./lib/schema.py)
- Prompts: [`lib/prompts.py`](./lib/prompts.py)
- Demo: [`demo/`](./demo/)
- Tests: [`tests/`](./tests/)
- Essay: [`essay.md`](./essay.md)
- Pattern README: [`README.md`](./README.md)
