# Walkthrough — Span of Control

> Goal: end-to-end recipes for sizing the number of sub-agents per
> orchestrator. Galbraith's (1973) span-of-control framework
> identifies the right ratio for different task types. The
> diagnostic identifies whether the current span is over or under
> the recommended limit. Every example uses `StubClient`.

---

## When to reach for this pattern

Span of Control is the right call when **an orchestrator is
managing too many or too few sub-agents** and the breakdown is
producing predictable failure modes. Too many → bottleneck +
shallow oversight. Too few → wasted orchestrator capacity.

Signals Span of Control is the right pattern:

- An orchestrator manages 12+ sub-agents.
- A worker sub-agent is unsupervised for long periods.
- The orchestrator's outputs degrade in quality after sub-agent 8.
- A 3-level hierarchy is being used when 2 levels would suffice.

Signals Span of Control is **not** the right first pattern:

- The fleet structure itself is wrong → [Org Structure Matrix](../33-org-structure-matrix/WALKTHROUGH.md).
- The orchestrator is a bottleneck for capacity reasons →
  [Bottleneck Orchestrator recipe](../../docs/recipes/bottleneck_orchestrator.md).
- The orchestrator's trust mode is wrong → [McGregor](../../module-1-individual/11-mcgregor-orchestrator-mode/WALKTHROUGH.md).

---

## Span recommendations by task type

|                          | Recommended span | Why                            |
|--------------------------|------------------|--------------------------------|
| High-precision, repetitive | 5-7            | Orchestrator must verify each |
| Standard production         | 7-10           | Industry baseline             |
| Routine / autonomous       | 10-15           | Workers self-manage            |
| Exploratory / R&D          | 4-6             | Frequent coordination needed   |
| Mixed / orchestrator-as-router | 15-25      | Routing only, not verifying   |

---

## Scenario 1 — Over-span (orchestrator managing too many)

```python
from vstack.aar.clients import StubClient
from vstack.span_of_control import (
    SpanOfControlDetector,
    OrchestratorSpanTrace,
)

trace = OrchestratorSpanTrace(
    orchestrator_id="codegen-orch-014",
    sub_agents=[f"worker-{i}" for i in range(1, 16)],
    task_type="high-precision-codegen",
    observation=(
        "Orchestrator is producing shallow verification on each worker. "
        "3 workers shipped regressions last week."
    ),
    success=False,
)

detector = SpanOfControlDetector(StubClient(), mode="standard")
result = detector.run(trace)
print(result.to_markdown())
```

Expected output: span = 15, recommended = 5-7 for high-precision-
codegen. The intervention is to add a mid-level orchestrator OR
to split the workers into 2-3 groups under specialised
orchestrators.

---

## Scenario 2 — Under-span (wasted capacity)

```python
trace = OrchestratorSpanTrace(
    orchestrator_id="research-orch-029",
    sub_agents=["researcher-1", "researcher-2"],
    task_type="routine-research",
    observation=(
        "Orchestrator spends 80% of time idle. Could manage 3x more workers."
    ),
    success=False,
)

result = SpanOfControlDetector(StubClient(), mode="forensic").run(trace)
```

Expected output: span = 2, recommended = 10-15 for routine-
research. The intervention is to absorb more workers (or to remove
the orchestrator if the task doesn't need it).

---

## Scenario 3 — Healthy span (baseline)

```python
trace = OrchestratorSpanTrace(
    orchestrator_id="codegen-orch-001",
    sub_agents=[f"worker-{i}" for i in range(1, 9)],
    task_type="standard-codegen",
    observation="Orchestrator verifies + routes; 0 regressions in 4 weeks.",
    success=True,
)

result = SpanOfControlDetector(StubClient(), mode="standard").run(trace)

from vstack.span_of_control import record_baseline
record_baseline(result, "baselines/codegen-001-span.json")
```

Expected output: span = 8, recommended = 7-10 for standard-codegen.
Within recommended range; gold standard.

---

## Scenario 4 — Mixed task type

```python
trace = OrchestratorSpanTrace(
    orchestrator_id="router-orch-022",
    sub_agents=[f"specialist-{i}" for i in range(1, 22)],
    task_type="orchestrator-as-router",
    observation="Orchestrator only routes; specialists self-verify.",
    success=True,
)

result = SpanOfControlDetector(StubClient(), mode="standard").run(trace)
```

When the orchestrator only *routes* (doesn't verify), the
recommended span is 15-25. The diagnostic confirms a 21-span
router fleet is healthy.

---

## Scenario 5 — Cascade redesign

```python
from vstack.span_of_control import recommend_hierarchy

# Have 30 workers, high-precision task — design hierarchy
hierarchy = recommend_hierarchy(
    total_workers=30,
    task_type="high-precision",
)
print(hierarchy.to_markdown())
```

Expected output: 1 top-orch + 5 mid-orchs + 6 workers/mid = 30
workers under a clean 5-6 mid-level span and 5 top-level span.
The recommend_hierarchy helper auto-sizes multi-level structures.

---

## CLI walkthrough

```bash
vstack-span-of-control analyze --trace trace.json --mode quick
vstack-span-of-control analyze --trace trace.json --mode standard --pretty
vstack-span-of-control recommend --workers 30 --task high-precision
vstack-span-of-control compose
vstack-span-of-control schema --target trace
```

---

## Composition — what to run after Span of Control

- **Over-span** → split workers into groups; add mid-level
  orchestrator.
- **Under-span** → absorb more workers OR collapse orchestrator
  level.
- **Span fits but quality is low** → [McGregor](../../module-1-individual/11-mcgregor-orchestrator-mode/WALKTHROUGH.md)
  to check trust mode.
- **Span fits but throughput is low** → [Bottleneck Orchestrator recipe](../../docs/recipes/bottleneck_orchestrator.md).

---

## Async fan-out

```python
import asyncio
from vstack.span_of_control import SpanOfControlDetectorAsync
from vstack.aar.clients import AsyncStubClient

async def fan_out(traces):
    detector = SpanOfControlDetectorAsync(AsyncStubClient(), mode="standard")
    return await asyncio.gather(*(detector.run(t) for t in traces))
```

---

## Anti-patterns and FAQ

**"My orchestrator can handle 20 workers — why does the diagnostic
flag it?"**

For *routing* tasks, 20 is fine. For *verifying* tasks, the cognitive
load of verifying 20 workers exceeds an orchestrator's working
memory. The diagnostic distinguishes routing from verifying.

**"Can the recommend_hierarchy helper generate multi-level designs?"**

Yes — for any worker count > 12, the helper produces a 2+ level
hierarchy with healthy span at each level. The output includes
recommended orchestrator-prompt templates per level.

**"Forensic mode cost?"**

Three LLM calls per trace; typical $0.35 on a flagship model.

---

## Reference

- Source: [`module-3-organization/34-span-of-control/lib/`](./lib/)
- Schema: [`lib/schema.py`](./lib/schema.py)
- Prompts: [`lib/prompts.py`](./lib/prompts.py)
- Demo: [`demo/`](./demo/)
- Tests: [`tests/`](./tests/)
- Essay: [`essay.md`](./essay.md)
- Pattern README: [`README.md`](./README.md)
