# CrewAI Integration Playbook

> Goal: integrate vstack diagnostics into CrewAI multi-agent crews.
> Covers the CrewAI adapter, role-based trace mapping, and the 8
> patterns most useful in CrewAI workloads.

---

## When to use vstack with CrewAI

CrewAI is the role-based multi-agent framework. The integration
sweet spot:

- A crew's deliverable is below the quality of the strongest
  individual agent solo.
- Agents are stepping on each other's roles.
- The crew's coordinator is over-verifying.
- A task takes much longer in crew mode than solo.

---

## Install

```bash
pip install valanistack crewai langchain-anthropic
```

The CrewAI adapter is bundled in vstack but optional.

---

## Quick start — diagnose a CrewAI crew run

```python
from crewai import Agent, Task, Crew, Process
from vstack.adapters.crewai_adapter import crewai_to_team_trace
from vstack import diagnose

# Standard CrewAI setup.
researcher = Agent(role="Researcher", goal="Find sources", ...)
writer = Agent(role="Writer", goal="Draft summary", ...)
reviewer = Agent(role="Reviewer", goal="Audit", ...)

task1 = Task(description="Find 5 sources", agent=researcher)
task2 = Task(description="Write summary", agent=writer)
task3 = Task(description="Review", agent=reviewer)

crew = Crew(
    agents=[researcher, writer, reviewer],
    tasks=[task1, task2, task3],
    process=Process.sequential,
)

# Run.
result = crew.kickoff()

# Convert to vstack team trace.
trace = crewai_to_team_trace(
    crew=crew,
    crew_result=result,
    goal="Produce a verified literature summary.",
)

# Diagnose.
report = diagnose(trace=trace, llm_client=llm)
print(report.to_markdown())
```

---

## Patterns most useful for CrewAI

### 1. GRPI (`#13`)

CrewAI's role-based design makes GRPI the canonical first call.
Goals (per-agent goal vs crew goal), Roles (role definition
overlap), Processes (sequential vs hierarchical), Interpersonal
(cross-agent communication).

### 2. McGregor Orchestrator Mode (`#11`)

CrewAI's hierarchical process has a manager agent. McGregor
identifies whether the manager is over-verifying.

### 3. Social Loafing (`#15`)

In fan-out crews, identifies underperforming agents.

### 4. Lencioni 5 Dysfunctions (`#17`)

CrewAI crews often have all 5 dysfunctions. Lencioni finds the
lowest broken layer.

### 5. Trust Triangle (`#18`)

Audit cross-agent trust in the crew's handoffs.

### 6. Process Gain/Loss (`#14`)

Quantifies whether the crew is paying for itself vs solo.

### 7. Span of Control (`#34`)

Crew size is often wrong — too many agents (over-span) or too
few (under-span).

### 8. AAR (`#30`)

Persist a retro for each crew completion.

---

## Trace capture from CrewAI

### Sequential crews

```python
trace = crewai_to_team_trace(
    crew=crew,
    crew_result=result,
    goal="...",
)
```

### Hierarchical crews

CrewAI's `Process.hierarchical` introduces a manager agent. The
adapter captures the manager's decisions separately:

```python
trace = crewai_to_team_trace(
    crew=crew,
    crew_result=result,
    goal="...",
    include_manager_decisions=True,
)

# Diagnose the manager separately with McGregor.
manager_trace = extract_manager_trace(trace)
from vstack.mcgregor import McGregorOrchestratorDetector
mcgregor = McGregorOrchestratorDetector(llm).run(manager_trace, mode="forensic")
```

### Custom tools

CrewAI agents use LangChain-compatible tools. The adapter resolves
tool calls via the same mapping as the LangChain adapter:

```python
trace = crewai_to_team_trace(
    crew=crew,
    crew_result=result,
    goal="...",
    tool_name_map={"_internal_rag_v3": "rag_search"},
)
```

---

## Common CrewAI pathologies

### Manager-bottleneck

`Process.hierarchical` with a manager that verifies every agent
output → manager becomes the bottleneck.

Run: **Span of Control** + **McGregor Orchestrator Mode**.

Common fix: split into 2 sub-crews, each with its own manager.

### Role overlap

Two agents have nominally distinct roles but the goals overlap, so
both produce the same deliverable.

Run: **GRPI Roles layer**.

Common fix: rewrite role + goal to be mutually exclusive.

### Sequential-mode info loss

`Process.sequential` agents only see their immediate predecessor's
output, not the full task context.

Run: **Process Gain/Loss** + **Cold Handoff recipe**.

Common fix: pass the original goal + constraints in each handoff,
not just the prior agent's output.

### Crew vs solo

The crew's deliverable is worse than the strongest agent solo.

Run: **Process Gain/Loss** (forensic mode) + **Social Loafing**.

Common fix: reduce crew size; the gain from specialization is
below the loss from coordination.

---

## Production wiring

```python
from crewai import Crew
from vstack.adapters.crewai_adapter import crewai_to_team_trace
from vstack import diagnose
from vstack.aar import AARAnalyzer
from vstack.dashboard import render_report

def diagnosed_crew_kickoff(crew: Crew, goal: str):
    result = crew.kickoff()
    trace = crewai_to_team_trace(
        crew=crew,
        crew_result=result,
        goal=goal,
    )

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
- LangGraph integration: [`langgraph.md`](./langgraph.md)
- Multi-agent recipe: `examples/cookbook/09_bottleneck_orchestrator.py`
