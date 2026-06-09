# Walkthrough — Group Decision Models

> Goal: end-to-end recipes for matching multi-agent decisions to the
> right Vroom-Yetton-Jago (1988) decision model — Autocratic /
> Consultative / Group-Consensus. Different decisions need
> different models; mismatches are the canonical multi-agent
> dysfunction. Every example uses `StubClient`.

---

## When to reach for this pattern

Group Decision Models is the right call when **a multi-agent team
is taking too long to decide** or **deciding too fast** for the
quality of the resulting decision. The Vroom-Yetton-Jago model
maps decision type to recommended process.

Signals Group Decision Models is the right pattern:

- A simple yes/no got escalated to a 5-agent panel.
- A high-stakes architectural call was made by one agent without
  consultation.
- Decisions converge fast (suspect: under-deliberated) or slow
  (suspect: wrong process).

Signals Group Decision Models is **not** the right first pattern:

- The team's structure itself is wrong → [GRPI](../13-grpi-working-agreement/WALKTHROUGH.md).
- The team converges on wrong answers → [Heffernan Superflocks](../16-heffernan-superflocks-detector/WALKTHROUGH.md).

---

## The five decision styles (Vroom-Yetton-Jago 1988, ported)

- **AI (Autocratic-I)** — orchestrator decides alone with available info.
- **AII (Autocratic-II)** — orchestrator polls sub-agents for info,
  decides alone.
- **CI (Consultative-I)** — orchestrator consults sub-agents
  individually, decides alone.
- **CII (Consultative-II)** — orchestrator consults sub-agents as
  a group, decides alone.
- **GII (Group)** — orchestrator + sub-agents reach consensus
  together.

---

## Scenario 1 — Mismatched style (over-deliberation)

```python
from vstack.aar.clients import StubClient
from vstack.group_decision import (
    DecisionStyleDetector,
    DecisionTrace,
    DecisionAttribute,
)

trace = DecisionTrace(
    decision_id="approve-typo-fix",
    attributes=DecisionAttribute(
        quality_requirement="low",
        commitment_requirement="low",
        info_sufficiency_orchestrator="high",
        time_pressure="low",
    ),
    style_used="GII",
    outcome="3-day debate to approve a 1-line typo fix.",
    success=False,
)

detector = DecisionStyleDetector(StubClient(), mode="standard")
result = detector.run(trace)
print(result.to_markdown())
```

Expected output: recommended = AI. Used = GII. Mismatch = over-
deliberation. The intervention is to give the orchestrator authority
on low-stakes decisions with clear info.

---

## Scenario 2 — Mismatched style (under-consultation)

```python
trace = DecisionTrace(
    decision_id="architectural-pivot",
    attributes=DecisionAttribute(
        quality_requirement="high",
        commitment_requirement="high",
        info_sufficiency_orchestrator="low",
        time_pressure="low",
    ),
    style_used="AI",
    outcome="Architectural pivot decided by orchestrator alone; team rejected on review.",
    success=False,
)

result = DecisionStyleDetector(StubClient(), mode="forensic").run(trace)
```

Expected output: recommended = GII. Used = AI. Mismatch = under-
consultation. The intervention is to route high-stakes decisions
through group consensus to gain commitment.

---

## Scenario 3 — Healthy match (baseline)

```python
trace = DecisionTrace(
    decision_id="ship-release",
    attributes=DecisionAttribute(
        quality_requirement="high",
        commitment_requirement="medium",
        info_sufficiency_orchestrator="medium",
        time_pressure="medium",
    ),
    style_used="CII",
    outcome="Orchestrator consulted group, decided; team committed.",
    success=True,
)

result = DecisionStyleDetector(StubClient(), mode="standard").run(trace)

from vstack.group_decision import record_baseline
record_baseline(result, "baselines/release-CII.json")
```

---

## Scenario 4 — Time-pressure escalation

```python
trace = DecisionTrace(
    decision_id="rollback-prod",
    attributes=DecisionAttribute(
        quality_requirement="high",
        commitment_requirement="medium",
        info_sufficiency_orchestrator="high",
        time_pressure="very_high",
    ),
    style_used="GII",
    outcome="Outage extended by 30 minutes due to deliberation.",
    success=False,
)

result = DecisionStyleDetector(StubClient(), mode="forensic").run(trace)
```

Expected output: recommended = AI (time pressure overrides
commitment). The intervention is a "time-pressure → escalate to
AI" rule at the orchestrator.

---

## Scenario 5 — Commitment-required match

```python
trace = DecisionTrace(
    decision_id="team-policy",
    attributes=DecisionAttribute(
        quality_requirement="medium",
        commitment_requirement="very_high",
        info_sufficiency_orchestrator="high",
        time_pressure="low",
    ),
    style_used="GII",
    outcome="Policy adopted; team complied for 6 months.",
    success=True,
)

result = DecisionStyleDetector(StubClient(), mode="standard").run(trace)
```

When commitment matters, GII is the correct style even at info-
high. The diagnostic enforces this rule.

---

## CLI walkthrough

```bash
vstack-group-decision analyze --trace trace.json --mode quick
vstack-group-decision analyze --trace trace.json --mode standard --pretty
vstack-group-decision styles      # explain AI/AII/CI/CII/GII
vstack-group-decision compose
vstack-group-decision schema --target trace
```

---

## Composition — what to run after Group Decision Models

- **Over-deliberation** → [Process Gain/Loss](../14-process-gain-loss-detector/WALKTHROUGH.md)
  to confirm the deliberation is producing the gain.
- **Under-consultation** → [GRPI Goals layer](../13-grpi-working-agreement/WALKTHROUGH.md)
  to ensure goal alignment.
- **Time-pressure mismatch** → escalation rule at orchestrator.
- **Commitment-required mismatch** → [Lencioni Commitment layer](../17-lencioni-diagnostic/WALKTHROUGH.md).

---

## Async fan-out

```python
import asyncio
from vstack.group_decision import DecisionStyleDetectorAsync
from vstack.aar.clients import AsyncStubClient

async def fan_out(traces):
    detector = DecisionStyleDetectorAsync(AsyncStubClient(), mode="standard")
    return await asyncio.gather(*(detector.run(t) for t in traces))
```

---

## Anti-patterns and FAQ

**"My orchestrator always picks GII to be safe."**

GII has the highest deliberation cost. The diagnostic shows when
GII is over-applied. AI / AII are cheap and correct for many
decisions; default to those and escalate.

**"How do I encode the decision-style rule at the orchestrator?"**

A pre-decision routing rule: classify (quality / commitment /
info / time) → table-lookup the recommended style → apply. The
diagnostic surfaces mismatches for the audit.

**"Forensic mode cost?"**

Three LLM calls per trace; typical $0.35 on a flagship model.

---

## Reference

- Source: [`module-2-team/25-group-decision-models/lib/`](./lib/)
- Schema: [`lib/schema.py`](./lib/schema.py)
- Prompts: [`lib/prompts.py`](./lib/prompts.py)
- Demo: [`demo/`](./demo/)
- Tests: [`tests/`](./tests/)
- Essay: [`essay.md`](./essay.md)
- Pattern README: [`README.md`](./README.md)
