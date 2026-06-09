# Framework Integration Playbooks

vstack ships adapters for the major agent frameworks. Each playbook
covers when to use vstack with that framework, the trace-capture
mechanics, the most useful patterns for that framework's failure
modes, and an end-to-end production wiring snippet.

| Framework        | Playbook                          | Adapter                          |
|------------------|-----------------------------------|----------------------------------|
| LangChain        | [`langchain.md`](./langchain.md)  | `langchain_core_adapter.py`     |
| LangGraph        | [`langgraph.md`](./langgraph.md)  | `langchain_core_adapter.py`     |
| CrewAI           | [`crewai.md`](./crewai.md)        | `crewai_adapter.py`             |
| AutoGen          | [`autogen.md`](./autogen.md)      | `autogen_adapter.py`            |
| Pydantic-AI      | [`pydantic-ai.md`](./pydantic-ai.md) | `pydantic_ai_adapter.py`     |
| LlamaIndex       | [`llama-index.md`](./llama-index.md) | `llama_index_adapter.py`     |

## Framework-agnostic integration

If you're using a framework not listed above, use the
`vstack.aar.AgentTrace` schema directly:

```python
from vstack.aar import AgentTrace, TraceStep
from vstack import diagnose

trace = AgentTrace(
    goal="...",
    steps=[
        TraceStep(type="thought", content="..."),
        TraceStep(type="tool_call", content="..."),
        TraceStep(type="observation", content="..."),
        TraceStep(type="message", content="..."),
    ],
    outcome="...",
    success=False,
)

report = diagnose(trace=trace, llm_client=llm)
```

The schema accepts any agent trace with the standard step types
(thought / tool_call / observation / message / decision). vstack
doesn't care which framework produced it.

## When to write a custom adapter

You should write a custom adapter (and contribute it back to vstack)
if:

- Your framework has a structured trace format that's lossy
  through plain `TraceStep`.
- Your framework has multi-agent semantics (handoffs, roles,
  voting) that vstack's team-shape trace can express but plain
  conversion would lose.
- Your team relies on the framework heavily and a clean adapter
  is a real productivity win.

Adapter source: `_adapters/lib/`. Tests: `_adapters/tests/`.
