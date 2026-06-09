# Walkthrough — Lencioni 5 Dysfunctions Diagnostic

> Goal: end-to-end recipes for mapping a multi-agent team's failure
> mode onto Lencioni's (2002) Five Dysfunctions pyramid. The
> dysfunctions cascade — each one enables the next. The diagnostic
> finds the *lowest* dysfunction and tells you which intervention
> unblocks all the others. Every example uses `StubClient`.

---

## When to reach for this pattern

Lencioni is the right call when **the team is failing in a way that
spans multiple dimensions** — trust, conflict, commitment,
accountability, attention to results — and you need to know which
layer to address first.

Signals Lencioni is the right pattern:

- A team is producing low-quality output AND missing deadlines AND
  blaming each other AND nobody's clear on the goal.
- A team has tried four targeted fixes and each one regressed.
- The team's failure pattern resembles a textbook organisational
  pathology more than a technical bug.

Signals Lencioni is **not** the right first pattern:

- The failure is in a single agent → [Lewin](../../module-1-individual/01-lewin-formula/WALKTHROUGH.md).
- The team layers are misaligned at a structural level → [GRPI](../13-grpi-working-agreement/WALKTHROUGH.md).
- Only one dysfunction is in play → see the named pattern (Trust →
  [Trust Triangle](../18-trust-triangle-audit/WALKTHROUGH.md);
  Results → [Process Gain/Loss](../14-process-gain-loss-detector/WALKTHROUGH.md)).

---

## The five dysfunctions (Lencioni 2002, ported)

The pyramid cascades from bottom to top — fix lower levels first.

5. **Inattention to Results** — the team optimises individual agent
   metrics rather than the team's deliverable.
4. **Avoidance of Accountability** — no agent holds another to
   commitments.
3. **Lack of Commitment** — decisions are made but agents don't
   commit to them.
2. **Fear of Conflict** — agents avoid productive disagreement.
1. **Absence of Trust** — agents don't expose their uncertainty or
   mistakes.

---

## Scenario 1 — Trust-layer break (bottom of pyramid)

```python
from vstack.aar.clients import StubClient
from vstack.lencioni import (
    LencioniDysfunctionDetector,
    TeamDysfunctionTrace,
    TeamObservation,
)

trace = TeamDysfunctionTrace(
    team_id="codegen-pipeline-014",
    agents=["planner", "coder", "reviewer"],
    observations=[
        TeamObservation(
            dysfunction_signal="trust",
            evidence="Coder never tells planner when implementation diverges from plan.",
        ),
        TeamObservation(
            dysfunction_signal="trust",
            evidence="Reviewer never asks planner to clarify ambiguities — invents own interpretation.",
        ),
    ],
    outcome="Three weeks of releases drifted from product spec; nobody flagged.",
    success=False,
)

detector = LencioniDysfunctionDetector(StubClient(), mode="standard")
result = detector.run(trace)
print(result.to_markdown())
```

Expected output: lowest dysfunction = `Absence of Trust`. The
intervention is to build *vulnerability-based trust* at the agent
boundary — each agent's prompt explicitly permits "I don't know" and
"I disagree" outputs. This is the only intervention that unblocks
the four upper layers.

---

## Scenario 2 — Conflict-layer break (artificial harmony)

```python
trace = TeamDysfunctionTrace(
    team_id="research-panel-007",
    agents=["researcher-1", "researcher-2", "researcher-3"],
    observations=[
        TeamObservation(
            dysfunction_signal="conflict",
            evidence="All three agents agreed with each other in 100% of rounds.",
        ),
        TeamObservation(
            dysfunction_signal="conflict",
            evidence="No agent challenged a citation that turned out to be fabricated.",
        ),
    ],
    outcome="Survey article published with 3 fabricated citations.",
    success=False,
)

result = LencioniDysfunctionDetector(StubClient(), mode="forensic").run(trace)
```

Expected output: lowest dysfunction = `Fear of Conflict`. The
intervention is to formalise productive disagreement — e.g.
[Devil's Advocate Separator](../28-devils-advocate-separator/WALKTHROUGH.md)
as a structural team role.

---

## Scenario 3 — Commitment-layer break (ambiguous decisions)

```python
trace = TeamDysfunctionTrace(
    team_id="planning-team-022",
    agents=["planner", "estimator", "approver"],
    observations=[
        TeamObservation(
            dysfunction_signal="commitment",
            evidence="Approver accepted the plan; estimator continued estimating against an older version.",
        ),
        TeamObservation(
            dysfunction_signal="commitment",
            evidence="Planner kept revising after approval without flagging.",
        ),
    ],
    outcome="Plan executed with three different agents on three different versions.",
    success=False,
)

result = LencioniDysfunctionDetector(StubClient(), mode="standard").run(trace)
```

Expected output: lowest dysfunction = `Lack of Commitment`. The
intervention is to formalise decision finality — a decision is a
versioned artifact that all agents reference; revisions require
explicit re-commitment from all agents.

---

## Scenario 4 — Accountability-layer break

```python
trace = TeamDysfunctionTrace(
    team_id="codegen-pipeline-029",
    agents=["coder-1", "coder-2", "coder-3"],
    observations=[
        TeamObservation(
            dysfunction_signal="accountability",
            evidence="Coder-1 missed deadline; coder-2 and coder-3 didn't ask why.",
        ),
        TeamObservation(
            dysfunction_signal="accountability",
            evidence="Output quality dropped 30% over 2 weeks; no agent raised it.",
        ),
    ],
    outcome="Regression compounded for 2 weeks before orchestrator caught it.",
    success=False,
)

result = LencioniDysfunctionDetector(StubClient(), mode="standard").run(trace)
```

Expected output: lowest dysfunction = `Avoidance of Accountability`.
The intervention is to add explicit peer-accountability checkpoints
— each agent reviews the others' output against the shared goal.

---

## Scenario 5 — Healthy team (baseline)

```python
trace = TeamDysfunctionTrace(
    team_id="research-pipeline-001",
    agents=["researcher", "writer", "fact-checker"],
    observations=[
        TeamObservation(
            dysfunction_signal="trust",
            evidence="All three agents flag uncertainty explicitly.",
            healthy=True,
        ),
        TeamObservation(
            dysfunction_signal="conflict",
            evidence="Fact-checker reliably challenges researcher's citations.",
            healthy=True,
        ),
        TeamObservation(
            dysfunction_signal="commitment",
            evidence="Each agent references the versioned shared goal.",
            healthy=True,
        ),
        TeamObservation(
            dysfunction_signal="accountability",
            evidence="Reviewer surfaces missed deadlines proactively.",
            healthy=True,
        ),
        TeamObservation(
            dysfunction_signal="results",
            evidence="Each agent reports a results-aligned metric, not its own metric.",
            healthy=True,
        ),
    ],
    outcome="Team delivered on time at quality.",
    success=True,
)

result = LencioniDysfunctionDetector(StubClient(), mode="standard").run(trace)

from vstack.lencioni import record_baseline
record_baseline(result, "baselines/research-001-lencioni.json")
```

---

## CLI walkthrough

```bash
vstack-lencioni analyze --trace trace.json --mode quick
vstack-lencioni analyze --trace trace.json --mode standard --pretty
vstack-lencioni analyze --trace trace.json --mode forensic --pretty
vstack-lencioni pyramid       # render the 5-layer pyramid
vstack-lencioni compose
vstack-lencioni schema --target trace
```

---

## Composition — what to run after Lencioni

The cascade rule says fix lowest dysfunction first; the diagnostic
recommends the next pattern based on the lowest broken layer.

- **Trust broken** → [Trust Triangle](../18-trust-triangle-audit/WALKTHROUGH.md)
  to find which trust dimension regressed.
- **Conflict broken** → [Devil's Advocate Separator](../28-devils-advocate-separator/WALKTHROUGH.md)
  to formalise productive disagreement.
- **Commitment broken** → [SMART Goal Generator](../24-smart-goal-generator/WALKTHROUGH.md)
  to add commitment-ready goal statements.
- **Accountability broken** → [Plus-Delta Feedback](../23-plus-delta-feedback-format/WALKTHROUGH.md)
  for peer-accountability checkpoints.
- **Results broken** → [Process Gain/Loss](../14-process-gain-loss-detector/WALKTHROUGH.md)
  to refocus on team output.

---

## Async fan-out

```python
import asyncio
from vstack.lencioni import LencioniDysfunctionDetectorAsync
from vstack.aar.clients import AsyncStubClient

async def fan_out(traces):
    detector = LencioniDysfunctionDetectorAsync(AsyncStubClient(), mode="standard")
    return await asyncio.gather(*(detector.run(t) for t in traces))
```

---

## Anti-patterns and FAQ

**"Lencioni always flags Trust. Is the diagnostic biased?"**

Trust is the foundation; almost every other dysfunction has a
trust-shaped root. The diagnostic is doing its job. The
intervention — vulnerability-based trust prompts — is cheap, so
just apply it and re-run.

**"How is this different from GRPI?"**

GRPI is about *what the team is doing*; Lencioni is about *how the
team is being*. They compose: GRPI says "the team isn't doing
their roles right"; Lencioni says "the team isn't trusting each
other enough to even disagree about the roles." Run GRPI first for
structural failures, Lencioni for behavioural ones.

**"Forensic mode cost?"**

Four LLM calls per trace; typical $0.55 on a flagship model.

---

## Reference

- Source: [`module-2-team/17-lencioni-diagnostic/lib/`](./lib/)
- Schema: [`lib/schema.py`](./lib/schema.py)
- Prompts: [`lib/prompts.py`](./lib/prompts.py)
- Demo: [`demo/`](./demo/)
- Tests: [`tests/`](./tests/)
- Essay: [`essay.md`](./essay.md)
- Pattern README: [`README.md`](./README.md)
