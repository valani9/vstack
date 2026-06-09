# Walkthrough — Process Gain/Loss Detector

> Goal: end-to-end recipes for measuring whether a multi-agent team
> is producing *more* than the sum of its parts (gain) or *less*
> (loss). Steiner's (1972) process-loss framework named the
> overhead of coordination; the diagnostic decomposes it. Every
> example uses `StubClient`.

---

## When to reach for this pattern

Process Gain/Loss is the right call when **a team's output is
underperforming what each agent could do solo**. The team should
have the *benefit* of parallelism, specialisation, and cross-
checking; if it doesn't, you're paying coordination overhead
without getting the gain.

Signals Process Gain/Loss is the right pattern:

- A 3-agent pipeline takes longer to produce results than one
  agent solo would.
- The team's quality is lower than the strongest individual agent's.
- Adding a sub-agent made the system *worse*.
- A reviewer agent is consistently approving low-quality work
  produced under team pressure.

Signals Process Gain/Loss is **not** the right first pattern:

- The team layers are misaligned → [GRPI](../13-grpi-working-agreement/WALKTHROUGH.md).
- A single agent is bottlenecking → [Bottleneck Orchestrator recipe](../../docs/recipes/bottleneck_orchestrator.md).
- The team's structure itself is wrong → [Span of Control](../../module-3-organization/34-span-of-control/WALKTHROUGH.md).

---

## The two budgets (Steiner 1972, ported)

```
Actual output = Potential output - Process Loss + Process Gain
```

- **Process Loss** sources: coordination overhead, motivation loss,
  information loss at handoff, redundant verification.
- **Process Gain** sources: specialisation, parallelism, cross-
  checking, complementary perspectives.

---

## Scenario 1 — Coordination overhead loss

```python
from vstack.aar.clients import StubClient
from vstack.process_gain_loss import (
    ProcessGainLossDetector,
    TeamProductionTrace,
    AgentContribution,
    HandoffOverhead,
)

trace = TeamProductionTrace(
    team_id="research-pipeline-022",
    agents=[
        AgentContribution(id="researcher", solo_time=120, team_time=180),
        AgentContribution(id="writer", solo_time=180, team_time=300),
        AgentContribution(id="reviewer", solo_time=60, team_time=240),
    ],
    handoff_overheads=[
        HandoffOverhead(from_="researcher", to="writer", overhead_seconds=120),
        HandoffOverhead(from_="writer", to="reviewer", overhead_seconds=240),
        HandoffOverhead(from_="reviewer", to="writer", overhead_seconds=180),
    ],
    outcome="Team total 1140s; solo total 360s; team is 3.2x slower.",
    success=False,
)

detector = ProcessGainLossDetector(StubClient(), mode="standard")
result = detector.run(trace)
print(result.to_markdown())
```

Expected output: process loss source = `coordination overhead`. The
team is paying 540s of handoff overhead on 360s of solo work. The
intervention is to reduce the handoff count (merge researcher and
writer into one agent, OR remove the reviewer→writer feedback loop).

---

## Scenario 2 — Information loss at handoff

```python
trace = TeamProductionTrace(
    team_id="codegen-pipeline-014",
    agents=[
        AgentContribution(id="planner", solo_time=60, team_time=90),
        AgentContribution(id="coder", solo_time=180, team_time=300),
        AgentContribution(id="tester", solo_time=60, team_time=180),
    ],
    handoff_overheads=[
        HandoffOverhead(
            from_="planner", to="coder",
            overhead_seconds=30, information_retained_pct=0.65,
        ),
        HandoffOverhead(
            from_="coder", to="tester",
            overhead_seconds=30, information_retained_pct=0.45,
        ),
    ],
    outcome="Tester missed 55% of context; produced wrong tests.",
    success=False,
)

result = ProcessGainLossDetector(StubClient(), mode="forensic").run(trace)
```

Expected output: process loss source = `information loss`. The
handoffs are short but each one drops a large fraction of context.
The intervention is a structured handoff payload (Pydantic model
covering goal / constraints / decisions / evidence) instead of a
prose summary.

---

## Scenario 3 — Genuine process gain (baseline)

```python
trace = TeamProductionTrace(
    team_id="research-pipeline-001",
    agents=[
        AgentContribution(
            id="researcher", solo_time=300, team_time=180,
            output_quality=8,
        ),
        AgentContribution(
            id="writer", solo_time=180, team_time=120,
            output_quality=9,
        ),
        AgentContribution(
            id="fact-checker", solo_time=120, team_time=60,
            output_quality=10,
        ),
    ],
    handoff_overheads=[
        HandoffOverhead(
            from_="researcher", to="writer",
            overhead_seconds=15, information_retained_pct=0.95,
        ),
        HandoffOverhead(
            from_="writer", to="fact-checker",
            overhead_seconds=15, information_retained_pct=0.95,
        ),
    ],
    outcome=(
        "Team total 390s vs solo total 600s; quality up from 7 (best solo) "
        "to 10 (team)."
    ),
    success=True,
)

result = ProcessGainLossDetector(StubClient(), mode="standard").run(trace)

from vstack.process_gain_loss import record_baseline
record_baseline(result, "baselines/research-001-pgl.json")
```

Expected output: process gain = strongly positive. Three sources of
gain present: specialisation (each agent works in its strength),
parallelism (researcher and writer overlap), cross-checking (fact-
checker catches what the other two miss).

---

## Scenario 4 — Redundant verification (review-the-review pattern)

```python
trace = TeamProductionTrace(
    team_id="codegen-pipeline-029",
    agents=[
        AgentContribution(id="coder", solo_time=180, team_time=180),
        AgentContribution(id="reviewer-1", solo_time=120, team_time=120),
        AgentContribution(id="reviewer-2", solo_time=120, team_time=120),
        AgentContribution(id="reviewer-3", solo_time=120, team_time=120),
    ],
    handoff_overheads=[
        HandoffOverhead(from_="coder", to="reviewer-1", overhead_seconds=30),
        HandoffOverhead(from_="reviewer-1", to="reviewer-2", overhead_seconds=30),
        HandoffOverhead(from_="reviewer-2", to="reviewer-3", overhead_seconds=30),
    ],
    outcome="All three reviewers approved; no review caught a bug the others didn't.",
    success=True,
)

result = ProcessGainLossDetector(StubClient(), mode="standard").run(trace)
```

Expected output: redundant verification loss = high. Three reviewers
are all catching the same bugs; the marginal value of the 2nd and
3rd reviewer is near-zero. The intervention is either to
*differentiate* the reviewers (each gets a distinct lens — security,
performance, style) or to drop the 2nd and 3rd entirely.

---

## Scenario 5 — Negative parallelism (more agents, less throughput)

```python
trace = TeamProductionTrace(
    team_id="research-pipeline-044",
    agents=[
        AgentContribution(id="researcher-1", solo_time=120, team_time=240),
        AgentContribution(id="researcher-2", solo_time=120, team_time=240),
        AgentContribution(id="researcher-3", solo_time=120, team_time=240),
    ],
    handoff_overheads=[
        HandoffOverhead(
            from_="researcher-1", to="researcher-2",
            overhead_seconds=120, redundant_pct=0.7,
        ),
        HandoffOverhead(
            from_="researcher-2", to="researcher-3",
            overhead_seconds=120, redundant_pct=0.7,
        ),
    ],
    outcome="3 researchers, each duplicating ~70% of the others' work.",
    success=False,
)

result = ProcessGainLossDetector(StubClient(), mode="forensic").run(trace)
```

Expected output: process loss source = `negative parallelism`. The
researchers aren't dividing labour — they're all doing the same
work. The intervention is explicit work-partitioning at the
orchestrator level.

---

## CLI walkthrough

```bash
vstack-process-gain-loss analyze --trace trace.json --mode quick
vstack-process-gain-loss analyze --trace trace.json --mode standard --pretty
vstack-process-gain-loss analyze --trace trace.json --mode forensic --pretty
vstack-process-gain-loss sources       # list all gain / loss sources
vstack-process-gain-loss compose
vstack-process-gain-loss schema --target trace
```

---

## Composition — what to run after Process Gain/Loss

- **Coordination overhead loss** → [GRPI](../13-grpi-working-agreement/WALKTHROUGH.md)
  to identify which team layer is causing the overhead.
- **Information loss** → [Cold Handoff recipe](../../docs/recipes/cold_handoff.md).
- **Redundant verification** → [Consensus Dilution recipe](../../docs/recipes/consensus_dilution.md).
- **Negative parallelism** → [Hyper-Specialization recipe](../../docs/recipes/hyper_specialization.md)
  or [Social Loafing](../15-social-loafing-detector/WALKTHROUGH.md).

---

## Async fan-out

```python
import asyncio
from vstack.process_gain_loss import ProcessGainLossDetectorAsync
from vstack.aar.clients import AsyncStubClient

async def fan_out(traces):
    detector = ProcessGainLossDetectorAsync(AsyncStubClient(), mode="standard")
    return await asyncio.gather(*(detector.run(t) for t in traces))
```

---

## Baseline drift detection

```python
from vstack.process_gain_loss import compare_to_baseline, load_baseline

baseline = load_baseline("baselines/research-001-pgl.json")
drift = compare_to_baseline(result, baseline)

if drift.gain_dropped:
    alert(f"Process gain regression: was {drift.was}, now {drift.now}")
```

---

## Anti-patterns and FAQ

**"My team always shows process loss. Should we just go solo?"**

Not yet. Process loss has identifiable sources. Most teams paying
coordination overhead are doing so because the handoff protocol is
informal — fix the handoff and the loss often drops below the gain
from specialisation. Only collapse to solo if all four loss sources
are above the gain *after* a structured intervention.

**"Process gain is hard to verify."**

The diagnostic computes a counterfactual: "what would the best solo
agent produce." If team output > best-solo output, you have gain.
This requires having a baseline of solo performance to compare
against; record one before you build the team.

**"Forensic mode cost?"**

Four LLM calls per trace; typical $0.55 on a flagship model.

---

## Reference

- Source: [`module-2-team/14-process-gain-loss-detector/lib/`](./lib/)
- Schema: [`lib/schema.py`](./lib/schema.py)
- Prompts: [`lib/prompts.py`](./lib/prompts.py)
- Demo: [`demo/`](./demo/)
- Tests: [`tests/`](./tests/)
- Essay: [`essay.md`](./essay.md)
- Pattern README: [`README.md`](./README.md)
