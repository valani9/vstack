# LangGraph Integration Playbook

> Goal: integrate vstack diagnostics into LangGraph multi-agent
> workflows. Covers the StateGraph adapter, common multi-agent
> failure modes, and the 10 patterns most useful in LangGraph.

---

## When to use vstack with LangGraph

LangGraph is the standard for stateful multi-agent workflows. The
integration sweet spot:

- A `StateGraph` workflow is failing at coordination, not at any
  single node.
- Agents in the graph are duplicating work or producing
  inconsistent outputs.
- The graph has stalled (infinite revision loops, never reaching
  END).
- You want to audit a graph design before promoting to production.

---

## Install

```bash
pip install valanistack langgraph langchain-anthropic
```

---

## Quick start — diagnose a LangGraph run

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

from vstack.adapters.langchain_core import langgraph_to_team_trace
from vstack import diagnose

class State(TypedDict):
    messages: list
    plan: str | None

# Build the graph.
def planner(state: State) -> dict:
    # ...
    return {"plan": "..."}

def coder(state: State) -> dict:
    # ...
    return {"messages": state["messages"] + [{"role": "agent", "content": "..."}]}

def reviewer(state: State) -> dict:
    # ...
    return {"messages": state["messages"] + [{"role": "reviewer", "content": "..."}]}

graph = StateGraph(State)
graph.add_node("planner", planner)
graph.add_node("coder", coder)
graph.add_node("reviewer", reviewer)
graph.add_edge("planner", "coder")
graph.add_edge("coder", "reviewer")
graph.add_conditional_edges("reviewer", route_after_review, {"coder": "coder", "end": END})
graph.set_entry_point("planner")

compiled = graph.compile()

# Run.
result = compiled.invoke({"messages": [{"role": "user", "content": "..."}]})

# Convert to vstack team trace.
trace = langgraph_to_team_trace(
    graph_result=result,
    goal="3-agent code-review pipeline.",
)

# Diagnose.
report = diagnose(trace=trace, llm_client=llm, recipe="agents_arguing")
print(report.to_markdown())
```

---

## Patterns most useful for LangGraph

### 1. GRPI (`#13`)

LangGraph workflows almost always fail at Goals or Roles. GRPI is
the first call.

### 2. McGregor Orchestrator Mode (`#11`)

If the graph has a coordinator node, McGregor identifies whether
it's over-verifying (Theory-X) or under-verifying (Theory-Y).

### 3. Process Gain/Loss (`#14`)

Quantifies whether the graph's coordination overhead is paying for
itself.

### 4. Trust Triangle (`#18`)

Edges in the graph are trust relationships. Trust Triangle
audits each edge for Authenticity / Logic / Empathy.

### 5. Social Loafing (`#15`)

In a fan-out node (one orchestrator → many workers), Social
Loafing identifies underperforming workers.

### 6. Heffernan Superflocks (`#16`)

If all nodes use the same model, the graph is a superflock — high
benchmark, low robustness.

### 7. Group Pathology (`#26`)

Voting nodes in the graph are vulnerable to groupthink / polarization
/ contagion.

### 8. Span of Control (`#34`)

Identifies whether the coordinator node has too many or too few
sub-nodes.

### 9. Stone-Heen Triggers (`#22`)

Conditional edges that revise based on feedback can fire the wrong
trigger. Stone-Heen identifies which.

### 10. AAR (`#30`)

Persist a structured retro for each graph completion.

---

## Trace capture from LangGraph

### Whole-run capture

```python
from vstack.adapters.langchain_core import langgraph_to_team_trace

result = compiled.invoke({...})
trace = langgraph_to_team_trace(
    graph_result=result,
    goal="...",
)
```

### Per-node capture (for per-node diagnostics)

```python
from vstack.adapters.langchain_core import LangGraphNodeCallback

callback = LangGraphNodeCallback()
compiled = graph.compile().with_config(callbacks=[callback])
result = compiled.invoke({...})

per_node_traces = callback.get_traces_by_node()
for node_name, node_trace in per_node_traces.items():
    report = diagnose(trace=node_trace, llm_client=llm)
    print(f"=== Node {node_name} ===")
    print(report.to_markdown())
```

### Cyclic graphs

LangGraph's cyclic edges produce traces where the same node
appears multiple times. The adapter handles this with a
`cycle_iteration` field on each step.

---

## Common LangGraph pathologies and their vstack diagnoses

### Endless revision loops

`reviewer → coder → reviewer → coder → ...` indefinitely.

Run: **Stone-Heen Triggers** + **Group Pathology** + **Lencioni
Commitment layer**.

Common root cause: the reviewer's reject criteria are vague, so
the coder can't satisfy them. Use **SMART Goal Generator** to
rewrite the criteria.

### Orchestrator bottleneck

The graph stalls because the coordinator node serializes everything.

Run: **Span of Control** + **McGregor Orchestrator Mode** +
**Process Gain/Loss**.

Common root cause: Theory-X coordinator with too many sub-nodes.
Add a middle layer.

### Silent state corruption

The graph completes but the final state is wrong because an
intermediate node silently dropped a field.

Run: **Johari Window** + **Trust Triangle Authenticity leg** +
**Stone-Heen Triggers**.

Common root cause: a node's `return` is silently overwriting the
state field instead of merging. The adapter detects this.

### Conflicting node outputs

Two nodes return different values for the same state key; the
graph picks the second (silent override).

Run: **GRPI Roles layer** + **Trust Triangle**.

Common root cause: scope overlap between nodes. Each node should
own a *distinct* state field.

---

## Production wiring

```python
from langgraph.graph import StateGraph
from vstack.adapters.langchain_core import langgraph_to_team_trace
from vstack import diagnose
from vstack.aar import AARAnalyzer
from vstack.dashboard import render_report

def diagnosed_graph_run(compiled, inputs, goal: str):
    result = compiled.invoke(inputs)
    trace = langgraph_to_team_trace(graph_result=result, goal=goal)

    # Default bundle for team-shape traces.
    report = diagnose(trace=trace, llm_client=llm)

    if any(f.severity == "high" for f in report.findings):
        # Generate an AAR for high-severity findings.
        aar = AARAnalyzer(llm).run(trace, prior_findings=report.findings)
        persist_lesson(aar.lessons)

    # Render HTML for the dashboard.
    html = render_report(report)
    write_html_report(html)

    return result
```

---

## See also

- LangChain integration: [`langchain.md`](./langchain.md)
- Multi-agent recipe: `examples/cookbook/09_bottleneck_orchestrator.py`
- LangGraph composition graph: docs/composition.md#langgraph
