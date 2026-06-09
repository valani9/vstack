# Walkthrough — Organisation Structure Matrix

> Goal: end-to-end recipes for matching a multi-agent system's
> *structure* to its task: **Functional**, **Divisional**,
> **Matrix**, **Network**, **Holacratic**. Mintzberg + Galbraith's
> framework for human orgs ports cleanly to fleets of agents.
> Every example uses `StubClient`.

---

## When to reach for this pattern

Structure is the right call when **the fleet is failing in a way
that suggests the *organisational shape* is wrong** — too narrow
specialisation, too deep hierarchy, too many cross-team handoffs,
too few. The diagnostic identifies the current structure and
recommends a target structure for the task at hand.

Signals Structure is the right pattern:

- A small team produces narrow output (functional structure may
  fit better).
- A divisional structure produces siloed outputs.
- A matrix structure produces conflicting priorities.
- A network structure can't make decisions.

Signals Structure is **not** the right first pattern:

- The team is small and unified — structure is moot.
- A single agent is the bottleneck → [Bottleneck Orchestrator recipe](../../docs/recipes/bottleneck_orchestrator.md).
- The team layers are aligned but failing → [Lencioni](../../module-2-team/17-lencioni-diagnostic/WALKTHROUGH.md).

---

## The five structures

|              | Decision authority | Specialisation | Best for                       |
|--------------|--------------------|----------------|--------------------------------|
| Functional   | Top-down           | High           | Repetitive, high-precision     |
| Divisional   | Per-division       | High           | Multiple products / markets    |
| Matrix       | Dual-report        | High           | Cross-cutting projects         |
| Network      | Peer               | Medium         | Exploration, R&D               |
| Holacratic   | Distributed        | Low            | Self-organising, ambiguous     |

---

## Scenario 1 — Wrong structure (matrix on a single-product fleet)

```python
from vstack.aar.clients import StubClient
from vstack.org_structure import (
    OrgStructureDetector,
    FleetStructureTrace,
    ReportingLine,
)

trace = FleetStructureTrace(
    fleet_id="codegen-fleet-014",
    agents=["coder", "tester", "reviewer", "deployer"],
    reporting_lines=[
        ReportingLine(agent="coder", reports_to=["tech-lead", "product-orch"]),
        ReportingLine(agent="tester", reports_to=["tech-lead", "qa-orch"]),
        ReportingLine(agent="reviewer", reports_to=["tech-lead", "product-orch"]),
    ],
    task_type="single-product release pipeline",
    outcome="Dual-reporting drove priority conflicts; releases stalled.",
    success=False,
)

detector = OrgStructureDetector(StubClient(), mode="standard")
result = detector.run(trace)
print(result.to_markdown())
```

Expected output: structure = `matrix`, recommended = `functional`.
The intervention is to consolidate reporting under a single
orchestrator for single-product fleets.

---

## Scenario 2 — Right structure (network for R&D)

```python
trace = FleetStructureTrace(
    fleet_id="rnd-fleet-007",
    agents=["explorer-1", "explorer-2", "explorer-3", "synthesizer"],
    reporting_lines=[
        ReportingLine(agent="explorer-1", reports_to=[]),
        ReportingLine(agent="explorer-2", reports_to=[]),
        ReportingLine(agent="explorer-3", reports_to=[]),
        ReportingLine(agent="synthesizer", reports_to=[]),
    ],
    task_type="open-ended R&D",
    outcome="Three exploration paths surfaced; synthesizer chose best.",
    success=True,
)

result = OrgStructureDetector(StubClient(), mode="standard").run(trace)

from vstack.org_structure import record_baseline
record_baseline(result, "baselines/rnd-007-org.json")
```

Network structure with peer agents + synthesizer is correct for
open-ended exploration. The diagnostic confirms the match.

---

## Scenario 3 — Functional structure (high precision)

```python
trace = FleetStructureTrace(
    fleet_id="audit-fleet-022",
    agents=["auditor-1", "auditor-2", "auditor-3"],
    reporting_lines=[
        ReportingLine(agent="auditor-1", reports_to=["audit-orchestrator"]),
        ReportingLine(agent="auditor-2", reports_to=["audit-orchestrator"]),
        ReportingLine(agent="auditor-3", reports_to=["audit-orchestrator"]),
    ],
    task_type="high-precision compliance audit",
    outcome="Audit produced 0 false positives; orchestrator caught duplications.",
    success=True,
)

result = OrgStructureDetector(StubClient(), mode="standard").run(trace)
```

Expected output: structure = `functional`. Correct for high-
precision tasks where consistency matters more than exploration.

---

## Scenario 4 — Divisional (multi-product fleet)

```python
trace = FleetStructureTrace(
    fleet_id="multi-product-fleet-029",
    agents=[
        "product-A-coder", "product-A-tester",
        "product-B-coder", "product-B-tester",
        "product-C-coder", "product-C-tester",
    ],
    reporting_lines=[
        ReportingLine(agent="product-A-coder", reports_to=["product-A-orch"]),
        ReportingLine(agent="product-A-tester", reports_to=["product-A-orch"]),
        ReportingLine(agent="product-B-coder", reports_to=["product-B-orch"]),
        ReportingLine(agent="product-B-tester", reports_to=["product-B-orch"]),
        ReportingLine(agent="product-C-coder", reports_to=["product-C-orch"]),
        ReportingLine(agent="product-C-tester", reports_to=["product-C-orch"]),
    ],
    task_type="three independent product lines",
    outcome="Each product shipped independently.",
    success=True,
)

result = OrgStructureDetector(StubClient(), mode="standard").run(trace)
```

Divisional structure correctly chosen for multi-product fleets.

---

## Scenario 5 — Holacratic (self-organising team)

```python
trace = FleetStructureTrace(
    fleet_id="self-org-fleet-001",
    agents=["worker-1", "worker-2", "worker-3"],
    reporting_lines=[
        ReportingLine(agent="worker-1", reports_to=[]),
        ReportingLine(agent="worker-2", reports_to=[]),
        ReportingLine(agent="worker-3", reports_to=[]),
    ],
    task_type="ambiguous goal, claim-as-you-go",
    outcome="Workers self-claimed sub-tasks; produced coherent output.",
    success=True,
)

result = OrgStructureDetector(StubClient(), mode="standard").run(trace)
```

Holacratic structure (no fixed authority) is correct when agents
need to self-claim work. Requires strong inter-agent trust;
compose with [Trust Triangle](../../module-2-team/18-trust-triangle-audit/WALKTHROUGH.md).

---

## CLI walkthrough

```bash
vstack-org-structure analyze --trace trace.json --mode quick
vstack-org-structure analyze --trace trace.json --mode standard --pretty
vstack-org-structure structures      # explain the five structures
vstack-org-structure compose
vstack-org-structure schema --target trace
```

---

## Composition — what to run after Org Structure

- **Structure mismatched with task** → restructure reporting lines
  at the orchestrator. No downstream pattern.
- **Matrix conflict** → [Group Decision Models](../../module-2-team/25-group-decision-models/WALKTHROUGH.md)
  to pick the decision style.
- **Holacratic structure** → [Trust Triangle](../../module-2-team/18-trust-triangle-audit/WALKTHROUGH.md)
  to verify trust substrate.
- **Functional structure with low precision** → [Yerkes-Dodson](../../module-1-individual/06-yerkes-dodson-workload/WALKTHROUGH.md).

---

## Async fan-out

```python
import asyncio
from vstack.org_structure import OrgStructureDetectorAsync
from vstack.aar.clients import AsyncStubClient

async def fan_out(traces):
    detector = OrgStructureDetectorAsync(AsyncStubClient(), mode="standard")
    return await asyncio.gather(*(detector.run(t) for t in traces))
```

---

## Anti-patterns and FAQ

**"My fleet is 3 agents. Does structure even matter?"**

At 3 agents, functional vs network is the only choice that matters.
Below 6 agents, simpler structures dominate. Above 6, structure
choice becomes load-bearing.

**"How do I decide between matrix and divisional?"**

If sub-orchestrators need to *coordinate* across teams frequently
(handoffs at week granularity), matrix. If they're independent
(monthly granularity), divisional.

**"Forensic mode cost?"**

Three LLM calls per trace; typical $0.40 on a flagship model.

---

## Reference

- Source: [`module-3-organization/33-org-structure-matrix/lib/`](./lib/)
- Schema: [`lib/schema.py`](./lib/schema.py)
- Prompts: [`lib/prompts.py`](./lib/prompts.py)
- Demo: [`demo/`](./demo/)
- Tests: [`tests/`](./tests/)
- Essay: [`essay.md`](./essay.md)
- Pattern README: [`README.md`](./README.md)
