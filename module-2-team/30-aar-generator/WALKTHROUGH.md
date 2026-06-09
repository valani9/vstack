# Walkthrough — AAR (After-Action Review) Generator

> Goal: end-to-end recipes for producing structured After-Action
> Reviews from agent traces. The AAR is the canonical post-failure
> learning artifact — a 4-question structure (What was supposed to
> happen / What actually happened / What went well / What to
> change) borrowed from the U.S. Army's training doctrine. Every
> example uses `StubClient`.

---

## When to reach for this pattern

AAR is the right call when **a multi-agent task has completed
(success or failure) and the learning needs to be captured before
it's lost**. The AAR is the unit of permanent organisational
memory; it composes with every other vstack pattern.

Signals AAR is the right pattern:

- Any task with a clear start + end.
- A failure whose root cause needs to be documented.
- A success worth recording as a pattern for reuse.
- A retro about a multi-day pipeline run.

Signals AAR is **not** the right first pattern:

- The task is still in-flight — wait until completion.
- The failure mode is already documented in a recipe — link to it
  rather than re-AAR.

---

## The four-question structure

1. **What was supposed to happen?** — the planned outcome and the
   conditions for success.
2. **What actually happened?** — the observed outcome.
3. **What went well?** — the practices to keep.
4. **What needs to change?** — concrete behaviour changes for next
   time.

The AAR ends with a **Lessons** section: 2-5 permanent rules that
should propagate to other tasks.

---

## Scenario 1 — AAR for a failed migration

```python
from vstack.aar.clients import StubClient
from vstack.aar import (
    AARAnalyzer,
    AgentTrace,
    TraceStep,
)

trace = AgentTrace(
    agent_id="migration-bot-007",
    goal="Run schema migration M042 + verify zero data loss.",
    steps=[
        TraceStep(type="input", content="Run M042."),
        TraceStep(type="tool_call", content="psql -f M042.sql"),
        TraceStep(type="observation", content="ERROR: column users.tier does not exist"),
        TraceStep(type="output", content="Migration failed; rolled back."),
    ],
    outcome="Failed; staging-vs-prod schema drift detected.",
    success=False,
)

aar = AARAnalyzer(StubClient(), mode="standard").run(trace)
print(aar.to_markdown())
```

Expected output: a structured AAR identifying staging-prod schema
drift as the root cause. Lessons include "stage-prod-parity gate
before migration" and "auto-detect schema drift before tool_call."

---

## Scenario 2 — AAR for a successful complex task

```python
trace = AgentTrace(
    agent_id="research-pipeline-001",
    goal="Produce verified literature summary of 5 papers on topic X.",
    steps=[
        TraceStep(type="tool_call", content="search('topic X', 2024+)"),
        TraceStep(type="observation", content="20 candidates"),
        TraceStep(type="tool_call", content="filter(verifiable=True)"),
        TraceStep(type="observation", content="5 verified sources"),
        TraceStep(type="output", content="Summary delivered."),
    ],
    outcome="Delivered; cited by downstream consumer.",
    success=True,
)

aar = AARAnalyzer(StubClient(), mode="standard").run(trace)
```

Expected output: AAR captures the *successful* pattern as reusable:
"PLUS: pre-filtered for verifiability before summarisation." This
becomes a recipe in the catalogue.

---

## Scenario 3 — AAR with composed pattern findings

```python
from vstack import diagnose

trace = AgentTrace(
    agent_id="codegen-bot-014",
    goal="Implement feature X with tests passing.",
    steps=[...],
    outcome="Implementation shipped with regression.",
    success=False,
)

diagnosis = diagnose(trace, llm_client=StubClient())
aar = AARAnalyzer(StubClient(), mode="standard").run(
    trace, prior_findings=diagnosis.findings,
)
```

When AAR is composed with a `diagnose()` pre-pass, it incorporates
the prior findings as evidence. The Lessons section is correspondingly
more specific — it references the named pattern (Lewin, GRPI, etc.)
rather than generic post-mortem language.

---

## Scenario 4 — AAR for a multi-day pipeline retro

```python
trace = AgentTrace(
    agent_id="research-pipeline-week-22",
    goal="Run weekly research summary pipeline for 5 topics.",
    steps=[
        TraceStep(type="input", content="topic 1"),
        TraceStep(type="output", content="success"),
        TraceStep(type="input", content="topic 2"),
        TraceStep(type="output", content="success"),
        TraceStep(type="input", content="topic 3"),
        TraceStep(type="output", content="failure: cite check timeout"),
        TraceStep(type="input", content="topic 4"),
        TraceStep(type="output", content="success"),
        TraceStep(type="input", content="topic 5"),
        TraceStep(type="output", content="success"),
    ],
    outcome="4/5 delivered; topic 3 failed.",
    success=False,
)

aar = AARAnalyzer(StubClient(), mode="forensic").run(trace)
```

Forensic mode runs a deeper analysis on the single-topic failure
and surfaces whether it was an isolated infra issue or a pattern
that will recur.

---

## Scenario 5 — Healthy AAR baseline

```python
aar_baseline = AARAnalyzer(StubClient(), mode="standard").run(success_trace)

from vstack.aar import record_baseline
record_baseline(aar_baseline, "baselines/research-001-aar.json")
```

Baselining a successful AAR records the *gold standard* lessons so
later regressions can be flagged when those lessons reverse.

---

## CLI walkthrough

```bash
vstack-aar generate --trace trace.json --mode quick
vstack-aar generate --trace trace.json --mode standard --pretty
vstack-aar generate --trace trace.json --mode forensic --pretty --diagnose
vstack-aar compose
vstack-aar schema --target trace
```

---

## Composition — what to run BEFORE AAR

AAR is usually the *last* pattern in a chain. Run [Lewin](../../module-1-individual/01-lewin-formula/WALKTHROUGH.md)
for failure locus + targeted patterns based on shape, then write
the AAR with the prior findings as evidence.

The recommended sequence:

1. [Lewin](../../module-1-individual/01-lewin-formula/WALKTHROUGH.md) — locus.
2. Named patterns based on shape:
   - team failure → [GRPI](../13-grpi-working-agreement/WALKTHROUGH.md)
   - affective failure → [Goleman EI](../../module-1-individual/02-goleman-ei-audit/WALKTHROUGH.md)
   - decision failure → [Bias Stack](../27-bias-stack-detector/WALKTHROUGH.md)
3. [AAR](.) — write the lessons.

---

## Async fan-out

```python
import asyncio
from vstack.aar import AARAnalyzerAsync
from vstack.aar.clients import AsyncStubClient

async def fan_out(traces):
    analyzer = AARAnalyzerAsync(AsyncStubClient(), mode="standard")
    return await asyncio.gather(*(analyzer.run(t) for t in traces))
```

---

## Anti-patterns and FAQ

**"My team writes AARs but doesn't act on them."**

Check whether the Lessons section names *behaviours* or *outcomes*.
Behaviours change; outcomes don't. "Lesson: improve testing"
doesn't specify a behaviour. "Lesson: run typecheck before
claiming done" does.

**"How are AAR lessons different from a regular post-mortem?"**

AAR lessons are *forward-looking behaviour changes*, not backward-
looking analysis. The structural prompt explicitly asks "what will
you do differently next time" — that's where lessons differ from
narrative summary.

**"Forensic mode cost?"**

Four LLM calls per trace; typical $0.55 on a flagship model.

---

## Reference

- Source: [`module-2-team/30-aar-generator/lib/`](./lib/)
- Schema: [`lib/schema.py`](./lib/schema.py)
- Prompts: [`lib/prompts.py`](./lib/prompts.py)
- Demo: [`demo/`](./demo/)
- Tests: [`tests/`](./tests/)
- Essay: [`essay.md`](./essay.md)
- Pattern README: [`README.md`](./README.md)
