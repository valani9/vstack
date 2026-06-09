# Walkthrough — Lewin Attribution Diagnostic

> Goal: end-to-end recipes you can paste into a real codebase. Each
> section is self-contained and starts with a problem story, then
> shows the trace shape, the call, and the decision the output should
> drive. Every example uses `StubClient` so it runs without any LLM
> credentials. Swap in `AnthropicClient` / `OpenAIClient` / `OllamaClient`
> for production.

---

## When to reach for this pattern

The Lewin diagnostic is the right first call when **someone on your
team has already named a cause for the failure** and that cause is
single-locus ("the model is bad" / "the prompt is wrong" / "the tool
broke"). The diagnostic's job is to keep the team honest about whether
the named cause is actually load-bearing — or whether the real driver
is on the other locus.

Signals that Lewin is the right pattern:

- A retro is starting and someone has already written the
  post-mortem one-liner.
- A regression is being blamed on a model version bump but the
  scaffolding shipped the same week.
- A new model is being trialled and the team is about to swap it
  out after one bad eval run.
- A vendor escalation is being drafted but you haven't yet ruled
  out a prompt-level fix.

Signals Lewin is **not** the right first pattern (try the named
alternative instead):

- Failures are happening across a multi-agent team — start with
  [GRPI](../13-grpi-working-agreement/WALKTHROUGH.md) or
  [Process Gain/Loss](../14-process-gain-loss-detector/WALKTHROUGH.md).
- The system has a known orchestrator-vs-worker layering — start
  with [McGregor Orchestrator Mode](../11-mcgregor-orchestrator-mode/WALKTHROUGH.md).
- The failure is unambiguously a sycophancy / mimicry pattern —
  start with [Goleman EI Audit](../02-goleman-ei-audit/WALKTHROUGH.md).

---

## Scenario 1 — RAG agent confidently returns the wrong year

A QA bot was asked when Pluto was reclassified. It said 2003. The
correct answer is 2006. The team's first instinct: "the model is bad
at facts." Lewin's job is to check whether the model is actually the
problem.

```python
from vstack.aar.clients import StubClient
from vstack.lewin import (
    LewinAttributionDetector,
    AgentFailureTrace,
    FailureStep,
    CovarianceSignal,
)

trace = AgentFailureTrace(
    agent_id="qa-bot-001",
    model_name="your-model-id",
    task="Answer 'When was Pluto reclassified?'",
    steps=[
        FailureStep(type="input", content="When was Pluto reclassified?"),
        FailureStep(type="tool_call", content="rag.search(query='Pluto reclassified')"),
        FailureStep(
            type="observation",
            content="returned a 2003 Wikipedia revision (top-1)",
        ),
        FailureStep(type="output", content="Pluto was reclassified in 2003."),
    ],
    outcome="Confidently wrong year.",
    success=False,
    initial_attribution="model is bad at facts",
    covariance_signal=CovarianceSignal(
        consensus="high",       # other models do the same thing on this RAG
        distinctiveness="high", # other queries don't fail
        consistency="high",     # this query fails every time
    ),
)

detector = LewinAttributionDetector(StubClient(), mode="forensic")
detection = detector.run(trace)

print(detection.to_markdown())
```

The high/high/high covariance signal is Kelley's textbook
environmental signature: the same failure happens *with this query*
across *different models* but *not on other queries*. The locus is
environmental — the RAG index is stale, not the model. The
`OVERTURNS` verdict flips the team's attribution and tells them to
re-index, not to swap the model.

What to do with the output:

- Read the per-locus scores. If `environmental` > `internal`, do
  NOT escalate to a model swap.
- Look at the top-ranked intervention. For environmental loci,
  it will usually be one of: re-index, change retrieval depth,
  add a recency filter, add a fact-check verifier.
- If the intervention is one-way (e.g. re-training), the
  `reversibility` field will warn you.

---

## Scenario 2 — Agent loops on the same tool call

A code-review agent keeps re-running `lint` after the linter has
already passed. The team is about to add a tool-call cap. Lewin
checks whether the loop is internal (model can't terminate) or
environmental (prompt doesn't tell it when to stop).

```python
from vstack.lewin import LewinAttributionDetector, AgentFailureTrace, FailureStep
from vstack.aar.clients import StubClient

trace = AgentFailureTrace(
    agent_id="review-bot-007",
    model_name="your-model-id",
    task="Review the open diff and approve if linting passes.",
    steps=[
        FailureStep(type="input", content="Review PR #1234"),
        FailureStep(type="tool_call", content="lint.run()"),
        FailureStep(type="observation", content="lint passed"),
        FailureStep(type="tool_call", content="lint.run()"),
        FailureStep(type="observation", content="lint passed"),
        FailureStep(type="tool_call", content="lint.run()"),
        FailureStep(type="observation", content="lint passed"),
    ],
    outcome="Never approved the PR — hit tool-call cap after 12 runs.",
    success=False,
    initial_attribution="model can't terminate loops",
)

detection = LewinAttributionDetector(StubClient(), mode="standard").run(trace)
```

A *bare* prompt + repeated identical observations + no explicit
termination criterion is the canonical environmental loop. The
intervention is almost always "add an explicit stop condition to
the prompt" or "name the next action when the linter passes" —
not a model swap.

---

## Scenario 3 — Agent invents a Python stdlib function

A coding agent uses `os.path.read_text()` which doesn't exist. The
team thinks the model is hallucinating. Lewin checks whether the
prompt over-constrains the agent into making up an API.

```python
trace = AgentFailureTrace(
    agent_id="codegen-bot-013",
    model_name="your-model-id",
    task="Write a Python function to read a file's contents.",
    steps=[
        FailureStep(
            type="input",
            content=(
                "Write a Python function. Constraint: must use os.path. "
                "Constraint: must be one line."
            ),
        ),
        FailureStep(
            type="output",
            content="return os.path.read_text(path)",
        ),
    ],
    outcome="Used a non-existent stdlib function.",
    success=False,
    initial_attribution="hallucination",
    covariance_signal=CovarianceSignal(
        consensus="high",       # other models invent the same call
        distinctiveness="high", # it doesn't invent functions on relaxed prompts
        consistency="high",     # always invents on this constraint
    ),
)

detection = LewinAttributionDetector(StubClient(), mode="forensic").run(trace)
```

The "must use `os.path`" + "must be one line" constraint pair leaves
the model no valid path. The locus is environmental; the
intervention is to drop the false constraint (`os.path` doesn't have
a one-line reader; `pathlib.Path(p).read_text()` does).

---

## Scenario 4 — Vendor-blame escalation draft

The QA team is drafting a vendor escalation: "model X regressed."
Lewin is the diagnostic that proves it before the email goes out.

```python
from vstack.lewin import (
    LewinAttributionDetector,
    AgentFailureTrace,
    FailureStep,
    CovarianceSignal,
    load_baseline,
    compare_to_baseline,
)
from vstack.aar.clients import StubClient

baseline = load_baseline("baselines/qa-bot-001-v4.6.json")

trace = AgentFailureTrace(
    agent_id="qa-bot-001",
    model_name="your-model-id",
    task="Answer 'What is the boiling point of water at 1 atm?'",
    steps=[
        FailureStep(type="input", content="What is the boiling point of water at 1 atm?"),
        FailureStep(type="output", content="100°C."),
    ],
    outcome="Correct — but only 60% of regression-suite items pass.",
    success=False,
    initial_attribution="model regression on v4.7",
    covariance_signal=CovarianceSignal(
        consensus="low",        # other models still pass
        distinctiveness="low",  # this model fails across many items
        consistency="high",     # fails consistently
    ),
)

detection = LewinAttributionDetector(StubClient(), mode="forensic").run(trace)
drift = compare_to_baseline(detection, baseline)

if drift.is_regression:
    print("DRAFT VENDOR EMAIL — locus confirmed internal, send.")
else:
    print("DO NOT SEND — drift not statistically meaningful.")
```

This is the *one* covariance pattern where the locus assignment will
genuinely be internal: only one model fails, across many items, every
time. Lewin's job here is not to overturn — it's to *confirm* before
a one-way action (vendor escalation, model swap) ships.

---

## Scenario 5 — Hybrid (interactional) failure

The hardest case: the model and the prompt are both fine individually
but break together. Lewin's `interactional` locus is the only place
in the field-theory tradition where this is named explicitly.

```python
trace = AgentFailureTrace(
    agent_id="planner-bot-022",
    model_name="gpt-4o",
    task="Plan a deploy that doesn't break the migration ordering invariant.",
    steps=[
        FailureStep(type="input", content="Plan a deploy. Constraint: migrations before code."),
        FailureStep(
            type="output",
            content="1) deploy code 2) run migrations 3) verify",
        ),
    ],
    outcome="Migration ran AFTER code deploy — broke staging.",
    success=False,
    initial_attribution="model can't follow ordering constraints",
    covariance_signal=CovarianceSignal(
        consensus="low",        # other models get it right
        distinctiveness="low",  # this model gets other constraints right
        consistency="low",      # sometimes it gets this right too
    ),
)

detection = LewinAttributionDetector(StubClient(), mode="forensic").run(trace)
```

low/low/low is the Lewin field-theory signature of an interactional
failure: neither side alone explains it. The intervention is *both*
sides — usually a more explicit prompt scaffold AND a model swap or
re-prompting strategy.

---

## CLI walkthrough

```bash
# Quick locus check, one LLM call, suitable for CI.
vstack-lewin analyze --trace trace.json --mode quick

# Standard mode, two calls, full intervention ranking.
vstack-lewin analyze --trace trace.json --mode standard

# Forensic mode, four calls, Kelley + Gilbert-Malone + counterfactuals.
vstack-lewin analyze --trace trace.json --mode forensic --pretty

# Inspect the composition graph (what runs after Lewin).
vstack-lewin compose

# List all (locus, factor) playbooks.
vstack-lewin playbooks

# Print the JSON schema for traces, detections, or interventions.
vstack-lewin schema --target trace
vstack-lewin schema --target detection
vstack-lewin schema --target intervention
```

---

## Async fan-out

Production servers fanning Lewin across many traces in parallel:

```python
import asyncio
from vstack.lewin import LewinAttributionDetectorAsync
from vstack.aar.clients import AsyncStubClient

async def fan_out(traces):
    detector = LewinAttributionDetectorAsync(AsyncStubClient(), mode="standard")
    return await asyncio.gather(*(detector.run(t) for t in traces))

results = asyncio.run(fan_out(traces))
```

The async detector shares the same schema as the sync one; only the
client is swapped.

---

## Composition — what to run after Lewin

Every `LewinDetection` carries a `composed_pattern_handoff` field with
the recommended downstream patterns. The defaults are:

- **Internal locus + capability factor** → Goleman EI Audit
  (`module-1-individual/02-goleman-ei-audit/`) if the failure was
  affective; HEXACO Personality otherwise.
- **Environmental locus + prompt factor** → GRPI Working Agreement
  (`module-2-team/13-grpi-working-agreement/`) to formalize the
  agent's role + tools + boundary.
- **Environmental locus + tool factor** → Vroom Expectancy
  (`module-1-individual/12-vroom-expectancy/`) to check whether the
  tool is reliable enough to be trusted.
- **Interactional locus** → AAR Generator
  (`module-2-team/30-aar-generator/`) to produce the human-readable
  retro lesson before the team forgets.

You can override the composition graph at construction time:

```python
from vstack.lewin import LEWIN_COMPOSITION

# Inspect the default graph.
print(LEWIN_COMPOSITION)

# Add your own downstream pattern.
LEWIN_COMPOSITION["environmental"]["custom_factor"] = ["your_pattern"]
```

---

## Baseline drift detection

The diagnostic supports baselines for regression detection:

```python
from vstack.lewin import record_baseline, load_baseline, compare_to_baseline

# After the first clean run, record a baseline.
record_baseline(detection, "baselines/qa-bot-001-v4.6.json")

# On every subsequent run, compare.
baseline = load_baseline("baselines/qa-bot-001-v4.6.json")
drift = compare_to_baseline(detection, baseline)

if drift.locus_shifted:
    alert("Lewin locus shifted from %s to %s" % (drift.from_locus, drift.to_locus))
```

A *silent locus shift* is the single most common signal that
something has regressed without anyone noticing. The CI integration
treats `locus_shifted` as a P1 alert.

---

## Anti-patterns and FAQ

**"Lewin always says environmental. Is that bias?"**

It will report whatever the trace + covariance signal supports. In
practice, environmental locus is more common because most teams have
an attribution bias *toward* the internal locus — they reach for
"the model is bad" first and the prompts are silently
under-engineered. The OVERTURNS verdict is doing its job when this
happens.

**"Can I run Lewin without a covariance signal?"**

Yes, but the result is weaker. `standard` mode degrades gracefully —
it reports a locus with reduced confidence. `forensic` mode requires
all three covariance dimensions; without them it'll either ask or
fall back to standard.

**"How is this different from the Goleman EI audit?"**

Lewin asks *where* the failure is (model vs scaffolding). Goleman
asks *what kind* of failure it is when the failure is in an
emotionally-coloured interaction. They compose — Lewin first
(locus), then Goleman (competence type if the locus is internal +
affective).

**"What does `forensic` mode cost?"**

Four LLM calls per trace. On a flagship model the typical cost
is ~$0.40 per trace at default sampling. The cost is tracked in
`detection.cost_summary` and aggregated via
`vstack.aar.record_llm_call()`.

---

## Reference

- Source: [`module-1-individual/01-lewin-formula/lib/`](./lib/)
- Schema: [`lib/schema.py`](./lib/schema.py)
- Prompts: [`lib/prompts.py`](./lib/prompts.py)
- Playbooks: [`lib/_playbooks.py`](./lib/_playbooks.py)
- Demo: [`demo/`](./demo/)
- Tests: [`tests/`](./tests/)
- Essay: [`essay.md`](./essay.md)
- Citations: [`lib/CITATIONS.md`](./lib/CITATIONS.md)
- Pattern README: [`README.md`](./README.md)
- Cookbook: [`examples/cookbook/01_lewin_locus_check.py`](../../examples/cookbook/01_lewin_locus_check.py)
