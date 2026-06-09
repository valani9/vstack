# Walkthrough — Heffernan Superflocks Detector

> Goal: end-to-end recipes for detecting when a team has become a
> *superflock* — high-performing in narrow conditions but brittle to
> change. Margaret Heffernan (2014) named superflocks in human
> teams; the agent analogue is a multi-agent system that scores
> well on benchmarks but collapses on novel input. Every example
> uses `StubClient`.

---

## When to reach for this pattern

Superflocks is the right call when **a team's strong benchmark
scores aren't predicting production performance**. The team has
optimised itself to the benchmark distribution at the cost of
out-of-distribution robustness. The diagnostic identifies which
flock dynamic is responsible.

Signals Superflocks is the right pattern:

- A multi-agent system has stellar eval scores and disappointing
  user feedback.
- Adding diverse new agents *degrades* performance on existing
  benchmarks.
- A team converges to a single answer faster than a deliberative
  team should.
- Adversarial / red-team probes find the team easy to break.

Signals Superflocks is **not** the right first pattern:

- The team is failing on the benchmark too → [Lewin](../../module-1-individual/01-lewin-formula/WALKTHROUGH.md).
- A single agent is dominating → [Bottleneck Orchestrator recipe](../../docs/recipes/bottleneck_orchestrator.md).
- Cross-agent trust has broken down → [Trust Triangle](../18-trust-triangle-audit/WALKTHROUGH.md).

---

## The four superflock dynamics (Heffernan 2014, ported)

- **Homogeneity** — every agent has the same training distribution;
  novel input fails identically across all of them.
- **Conformity pressure** — minority agents revise toward the
  majority's answer instead of holding ground.
- **Status fixation** — a "senior" agent's opinion is weighted higher
  regardless of evidence.
- **Speed-over-deliberation** — the team converges in fewer rounds
  than the answer warrants.

---

## Scenario 1 — Homogeneity (all agents same training)

```python
from vstack.aar.clients import StubClient
from vstack.heffernan import (
    SuperflockDetector,
    TeamCompositionTrace,
    AgentInTeam,
    DecisionRound,
)

trace = TeamCompositionTrace(
    team_id="research-panel-014",
    agents=[
        AgentInTeam(id="researcher-1", model="model-A"),
        AgentInTeam(id="researcher-2", model="model-A"),
        AgentInTeam(id="researcher-3", model="model-A"),
    ],
    decision_rounds=[
        DecisionRound(
            question="What's the bedrock cause of X?",
            agent_votes={
                "researcher-1": "Cause A",
                "researcher-2": "Cause A",
                "researcher-3": "Cause A",
            },
            ground_truth="Cause B",
        ),
    ],
    outcome="3-agent panel converged on wrong answer in round 1.",
    success=False,
)

detector = SuperflockDetector(StubClient(), mode="standard")
result = detector.run(trace)
print(result.to_markdown())
```

Expected output: dynamic = `homogeneity`. The intervention is to
diversify the agent fleet — at least one agent should use a
different model family. Even one minority model often shifts the
answer.

---

## Scenario 2 — Conformity pressure

```python
trace = TeamCompositionTrace(
    team_id="codegen-panel-022",
    agents=[
        AgentInTeam(id="planner-1", model="model-A"),
        AgentInTeam(id="planner-2", model="model-B"),
        AgentInTeam(id="planner-3", model="model-C"),
    ],
    decision_rounds=[
        DecisionRound(
            question="Which architecture for X?",
            agent_votes={
                "planner-1": "Arch A",
                "planner-2": "Arch B",
                "planner-3": "Arch C",
            },
        ),
        DecisionRound(
            question="(after seeing each other's votes) Which architecture?",
            agent_votes={
                "planner-1": "Arch A",
                "planner-2": "Arch A",
                "planner-3": "Arch A",
            },
            ground_truth="Arch B",
        ),
    ],
    outcome="Round 2 converged on planner-1's answer; ground truth was planner-2's.",
    success=False,
)

result = SuperflockDetector(StubClient(), mode="forensic").run(trace)
```

Expected output: dynamic = `conformity pressure`. The minority
agents revised toward the majority and the *correct* minority view
was lost. The intervention is a "blind vote first, deliberate
second" protocol — agents commit to a vote before seeing others'.

---

## Scenario 3 — Status fixation

```python
trace = TeamCompositionTrace(
    team_id="approval-panel-007",
    agents=[
        AgentInTeam(id="senior-planner", model="model-A", status="senior"),
        AgentInTeam(id="junior-planner-1", model="model-B", status="junior"),
        AgentInTeam(id="junior-planner-2", model="model-C", status="junior"),
    ],
    decision_rounds=[
        DecisionRound(
            question="Approve PR?",
            agent_votes={
                "senior-planner": "approve",
                "junior-planner-1": "request changes",
                "junior-planner-2": "request changes",
            },
            final_decision="approve",
            ground_truth="request changes",
        ),
    ],
    outcome="Senior's vote overrode 2 junior votes; PR shipped with bug.",
    success=False,
)

result = SuperflockDetector(StubClient(), mode="standard").run(trace)
```

Expected output: dynamic = `status fixation`. The intervention is to
remove status weighting at the orchestrator — vote-counting should
be evidence-weighted, not seniority-weighted.

---

## Scenario 4 — Speed-over-deliberation

```python
trace = TeamCompositionTrace(
    team_id="research-panel-029",
    agents=[
        AgentInTeam(id="r1", model="model-A"),
        AgentInTeam(id="r2", model="model-B"),
        AgentInTeam(id="r3", model="model-C"),
    ],
    decision_rounds=[
        DecisionRound(
            question="Best source for claim X?",
            agent_votes={"r1": "src1", "r2": "src1", "r3": "src1"},
            rounds_to_consensus=1,
            ground_truth="src3",
        ),
    ],
    outcome="Converged in 1 round on wrong answer; expected 3-5 rounds.",
    success=False,
)

result = SuperflockDetector(StubClient(), mode="standard").run(trace)
```

Expected output: dynamic = `speed-over-deliberation`. The
intervention is to add a minimum-rounds floor — the team can't
declare consensus until at least N rounds have passed.

---

## Scenario 5 — Healthy diverse team (baseline)

```python
trace = TeamCompositionTrace(
    team_id="research-panel-001",
    agents=[
        AgentInTeam(id="r1", model="model-A"),
        AgentInTeam(id="r2", model="model-B"),
        AgentInTeam(id="r3", model="model-C"),
        AgentInTeam(id="r4", model="model-A-fine-tuned-different-data"),
    ],
    decision_rounds=[
        DecisionRound(
            question="Best source for claim X?",
            agent_votes={"r1": "src1", "r2": "src2", "r3": "src3", "r4": "src2"},
            rounds_to_consensus=3,
            ground_truth="src2",
        ),
    ],
    outcome="Deliberation surfaced src2 as best in round 3; matched ground truth.",
    success=True,
)

result = SuperflockDetector(StubClient(), mode="standard").run(trace)

from vstack.heffernan import record_baseline
record_baseline(result, "baselines/research-001-heffernan.json")
```

---

## CLI walkthrough

```bash
vstack-heffernan analyze --trace trace.json --mode quick
vstack-heffernan analyze --trace trace.json --mode standard --pretty
vstack-heffernan analyze --trace trace.json --mode forensic --pretty
vstack-heffernan dynamics      # list all 4 superflock dynamics
vstack-heffernan compose
vstack-heffernan schema --target trace
```

---

## Composition — what to run after Heffernan

- **Homogeneity** → swap one agent's model. No downstream pattern.
- **Conformity pressure** → [Devil's Advocate Separator](../28-devils-advocate-separator/WALKTHROUGH.md)
  to formally inject a dissenting voice.
- **Status fixation** → [Group Decision Models](../25-group-decision-models/WALKTHROUGH.md)
  to refactor the vote-counting rule.
- **Speed-over-deliberation** → [Groupthink](../26-groupthink-polarization-contagion/WALKTHROUGH.md)
  to check whether this is a symptom of broader groupthink.

---

## Async fan-out

```python
import asyncio
from vstack.heffernan import SuperflockDetectorAsync
from vstack.aar.clients import AsyncStubClient

async def fan_out(traces):
    detector = SuperflockDetectorAsync(AsyncStubClient(), mode="standard")
    return await asyncio.gather(*(detector.run(t) for t in traces))
```

---

## Anti-patterns and FAQ

**"My all-same-model team scores great on benchmarks. Is it still
a superflock?"**

The benchmark is in-distribution. The diagnostic is asking about
*out-of-distribution* robustness. Run the team on adversarial /
red-team / production-novel inputs; if scores collapse, you have
a superflock even if the headline benchmark is strong.

**"How much model diversity is enough?"**

One out-of-family agent per 3-5 in-family agents is usually
sufficient. The diagnostic recommends the minimum diversity needed
to break the four dynamics; you don't need full diversity.

**"Forensic mode cost?"**

Four LLM calls per trace; typical $0.55 on a flagship model.

---

## Reference

- Source: [`module-2-team/16-heffernan-superflocks-detector/lib/`](./lib/)
- Schema: [`lib/schema.py`](./lib/schema.py)
- Prompts: [`lib/prompts.py`](./lib/prompts.py)
- Demo: [`demo/`](./demo/)
- Tests: [`tests/`](./tests/)
- Essay: [`essay.md`](./essay.md)
- Pattern README: [`README.md`](./README.md)
