# Tutorial 03 — Integrating vstack with your agent framework

vstack ships first-class adapters for seven popular agent
frameworks. The integration shape is the same in every case:

1. Build your agent with the framework as usual.
2. Wrap its trace in the corresponding adapter.
3. Hand the result to any vstack pattern (or to `diagnose()`).

The adapter takes care of converting framework-specific trace
structures (LangGraph state graphs, CrewAI agent rosters, AutoGen
chat histories, etc.) into the canonical vstack `AgentTrace` /
`MultiAgentTrace` / `MultiAgentSafetyTrace` / etc. models.

## Install

Each adapter is a vstack extra:

```bash
pip install 'valanistack[langchain]'      # langchain ChatModel + Runnable
pip install 'valanistack[langgraph]'      # langgraph StateGraph + checkpointer
pip install 'valanistack[crewai]'         # crewai Agent + Crew + Task
pip install 'valanistack[autogen]'        # autogen ConversableAgent
pip install 'valanistack[llamaindex]'     # llamaindex Workflow + Event
pip install 'valanistack[pydantic_ai]'    # pydantic_ai Agent
```

OpenAI Assistants and a generic JSON adapter ship in the base wheel.

## LangChain

```python
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

from vstack.adapters.langchain import LangChainTraceAdapter
from vstack.diagnose import diagnose

# 1. Your existing chain
llm = ChatAnthropic(model="claude-sonnet-4-6")
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a careful debugger."),
    ("user", "{question}"),
])
chain = prompt | llm

# 2. Wrap the chain with the adapter
traced_chain = LangChainTraceAdapter(chain)

# 3. Run as normal; the adapter captures the trace
response = traced_chain.invoke({"question": "why is migration 0042 failing?"})

# 4. Diagnose
report = diagnose(trace=traced_chain.trace(), llm_client=llm)
print(report.to_markdown())
```

## LangGraph

```python
from langgraph.graph import StateGraph

from vstack.adapters.langgraph import LangGraphTraceAdapter
from vstack.diagnose import diagnose

# Build your StateGraph as normal
workflow = StateGraph(MyState)
workflow.add_node("planner", planner_node)
workflow.add_node("executor", executor_node)
workflow.add_edge("planner", "executor")
graph = workflow.compile()

# Wrap with the adapter
traced_graph = LangGraphTraceAdapter(graph)

# Invoke as normal
result = traced_graph.invoke({"task": "..."})

# Diagnose -- the adapter exposes both single-agent and multi-agent views
report = diagnose(trace=traced_graph.team_trace(), llm_client=llm)
```

## CrewAI

```python
from crewai import Agent, Crew, Task

from vstack.adapters.crewai import CrewAITraceAdapter
from vstack.diagnose import diagnose

researcher = Agent(role="Researcher", ...)
writer = Agent(role="Writer", ...)
crew = Crew(agents=[researcher, writer], tasks=[Task(...)])

# Wrap
traced_crew = CrewAITraceAdapter(crew)
result = traced_crew.kickoff()

# Diagnose -- crew traces map to vstack's MultiAgentTrace shape
report = diagnose(trace=traced_crew.trace(), recipe="agents_arguing")
```

## AutoGen

```python
from autogen import ConversableAgent, GroupChat, GroupChatManager

from vstack.adapters.autogen import AutoGenTraceAdapter
from vstack.diagnose import diagnose

agent_a = ConversableAgent(...)
agent_b = ConversableAgent(...)
chat = GroupChat(agents=[agent_a, agent_b], messages=[])
manager = GroupChatManager(groupchat=chat)

# Wrap
traced_manager = AutoGenTraceAdapter(manager)

agent_a.initiate_chat(traced_manager, message="...")

report = diagnose(trace=traced_manager.trace(), recipe="debate_pathology")
```

## LlamaIndex Workflows

```python
from llama_index.core.workflow import Workflow, step

from vstack.adapters.llamaindex import LlamaIndexTraceAdapter
from vstack.diagnose import diagnose

class MyWorkflow(Workflow):
    @step
    async def step_one(self, ev): ...

traced = LlamaIndexTraceAdapter(MyWorkflow())
await traced.run(...)

report = diagnose(trace=traced.trace())
```

## Pydantic-AI

```python
from pydantic_ai import Agent

from vstack.adapters.pydantic_ai import PydanticAITraceAdapter
from vstack.diagnose import diagnose

agent = Agent("anthropic:claude-sonnet-4-6", deps_type=...)

traced_agent = PydanticAITraceAdapter(agent)
result = await traced_agent.run(...)

report = diagnose(trace=traced_agent.trace())
```

## OpenAI Assistants

```python
from openai import OpenAI

from vstack.adapters.openai_assistants import OpenAIAssistantsTraceAdapter
from vstack.diagnose import diagnose

client = OpenAI()
assistant = client.beta.assistants.retrieve("asst_...")

traced = OpenAIAssistantsTraceAdapter(client, assistant)
thread = traced.create_thread()
traced.add_message(thread.id, "Help me debug...")
run = traced.create_run(thread.id)
traced.poll_until_complete(run.id)

report = diagnose(trace=traced.trace(thread.id))
```

## Going the other direction: a generic JSON adapter

If your framework isn't in the list above, you can hand-craft a
trace in the canonical vstack shape and feed it straight to
`diagnose()`. The runner only requires attribute presence
(`steps` → individual, `agents` + `messages` → team,
`org_chart` → org). Everything else is optional.

```python
from types import SimpleNamespace

from vstack.diagnose import diagnose

trace = SimpleNamespace(
    goal="...",
    steps=[
        SimpleNamespace(type="thought", content="...", timestamp=...),
    ],
    outcome="...",
    success=False,
)

report = diagnose(trace=trace, llm_client=...)
```

The shape inference walks attribute presence, so a `SimpleNamespace`
or a `pydantic.BaseModel` or a `dict` (via attribute proxy) all work.

## Mixing frameworks

You can run vstack analysis on a trace assembled from multiple
framework integrations. For instance, capture the LangGraph
planner's reasoning trace separately from the CrewAI executor crew's
messages, then run two diagnoses and compose the findings:

```python
planner_report = diagnose(trace=langgraph_planner_trace, ...)
executor_report = diagnose(trace=crewai_executor_trace, ...)

combined_findings = planner_report.findings + executor_report.findings
combined_findings.sort(key=lambda f: -f.severity_rank())
```

The `Finding` dataclass is framework-agnostic, so this composition
works regardless of where the upstream traces came from.

## See also

- `examples/langchain_demo.py` — runnable end-to-end LangChain demo
- `examples/langgraph_demo.py` — runnable LangGraph demo
- `examples/crewai_demo.py` — runnable CrewAI demo
- `examples/autogen_demo.py` — runnable AutoGen demo
- `examples/llamaindex_demo.py` — runnable LlamaIndex demo
- `examples/pydantic_ai_demo.py` — runnable Pydantic-AI demo
- `examples/openai_assistants_demo.py` — runnable OpenAI Assistants demo
