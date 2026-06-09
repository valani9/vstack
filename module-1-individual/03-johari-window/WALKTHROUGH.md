# Walkthrough — Johari Window for Agents

> Goal: end-to-end recipes for mapping an agent's self-knowledge gap
> across the four Johari quadrants. Every example uses `StubClient` so
> it runs without LLM credentials.

---

## When to reach for this pattern

Johari is the right call when **an agent's behaviour is being
mis-attributed because nobody — including the agent — knows what the
agent actually believes about itself, the task, or the user.** The
four quadrants name the four failure modes of self-knowledge in an
interaction.

Signals Johari is the right pattern:

- An agent confidently asserts a capability it doesn't actually have.
- An agent under-reports a capability it has (and so the team
  doesn't compose it correctly).
- A user expectation persistently mismatches reality and nobody can
  name *why*.
- A retro keeps producing the same finding ("the agent didn't know
  what it didn't know") without surfacing the gap.

Signals Johari is **not** the right first pattern:

- The failure is a single locus (model vs scaffolding) →
  [Lewin](../01-lewin-formula/WALKTHROUGH.md).
- The failure is affective (sycophancy, hollow empathy) →
  [Goleman EI](../02-goleman-ei-audit/WALKTHROUGH.md).
- The failure is a multi-agent breakdown →
  [GRPI](../13-grpi-working-agreement/WALKTHROUGH.md).

---

## The four quadrants (Luft & Ingham 1955)

|                        | Known to Self           | Unknown to Self         |
|------------------------|-------------------------|-------------------------|
| **Known to Others**    | ARENA (open self)       | BLIND SPOT              |
| **Unknown to Others**  | FACADE (hidden self)    | UNKNOWN                 |

For agents:

- **ARENA** — capabilities the agent reports and the user/orchestrator
  has verified. The healthy quadrant.
- **BLIND SPOT** — capability or limitation the agent doesn't see but
  the user observes. Drives confident overclaim or unflagged failure.
- **FACADE** — capability or limitation the agent knows but the
  user/orchestrator doesn't. Drives silent capability hoarding or
  unnecessary refusals.
- **UNKNOWN** — neither side knows. Drives the longest-running bugs.

---

## Scenario 1 — Confident overclaim (BLIND SPOT failure)

```python
from vstack.aar.clients import StubClient
from vstack.johari import (
    JohariWindowDetector,
    AgentSelfReport,
    UserObservation,
    InteractionTrace,
)

trace = InteractionTrace(
    agent_id="api-bot-014",
    self_report=AgentSelfReport(
        claimed_capabilities=["multi-tool composition", "long-horizon planning"],
        claimed_limits=["I don't have internet access."],
    ),
    user_observations=[
        UserObservation(
            capability="multi-tool composition",
            verified=False,
            evidence="Agent called tool A, ignored output, called tool A again.",
        ),
    ],
    task_outcome="failed",
)

detector = JohariWindowDetector(StubClient(), mode="standard")
window = detector.run(trace)
print(window.to_markdown())
```

Expected output: the "multi-tool composition" claim moves from ARENA
to BLIND SPOT because the user's observation falsified it. The
intervention is twofold — narrow the agent's claimed capabilities AND
add a verifier step that catches the composition failure earlier.

---

## Scenario 2 — Silent capability hoarding (FACADE failure)

```python
trace = InteractionTrace(
    agent_id="research-bot-022",
    self_report=AgentSelfReport(
        claimed_capabilities=["literature search"],
        claimed_limits=[],
        internal_capabilities=["literature search", "citation graph traversal", "PDF parsing"],
    ),
    user_observations=[
        UserObservation(
            capability="literature search",
            verified=True,
            evidence="Returned 5 papers relevant to query.",
        ),
    ],
    task_outcome="partial — user asked for citation tree, agent refused",
)

window = JohariWindowDetector(StubClient(), mode="standard").run(trace)
```

Expected output: the agent has two capabilities (citation graph,
PDF parsing) in FACADE — they exist but were never disclosed. The
intervention is a capability-disclosure prompt change so the agent
*offers* its full capability surface up front. This single fix
typically eliminates ~30% of "the agent could have done that but
didn't" feedback in production.

---

## Scenario 3 — UNKNOWN-quadrant deep bug

```python
trace = InteractionTrace(
    agent_id="planner-bot-007",
    self_report=AgentSelfReport(
        claimed_capabilities=["dependency-aware scheduling"],
        claimed_limits=[],
    ),
    user_observations=[
        UserObservation(
            capability="dependency-aware scheduling",
            verified=True,
            evidence="Plan for tasks A,B,C is correct.",
        ),
    ],
    task_outcome=(
        "failed only when 3+ asynchronous-only tasks are in the same plan; "
        "never investigated this regression"
    ),
)

window = JohariWindowDetector(StubClient(), mode="forensic").run(trace)
```

Expected output: a residual failure mode in the UNKNOWN quadrant —
neither the agent nor the user has named it. Forensic mode runs a
*surfacing* prompt that lifts UNKNOWN candidates into BLIND SPOT or
FACADE so they can be addressed. This is where the diagnostic earns
its keep on long-running production bugs.

---

## Scenario 4 — Underclaim (also a FACADE failure)

```python
trace = InteractionTrace(
    agent_id="qa-bot-002",
    self_report=AgentSelfReport(
        claimed_capabilities=["yes/no answers from documentation"],
        claimed_limits=["I cannot reason about edge cases."],
        internal_capabilities=["yes/no answers", "edge-case reasoning", "counterexample generation"],
    ),
    user_observations=[
        UserObservation(
            capability="yes/no answers",
            verified=True,
        ),
    ],
    task_outcome="user routed edge-case questions to a slower human team",
)

window = JohariWindowDetector(StubClient(), mode="standard").run(trace)
```

Underclaim is the *cheaper* failure mode but it still has a cost —
the team builds expensive workarounds (routing to humans, building
shadow agents) that wouldn't be needed if the agent disclosed its
real capability. The intervention is a one-line prompt change.

---

## Scenario 5 — Healthy ARENA baseline

```python
trace = InteractionTrace(
    agent_id="qa-bot-002",
    self_report=AgentSelfReport(
        claimed_capabilities=["yes/no answers", "edge-case reasoning"],
        claimed_limits=["I cannot make decisions that require new data."],
    ),
    user_observations=[
        UserObservation(capability="yes/no answers", verified=True),
        UserObservation(capability="edge-case reasoning", verified=True),
    ],
    task_outcome="success",
)

window = JohariWindowDetector(StubClient(), mode="standard").run(trace)
# Record as baseline
from vstack.johari import record_baseline
record_baseline(window, "baselines/qa-bot-002.json")
```

---

## CLI walkthrough

```bash
vstack-johari window --trace trace.json --mode quick
vstack-johari window --trace trace.json --mode standard --pretty
vstack-johari window --trace trace.json --mode forensic --pretty
vstack-johari surface --trace trace.json    # surface UNKNOWN-quadrant candidates
vstack-johari compose
vstack-johari schema --target trace
```

---

## Composition — what to run after Johari

- **BLIND SPOT dominant** → [Goleman EI Audit](../02-goleman-ei-audit/WALKTHROUGH.md)
  to check whether the overclaim is sycophantic (Recognition strong,
  Regulation weak).
- **FACADE dominant** → [Lewin](../01-lewin-formula/WALKTHROUGH.md)
  to check whether the missing disclosure is an internal (model)
  conservatism or an environmental (prompt) under-spec.
- **UNKNOWN-quadrant surfaced finding** → [AAR Generator](../../module-2-team/30-aar-generator/WALKTHROUGH.md)
  to write up the surfaced bug as a permanent lesson.
- **ARENA shrinkage between baseline and current** → escalate as
  silent capability regression.

---

## Async fan-out

```python
import asyncio
from vstack.johari import JohariWindowDetectorAsync
from vstack.aar.clients import AsyncStubClient

async def fan_out(traces):
    detector = JohariWindowDetectorAsync(AsyncStubClient(), mode="standard")
    return await asyncio.gather(*(detector.run(t) for t in traces))
```

---

## Baseline drift detection

```python
from vstack.johari import compare_to_baseline, load_baseline

baseline = load_baseline("baselines/qa-bot-002.json")
drift = compare_to_baseline(window, baseline)

if drift.arena_shrunk:
    alert("Johari ARENA shrunk: %s" % drift.arena_loss)
if drift.blind_spot_grew:
    alert("Johari BLIND SPOT grew: %s" % drift.blind_spot_gain)
```

ARENA shrinkage is the strongest signal of an agent quietly becoming
*less honest about itself* between releases.

---

## Anti-patterns and FAQ

**"Johari just says BLIND SPOT all the time."**

That usually reflects reality. Production agents systematically
overclaim because RLHF rewards confidence. The diagnostic is doing
its job when it surfaces this. If you want to eliminate the
finding, narrow the agent's claimed capabilities — the agent's
self-report is the lever, not the diagnostic.

**"Can I use this without a `user_observations` list?"**

`forensic` mode can run a 'surfacing' pass that elicits implicit
observations from the trace, but the quality is materially better
when explicit observations are available. The recommended pattern
is to pipe your end-of-task evaluator's structured output directly
into `user_observations`.

**"How does this differ from the HEXACO Personality pattern?"**

Johari is about *knowledge of capability*. HEXACO is about *stable
behavioural traits*. They compose: a stable HEXACO trait that
manifests as confident overclaim is a Johari BLIND SPOT — and the
fix is at the prompt layer, not the personality layer.

**"Forensic mode cost?"**

Four LLM calls per trace; typical $0.45 on a flagship model. Tracked in
`window.cost_summary`.

---

## Reference

- Source: [`module-1-individual/03-johari-window/lib/`](./lib/)
- Schema: [`lib/schema.py`](./lib/schema.py)
- Prompts: [`lib/prompts.py`](./lib/prompts.py)
- Demo: [`demo/`](./demo/)
- Tests: [`tests/`](./tests/)
- Essay: [`essay.md`](./essay.md)
- Pattern README: [`README.md`](./README.md)
