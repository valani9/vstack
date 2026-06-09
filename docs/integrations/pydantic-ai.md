# Pydantic-AI Integration Playbook

> Goal: integrate vstack diagnostics into Pydantic-AI agents.
> Pydantic-AI's strongly-typed agent interface makes vstack
> integration particularly clean. Covers the adapter, type-safe
> trace mapping, and the 8 patterns most useful in
> Pydantic-AI workloads.

---

## When to use vstack with Pydantic-AI

Pydantic-AI is the type-first agent framework. The integration
sweet spot:

- A typed agent is producing structurally-valid but semantically-
  wrong outputs.
- A multi-agent system using `RunContext` is dropping context
  across handoffs.
- Tool calls are validated by Pydantic but logically incorrect.
- You want pre-deployment diagnostics on a strongly-typed agent.

---

## Install

```bash
pip install valanistack pydantic-ai
```

---

## Quick start — diagnose a Pydantic-AI run

```python
from pydantic_ai import Agent, RunContext
from pydantic import BaseModel

from vstack.adapters.pydantic_ai_adapter import pydantic_ai_to_agent_trace
from vstack import diagnose


class TaskOutput(BaseModel):
    answer: str
    confidence: float
    sources: list[str]


agent = Agent("anthropic:flagship", result_type=TaskOutput)


@agent.tool
def search(ctx: RunContext, query: str) -> list[str]:
    return ["..."]


# Run.
result = agent.run_sync("Find 5 sources on transformer scaling.")

# Convert to vstack trace.
trace = pydantic_ai_to_agent_trace(
    run_result=result,
    goal="Find 5 verified sources on transformer scaling.",
)

# Diagnose.
report = diagnose(trace=trace, llm_client=llm)
print(report.to_markdown())
```

---

## Patterns most useful for Pydantic-AI

### 1. Trust Triangle (`#18`)

Pydantic-AI guarantees *structural* validity — the output is the
right shape. Trust Triangle audits *semantic* validity — is the
shape's content trustworthy?

### 2. Motivation Traps (`#09`)

When the result_type has a `confidence` field, models often game
it. Motivation Traps identifies the confidence trap.

### 3. Lewin (`#01`)

When a typed output is wrong, was it the model or the type
constraints? Lewin distinguishes.

### 4. Stone-Heen Triggers (`#22`)

In multi-turn agents, feedback rejection on validation errors is
common. Stone-Heen identifies which trigger fired.

### 5. Johari (`#03`)

The typed schema is the agent's *claimed* capability. Johari
checks whether the *actual* behaviour matches.

### 6. Yerkes-Dodson (`#06`)

Complex Pydantic schemas (deeply nested, many fields) increase
cognitive load. Yerkes-Dodson identifies the saturation point.

### 7. SMART Goal Generator (`#24`)

Pydantic-AI's `result_type` is the goal's measurability. Run
SMART to verify the type contract matches the user need.

### 8. AAR (`#30`)

Per-run retro on typed outputs.

---

## Trace capture from Pydantic-AI

### Sync runs

```python
result = agent.run_sync("...")
trace = pydantic_ai_to_agent_trace(run_result=result, goal="...")
```

### Async runs

```python
result = await agent.run("...")
trace = pydantic_ai_to_agent_trace(run_result=result, goal="...")
```

### Streaming runs

```python
async with agent.run_stream("...") as result:
    async for chunk in result.stream():
        process(chunk)

trace = pydantic_ai_to_agent_trace(run_result=result, goal="...")
```

### Multi-turn with context

```python
context = {"user_id": "...", "session_id": "..."}
result = agent.run_sync("...", deps=context)

trace = pydantic_ai_to_agent_trace(
    run_result=result,
    goal="...",
    context_field_path="deps",
)
```

---

## Type-aware diagnostics

Pydantic-AI's type system lets vstack run *type-aware* diagnostics.
For example, when the result type has a `confidence` field, the
diagnostic can check calibration directly:

```python
from vstack.adapters.pydantic_ai_adapter import audit_confidence_field

calibration_error = audit_confidence_field(
    runs=[run1, run2, run3, ...],
    ground_truth_field="actual_correctness",
)

if calibration_error > 0.2:
    # Run Bias Stack + HEXACO H-factor to surface overconfidence.
    pass
```

When the result type has a `sources` field that's expected to
be verifiable, the diagnostic auto-runs citation verification:

```python
from vstack.adapters.pydantic_ai_adapter import audit_sources_field

unverified_pct = audit_sources_field(
    runs=[run1, run2, ...],
    source_field="sources",
    verifier=resolve_doi,
)
```

---

## Common Pydantic-AI pathologies

### Structurally valid, semantically wrong

The output passes Pydantic validation but the values are wrong.

Run: **Trust Triangle Authenticity leg** + **Lewin**.

Common fix: tighten the field validators (e.g., `confidence: float
= Field(ge=0.0, le=1.0)` instead of `confidence: float`).

### Confidence inflation

The `confidence` field is consistently high but accuracy is low.

Run: **Motivation Traps** (confidence trap) + **HEXACO H-factor**
+ **Bias Stack** (overconfidence).

Common fix: add a calibration loss to the eval; reward calibrated
confidence, not high confidence.

### Source fabrication

The `sources` field returns plausible-looking but invalid sources.

Run: **Motivation Traps** (citation trap) + **Hallucination
Cascade recipe**.

Common fix: post-validation source resolver; reject runs with
unresolvable sources.

### Type-constraint over-specialization

A complex result type works on benchmark inputs but breaks on
production inputs.

Run: **Johari Window** + **Yerkes-Dodson** + **Lewin**.

Common fix: simpler result type with structured optional fields.

---

## Production wiring

```python
from pydantic_ai import Agent
from vstack.adapters.pydantic_ai_adapter import pydantic_ai_to_agent_trace
from vstack import diagnose
from vstack.aar import AARAnalyzer
from vstack.dashboard import render_report

def diagnosed_run(agent: Agent, prompt: str, goal: str):
    result = agent.run_sync(prompt)
    trace = pydantic_ai_to_agent_trace(run_result=result, goal=goal)

    report = diagnose(trace=trace, llm_client=llm)

    if any(f.severity == "high" for f in report.findings):
        aar = AARAnalyzer(llm).run(trace, prior_findings=report.findings)
        persist_lesson(aar.lessons)

    html = render_report(report)
    write_html_report(html)

    return result
```

---

## See also

- LangChain integration: [`langchain.md`](./langchain.md)
- AutoGen integration: [`autogen.md`](./autogen.md)
- Single-agent recipe: `examples/cookbook/22_overconfidence_spiral.py`
