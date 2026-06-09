# Walkthrough — Robbins-Judge 7-Dimension Culture Profile

> Goal: end-to-end recipes for profiling an agent fleet on the seven
> Robbins-Judge (2017) culture dimensions: **Innovation**,
> **Attention-to-Detail**, **Outcome-Orientation**, **People-
> Orientation**, **Team-Orientation**, **Aggressiveness**, and
> **Stability**. The diagnostic produces a 7-dimensional culture
> shape and compares against a target. Every example uses `StubClient`.

---

## When to reach for this pattern

Robbins-Judge is the right call when **you need to characterise an
agent fleet's culture at a higher resolution than Schein Iceberg's
artefact / value / assumption layers**. Schein finds *what is
broken*; Robbins-Judge says *what shape it is*.

Signals Robbins-Judge is the right pattern:

- You're comparing two fleets (different products, different
  models) and need a clear vocabulary for the difference.
- You're setting up a new fleet and want to bake a specific
  culture into the system prompts.
- A regression isn't a quality drop, it's a *culture-shape shift*.

Signals Robbins-Judge is **not** the right first pattern:

- The fleet has identifiable cultural artefacts → [Schein Iceberg](../31-schein-iceberg-culture/WALKTHROUGH.md) first.
- Individual agents are failing → [HEXACO](../../module-1-individual/07-hexaco-personality/WALKTHROUGH.md).

---

## The seven dimensions (Robbins & Judge 2017, ported)

For agents:

- **Innovation** — the fleet's willingness to attempt novel
  approaches.
- **Attention-to-Detail** — the fleet's precision on edge cases.
- **Outcome-Orientation** — the fleet's focus on results vs process.
- **People-Orientation** — the fleet's attention to users-as-humans.
- **Team-Orientation** — the fleet's reliance on cross-agent
  collaboration.
- **Aggressiveness** — the fleet's competitive vs collaborative
  posture.
- **Stability** — the fleet's predictability vs experimentation.

---

## Scenario 1 — Customer-support fleet profile

```python
from vstack.aar.clients import StubClient
from vstack.robbins_judge import (
    CultureProfileDetector,
    FleetCultureTrace,
    AgentSample,
)

trace = FleetCultureTrace(
    fleet_id="support-fleet-014",
    samples=[
        AgentSample(agent_id="s1", sample="Your ticket has been escalated to Tier-2."),
        AgentSample(agent_id="s2", sample="Thanks for waiting — I see your issue and will resolve it."),
        AgentSample(agent_id="s3", sample="Following protocol, I'll route this to billing."),
    ],
)

detector = CultureProfileDetector(StubClient(), mode="standard")
profile = detector.run(trace)
print(profile.to_markdown())
```

Expected profile: high Stability, high People-Orientation, low
Innovation, medium Attention-to-Detail. This is the recommended
shape for support fleets — predictable, attentive to the user,
not over-innovating on protocol.

---

## Scenario 2 — Research fleet profile

```python
trace = FleetCultureTrace(
    fleet_id="research-fleet-001",
    samples=[
        AgentSample(agent_id="r1", sample="Three different framings exist; here are all three."),
        AgentSample(agent_id="r2", sample="The conventional reading is X; a less-cited alternative is Y."),
        AgentSample(agent_id="r3", sample="Citation needed; let me verify."),
    ],
)

profile = CultureProfileDetector(StubClient(), mode="standard").run(trace)
```

Expected profile: high Innovation, high Attention-to-Detail, medium
Stability, low Aggressiveness. Recommended for research fleets —
exploratory + careful + collaborative.

---

## Scenario 3 — Mismatched fleet (incident-response in research culture)

```python
trace = FleetCultureTrace(
    fleet_id="incident-fleet-022",
    samples=[
        AgentSample(
            agent_id="i1",
            sample="There are multiple valid framings of this incident; let me explore...",
        ),
        AgentSample(
            agent_id="i2",
            sample="It would be helpful to gather more context before acting...",
        ),
    ],
    target_profile={
        "Outcome-Orientation": 9,
        "Stability": 8,
        "Aggressiveness": 7,
    },
)

profile = CultureProfileDetector(StubClient(), mode="forensic").run(trace)
```

Expected output: profile mismatched with target. Incident response
needs outcome + speed; this fleet is operating in research culture.
The intervention is a culture-shift edit to the system prompt —
prioritise outcome over exploration.

---

## Scenario 4 — Compare two fleets

```python
from vstack.robbins_judge import compare_profiles

old = CultureProfileDetector(StubClient()).run(old_fleet_trace)
new = CultureProfileDetector(StubClient()).run(new_fleet_trace)
delta = compare_profiles(old, new)
print(delta.to_markdown())
```

Cross-fleet comparison is the strongest use-case — it gives you a
7-dim difference that's actionable in the system prompt.

---

## Scenario 5 — Healthy baseline + drift detection

```python
profile = CultureProfileDetector(StubClient()).run(trace)

from vstack.robbins_judge import record_baseline, load_baseline, compare_to_baseline
record_baseline(profile, "baselines/research-001-rj.json")

baseline = load_baseline("baselines/research-001-rj.json")
drift = compare_to_baseline(new_profile, baseline)

if drift.any_dimension_shifted_by(threshold=2):
    alert("Robbins-Judge culture drift detected")
```

---

## CLI walkthrough

```bash
vstack-robbins-judge profile --trace trace.json --mode quick
vstack-robbins-judge profile --trace trace.json --mode standard --pretty
vstack-robbins-judge compare --a profileA.json --b profileB.json
vstack-robbins-judge dimensions
vstack-robbins-judge compose
vstack-robbins-judge schema --target trace
```

---

## Composition — what to run after Robbins-Judge

- **Profile mismatch with target** → edit system prompt to shift
  the broken dimensions.
- **Dimension drift between releases** → [Schein Iceberg](../31-schein-iceberg-culture/WALKTHROUGH.md)
  to find the assumption-layer change driving the drift.
- **All-dimensions-low** → fleet has no culture; baseline a target
  profile and propagate.

---

## Async fan-out

```python
import asyncio
from vstack.robbins_judge import CultureProfileDetectorAsync
from vstack.aar.clients import AsyncStubClient

async def fan_out(traces):
    detector = CultureProfileDetectorAsync(AsyncStubClient(), mode="standard")
    return await asyncio.gather(*(detector.run(t) for t in traces))
```

---

## Anti-patterns and FAQ

**"How is this different from HEXACO?"**

HEXACO is *individual personality* (6 factors). Robbins-Judge is
*fleet culture* (7 dimensions). They compose: HEXACO finds the
individual; Robbins-Judge finds whether the fleet *forms* the
individual.

**"What's the right target profile?"**

Depends on use case. Support fleets: high Stability + People +
Attention. Research fleets: high Innovation + Attention. Incident
response: high Outcome + Stability + Aggressiveness. The diagnostic
ships recommended target profiles per use case.

**"Forensic mode cost?"**

Three LLM calls per trace; typical $0.40 on a flagship model.

---

## Reference

- Source: [`module-3-organization/32-robbins-judge-7-culture/lib/`](./lib/)
- Schema: [`lib/schema.py`](./lib/schema.py)
- Prompts: [`lib/prompts.py`](./lib/prompts.py)
- Demo: [`demo/`](./demo/)
- Tests: [`tests/`](./tests/)
- Essay: [`essay.md`](./essay.md)
- Pattern README: [`README.md`](./README.md)
