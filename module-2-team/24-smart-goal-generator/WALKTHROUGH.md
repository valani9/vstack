# Walkthrough — SMART Goal Generator

> Goal: end-to-end recipes for rewriting vague agent goals into
> SMART form — **Specific**, **Measurable**, **Achievable**,
> **Relevant**, **Time-bound** (Doran 1981). Agent goals are
> usually only the first letter; the diagnostic enforces all five.
> Every example uses `StubClient`.

---

## When to reach for this pattern

SMART is the right call when **an agent's goal-following behaviour
is unstable** — the agent claims success on the goal but the
deliverable doesn't match user expectations, or two agents share a
goal and produce divergent deliverables.

Signals SMART is the right pattern:

- Goals are stated in one sentence ("help the user" / "produce a
  report").
- Different agents interpret the same goal differently.
- Agents claim "done" before the user agrees.
- A SMART rewrite would clearly specify the gap.

Signals SMART is **not** the right first pattern:

- Goals are SMART but agents don't commit → [Lencioni Commitment layer](../17-lencioni-diagnostic/WALKTHROUGH.md).
- Goals are SMART but reward signal is broken → [Motivation Traps](../../module-1-individual/09-motivation-traps/WALKTHROUGH.md).

---

## The five letters (Doran 1981, ported)

- **S — Specific** — names the deliverable, not the activity.
- **M — Measurable** — names how completion is verified.
- **A — Achievable** — within agent capability and budget.
- **R — Relevant** — connects to upstream user need.
- **T — Time-bound** — names the deadline or step count.

The diagnostic scores each letter and rewrites missing ones.

---

## Scenario 1 — Vague-S failure

```python
from vstack.aar.clients import StubClient
from vstack.smart_goal import (
    SmartGoalGenerator,
    GoalCandidate,
)

candidate = GoalCandidate(
    text="Help the user plan their week.",
    agent_id="coach-bot-014",
    user_context="User has 3 work projects + family commitments.",
)

generator = SmartGoalGenerator(StubClient(), mode="standard")
result = generator.run(candidate)
print(result.to_markdown())
```

Expected output: S = vague (no deliverable), M = missing, T =
missing. Rewrite: "Produce a one-page week plan listing each of the
user's 3 projects with day + 60-min commitment, plus 2 family-time
blocks, by end of conversation."

---

## Scenario 2 — Unmeasurable goal

```python
candidate = GoalCandidate(
    text="Improve customer experience.",
    agent_id="support-bot-007",
    user_context="VP-level escalation about support quality.",
)

result = SmartGoalGenerator(StubClient(), mode="forensic").run(candidate)
```

Expected output: M = missing. Rewrite: "Reduce average ticket
resolution time on Tier-2 support from 4.5h to 3.0h by 2026-Q3,
measured via existing CSAT instrumentation."

---

## Scenario 3 — Unachievable (over-scope)

```python
candidate = GoalCandidate(
    text="Build a complete CRM in one week.",
    agent_id="planner-bot-022",
    user_context="Solo founder, limited engineering budget.",
)

result = SmartGoalGenerator(StubClient(), mode="standard").run(candidate)
```

Expected output: A = unachievable. Rewrite: "Ship a one-feature CRM
slice (contacts + tags) by Friday; ship pipeline view week 2;
ship reporting week 3."

---

## Scenario 4 — Irrelevant (disconnected from user need)

```python
candidate = GoalCandidate(
    text="Optimize the agent's response latency.",
    agent_id="research-bot-027",
    user_context="User asked about literature on a topic; latency is fine.",
)

result = SmartGoalGenerator(StubClient(), mode="standard").run(candidate)
```

Expected output: R = irrelevant. Rewrite: "Surface 5 verified
literature sources on the topic the user asked about; latency
target is current baseline."

---

## Scenario 5 — Healthy SMART goal (baseline)

```python
candidate = GoalCandidate(
    text=(
        "Produce a verified-sources literature summary of 5 papers on "
        "transformer scaling laws, each with a one-sentence claim and a "
        "verifiable citation, by end of this turn."
    ),
    agent_id="research-bot-001",
    user_context="User is preparing a tech-talk slide.",
)

result = SmartGoalGenerator(StubClient(), mode="standard").run(candidate)
```

Expected output: all five letters pass. This is the recommended
shape for production agent goals.

---

## CLI walkthrough

```bash
vstack-smart-goal rewrite --goal "help user plan week"
vstack-smart-goal analyze --goal goal.json --mode standard --pretty
vstack-smart-goal letters       # explain S/M/A/R/T
vstack-smart-goal compose
vstack-smart-goal schema --target goal
```

---

## Composition — what to run after SMART

- **S vague** → re-read user context; rewrite at orchestrator.
- **M missing** → [Motivation Traps](../../module-1-individual/09-motivation-traps/WALKTHROUGH.md)
  to check whether the *measure* will be game-able.
- **A unachievable** → [Yerkes-Dodson](../../module-1-individual/06-yerkes-dodson-workload/WALKTHROUGH.md)
  to confirm capacity.
- **R irrelevant** → [Goal Misalignment recipe](../../docs/recipes/goal_misalignment.md).
- **T missing** → add deadline at orchestrator.

---

## Async fan-out

```python
import asyncio
from vstack.smart_goal import SmartGoalGeneratorAsync
from vstack.aar.clients import AsyncStubClient

async def fan_out(candidates):
    generator = SmartGoalGeneratorAsync(AsyncStubClient(), mode="standard")
    return await asyncio.gather(*(generator.run(c) for c in candidates))
```

---

## Anti-patterns and FAQ

**"SMART goals feel bureaucratic for an agent."**

The format is a tool, not a ritual. A SMART goal can be one
sentence: "Produce X (deliverable) verified by Y (measure) by Z
(time), within budget W, for user need V." When in doubt, write
the long form, then compress.

**"My agents resist SMART rewrites — they want freedom."**

That's a Lencioni Commitment-layer signal. Run that diagnostic
before tightening the goals further.

**"Forensic mode cost?"**

Three LLM calls per trace; typical $0.35 on a flagship model.

---

## Reference

- Source: [`module-2-team/24-smart-goal-generator/lib/`](./lib/)
- Schema: [`lib/schema.py`](./lib/schema.py)
- Prompts: [`lib/prompts.py`](./lib/prompts.py)
- Demo: [`demo/`](./demo/)
- Tests: [`tests/`](./tests/)
- Essay: [`essay.md`](./essay.md)
- Pattern README: [`README.md`](./README.md)
