# LangChain Integration Playbook

> Goal: integrate vstack diagnostics into a LangChain agent pipeline.
> Covers the `langchain-core` adapter, common trace shapes, and the
> 8 vstack patterns most useful in LangChain-shaped workloads.

---

## When to use vstack with LangChain

LangChain is the most common framework for agent scaffolding in
production. The integration sweet spot:

- You have a LangChain `AgentExecutor` or `Runnable` that's failing
  in production.
- You have a multi-step chain whose intermediate steps degrade in
  quality.
- You have a multi-agent setup using LangGraph and want to detect
  coordination issues.
- You want pre-flight diagnostics on a prompt change before
  promoting to production.

---

## Install

```bash
pip install valanistack langchain langchain-core langchain-anthropic
```

The `langchain-core` adapter is bundled in vstack but optional —
LangChain isn't required unless you're integrating.

---

## Quick start — diagnose a LangChain run

```python
from langchain_core.runnables import RunnablePassthrough
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

from vstack.adapters.langchain_core import langchain_to_agent_trace
from vstack import diagnose

# 1. Build the chain as usual.
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant."),
    ("human", "{question}"),
])
llm = ChatAnthropic(model="anthropic-claude-flagship")
chain = prompt | llm | RunnablePassthrough()

# 2. Run with callbacks that capture the trace.
result = chain.invoke({"question": "What is RAG?"})

# 3. Convert the LangChain run output to a vstack trace.
trace = langchain_to_agent_trace(
    chain_run=result,
    goal="Explain RAG to a junior engineer.",
)

# 4. Diagnose.
report = diagnose(trace=trace, llm_client=llm)
print(report.to_markdown())
```

The adapter handles the LangChain → vstack trace mapping
automatically — you don't construct `AgentTrace` by hand.

---

## Patterns most useful for LangChain

These 8 patterns map directly onto LangChain-shaped failure modes:

### 1. Lewin Attribution (`#01`)

LangChain agents fail in 3 places: the model, the prompt template,
or the tool wrapper. Lewin tells you *which*. Run after any
single-agent failure.

```python
from vstack.lewin import LewinAttributionDetector

detector = LewinAttributionDetector(llm)
detection = detector.run(trace, mode="forensic")

if detection.locus == "environmental":
    # It's the prompt or tool wrapper, not the model.
    edit_the_template(detection.top_intervention)
elif detection.locus == "internal":
    # The model itself is the issue.
    consider_model_swap(detection.top_intervention)
```

### 2. Yerkes-Dodson Workload (`#06`)

LangChain runs that aggregate retrieval context are particularly
vulnerable to context saturation. Yerkes-Dodson identifies the
saturation point.

```python
from vstack.yerkes_dodson import YerkesDodsonWorkloadDetector

detector = YerkesDodsonWorkloadDetector(llm)
result = detector.run(trace, mode="standard")

if result.arousal_region == "HIGH":
    # Reduce retrieved chunk count or summarize before injection.
    reduce_context_size(target_occupancy=0.40)
```

### 3. Motivation Traps (`#09`)

LangChain has a tendency to over-call tools because the eval
metric implicitly rewards complexity. Motivation Traps surfaces
the trap.

### 4. McGregor Orchestrator Mode (`#11`)

LangGraph workflows with a coordinator + workers often slip into
Theory-X (coordinator verifies every worker output). McGregor
identifies this.

### 5. GRPI (`#13`)

LangGraph multi-agent setups fail at the Goals or Roles layer
more often than at Trust. GRPI is the first call on any
LangGraph failure.

### 6. Process Gain/Loss (`#14`)

LangChain teams produce process loss when intermediate steps
duplicate work or strip context. Run after any team setup.

### 7. Trust Triangle (`#18`)

LangChain sub-agents often produce technically-correct outputs
that downstream consumers can't trust. Trust Triangle identifies
which leg.

### 8. AAR (`#30`)

After any LangChain task completes (success or failure), AAR is
the canonical retro output. Persist the lessons.

---

## Trace capture from LangChain

### Synchronous chains

```python
from langchain_core.runnables import RunnableConfig
from vstack.adapters.langchain_core import LangChainTraceCallback

callback = LangChainTraceCallback(goal="...")
config = RunnableConfig(callbacks=[callback])

result = chain.invoke({"question": "..."}, config=config)
trace = callback.get_trace()
```

### Async chains

```python
from vstack.adapters.langchain_core import LangChainAsyncTraceCallback

callback = LangChainAsyncTraceCallback(goal="...")
config = RunnableConfig(callbacks=[callback])

result = await chain.ainvoke({"question": "..."}, config=config)
trace = await callback.aget_trace()
```

### Streaming chains

```python
callback = LangChainTraceCallback(goal="...")
config = RunnableConfig(callbacks=[callback])

for chunk in chain.stream({"question": "..."}, config=config):
    process(chunk)

trace = callback.get_trace()
```

---

## LangGraph multi-agent integration

LangGraph's StateGraph workflows map onto vstack's `team` trace
shape. The adapter handles the conversion.

```python
from langgraph.graph import StateGraph
from vstack.adapters.langchain_core import langgraph_to_team_trace

# Your existing LangGraph workflow.
graph = StateGraph(...)
# ... node definitions ...

# Run the workflow with trace capture.
result = graph.invoke({"messages": [...]})

# Convert to vstack team trace.
trace = langgraph_to_team_trace(
    graph_result=result,
    goal="Multi-agent code-review pipeline.",
)

# Diagnose.
from vstack import diagnose
report = diagnose(trace=trace, llm_client=llm, recipe="agents_arguing")
```

---

## Common gotchas

### Tool name mapping

LangChain's tool names sometimes include framework-specific
prefixes (`tool_call_id` etc.). The adapter normalizes these.

If you have custom tool names that look meaningful but won't be
verified, the adapter has a `tool_name_map` parameter:

```python
trace = langchain_to_agent_trace(
    chain_run=result,
    goal="...",
    tool_name_map={"_internal_rag_v3": "rag_search"},
)
```

### Streaming token-level traces

By default the adapter captures at message granularity, not token
granularity. For token-level analysis, pass
`capture_granularity="token"`.

### Memory backends

If your LangChain agent uses a memory backend (Redis, Postgres,
etc.), the trace captures the *retrieved* memory, not the *full
memory*. For full-memory analysis, run `Schein Iceberg` against the
memory store directly.

---

## End-to-end pipeline

A production-ready integration looks like:

```python
from langchain_core.runnables import RunnableConfig
from vstack.adapters.langchain_core import LangChainTraceCallback
from vstack import diagnose
from vstack.aar import AARAnalyzer
from vstack.dashboard import DashboardConfig, render_report

def diagnosed_invoke(chain, inputs, goal: str):
    callback = LangChainTraceCallback(goal=goal)
    config = RunnableConfig(callbacks=[callback])

    result = chain.invoke(inputs, config=config)
    trace = callback.get_trace()

    # Diagnose with the shape-default bundle.
    report = diagnose(trace=trace, llm_client=llm)

    if not trace.success:
        # Write an AAR for the failure.
        aar = AARAnalyzer(llm).run(trace)
        persist_lesson(aar.lessons)

    # Render an HTML report.
    html = render_report(report, config=DashboardConfig(title=goal))
    write_html_report(html)

    return result

# Use it like any LangChain Runnable call:
result = diagnosed_invoke(chain, {"question": "..."}, goal="...")
```

---

## See also

- LangChain-specific [composition graphs](../composition.md#langchain)
- Adapter source: `_adapters/lib/langchain_core_adapter.py`
- LangGraph example: `examples/cookbook/09_bottleneck_orchestrator.py`
- Live LangChain demo: `examples/patterns/01_lewin.py`
