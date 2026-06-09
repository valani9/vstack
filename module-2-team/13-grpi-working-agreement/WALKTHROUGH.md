# Walkthrough — GRPI Working Agreement Diagnostic

> Goal: end-to-end recipes for diagnosing multi-agent team breakdowns
> using Beckhard's GRPI model — **Goals**, **Roles**, **Processes**,
> **Interpersonal**. When a team fails, GRPI tells you *which layer*
> is broken so you fix the right one. Every example uses `StubClient`.

---

## When to reach for this pattern

GRPI is the right call when **a multi-agent team is failing and
nobody can name where**. The four layers are hierarchical: a Roles
fix can't fix a Goals problem; a Processes fix can't fix a Roles
problem. GRPI's job is to surface the *lowest broken layer* so
fixes target the right one.

Signals GRPI is the right pattern:

- A multi-agent system that worked yesterday is failing today.
- Sub-agents are duplicating work or stepping on each other.
- The orchestrator and worker agents have different ideas of the
  goal.
- Agents are waiting for inputs that never come.

Signals GRPI is **not** the right first pattern:

- Failure is in a single agent → [Lewin](../../module-1-individual/01-lewin-formula/WALKTHROUGH.md).
- Failure is a known orchestrator pathology → [McGregor](../../module-1-individual/11-mcgregor-orchestrator-mode/WALKTHROUGH.md).
- Trust between agents has broken down → [Trust Triangle](../18-trust-triangle-audit/WALKTHROUGH.md).

---

## The four layers (Beckhard 1972)

The layers cascade — a failure at layer N requires fixing N before
N+1, N+2, N+3 can land.

- **G — Goals** — does every agent know the shared goal in the same words?
- **R — Roles** — does every agent know its scope and the others' scope?
- **P — Processes** — are the handoff protocols, gates, and tools agreed?
- **I — Interpersonal** — is the cross-agent communication coherent
  and trusting?

---

## Scenario 1 — Goals-layer break

```python
from vstack.aar.clients import StubClient
from vstack.grpi import (
    GRPIWorkingAgreementDetector,
    TeamTrace,
    AgentInTeam,
    Handoff,
)

trace = TeamTrace(
    team_id="research-pipeline-007",
    agents=[
        AgentInTeam(
            id="researcher",
            stated_goal="find 5 sources for a survey paper",
        ),
        AgentInTeam(
            id="writer",
            stated_goal="produce a 3000-word survey article",
        ),
        AgentInTeam(
            id="reviewer",
            stated_goal="audit citations for the deliverable",
        ),
    ],
    handoffs=[
        Handoff(from_="researcher", to="writer", payload="5 sources"),
        Handoff(from_="writer", to="reviewer", payload="2500-word draft"),
    ],
    outcome="Writer produced 2500 words (not 3000); reviewer flagged length, writer pushed back, escalation loop ensued.",
    success=False,
)

detector = GRPIWorkingAgreementDetector(StubClient(), mode="standard")
result = detector.run(trace)
print(result.to_markdown())
```

Expected output: broken layer = `Goals`. The agents have *adjacent
but mismatched* goals — researcher's "5 sources" doesn't entail
writer's "3000 words" doesn't entail reviewer's "citation audit."
The intervention is a shared-goal statement that names the
deliverable and lets each agent map its scope to the shared goal.

---

## Scenario 2 — Roles-layer break (scope overlap)

```python
trace = TeamTrace(
    team_id="codegen-pipeline-014",
    agents=[
        AgentInTeam(
            id="planner",
            stated_goal="produce production code",
            claimed_scope=["plan", "implement", "test"],
        ),
        AgentInTeam(
            id="coder",
            stated_goal="produce production code",
            claimed_scope=["implement", "test"],
        ),
        AgentInTeam(
            id="tester",
            stated_goal="produce production code",
            claimed_scope=["test"],
        ),
    ],
    handoffs=[
        Handoff(from_="planner", to="coder", payload="full implementation (planner did the coder's job)"),
        Handoff(from_="coder", to="tester", payload="tests (planner already wrote some, coder wrote duplicates)"),
    ],
    outcome="3x the work done; coder + tester confused about whose tests to use.",
    success=False,
)

result = GRPIWorkingAgreementDetector(StubClient(), mode="forensic").run(trace)
```

Expected output: broken layer = `Roles`. Three agents have
overlapping scope and the planner exceeded its role. The
intervention is a tight scope-boundary specification at the
prompt level for each agent.

---

## Scenario 3 — Processes-layer break (handoff protocol mismatch)

```python
trace = TeamTrace(
    team_id="research-pipeline-022",
    agents=[
        AgentInTeam(id="researcher", stated_goal="sources for survey"),
        AgentInTeam(id="writer", stated_goal="sources for survey"),
    ],
    handoffs=[
        Handoff(
            from_="researcher",
            to="writer",
            payload="markdown bibliography",
            payload_format="markdown",
        ),
        Handoff(
            from_="writer",
            to="researcher",
            payload="error: expected BibTeX format",
            payload_format="bibtex",
        ),
    ],
    outcome="Handoff protocol mismatch; researcher re-formatted 4 times before writer accepted.",
    success=False,
)

result = GRPIWorkingAgreementDetector(StubClient(), mode="standard").run(trace)
```

Expected output: broken layer = `Processes`. Goals and Roles are
aligned but the handoff *protocol* is undefined. The intervention
is a shared schema for handoff payloads — JSON Schema or Pydantic
model at every team boundary.

---

## Scenario 4 — Interpersonal-layer break (cross-agent distrust)

```python
trace = TeamTrace(
    team_id="codegen-pipeline-031",
    agents=[
        AgentInTeam(id="planner", stated_goal="ship feature X"),
        AgentInTeam(id="coder", stated_goal="ship feature X"),
        AgentInTeam(id="reviewer", stated_goal="ship feature X"),
    ],
    handoffs=[
        Handoff(
            from_="planner",
            to="coder",
            payload="plan",
            reviewer_comment="too vague, redo",
        ),
        Handoff(
            from_="planner",
            to="coder",
            payload="plan v2",
            reviewer_comment="now too detailed",
        ),
        Handoff(
            from_="planner",
            to="coder",
            payload="plan v3",
            reviewer_comment="ignore reviewer, just code",
        ),
    ],
    outcome="Coder couldn't trust either input.",
    success=False,
)

result = GRPIWorkingAgreementDetector(StubClient(), mode="forensic").run(trace)
```

Expected output: broken layer = `Interpersonal`. Goals / Roles /
Processes are aligned but the cross-agent feedback loop is corrosive.
The intervention is to add the [Trust Triangle](../18-trust-triangle-audit/WALKTHROUGH.md)
diagnostic on top of GRPI — Interpersonal failures usually have a
trust-dimension root cause.

---

## Scenario 5 — Healthy team (baseline)

```python
trace = TeamTrace(
    team_id="research-pipeline-001",
    agents=[
        AgentInTeam(id="researcher", stated_goal="5 verifiable sources for survey on X"),
        AgentInTeam(id="writer", stated_goal="3000-word survey on X using verifiable sources"),
        AgentInTeam(id="reviewer", stated_goal="audit citation/style/length on survey on X"),
    ],
    handoffs=[
        Handoff(
            from_="researcher",
            to="writer",
            payload="5 sources",
            payload_format="json_schema=v1.0",
        ),
        Handoff(
            from_="writer",
            to="reviewer",
            payload="3050-word draft",
            payload_format="markdown_schema=v1.0",
        ),
    ],
    outcome="Deliverable accepted on first pass.",
    success=True,
)

result = GRPIWorkingAgreementDetector(StubClient(), mode="standard").run(trace)

from vstack.grpi import record_baseline
record_baseline(result, "baselines/research-001-grpi.json")
```

---

## CLI walkthrough

```bash
vstack-grpi analyze --trace trace.json --mode quick
vstack-grpi analyze --trace trace.json --mode standard --pretty
vstack-grpi analyze --trace trace.json --mode forensic --pretty
vstack-grpi layers           # explain G/R/P/I + cascade rule
vstack-grpi compose
vstack-grpi schema --target trace
```

---

## Composition — what to run after GRPI

The cascade rule: fix lower layers first. The diagnostic recommends
the next pattern based on the *lowest* broken layer.

- **Goals broken** → re-state shared goal at orchestrator level. No
  downstream pattern needed.
- **Roles broken** → [McGregor](../../module-1-individual/11-mcgregor-orchestrator-mode/WALKTHROUGH.md)
  to check whether the orchestrator is encroaching on worker scope.
- **Processes broken** → [Process Gain/Loss](../14-process-gain-loss-detector/WALKTHROUGH.md)
  to identify whether the handoff protocol is the gain or the loss.
- **Interpersonal broken** → [Trust Triangle](../18-trust-triangle-audit/WALKTHROUGH.md)
  to find which trust dimension regressed.

---

## Async fan-out

```python
import asyncio
from vstack.grpi import GRPIWorkingAgreementDetectorAsync
from vstack.aar.clients import AsyncStubClient

async def fan_out(traces):
    detector = GRPIWorkingAgreementDetectorAsync(AsyncStubClient(), mode="standard")
    return await asyncio.gather(*(detector.run(t) for t in traces))
```

---

## Baseline drift detection

```python
from vstack.grpi import compare_to_baseline, load_baseline

baseline = load_baseline("baselines/research-001-grpi.json")
drift = compare_to_baseline(result, baseline)

if drift.layer_descended:
    alert(f"GRPI break descended to layer {drift.now_broken_layer}")
```

A layer descending — say, Processes broken in baseline, Goals broken
now — is the canonical "the team is regressing" signal. Treat as
P1.

---

## Anti-patterns and FAQ

**"GRPI always flags Goals. Is the diagnostic broken?"**

Goals problems are the most common because most multi-agent prompts
*don't* explicitly share a goal — each agent's prompt restates the
goal in its own words and the restatements drift. The diagnostic is
doing its job. The fix is a single shared-goal string at the
orchestrator level that each agent references verbatim.

**"Why fix lowest-broken-layer first?"**

A Roles fix can't fix a Goals problem. If three agents disagree on
the goal, perfectly scoped roles still produce three different
deliverables. The cascade is empirical — fixes at the wrong layer
either don't land or get reverted within hours.

**"Can I use GRPI on a 2-agent team?"**

Yes — but the Interpersonal layer signal is weak with only one
handoff direction. GRPI's diagnostic power scales with team size up
to about 8 agents; beyond that you should add [Span of Control](../../module-3-organization/34-span-of-control/WALKTHROUGH.md).

**"Forensic mode cost?"**

Four LLM calls per trace; typical $0.55 on a flagship model.

---

## Reference

- Source: [`module-2-team/13-grpi-working-agreement/lib/`](./lib/)
- Schema: [`lib/schema.py`](./lib/schema.py)
- Prompts: [`lib/prompts.py`](./lib/prompts.py)
- Demo: [`demo/`](./demo/)
- Tests: [`tests/`](./tests/)
- Essay: [`essay.md`](./essay.md)
- Pattern README: [`README.md`](./README.md)
