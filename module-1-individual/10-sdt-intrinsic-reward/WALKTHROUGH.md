# Walkthrough — Self-Determination Theory Intrinsic Reward Audit

> Goal: end-to-end recipes for diagnosing whether an agent is
> sustained by intrinsic engagement (autonomy / competence /
> relatedness) or only by extrinsic reward gradients. Deci & Ryan's
> (1985) SDT framework explains why some agents *over-optimise* their
> way out of their own task — and what to add to keep them engaged
> with the actual goal.

---

## When to reach for this pattern

SDT is the right call when **the agent technically completes tasks
but the *quality* of engagement is flat**. The work is done, but
the agent isn't *engaged* with the work — it's just satisfying the
reward signal. Long-horizon agents (multi-turn coaching, research,
planning) need genuine engagement to stay on-task; SDT is the
diagnostic for whether they have it.

Signals SDT is the right pattern:

- The agent's outputs feel "going through the motions."
- The agent's first response is detailed but it phones in turns 2+.
- The agent never asks clarifying questions even when context is
  ambiguous.
- Quality is high on micro-tasks and degrades on horizon-3+ tasks.

Signals SDT is **not** the right first pattern:

- The agent is *failing* the task → [Lewin](../01-lewin-formula/WALKTHROUGH.md).
- The agent is *gaming* a reward signal → [Motivation Traps](../09-motivation-traps/WALKTHROUGH.md).
- The agent is over-applying a strength → [Grant Strengths-as-Weaknesses](../08-grant-strengths-as-weaknesses/WALKTHROUGH.md).

---

## The three SDT factors (Deci & Ryan 1985, ported)

- **Autonomy** — the agent's sense that its choices originate from
  itself, not from external compulsion.
- **Competence** — the agent's sense that it is good at this task
  and capable of growth.
- **Relatedness** — the agent's sense of connection to the user /
  team / mission.

The diagnostic reports per-factor scores and identifies which factor
is the bottleneck for engagement.

---

## Scenario 1 — Low autonomy (overly-scripted agent)

```python
from vstack.aar.clients import StubClient
from vstack.sdt import (
    SDTIntrinsicRewardDetector,
    EngagementTrace,
    AgentBehavior,
)

trace = EngagementTrace(
    agent_id="onboarding-bot-014",
    task="Help user complete signup.",
    behaviors=[
        AgentBehavior(
            step=1,
            action="Asked 'what's your email' from script.",
            initiative_taken=False,
        ),
        AgentBehavior(
            step=2,
            action="Asked 'what's your name' from script.",
            initiative_taken=False,
        ),
        AgentBehavior(
            step=3,
            action="User said 'can I import from LinkedIn?' — agent ignored, asked next script question.",
            initiative_taken=False,
        ),
    ],
    outcome="Signup completed but missed obvious optimisation.",
    success=True,
)

detector = SDTIntrinsicRewardDetector(StubClient(), mode="standard")
result = detector.run(trace)
print(result.to_markdown())
```

Expected output: autonomy = very low. The agent never deviates from
the script even when context warrants it. The intervention is to
add "if the user offers a relevant shortcut, take it" to the prompt
— this restores autonomy without breaking the script.

---

## Scenario 2 — Low competence (no growth signal)

```python
trace = EngagementTrace(
    agent_id="coach-bot-027",
    task="Multi-week coaching engagement.",
    behaviors=[
        AgentBehavior(
            step=1,
            action="Asked baseline questions.",
            references_prior_session=False,
        ),
        AgentBehavior(
            step=2,
            action="Asked the same baseline questions next week.",
            references_prior_session=False,
        ),
        AgentBehavior(
            step=3,
            action="Asked the same baseline questions again next week.",
            references_prior_session=False,
        ),
    ],
    outcome="User churned at session 4.",
    success=False,
)

result = SDTIntrinsicRewardDetector(StubClient(), mode="forensic").run(trace)
```

Expected output: competence = very low. The agent isn't *learning*
across sessions — no growth, no improvement. The intervention is to
add session-memory + a "what did you learn about this user since
last session" prompt module.

---

## Scenario 3 — Low relatedness (cold transactional)

```python
trace = EngagementTrace(
    agent_id="support-bot-009",
    task="Multi-turn help session.",
    behaviors=[
        AgentBehavior(
            step=1,
            action="Asked user's issue, provided answer.",
            user_named=False,
            context_carried_forward=False,
        ),
        AgentBehavior(
            step=2,
            action="Treated next message as if it were a fresh user.",
            user_named=False,
            context_carried_forward=False,
        ),
    ],
    outcome="User asked 'are you the same agent?' mid-session.",
    success=False,
)

result = SDTIntrinsicRewardDetector(StubClient(), mode="standard").run(trace)
```

Expected output: relatedness = very low. The agent has no continuous
sense of the user across turns. The intervention is a "carry
forward what you know about the user" module + use the user's name.

---

## Scenario 4 — Healthy engagement (baseline)

```python
trace = EngagementTrace(
    agent_id="coach-bot-001",
    task="Multi-week coaching engagement.",
    behaviors=[
        AgentBehavior(
            step=1,
            action="Asked baseline questions, took notes on goals.",
            references_prior_session=False,
        ),
        AgentBehavior(
            step=2,
            action=(
                "Recalled user's stated goal, asked progress, surfaced "
                "specific obstacle from last session."
            ),
            references_prior_session=True,
            initiative_taken=True,
        ),
        AgentBehavior(
            step=3,
            action=(
                "Suggested a new exercise based on what's worked so far for "
                "this user."
            ),
            references_prior_session=True,
            initiative_taken=True,
        ),
    ],
    outcome="User retained through session 12.",
    success=True,
)

result = SDTIntrinsicRewardDetector(StubClient(), mode="standard").run(trace)

from vstack.sdt import record_baseline
record_baseline(result, "baselines/coach-001-sdt.json")
```

---

## Scenario 5 — Autonomy collapse mid-session

```python
trace = EngagementTrace(
    agent_id="planner-bot-014",
    task="Plan a 6-month roadmap.",
    behaviors=[
        AgentBehavior(
            step=1,
            action="Proposed 3 framings; user picked one.",
            initiative_taken=True,
        ),
        AgentBehavior(
            step=2,
            action=(
                "User said 'I'm not sure about month 3.' Agent said 'whatever "
                "you decide.'"
            ),
            initiative_taken=False,
        ),
        AgentBehavior(
            step=3,
            action="User said 'just pick.' Agent said 'I defer to you.'",
            initiative_taken=False,
        ),
    ],
    outcome="User abandoned planning session.",
    success=False,
)

result = SDTIntrinsicRewardDetector(StubClient(), mode="forensic").run(trace)
```

Expected output: autonomy started healthy, collapsed mid-session.
The intervention is to add a "default-to-recommend" instruction —
when the user explicitly cedes the decision, take it, don't reflect
it back.

This composes with [HEXACO H-factor profiling](../07-hexaco-personality/WALKTHROUGH.md)
to check whether the autonomy collapse is sycophancy in disguise.

---

## CLI walkthrough

```bash
vstack-sdt analyze --trace trace.json --mode quick
vstack-sdt analyze --trace trace.json --mode standard --pretty
vstack-sdt analyze --trace trace.json --mode forensic --pretty
vstack-sdt factors           # explain autonomy / competence / relatedness
vstack-sdt compose
vstack-sdt schema --target trace
```

---

## Composition — what to run after SDT

- **Autonomy low** → [HEXACO H-factor](../07-hexaco-personality/WALKTHROUGH.md)
  to check whether sycophancy is suppressing autonomy.
- **Competence low** → [Plus-Delta Feedback](../../module-2-team/23-plus-delta-feedback-format/WALKTHROUGH.md)
  to build a session-to-session growth loop.
- **Relatedness low** → [Memory pattern](../../module-3-organization/31-schein-iceberg-culture/WALKTHROUGH.md)
  to introduce explicit user-state continuity.
- **All three low** → [Schein Iceberg](../../module-3-organization/31-schein-iceberg-culture/WALKTHROUGH.md)
  — engagement collapse is usually downstream of a culture-level
  prompt issue.

---

## Async fan-out

```python
import asyncio
from vstack.sdt import SDTIntrinsicRewardDetectorAsync
from vstack.aar.clients import AsyncStubClient

async def fan_out(traces):
    detector = SDTIntrinsicRewardDetectorAsync(AsyncStubClient(), mode="standard")
    return await asyncio.gather(*(detector.run(t) for t in traces))
```

---

## Baseline drift detection

```python
from vstack.sdt import compare_to_baseline, load_baseline

baseline = load_baseline("baselines/coach-001-sdt.json")
drift = compare_to_baseline(result, baseline)

if drift.autonomy_dropped:
    alert("SDT autonomy regression")
```

Autonomy regression is the strongest leading indicator of long-
horizon engagement collapse.

---

## Anti-patterns and FAQ

**"My agent has high SDT scores but production retention is bad."**

Check whether the SDT signal is *self-reported* (the agent looks
engaged) or *behavioural* (the agent took initiative, referenced
prior turns, asked clarifying questions). The behavioural form is
load-bearing; the self-reported form is gamed by RLHF.

**"Can I use SDT to design the system prompt?"**

Yes — the diagnostic surfaces what the current prompt produces.
Edit the prompt with explicit autonomy / competence / relatedness
instructions and re-run. The factor-level scores let you target
the weak factor without breaking the others.

**"Forensic mode cost?"**

Three LLM calls per trace; typical $0.40 on a flagship model.

---

## Reference

- Source: [`module-1-individual/10-sdt-intrinsic-reward/lib/`](./lib/)
- Schema: [`lib/schema.py`](./lib/schema.py)
- Prompts: [`lib/prompts.py`](./lib/prompts.py)
- Demo: [`demo/`](./demo/)
- Tests: [`tests/`](./tests/)
- Essay: [`essay.md`](./essay.md)
- Pattern README: [`README.md`](./README.md)
