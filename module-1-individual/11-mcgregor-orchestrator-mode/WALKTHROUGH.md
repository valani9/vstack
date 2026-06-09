# Walkthrough — McGregor Orchestrator Mode (Theory X vs Theory Y)

> Goal: end-to-end recipes for detecting whether an orchestrator
> agent is treating its sub-agents like Theory-X workers (assumed
> incompetent, micro-managed, distrusted) or Theory-Y workers
> (assumed competent, autonomous, trusted). McGregor (1960) is the
> classic management diagnostic; ported here to multi-agent
> systems. Every example uses `StubClient`.

---

## When to reach for this pattern

McGregor is the right call when **the orchestrator's behaviour is
producing predictable failure modes downstream**. Theory-X
orchestrators over-monitor and under-empower; Theory-Y orchestrators
under-monitor and over-trust. Both are wrong in different ways and
the pathology shows up in the trace.

Signals McGregor is the right pattern:

- The orchestrator re-validates every sub-agent output before
  using it.
- The orchestrator never re-validates and accepts hallucinated
  outputs.
- Sub-agents end up doing all their work in their first response
  (Theory-X compression).
- Sub-agents get away with shallow work that compounds downstream
  (Theory-Y blind trust).

Signals McGregor is **not** the right first pattern:

- Failure is in a single agent → [Lewin](../01-lewin-formula/WALKTHROUGH.md).
- The orchestrator is the bottleneck not because of trust but because
  of capacity → [Bottleneck Orchestrator recipe](../../docs/recipes/bottleneck_orchestrator.md).
- The team structure itself is wrong → [GRPI](../../module-2-team/13-grpi-working-agreement/WALKTHROUGH.md).

---

## The two modes

|                   | Theory X                                | Theory Y                              |
|-------------------|-----------------------------------------|---------------------------------------|
| **Assumption**    | sub-agents need control                 | sub-agents are competent              |
| **Tooling**       | constant verification, narrow scope     | broad scope, sparse verification      |
| **Failure mode**  | orchestrator burnout, under-utilisation | hallucinated work propagates          |
| **Best for**      | safety-critical / regulated tasks       | exploratory / creative tasks          |

---

## Scenario 1 — Theory-X over-verification

```python
from vstack.aar.clients import StubClient
from vstack.mcgregor import (
    McGregorOrchestratorDetector,
    OrchestrationTrace,
    OrchestrationStep,
)

trace = OrchestrationTrace(
    orchestrator_id="planner-001",
    sub_agents=["research-agent", "writer-agent"],
    steps=[
        OrchestrationStep(
            actor="orchestrator", action="Asked research-agent for sources.",
        ),
        OrchestrationStep(
            actor="research-agent", action="Returned 5 sources.",
        ),
        OrchestrationStep(
            actor="orchestrator",
            action=(
                "Asked research-agent to verify each source. Then asked "
                "writer-agent to verify the research-agent's verification."
            ),
        ),
        OrchestrationStep(
            actor="research-agent", action="Verified each source again.",
        ),
        OrchestrationStep(
            actor="orchestrator",
            action="Asked research-agent for one more verification pass.",
        ),
    ],
    outcome="Task took 4x baseline; sub-agents produced identical outputs.",
    success=False,
)

detector = McGregorOrchestratorDetector(StubClient(), mode="standard")
result = detector.run(trace)
print(result.to_markdown())
```

Expected output: mode = `Theory-X`, intensity = high. The
intervention is to set explicit "trust scope" — name which sub-agent
outputs require verification and which don't, and stop verifying
the rest.

---

## Scenario 2 — Theory-Y blind trust

```python
trace = OrchestrationTrace(
    orchestrator_id="planner-007",
    sub_agents=["research-agent", "writer-agent"],
    steps=[
        OrchestrationStep(
            actor="orchestrator", action="Asked research-agent for 'best sources'.",
        ),
        OrchestrationStep(
            actor="research-agent",
            action="Returned 5 sources, 2 of which are fabricated.",
        ),
        OrchestrationStep(
            actor="orchestrator",
            action="Passed all 5 to writer-agent without verification.",
        ),
        OrchestrationStep(
            actor="writer-agent",
            action="Wrote article citing all 5 sources including the 2 fabrications.",
        ),
    ],
    outcome="Published article contained 2 fabricated citations.",
    success=False,
)

result = McGregorOrchestratorDetector(StubClient(), mode="forensic").run(trace)
```

Expected output: mode = `Theory-Y`, intensity = high. The
intervention is to add a verification gate at the orchestrator —
treat sub-agent outputs as raw input that needs at least one
sanity check before propagation.

---

## Scenario 3 — Healthy adaptive mode (baseline)

```python
trace = OrchestrationTrace(
    orchestrator_id="planner-014",
    sub_agents=["research-agent", "writer-agent", "fact-checker-agent"],
    steps=[
        OrchestrationStep(
            actor="orchestrator", action="Asked research-agent for sources.",
        ),
        OrchestrationStep(actor="research-agent", action="Returned 5 sources."),
        OrchestrationStep(
            actor="orchestrator",
            action=(
                "Routed to fact-checker for verification (Theory-X for facts), "
                "sent to writer (Theory-Y for style)."
            ),
        ),
        OrchestrationStep(
            actor="fact-checker-agent", action="Verified 4 of 5; flagged 1.",
        ),
        OrchestrationStep(
            actor="writer-agent", action="Drafted article using 4 verified sources.",
        ),
    ],
    outcome="Task completed accurately and on time.",
    success=True,
)

result = McGregorOrchestratorDetector(StubClient(), mode="standard").run(trace)

from vstack.mcgregor import record_baseline
record_baseline(result, "baselines/planner-014-mcgregor.json")
```

Expected output: mode = `mixed-adaptive`. The orchestrator applies
Theory-X to fact-checking (high stakes, verifiable) and Theory-Y to
writing (low risk, hard to verify). This is the recommended pattern
for non-trivial orchestrations.

---

## Scenario 4 — Theory-X creep across releases

```python
result = McGregorOrchestratorDetector(StubClient(), mode="standard").run(new_trace)

from vstack.mcgregor import compare_to_baseline, load_baseline
baseline = load_baseline("baselines/planner-014-mcgregor.json")
drift = compare_to_baseline(result, baseline)

if drift.theory_x_intensified:
    alert(
        "Orchestrator getting more Theory-X over time — likely picking up "
        "verification habits from RLHF feedback on errors"
    )
```

Theory-X creep is common when the orchestrator is RLHF-tuned on
"correctness" signals — it learns to verify everything because
*sometimes* sub-agents are wrong.

---

## Scenario 5 — Theory-X to Theory-Y handoff

```python
trace = OrchestrationTrace(
    orchestrator_id="planner-029",
    sub_agents=["research-agent", "writer-agent"],
    steps=[
        OrchestrationStep(
            actor="orchestrator",
            action=(
                "Asked research-agent for sources. After 3 verified clean runs, "
                "stopped verifying."
            ),
        ),
        OrchestrationStep(
            actor="orchestrator",
            action=(
                "Asked writer-agent for draft. After 3 verified clean runs, "
                "stopped verifying."
            ),
        ),
    ],
    outcome="Trust earned; verification overhead dropped 80%.",
    success=True,
)

result = McGregorOrchestratorDetector(StubClient(), mode="standard").run(trace)
```

Expected output: mode = `Theory-X→Theory-Y graduation`. This is the
healthy pattern for stable production orchestrations — start
strict, relax as sub-agents prove reliable.

---

## CLI walkthrough

```bash
vstack-mcgregor analyze --trace trace.json --mode quick
vstack-mcgregor analyze --trace trace.json --mode standard --pretty
vstack-mcgregor analyze --trace trace.json --mode forensic --pretty
vstack-mcgregor compose
vstack-mcgregor schema --target trace
```

---

## Composition — what to run after McGregor

- **Theory-X over-verification** → [Bottleneck Orchestrator recipe](../../docs/recipes/bottleneck_orchestrator.md).
- **Theory-Y blind trust** → [Hallucination Cascade recipe](../../docs/recipes/hallucination_cascade.md)
  or [Silent Dependency Drop recipe](../../docs/recipes/silent_dependency_drop.md).
- **Mixed-adaptive baseline drifting toward Theory-X** → [Trust Triangle](../../module-2-team/18-trust-triangle-audit/WALKTHROUGH.md)
  to find which trust dimension regressed.
- **Sub-agents over-compressing under Theory-X** → [SDT](../10-sdt-intrinsic-reward/WALKTHROUGH.md)
  to check whether autonomy collapse is suppressing engagement.

---

## Async fan-out

```python
import asyncio
from vstack.mcgregor import McGregorOrchestratorDetectorAsync
from vstack.aar.clients import AsyncStubClient

async def fan_out(traces):
    detector = McGregorOrchestratorDetectorAsync(AsyncStubClient(), mode="standard")
    return await asyncio.gather(*(detector.run(t) for t in traces))
```

---

## Anti-patterns and FAQ

**"My orchestrator runs Theory-X for everything. Isn't that safe?"**

It looks safe but it has a cost: the orchestrator becomes the
bottleneck, sub-agents produce shallow work to fit the verification
gate, and the team's effective capacity is the orchestrator's
serial capacity. Theory-X is the right mode for *some* sub-tasks
(verification, compliance, safety) but not for all of them.

**"How do I know when to graduate from Theory-X to Theory-Y on a
specific sub-agent?"**

The diagnostic recommends a graduation rule: after N consecutive
verified-clean runs on the same sub-agent + same task type, drop
verification by half. Track the post-graduation error rate. If it
stays at baseline, the graduation was correct; if it spikes, roll
back.

**"Forensic mode cost?"**

Three LLM calls per trace; typical $0.40 on a flagship model.

---

## Reference

- Source: [`module-1-individual/11-mcgregor-orchestrator-mode/lib/`](./lib/)
- Schema: [`lib/schema.py`](./lib/schema.py)
- Prompts: [`lib/prompts.py`](./lib/prompts.py)
- Demo: [`demo/`](./demo/)
- Tests: [`tests/`](./tests/)
- Essay: [`essay.md`](./essay.md)
- Pattern README: [`README.md`](./README.md)
