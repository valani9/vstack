# Tutorial 02 — Chaining patterns by hand

When you need fine-grained control over which patterns run, in what
order, and with what parameters, skip the `diagnose()` runner and
wire the patterns directly. This is also the path you'd take to
**compose** patterns: one pattern's output becomes another's input.

## When to chain

Use `diagnose()` when:

- you want the cross-pattern report
- you're routing based on shape / recipe
- you want cost + cache aggregation across the bundle

Use manual chaining when:

- one pattern's finding determines whether the next pattern runs
- you need to transform a pattern's output before feeding it to
  another
- you want to compose pattern-specific Pydantic models (e.g.,
  hand AAR's `Lesson` list to Lewin as `failure_factors`)

## Example: AAR → Lewin

The canonical chain is **AAR identifies what happened**, **Lewin
identifies whether the fix targets the agent (P) or the scaffold (E)**.

```python
from datetime import datetime, timezone

from vstack.aar import (
    AARGenerator,
    AgentTrace,
    TraceStep,
    new_run_id,
    run_context,
)
from vstack.aar.clients import AnthropicClient
from vstack.lewin import (
    AgentFailureTrace,
    FailureStep,
    LewinAttributionDetector,
)

# 1. The trace
trace = AgentTrace(
    goal="Refactor the auth module to use JWTs",
    steps=[
        TraceStep(
            timestamp=datetime(2026, 6, 8, tzinfo=timezone.utc),
            type="message",
            content="Created tokens but broke session middleware",
        ),
    ],
    outcome="JWT issuance works; session middleware broken; tests red",
    success=False,
)

client = AnthropicClient()

# 2. AAR identifies lessons
with run_context(run_id=new_run_id()):
    aar = AARGenerator(llm_client=client, mode="standard").run(trace)

print("AAR lessons:")
for lesson in aar.lessons:
    print(f"  {lesson.pattern}: {lesson.description}")

# 3. Convert AAR lessons into a Lewin failure trace
lewin_trace = AgentFailureTrace(
    agent_id="auth-refactor-agent",
    model_name="claude-sonnet-4-6",
    framework="custom",
    task=trace.goal,
    outcome=trace.outcome,
    success=trace.success,
    initial_attribution="internal",
    individual_factors=[],
    environmental_factors=[
        {
            "factor_id": f"env-{i}",
            "name": lesson.pattern,
            "description": lesson.description,
        }
        for i, lesson in enumerate(aar.lessons)
    ],
    steps=[
        FailureStep(
            step_index=i,
            content=step.content,
            timestamp=step.timestamp,
        )
        for i, step in enumerate(trace.steps)
    ],
)

# 4. Lewin attributes
lewin = LewinAttributionDetector(llm_client=client, mode="standard").run(
    lewin_trace
)

print("\nLewin attribution:")
for ev in lewin.locus_evidence:
    print(f"  {ev.locus}: {ev.score:.2f} ({ev.severity})")
print(f"\nDominant: {lewin.dominant_locus}")
```

The output tells you both *what* the lessons are (AAR) and *where to
intervene* (Lewin: the model itself, the scaffolding around it, or
the interaction between them).

## Example: Trust Triangle → Stone-Heen → Cognitive Reappraisal

A sycophancy-spiral diagnosis chain:

```python
# 1. Trust Triangle: is the wobble on authenticity?
trust = TrustTriangleDetector(llm_client=client).run(interaction_trace)

if trust.dominant_wobble == "authenticity":
    # 2. Stone-Heen: which trigger fired?
    triggers = StoneHeenTriggerDetector(llm_client=client).run(exchange)

    if triggers.dominant_trigger == "identity":
        # 3. Cognitive Reappraisal: what regulation strategy?
        reapp = CognitiveReappraisalDetector(llm_client=client).run(reg_trace)
        # reapp.dominant_strategy is likely "suppression"
```

Conditional chains let you spend LLM budget only on the patterns that
the upstream diagnosis indicates are worth running.

## Composition_target_pattern

Several pattern interventions return a `composition_target_pattern`
field that names the *next* vstack pattern the caller should run.
The runner doesn't follow these automatically — they're a hint for
the caller — but you can build a simple recursive chain:

```python
from vstack.diagnose import PATTERNS, diagnose

# Start with one pattern
report = diagnose(trace=trace, llm_client=client, patterns=["lencioni"])

# Walk composition handoffs (one level deep)
followups = set()
for pr in report.per_pattern:
    handoff = getattr(pr.result, "composition_handoff", None)
    if handoff and handoff.downstream_patterns:
        for slug in handoff.downstream_patterns:
            # Strip vstack. prefix if present
            slug = slug.removeprefix("vstack.")
            if slug in PATTERNS:
                followups.add(slug)

if followups:
    followup_report = diagnose(
        trace=trace, llm_client=client, patterns=list(followups)
    )
```

This pattern composes especially well with `cache=True` because the
upstream and downstream patterns often issue overlapping prompts
(same trace, same goal field).

## Async chains

Every pattern ships an async mirror (e.g.,
`LewinAttributionDetectorAsync`) under the same module. The
`diagnose_async()` runner uses them automatically. For manual
chains, await each analyzer:

```python
async def diagnose_async_chain(trace, client):
    async with anyio.create_task_group() as tg:
        results = {}
        tg.start_soon(_run_aar, trace, client, results)
        tg.start_soon(_run_lewin, trace, client, results)
    return results
```

The async mirrors share the same input + output Pydantic models so
the chain code is identical to the sync version, modulo `await`.
