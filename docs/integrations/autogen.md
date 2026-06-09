# AutoGen Integration Playbook

> Goal: integrate vstack diagnostics into AutoGen GroupChat
> multi-agent workflows. Covers the AutoGen adapter, message-based
> trace mapping, and the 8 patterns most useful in AutoGen
> workloads.

---

## When to use vstack with AutoGen

AutoGen is the GroupChat-based multi-agent framework. The
integration sweet spot:

- A GroupChat is stalling in deliberation.
- An agent in the chat has stopped engaging substantively.
- The chat's deliverable is shallower than each agent could
  produce solo.
- A two-agent ChatRound is in a feedback loop.

---

## Install

```bash
pip install valanistack autogen-agentchat
```

---

## Quick start — diagnose an AutoGen GroupChat

```python
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.task import Console, MaxMessageTermination

from vstack.adapters.autogen_adapter import autogen_to_team_trace
from vstack import diagnose

# Standard AutoGen setup.
planner = AssistantAgent(name="planner", ...)
coder = AssistantAgent(name="coder", ...)
reviewer = AssistantAgent(name="reviewer", ...)

team = RoundRobinGroupChat(
    [planner, coder, reviewer],
    termination_condition=MaxMessageTermination(max_messages=20),
)

# Run.
result = await team.run(task="...")

# Convert to vstack team trace.
trace = autogen_to_team_trace(
    team_result=result,
    goal="3-agent code-review pipeline.",
)

# Diagnose.
report = diagnose(trace=trace, llm_client=llm, recipe="agents_arguing")
print(report.to_markdown())
```

---

## Patterns most useful for AutoGen

### 1. Group Pathology (`#26`)

AutoGen GroupChats are particularly vulnerable to groupthink,
polarization, and behavioural contagion. Run on every multi-round
chat.

### 2. Glaser Conversation Steering (`#21`)

GroupChats often drift between conversational levels (transactional /
positional / transformational). Glaser identifies the level
mismatch.

### 3. Edmondson Psych Safety (`#20`)

Agents that don't challenge or admit uncertainty in GroupChats
collapse to consensus too fast. Edmondson measures the four
learning behaviours.

### 4. Stone-Heen Triggers (`#22`)

When agents reject each other's feedback, Stone-Heen identifies
which trigger fired.

### 5. Plus-Delta Feedback (`#23`)

GroupChat critique is often unstructured. Plus-Delta enforces a
testable feedback shape.

### 6. Thomas-Kilmann (`#29`)

Two-agent ChatRound disagreements get stuck in one conflict mode.
Thomas-Kilmann picks the right mode.

### 7. Devil's Advocate Separator (`#28`)

GroupChat consensus often suppresses dissent. Configure a
formal devil's advocate role.

### 8. AAR (`#30`)

Persist a structured retro for each chat completion.

---

## Trace capture from AutoGen

### RoundRobinGroupChat

```python
result = await team.run(task="...")
trace = autogen_to_team_trace(team_result=result, goal="...")
```

### SelectorGroupChat (selector-based agent picking)

The selector's reasoning is captured as a separate orchestrator
trace:

```python
trace, selector_trace = autogen_to_team_trace_with_selector(
    team_result=result,
    goal="...",
)

# Diagnose the selector separately.
from vstack.group_decision import DecisionStyleDetector
DecisionStyleDetector(llm).run(selector_trace)
```

### Swarm (handoff-based)

Swarm agents pass turn explicitly via tool calls. The adapter
captures these as `Handoff` records:

```python
trace = autogen_to_team_trace(
    team_result=result,
    goal="...",
    capture_handoffs=True,
)
```

---

## Common AutoGen pathologies

### Endless deliberation

GroupChat exceeds `max_messages` without convergence.

Run: **Group Pathology** + **Decision Models** + **Bias Stack**.

Common fix: pre-anchor decision style (AI / CI / GII) based on
stakes, not deliberation-by-default.

### Two-agent loop

Two agents in `ChatRound` enter a never-ending revision loop.

Run: **Stone-Heen Triggers** + **Plus-Delta Feedback** +
**Thomas-Kilmann**.

Common fix: tie-break rule on round 3 + Plus-Delta structured
feedback.

### Silent agent

One agent stops engaging substantively mid-chat.

Run: **SDT Reward** + **Social Loafing** + **Vroom Expectancy**.

Common fix: per-agent reward signal at end of chat.

### Selector picks wrong agent

SelectorGroupChat consistently picks the wrong agent for a task.

Run: **GRPI Roles layer** + **Decision Models**.

Common fix: tighten role definitions; the selector can't pick
right if roles overlap.

---

## Production wiring

```python
from vstack.adapters.autogen_adapter import autogen_to_team_trace
from vstack import diagnose
from vstack.aar import AARAnalyzer
from vstack.dashboard import render_report

async def diagnosed_team_run(team, task: str, goal: str):
    result = await team.run(task=task)
    trace = autogen_to_team_trace(team_result=result, goal=goal)

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

- LangGraph integration: [`langgraph.md`](./langgraph.md)
- CrewAI integration: [`crewai.md`](./crewai.md)
- Multi-agent recipe: `examples/cookbook/16_agents_arguing.py`
