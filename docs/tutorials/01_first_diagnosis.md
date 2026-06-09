# Tutorial 01 — Your first vstack diagnosis

This is the 15-minute path from "I have an agent that's misbehaving"
to "I have a structured diagnosis with ranked findings and concrete
interventions."

## Prerequisites

```bash
pip install valanistack[anthropic]
export ANTHROPIC_API_KEY="sk-ant-..."
```

If you don't have an Anthropic API key, every example in this
tutorial also runs with the built-in `StubClient` — the structure of
the diagnosis is the same; only the LLM-driven analysis text changes.

## The premise

Suppose you have an agent that was supposed to apply a database
migration. The migration failed because the data wasn't in the state
the migration assumed (duplicate emails before adding a unique
constraint). Instead of investigating *why*, the agent retried the
same `ALTER TABLE` four times with minor variations and gave up.

In code, the trace looks like this:

```python
from datetime import datetime, timedelta, timezone

from vstack.aar import AgentTrace, TraceStep

base = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
trace = AgentTrace(
    goal="Apply migration 0042_user_email_unique to production.",
    steps=[
        TraceStep(
            timestamp=base,
            type="tool_call",
            content="ALTER TABLE users ADD CONSTRAINT ... UNIQUE (email)",
        ),
        TraceStep(
            timestamp=base + timedelta(seconds=8),
            type="observation",
            content="ERROR: Key (email)=(test@example.com) is duplicated.",
        ),
        TraceStep(
            timestamp=base + timedelta(seconds=12),
            type="tool_call",
            content="ALTER TABLE users ADD CONSTRAINT ... UNIQUE (email)",
        ),
        # ... three more retries with the same root cause ...
    ],
    outcome="Migration not applied. Agent never investigated WHY.",
    success=False,
    retry_count=3,
)
```

## The diagnosis

```python
from vstack.aar.clients import AnthropicClient
from vstack.diagnose import diagnose

report = diagnose(
    trace=trace,
    llm_client=AnthropicClient(),
    recipe="stuck_in_loop",   # the canonical recipe for this failure mode
)

print(report.to_markdown())
```

The runner:

1. **Infers trace shape** from attribute presence (here, `steps` →
   `individual` shape).
2. **Picks the bundle** based on the `recipe` slug. Without a recipe,
   it would use the shape-default bundle.
3. **Runs each pattern** with per-pattern error isolation. If one
   pattern raises, the others still produce findings; the failure
   appears in `report.errors` instead of aborting the run.
4. **Extracts findings** from each pattern's result via the smart
   adapter (`vstack.diagnose.adapters.extract_findings`). For
   patterns that emit a structured evidence list (Bias Stack's 4
   biases, Lewin's 3 loci, etc.), each evidence entry becomes its own
   `Finding`.
5. **Ranks the findings** by severity (highest first), then by
   pattern id (lowest first), so reports read top-down in the order a
   debugger would want to act on them.

## What you get back

A `DiagnoseReport` with:

- `findings: list[Finding]` — the ranked, merged view. This is what
  most users read.
- `per_pattern: list[PatternResult]` — the raw per-pattern result
  objects, preserved for callers who want the full structured detail.
- `errors: dict[str, str]` — pattern failures by name.
- `cost: CostSummary` — token + latency aggregation across the run,
  with per-pattern and per-model breakdowns.
- `cache_stats: CachingClientStats | None` — populated only when
  `cache=True` was passed; tells you the cache hit rate.

`report.to_markdown()` renders a self-contained markdown report
suitable for pasting into a PR description or Slack message.

## Picking a recipe

vstack ships 34 named recipes organized into 5 thematic clusters:

| Cluster        | Sample recipes                                          |
|----------------|---------------------------------------------------------|
| reasoning      | stuck_in_loop, hallucination_cascade, sycophancy_drift  |
| coordination   | agents_arguing, silent_dependency_drop, handoff_loss    |
| trust          | silent_failure, cold_handoff, performative_empathy      |
| workload       | context_saturation, decision_paralysis, role_thrash     |
| culture        | culture_drift, espoused_actual_drift, policy_decay      |

List them all:

```python
from vstack.diagnose import RECIPES, list_recipes_by_cluster

for cluster, recipes in list_recipes_by_cluster().items():
    print(f"== {cluster} ==")
    for r in recipes:
        print(f"  {r.name:30s} {r.description[:60]}")
```

If you don't know which recipe to pick, pass a free-text description
to `recipe_for_trigger()`:

```python
from vstack.diagnose import recipe_for_trigger

r = recipe_for_trigger("the agent keeps apologizing in circles")
# -> Recipe(name='over_apology_loop', ...)
```

The match is keyword-based: each recipe carries a `triggers` list of
phrases, and the first match wins. Returns `None` if nothing matches
— in that case, fall back to the shape-default bundle by omitting
`recipe`.

## Picking explicit patterns

When you know exactly which patterns you want, skip the recipe and
pass the slugs directly:

```python
report = diagnose(
    trace=trace,
    llm_client=AnthropicClient(),
    patterns=["lewin", "aar", "bias_stack"],
)
```

Patterns that don't fit the inferred shape (e.g., `lencioni` on an
individual-shape trace) are skipped with a warning rather than
raising.

## Cost tracking

Pass `cache=True` to share LLM responses across patterns in one run.
Two patterns that issue identical prompts only pay once:

```python
report = diagnose(
    trace=trace,
    llm_client=AnthropicClient(),
    recipe="stuck_in_loop",
    cache=True,
)
print(report.cache_stats)
# CachingClientStats(hits=4, misses=8, inserts=8, hit_rate=0.33)
```

The cost summary aggregates token usage, latency, and per-pattern
breakdown automatically — patterns just need to emit
`vstack.aar._telemetry.record_llm_call()` events (every shipped
pattern does this by default).

## What's next

- **Tutorial 02** — chaining patterns by hand for fine-grained
  control.
- **Tutorial 03** — wiring vstack into your existing agent
  framework (LangChain, LangGraph, CrewAI, AutoGen, LlamaIndex,
  Pydantic-AI, OpenAI Assistants).
- **Tutorial 04** — building a custom pattern.
- **Tutorial 05** — exposing the diagnose runner via MCP for use in
  Claude Desktop, Cursor, or Cline (uses the `vstack_diagnose` MCP
  tool added in v0.17.0).
- **Tutorial 06** — the FastAPI `/v1/diagnose` endpoint for
  programmatic access (v0.18.0+).
