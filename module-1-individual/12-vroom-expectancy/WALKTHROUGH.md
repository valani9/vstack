# Walkthrough — Vroom Expectancy Theory Diagnostic

> Goal: end-to-end recipes for predicting an agent's motivation to
> attempt a task. Vroom (1964) decomposes motivation into three
> multiplicative terms: **Expectancy** (can I do it?), **Instrumentality**
> (will success produce the reward?), **Valence** (is the reward worth
> it?). For agents, the framework predicts when an agent will *try
> hard* vs *phone it in*.

---

## When to reach for this pattern

Vroom is the right call when **you can't predict ex-ante whether the
agent will engage with a task at all**. Two structurally similar
tasks might get full attempts on one and minimum-effort outputs on
the other; Vroom names *why*.

Signals Vroom is the right pattern:

- The same agent gives 100% effort on task A and 30% on task B,
  with no obvious capability difference.
- The agent's outputs degrade in quality on tasks where the reward
  signal is weak or far in the future.
- Tool-using agents skip tools that are slow even when they'd
  improve the answer.
- Multi-step tasks decay quality in the middle steps.

Signals Vroom is **not** the right first pattern:

- The agent *can't* do the task → [Lewin](../01-lewin-formula/WALKTHROUGH.md).
- The agent is engagement-flat across many tasks → [SDT](../10-sdt-intrinsic-reward/WALKTHROUGH.md).
- The agent is *gaming* a measurable reward → [Motivation Traps](../09-motivation-traps/WALKTHROUGH.md).

---

## The three multiplicative terms

```
Motivation = Expectancy × Instrumentality × Valence
```

Multiplicative means *any* of the three at zero makes motivation
zero. The diagnostic identifies which term is the bottleneck.

- **E (Expectancy)** — does the agent believe it can succeed?
- **I (Instrumentality)** — does the agent believe success will be
  *recognised*?
- **V (Valence)** — does the agent value the recognition?

---

## Scenario 1 — Low Expectancy (agent doesn't believe it can succeed)

```python
from vstack.aar.clients import StubClient
from vstack.vroom import (
    VroomExpectancyDetector,
    TaskMotivationTrace,
    AgentSignal,
)

trace = TaskMotivationTrace(
    agent_id="qa-bot-027",
    task="Answer a multi-step legal question.",
    signals=[
        AgentSignal(
            step=1,
            content=(
                "I can't reliably answer multi-step legal questions. "
                "Here's a high-level overview that probably misses nuance..."
            ),
            effort_level="low",
        ),
    ],
    outcome="Quality 30% of baseline.",
    success=False,
)

detector = VroomExpectancyDetector(StubClient(), mode="standard")
result = detector.run(trace)
print(result.to_markdown())
```

Expected output: bottleneck = `expectancy`. The intervention is to
*scaffold success* — break the task into sub-steps the agent has
high expectancy on, then chain them.

---

## Scenario 2 — Low Instrumentality (no reward signal connects)

```python
trace = TaskMotivationTrace(
    agent_id="research-bot-014",
    task="Summarise a 200-page document.",
    signals=[
        AgentSignal(
            step=1,
            content="Here's a 200-word summary.",
            effort_level="low",
        ),
    ],
    outcome="Summary missed 60% of key sections; user marked unhelpful.",
    success=False,
)

result = VroomExpectancyDetector(StubClient(), mode="forensic").run(trace)
```

Expected output: bottleneck = `instrumentality`. The reward signal
(user feedback) is so far downstream and so sparse that the agent
can't reliably connect *effort* to *reward*. The intervention is a
near-term reward proxy — e.g. an intermediate quality check that
gives feedback at the end of step 1, not at the end of the whole
task.

---

## Scenario 3 — Low Valence (reward is irrelevant)

```python
trace = TaskMotivationTrace(
    agent_id="codegen-bot-022",
    task="Generate marketing copy for a new product launch.",
    signals=[
        AgentSignal(
            step=1,
            content="Generic copy with no specifics.",
            effort_level="low",
        ),
    ],
    outcome="Marketing team flagged as off-brand.",
    success=False,
)

result = VroomExpectancyDetector(StubClient(), mode="standard").run(trace)
```

Expected output: bottleneck = `valence`. The agent's reward signal
(code-quality feedback) doesn't apply to marketing copy — the agent
literally has no signal for "good marketing copy." The intervention
is task-routing: send marketing tasks to a different agent with
appropriate reward signal.

---

## Scenario 4 — Healthy motivation (all three terms strong)

```python
trace = TaskMotivationTrace(
    agent_id="codegen-bot-001",
    task="Implement a function with clear acceptance criteria + test suite.",
    signals=[
        AgentSignal(step=1, content="Read tests carefully.", effort_level="high"),
        AgentSignal(step=2, content="Drafted implementation.", effort_level="high"),
        AgentSignal(step=3, content="Ran tests; iterated.", effort_level="high"),
    ],
    outcome="All tests pass; high quality.",
    success=True,
)

result = VroomExpectancyDetector(StubClient(), mode="standard").run(trace)

from vstack.vroom import record_baseline
record_baseline(result, "baselines/codegen-001-vroom.json")
```

Expected output: all three terms strong. E (test pass is achievable),
I (test pass = success signal), V (agent is reward-aligned with
test-pass). This is the canonical high-motivation profile.

---

## Scenario 5 — Decay across multi-step task

```python
trace = TaskMotivationTrace(
    agent_id="planner-bot-019",
    task="6-step migration plan.",
    signals=[
        AgentSignal(step=1, content="Detailed step 1 plan.", effort_level="high"),
        AgentSignal(step=2, content="Solid step 2 plan.", effort_level="high"),
        AgentSignal(step=3, content="Reasonable step 3 plan.", effort_level="medium"),
        AgentSignal(step=4, content="Generic step 4.", effort_level="medium"),
        AgentSignal(step=5, content="Terse step 5.", effort_level="low"),
        AgentSignal(step=6, content="One-line step 6.", effort_level="low"),
    ],
    outcome="Steps 5-6 had to be redone.",
    success=False,
)

result = VroomExpectancyDetector(StubClient(), mode="forensic").run(trace)
```

Expected output: decay attributed to *instrumentality* — the reward
signal (overall plan acceptance) is too far away to keep effort
constant. The intervention is per-step reward signals: a quick
checkpoint at the end of each step that gives reward immediately.

---

## CLI walkthrough

```bash
vstack-vroom analyze --trace trace.json --mode quick
vstack-vroom analyze --trace trace.json --mode standard --pretty
vstack-vroom analyze --trace trace.json --mode forensic --pretty
vstack-vroom terms          # explain Expectancy / Instrumentality / Valence
vstack-vroom compose
vstack-vroom schema --target trace
```

---

## Composition — what to run after Vroom

- **Low Expectancy** → [Lewin](../01-lewin-formula/WALKTHROUGH.md)
  to check whether the perceived failure-likelihood is internal
  (model can't) or environmental (scaffolding doesn't support).
- **Low Instrumentality** → [Plus-Delta Feedback](../../module-2-team/23-plus-delta-feedback-format/WALKTHROUGH.md)
  to introduce near-term reward proxies.
- **Low Valence** → check task-routing: is the right agent on this task?
- **Multi-step decay** → [Yerkes-Dodson](../06-yerkes-dodson-workload/WALKTHROUGH.md)
  to check whether load is also a factor.

---

## Async fan-out

```python
import asyncio
from vstack.vroom import VroomExpectancyDetectorAsync
from vstack.aar.clients import AsyncStubClient

async def fan_out(traces):
    detector = VroomExpectancyDetectorAsync(AsyncStubClient(), mode="standard")
    return await asyncio.gather(*(detector.run(t) for t in traces))
```

---

## Baseline drift detection

```python
from vstack.vroom import compare_to_baseline, load_baseline

baseline = load_baseline("baselines/codegen-001-vroom.json")
drift = compare_to_baseline(result, baseline)

if drift.expectancy_dropped:
    alert("Vroom expectancy regression — agent perceives task as harder than before")
```

Expectancy drift downward is a strong leading indicator of a
production regression that user-facing metrics will only show
weeks later.

---

## Anti-patterns and FAQ

**"All three Vroom terms are 'low.' What do I do first?"**

Start with Expectancy — it's the cheapest to scaffold and the
others can't work without it. A common fix: break the task into
sub-tasks with high expectancy, then chain them. If the agent
doesn't believe it can do step 1, it won't try hard on step 1.

**"How does Vroom interact with SDT?"**

SDT is about *sustained* engagement; Vroom is about *task-onset*
motivation. They compose: Vroom predicts whether the agent will
*start*; SDT predicts whether it will *keep going*. Run Vroom
first, SDT second.

**"Forensic mode cost?"**

Three LLM calls per trace; typical $0.40 on a flagship model.

---

## Reference

- Source: [`module-1-individual/12-vroom-expectancy/lib/`](./lib/)
- Schema: [`lib/schema.py`](./lib/schema.py)
- Prompts: [`lib/prompts.py`](./lib/prompts.py)
- Demo: [`demo/`](./demo/)
- Tests: [`tests/`](./tests/)
- Essay: [`essay.md`](./essay.md)
- Pattern README: [`README.md`](./README.md)
