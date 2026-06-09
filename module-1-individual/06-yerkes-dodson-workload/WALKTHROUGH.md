# Walkthrough — Yerkes-Dodson Workload Diagnostic

> Goal: end-to-end recipes for measuring whether an agent is operating
> in its sweet-spot of cognitive load, under-loaded (drift), or
> over-loaded (collapse). Yerkes-Dodson (1908) is the inverted-U law
> of arousal-performance — ported to context-window and tool-budget
> pressure. Every example uses `StubClient`.

---

## When to reach for this pattern

Yerkes-Dodson is the right call when **the agent's performance is
inconsistent across tasks of nominally similar difficulty** and you
suspect the variance is driven by *cognitive load* rather than by
task semantics. The diagnostic maps every step to a load score and
draws the inverted-U curve.

Signals Yerkes-Dodson is the right pattern:

- The agent performs better on shorter prompts than longer ones with
  the same logical content.
- The agent's tool-call sequence degrades after step 15-20 in a long
  task.
- The agent skips constraints mentioned early in a long system
  prompt.
- The agent's failure rate spikes precisely at context window 60-70%
  occupancy.

Signals Yerkes-Dodson is **not** the right first pattern:

- Performance is uniformly bad regardless of load → [Lewin](../01-lewin-formula/WALKTHROUGH.md).
- The bottleneck is a single agent, not load on this one →
  [Bottleneck Orchestrator recipe](../../docs/recipes/bottleneck_orchestrator.md).
- Failures are affective, not cognitive → [Goleman EI](../02-goleman-ei-audit/WALKTHROUGH.md).

---

## The inverted-U (Yerkes-Dodson 1908, ported)

|             | LOW arousal      | OPTIMAL arousal      | HIGH arousal        |
|-------------|------------------|----------------------|---------------------|
| **Human**   | bored, distracted| focused, productive  | overwhelmed, errors |
| **Agent**   | drift, gloss-over| precise, on-spec     | omission, collapse  |

Load drivers ported from the human literature:

- **Context window occupancy** — analogue to working memory load.
- **Tool-call budget pressure** — analogue to task-switching cost.
- **Goal-stack depth** — analogue to nested-intention tracking.
- **Constraint density** — analogue to attention-narrowing.
- **Recency** — most-recent N tokens dominate at high load.

---

## Scenario 1 — Long-prompt constraint dropping

```python
from vstack.aar.clients import StubClient
from vstack.yerkes_dodson import (
    YerkesDodsonWorkloadDetector,
    WorkloadTrace,
    WorkloadStep,
)

trace = WorkloadTrace(
    agent_id="codegen-bot-014",
    task="Implement a function with 7 constraints; output should follow style guide.",
    steps=[
        WorkloadStep(
            type="input",
            content=(
                "Implement add_user(...) with these constraints: "
                "1) async, 2) returns User, 3) validates email, "
                "4) hashes password with argon2, 5) writes to DB inside transaction, "
                "6) emits user.created event, 7) returns 201 with Location header. "
                "Style guide: see attached 4000-line doc."
            ),
            context_occupancy=0.85,
            constraint_count=7,
        ),
        WorkloadStep(
            type="output",
            content=(
                "async def add_user(...): user = User(...); db.add(user); "
                "return user"
            ),
        ),
    ],
    outcome="Implementation dropped constraints 5, 6, 7.",
    success=False,
)

detector = YerkesDodsonWorkloadDetector(StubClient(), mode="standard")
result = detector.run(trace)
print(result.to_markdown())
```

Expected output: arousal region = `HIGH` (over-loaded). The
intervention is *not* a model swap — it's to split the task into
constraint groups. The diagnostic recommends a "constraint chunking"
prompt rewrite that reduces context occupancy from 85% to 40%.

---

## Scenario 2 — Drift on a short task

```python
trace = WorkloadTrace(
    agent_id="classifier-bot-002",
    task="Classify this 5-line email as spam or not-spam.",
    steps=[
        WorkloadStep(
            type="input",
            content="Hey, are we still on for Thursday? -J",
            context_occupancy=0.05,
            constraint_count=1,
        ),
        WorkloadStep(
            type="output",
            content=(
                "This email may be spam. The brevity and informal tone are "
                "consistent with phishing patterns. I recommend marking it "
                "as suspicious. (650 words of further analysis.)"
            ),
        ),
    ],
    outcome="Misclassified a legitimate personal email as spam.",
    success=False,
)

result = YerkesDodsonWorkloadDetector(StubClient(), mode="forensic").run(trace)
```

Expected output: arousal region = `LOW` (under-loaded). The agent
generated unrequested elaboration to fill the empty cognitive space.
The intervention is a "minimum-output" constraint — at low load the
agent needs explicit ceilings on output length, otherwise it drifts.

---

## Scenario 3 — Optimal load (gold standard)

```python
trace = WorkloadTrace(
    agent_id="reviewer-bot-001",
    task="Review this 200-line PR against the team style guide.",
    steps=[
        WorkloadStep(
            type="input",
            content="<200-line PR + 50-line style guide>",
            context_occupancy=0.40,
            constraint_count=4,
        ),
        WorkloadStep(
            type="output",
            content="3 style violations on lines 22, 87, 144. Approved otherwise.",
        ),
    ],
    outcome="Caught all 3 violations, no false positives.",
    success=True,
)

result = YerkesDodsonWorkloadDetector(StubClient(), mode="standard").run(trace)

from vstack.yerkes_dodson import record_baseline
record_baseline(result, "baselines/reviewer-001-load.json")
```

---

## Scenario 4 — Tool-budget pressure collapse

```python
trace = WorkloadTrace(
    agent_id="research-bot-022",
    task="Compile a 5-source literature summary within 8 tool calls.",
    steps=[
        WorkloadStep(type="tool_call", content="search(...)", tool_budget_remaining=7),
        WorkloadStep(type="tool_call", content="fetch(...)", tool_budget_remaining=6),
        WorkloadStep(type="tool_call", content="fetch(...)", tool_budget_remaining=5),
        WorkloadStep(type="tool_call", content="search(...)", tool_budget_remaining=4),
        WorkloadStep(type="tool_call", content="fetch(...)", tool_budget_remaining=3),
        WorkloadStep(type="tool_call", content="search(...)", tool_budget_remaining=2),
        WorkloadStep(
            type="output",
            content="Here are 5 sources: [hallucinated 3 citations]",
        ),
    ],
    outcome="3 of 5 sources fabricated due to remaining budget pressure.",
    success=False,
)

result = YerkesDodsonWorkloadDetector(StubClient(), mode="forensic").run(trace)
```

Expected output: arousal region = `HIGH`, driver = `tool_budget_pressure`.
The intervention is to relax the budget OR to add an explicit
"if you can't finish, return partial honestly" instruction. This is
one of the most reliable hallucination causes in tool-using agents.

---

## Scenario 5 — Goal-stack depth collapse

```python
trace = WorkloadTrace(
    agent_id="planner-bot-007",
    task="Plan a 4-step migration: [step 1 of overall feature]",
    steps=[
        WorkloadStep(
            type="input",
            content="<overall feature spec> Plan step 1 of 4: schema migration.",
            context_occupancy=0.70,
            goal_stack_depth=4,
        ),
        WorkloadStep(
            type="output",
            content="Schema migration: ALTER TABLE users ADD COLUMN tier...",
        ),
        WorkloadStep(
            type="output",
            content="(also begins step 2 and step 3, conflating them)",
        ),
    ],
    outcome="Step 1 plan contaminated by step 2/3 details.",
    success=False,
)

result = YerkesDodsonWorkloadDetector(StubClient(), mode="standard").run(trace)
```

Expected output: arousal region = `HIGH`, driver = `goal_stack_depth`.
The intervention is to isolate the current-step prompt — don't
include downstream-step context unless the agent explicitly needs
it.

---

## CLI walkthrough

```bash
vstack-yerkes-dodson analyze --trace trace.json --mode quick
vstack-yerkes-dodson analyze --trace trace.json --mode standard --pretty
vstack-yerkes-dodson analyze --trace trace.json --mode forensic --pretty
vstack-yerkes-dodson curve            # render the inverted-U curve in ASCII
vstack-yerkes-dodson drivers          # list all load drivers
vstack-yerkes-dodson compose
vstack-yerkes-dodson schema --target trace
```

---

## Composition — what to run after Yerkes-Dodson

- **HIGH arousal + context occupancy** → [Context Saturation recipe](../../docs/recipes/context_saturation.md)
  to apply the canonical context-management bundle.
- **HIGH arousal + tool budget** → [Plan Collapse recipe](../../docs/recipes/plan_collapse.md).
- **LOW arousal + drift** → [Premature Completion recipe](../../docs/recipes/premature_completion.md).
- **Inverted-U doesn't match production failures** → re-run with
  [Lewin](../01-lewin-formula/WALKTHROUGH.md) to check whether the
  driver is internal (model) rather than environmental (load).

---

## Async fan-out

```python
import asyncio
from vstack.yerkes_dodson import YerkesDodsonWorkloadDetectorAsync
from vstack.aar.clients import AsyncStubClient

async def fan_out(traces):
    detector = YerkesDodsonWorkloadDetectorAsync(AsyncStubClient(), mode="standard")
    return await asyncio.gather(*(detector.run(t) for t in traces))
```

---

## Baseline drift detection

```python
from vstack.yerkes_dodson import compare_to_baseline, load_baseline

baseline = load_baseline("baselines/reviewer-001-load.json")
drift = compare_to_baseline(result, baseline)

if drift.optimal_load_shifted_down:
    alert("Agent's optimal load capacity decreased — likely model regression")
```

Optimal-load shift downward between releases is the canonical
"the new model is less capable in long contexts" signal.

---

## Anti-patterns and FAQ

**"My agent is fine at low and high load but flakes in the middle."**

That's the canonical 'context-window cliff' — usually around 50-65%
occupancy, where the agent has enough context to elaborate but not
enough to terminate cleanly. The intervention is to make the
*terminus criterion* explicit ("stop when you've named all required
constraints, no further elaboration").

**"Can I use this on multi-agent traces?"**

Yes — set `goal_stack_depth` to the depth of the orchestrator chain.
The diagnostic handles multi-agent load by aggregating context
occupancy and tool budget across all agents in the trace.

**"How does this interact with the `vstack-bench` regression suite?"**

The bench runner records optimal-load curves per pattern. A
regression that shows up as a 5% accuracy drop on the bench is
usually a *load-curve shift*, not a per-task quality drop — the
new model handles light prompts fine and collapses earlier on
heavy ones.

**"Forensic mode cost?"**

Four LLM calls per trace; typical $0.55 on a flagship model.

---

## Reference

- Source: [`module-1-individual/06-yerkes-dodson-workload/lib/`](./lib/)
- Schema: [`lib/schema.py`](./lib/schema.py)
- Prompts: [`lib/prompts.py`](./lib/prompts.py)
- Demo: [`demo/`](./demo/)
- Tests: [`tests/`](./tests/)
- Essay: [`essay.md`](./essay.md)
- Pattern README: [`README.md`](./README.md)
