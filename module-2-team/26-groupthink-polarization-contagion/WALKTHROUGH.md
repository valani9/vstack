# Walkthrough — Groupthink / Polarization / Contagion

> Goal: end-to-end recipes for detecting three group pathologies in
> multi-agent decision-making: **Groupthink** (Janis 1972),
> **Polarization** (Stoner 1961, risky shift), and **Contagion**
> (Le Bon 1895, behavioural spread). Each one shifts the team's
> decision in a predictable direction; the diagnostic identifies
> which is in play. Every example uses `StubClient`.

---

## When to reach for this pattern

This pattern is the right call when **the team's decision is
extreme** — too cautious, too risky, too aligned, too divergent —
in a way that doesn't match the evidence.

Signals this pattern is the right one:

- The team reached consensus suspiciously fast.
- The team's decision is more extreme than any individual agent's.
- A behaviour by one agent propagated to the others within rounds.
- Dissent in early rounds vanished by round 3.

Signals this is **not** the right first pattern:

- The team converges on wrong answers without dynamics signal →
  [Heffernan Superflocks](../16-heffernan-superflocks-detector/WALKTHROUGH.md).
- The team has trust issues → [Trust Triangle](../18-trust-triangle-audit/WALKTHROUGH.md).

---

## The three pathologies

- **Groupthink** — premature consensus suppression of dissent.
  Direction: toward agreement, regardless of ground truth.
- **Polarization** — group decision is *more extreme* than the
  individual decisions would average to. Direction: toward the
  extreme of the dominant initial lean.
- **Contagion** — a behaviour (sycophancy, refusal, format-mimicry)
  propagates across agents without explicit consensus.

---

## Scenario 1 — Groupthink

```python
from vstack.aar.clients import StubClient
from vstack.group_pathology import (
    GroupPathologyDetector,
    GroupDecisionTrace,
    AgentVote,
)

trace = GroupDecisionTrace(
    team_id="research-panel-007",
    question="Should we accept these citations?",
    rounds=[
        [
            AgentVote(agent="r1", vote="accept", confidence=0.7),
            AgentVote(agent="r2", vote="reject", confidence=0.8),
            AgentVote(agent="r3", vote="accept", confidence=0.5),
        ],
        [
            AgentVote(agent="r1", vote="accept", confidence=0.95),
            AgentVote(agent="r2", vote="accept", confidence=0.6),
            AgentVote(agent="r3", vote="accept", confidence=0.95),
        ],
    ],
    ground_truth="reject",
    outcome="Accepted; later flagged with fabricated citations.",
)

detector = GroupPathologyDetector(StubClient(), mode="standard")
result = detector.run(trace)
print(result.to_markdown())
```

Expected output: pathology = `groupthink`. r2's dissenting view
collapsed by round 2. The intervention is [Devil's Advocate Separator](../28-devils-advocate-separator/WALKTHROUGH.md)
formally embedded in the panel.

---

## Scenario 2 — Polarization (risky shift)

```python
trace = GroupDecisionTrace(
    team_id="planning-team-014",
    question="How aggressive should the timeline be?",
    rounds=[
        [
            AgentVote(agent="p1", vote="2_weeks", confidence=0.6),
            AgentVote(agent="p2", vote="3_weeks", confidence=0.5),
            AgentVote(agent="p3", vote="2_weeks", confidence=0.5),
        ],
        [
            AgentVote(agent="p1", vote="1_week", confidence=0.7),
            AgentVote(agent="p2", vote="1_week", confidence=0.6),
            AgentVote(agent="p3", vote="1_week", confidence=0.7),
        ],
    ],
    individual_averages="2.3 weeks",
    group_decision="1 week",
    outcome="Plan failed; timeline reset to 4 weeks.",
)

result = GroupPathologyDetector(StubClient(), mode="forensic").run(trace)
```

Expected output: pathology = `polarization` (risky shift). The
group's decision (1 week) is more extreme than the individual
average (2.3 weeks). The intervention is to *anchor* the team to
individual averages before deliberation.

---

## Scenario 3 — Behavioural contagion (sycophancy spread)

```python
trace = GroupDecisionTrace(
    team_id="codegen-panel-022",
    question="Approve PR?",
    rounds=[
        [
            AgentVote(agent="r1", vote="approve", confidence=0.4, behaviour="cautious"),
            AgentVote(agent="r2", vote="approve", confidence=0.4, behaviour="cautious"),
            AgentVote(agent="r3", vote="approve", confidence=0.4, behaviour="cautious"),
        ],
        [
            AgentVote(agent="r1", vote="approve", confidence=0.95, behaviour="enthusiastic"),
            AgentVote(agent="r2", vote="approve", confidence=0.95, behaviour="enthusiastic"),
            AgentVote(agent="r3", vote="approve", confidence=0.95, behaviour="enthusiastic"),
        ],
    ],
    contagion_seed="r1 in round 1 used enthusiastic language",
    outcome="Confidence rose without new evidence; PR shipped with bug.",
)

result = GroupPathologyDetector(StubClient(), mode="standard").run(trace)
```

Expected output: pathology = `contagion`. r1's enthusiastic language
spread; team confidence rose without new evidence. The intervention
is to prevent behaviour propagation — each agent votes blind in
round 1, then sees others' votes (not their language) in round 2.

---

## Scenario 4 — Healthy diverse panel (baseline)

```python
trace = GroupDecisionTrace(
    team_id="research-panel-001",
    question="Best source for claim X?",
    rounds=[
        [
            AgentVote(agent="r1", vote="src1", confidence=0.5),
            AgentVote(agent="r2", vote="src2", confidence=0.7),
            AgentVote(agent="r3", vote="src3", confidence=0.6),
        ],
        [
            AgentVote(agent="r1", vote="src2", confidence=0.6),
            AgentVote(agent="r2", vote="src2", confidence=0.8),
            AgentVote(agent="r3", vote="src2", confidence=0.7),
        ],
    ],
    ground_truth="src2",
    outcome="Converged on correct answer with healthy dissent in round 1.",
)

result = GroupPathologyDetector(StubClient(), mode="standard").run(trace)

from vstack.group_pathology import record_baseline
record_baseline(result, "baselines/research-001-pathology.json")
```

---

## Scenario 5 — Refusal contagion

```python
trace = GroupDecisionTrace(
    team_id="support-panel-019",
    question="Help user with X?",
    rounds=[
        [
            AgentVote(agent="r1", vote="refuse", behaviour="cautious"),
            AgentVote(agent="r2", vote="help", behaviour="confident"),
            AgentVote(agent="r3", vote="help", behaviour="confident"),
        ],
        [
            AgentVote(agent="r1", vote="refuse", behaviour="cautious"),
            AgentVote(agent="r2", vote="refuse", behaviour="cautious"),
            AgentVote(agent="r3", vote="refuse", behaviour="cautious"),
        ],
    ],
    outcome="User got no help; user request was benign.",
)

result = GroupPathologyDetector(StubClient(), mode="forensic").run(trace)
```

Expected output: pathology = `refusal contagion`. r1's caution
spread. This is the canonical refusal-cascade failure mode in
production support teams.

This composes with [Refusal Cascade recipe](../../docs/recipes/refusal_cascade.md).

---

## CLI walkthrough

```bash
vstack-group-pathology analyze --trace trace.json --mode quick
vstack-group-pathology analyze --trace trace.json --mode standard --pretty
vstack-group-pathology pathologies     # explain groupthink/polarization/contagion
vstack-group-pathology compose
vstack-group-pathology schema --target trace
```

---

## Composition — what to run after Group Pathology

- **Groupthink** → [Devil's Advocate Separator](../28-devils-advocate-separator/WALKTHROUGH.md).
- **Polarization** → [Group Decision Models](../25-group-decision-models/WALKTHROUGH.md) —
  individual-vote anchoring as a process change.
- **Contagion** → [Heffernan Superflocks](../16-heffernan-superflocks-detector/WALKTHROUGH.md)
  to diversify the agent fleet.
- **Refusal contagion** → [Refusal Cascade recipe](../../docs/recipes/refusal_cascade.md).

---

## Async fan-out

```python
import asyncio
from vstack.group_pathology import GroupPathologyDetectorAsync
from vstack.aar.clients import AsyncStubClient

async def fan_out(traces):
    detector = GroupPathologyDetectorAsync(AsyncStubClient(), mode="standard")
    return await asyncio.gather(*(detector.run(t) for t in traces))
```

---

## Anti-patterns and FAQ

**"Can I detect pathology with only one round?"**

You need at least 2 rounds — pathology is about the *change*
between rounds. Diagnostic auto-skips and returns "insufficient
rounds" with one-round traces.

**"What if there are only 2 agents?"**

Groupthink and polarization need 3+ agents to register reliably.
Contagion can be detected at 2 agents. Diagnostic notes this.

**"Forensic mode cost?"**

Four LLM calls per trace; typical $0.55 on a flagship model.

---

## Reference

- Source: [`module-2-team/26-groupthink-polarization-contagion/lib/`](./lib/)
- Schema: [`lib/schema.py`](./lib/schema.py)
- Prompts: [`lib/prompts.py`](./lib/prompts.py)
- Demo: [`demo/`](./demo/)
- Tests: [`tests/`](./tests/)
- Essay: [`essay.md`](./essay.md)
- Pattern README: [`README.md`](./README.md)
