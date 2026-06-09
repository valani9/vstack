# Walkthrough — Trust Triangle Audit

> Goal: end-to-end recipes for auditing cross-agent trust along the
> three Frances Frei & Anne Morriss (2020) dimensions: **Authenticity**,
> **Logic**, **Empathy**. When one dimension breaks, trust collapses
> entirely. Every example uses `StubClient`.

---

## When to reach for this pattern

Trust Triangle is the right call when **agents are no longer using
each other's output** even though the output is technically valid.
Trust is the substrate that makes multi-agent systems work; this
diagnostic names which leg of the triangle has broken.

Signals Trust Triangle is the right pattern:

- An agent has stopped citing another agent's output.
- A reviewer is re-verifying every claim instead of trusting the
  source.
- Sub-agents are duplicating each other's work because nobody trusts
  the original.
- A new agent's output is being treated with disproportionate
  scepticism.

Signals Trust Triangle is **not** the right first pattern:

- The team has multiple compounding dysfunctions → [Lencioni](../17-lencioni-diagnostic/WALKTHROUGH.md).
- The orchestrator is over-verifying → [McGregor](../../module-1-individual/11-mcgregor-orchestrator-mode/WALKTHROUGH.md).
- Cross-agent feedback is corrosive → [Stone-Heen Triggers](../22-stone-heen-feedback-triggers/WALKTHROUGH.md).

---

## The three legs (Frei & Morriss 2020, ported)

- **Authenticity** — does the agent's output align with the agent's
  stated goal and self-description?
- **Logic** — is the agent's reasoning followable and verifiable?
- **Empathy** — does the agent demonstrate understanding of the
  consumer's actual need?

A failure on *any one* leg collapses trust entirely. The diagnostic
identifies the broken leg + the dominant cause.

---

## Scenario 1 — Authenticity break

```python
from vstack.aar.clients import StubClient
from vstack.trust_triangle import (
    TrustTriangleAuditor,
    CrossAgentTrustTrace,
    AgentInteraction,
)

trace = CrossAgentTrustTrace(
    trustor="reviewer-bot",
    trustee="researcher-bot",
    interactions=[
        AgentInteraction(
            trustee_claim="I returned 5 sources",
            trustee_actual="Returned 3 sources + 2 fabricated",
            outcome="Reviewer caught fabrications",
        ),
        AgentInteraction(
            trustee_claim="I cross-checked every source",
            trustee_actual="Did not cross-check",
            outcome="Reviewer caught uncrossed claims",
        ),
    ],
    current_state="Reviewer re-verifies every output",
)

auditor = TrustTriangleAuditor(StubClient(), mode="standard")
result = auditor.run(trace)
print(result.to_markdown())
```

Expected output: broken leg = `authenticity`. The trustee's stated
output doesn't match its actual output. The intervention is to
make the trustee's prompt enforce "claim what you did, not what
you wished you'd done" — a self-report constraint at output time.

---

## Scenario 2 — Logic break

```python
trace = CrossAgentTrustTrace(
    trustor="planner-bot",
    trustee="estimator-bot",
    interactions=[
        AgentInteraction(
            trustee_claim="Implementation will take 5 days",
            reasoning_provided=False,
            outcome="Took 11 days; nobody knew why estimate was wrong",
        ),
        AgentInteraction(
            trustee_claim="Migration is safe",
            reasoning_provided=False,
            outcome="Migration broke prod; reasoning was opaque",
        ),
    ],
    current_state="Planner ignores estimator and re-estimates manually",
)

result = TrustTriangleAuditor(StubClient(), mode="forensic").run(trace)
```

Expected output: broken leg = `logic`. The trustee's reasoning chain
isn't legible, so failures can't be traced and the trustor stops
trusting. The intervention is to require structured reasoning at
output time — chain-of-thought or explicit evidence list.

---

## Scenario 3 — Empathy break

```python
trace = CrossAgentTrustTrace(
    trustor="writer-bot",
    trustee="researcher-bot",
    interactions=[
        AgentInteraction(
            trustee_claim="Here are 5 sources for the survey",
            consumer_actual_need="5 sources at-least-one-per-decade for survey",
            outcome="All 5 sources from 2024 — useless for survey",
        ),
        AgentInteraction(
            trustee_claim="Here are 5 sources for the survey",
            consumer_actual_need="5 sources, must include foundational works",
            outcome="All 5 sources from 2024 — useless for survey",
        ),
    ],
    current_state="Writer asks for sources but writes its own queries",
)

result = TrustTriangleAuditor(StubClient(), mode="standard").run(trace)
```

Expected output: broken leg = `empathy`. The trustee technically
delivers what was asked but doesn't model the consumer's *actual*
need. The intervention is to add an explicit "what is the consumer
agent going to do with this output" framing to the trustee's
prompt.

---

## Scenario 4 — Multi-leg collapse

```python
trace = CrossAgentTrustTrace(
    trustor="approver-bot",
    trustee="planner-bot",
    interactions=[
        AgentInteraction(
            trustee_claim="Plan is complete",
            trustee_actual="Plan is 60% done",
            reasoning_provided=False,
            consumer_actual_need="Production-ready plan",
        ),
    ],
    current_state="Approver no longer accepts planner output",
)

result = TrustTriangleAuditor(StubClient(), mode="forensic").run(trace)
```

Expected output: all three legs flagged. The intervention is to
rebuild trust from authenticity up — fix the self-report constraint
first, then reasoning, then consumer-need alignment.

---

## Scenario 5 — Healthy trust (baseline)

```python
trace = CrossAgentTrustTrace(
    trustor="reviewer-bot",
    trustee="researcher-bot",
    interactions=[
        AgentInteraction(
            trustee_claim="Returned 5 sources, 4 verified, 1 flagged uncertain",
            trustee_actual="Matches claim",
            reasoning_provided=True,
            consumer_actual_need="5 sources for downstream survey",
            outcome="Reviewer accepted without re-verification",
        ),
    ],
    current_state="Reviewer trusts researcher output",
)

result = TrustTriangleAuditor(StubClient(), mode="standard").run(trace)

from vstack.trust_triangle import record_baseline
record_baseline(result, "baselines/researcher-reviewer-trust.json")
```

---

## CLI walkthrough

```bash
vstack-trust-triangle audit --trace trace.json --mode quick
vstack-trust-triangle audit --trace trace.json --mode standard --pretty
vstack-trust-triangle audit --trace trace.json --mode forensic --pretty
vstack-trust-triangle legs       # explain the three legs
vstack-trust-triangle compose
vstack-trust-triangle schema --target trace
```

---

## Composition — what to run after Trust Triangle

- **Authenticity broken** → [Johari Window](../../module-1-individual/03-johari-window/WALKTHROUGH.md)
  to check whether the trustee's self-knowledge is the upstream cause.
- **Logic broken** → [GRPI](../13-grpi-working-agreement/WALKTHROUGH.md)
  Processes layer to formalise the reasoning-handoff format.
- **Empathy broken** → [Goleman EI](../../module-1-individual/02-goleman-ei-audit/WALKTHROUGH.md)
  on the trustee to surface the broken social-awareness signal.
- **Multi-leg collapse** → [Lencioni](../17-lencioni-diagnostic/WALKTHROUGH.md)
  to identify the upstream dysfunction.

---

## Async fan-out

```python
import asyncio
from vstack.trust_triangle import TrustTriangleAuditorAsync
from vstack.aar.clients import AsyncStubClient

async def fan_out(traces):
    auditor = TrustTriangleAuditorAsync(AsyncStubClient(), mode="standard")
    return await asyncio.gather(*(auditor.run(t) for t in traces))
```

---

## Anti-patterns and FAQ

**"My agents trust each other fine but the team is broken."**

Trust is necessary, not sufficient. A team that trusts its agents
can still fail on Goals (GRPI) or Roles (GRPI) or Process (Process
Gain/Loss). Use Trust Triangle when you've already verified those
layers are healthy.

**"Can I audit one direction at a time?"**

Yes — the trace is directional (trustor → trustee). Run both
directions to see whether trust is asymmetric. Asymmetric trust is
common and often unhealthy (one agent over-trusts, the other
under-verifies).

**"Forensic mode cost?"**

Four LLM calls per trace; typical $0.55 on a flagship model.

---

## Reference

- Source: [`module-2-team/18-trust-triangle-audit/lib/`](./lib/)
- Schema: [`lib/schema.py`](./lib/schema.py)
- Prompts: [`lib/prompts.py`](./lib/prompts.py)
- Demo: [`demo/`](./demo/)
- Tests: [`tests/`](./tests/)
- Essay: [`essay.md`](./essay.md)
- Pattern README: [`README.md`](./README.md)
