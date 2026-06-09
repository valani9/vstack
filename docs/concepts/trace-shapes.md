# Concept — Trace Shapes

> vstack diagnostics distinguish three trace shapes: **individual**,
> **team**, and **org**. Each shape has different valid patterns,
> different default bundles, and different downstream tooling. This
> doc explains the distinction and when each applies.

---

## The three shapes

| Shape         | Subject                 | Default patterns                   | Example failures                       |
|---------------|-------------------------|------------------------------------|----------------------------------------|
| `individual`  | one agent, one task     | Lewin, Goleman, Johari, etc.       | hallucination, premature completion    |
| `team`        | multi-agent collab      | GRPI, Trust Triangle, Process G/L  | coordination loss, hand-off failures  |
| `org`         | fleet-wide              | Schein, Robbins-Judge, Span        | culture drift, policy decay            |

---

## Shape detection

`vstack.diagnose()` auto-detects shape from trace attributes:

- If trace has `agents` field with N > 1 → `team`.
- If trace has `fleet_id` or `samples` field → `org`.
- Otherwise → `individual`.

Override with `shape=` on `diagnose()`:

```python
report = diagnose(trace=trace, llm_client=llm, shape="team")
```

---

## Shape-specific schemas

### `individual` shape

```python
from vstack.aar import AgentTrace, TraceStep

trace = AgentTrace(
    shape="individual",
    goal="...",
    steps=[
        TraceStep(type="thought", content="..."),
        TraceStep(type="tool_call", content="..."),
        TraceStep(type="observation", content="..."),
        TraceStep(type="message", content="..."),
        TraceStep(type="decision", content="..."),
    ],
    outcome="...",
    success=False,
    # Optional metadata:
    model_name="...",
    agent_id="...",
    retry_count=0,
)
```

### `team` shape

```python
from vstack.aar import AgentTrace, TraceStep, AgentInTeam, Handoff

trace = AgentTrace(
    shape="team",
    goal="Shared team goal",
    agents=[
        AgentInTeam(id="planner", role="plan"),
        AgentInTeam(id="coder", role="implement"),
        AgentInTeam(id="reviewer", role="review"),
    ],
    steps=[
        TraceStep(
            type="message",
            actor="planner",
            content="...",
        ),
        # ...
    ],
    handoffs=[
        Handoff(from_="planner", to="coder", payload="...", format="json_v1"),
        Handoff(from_="coder", to="reviewer", payload="...", format="json_v1"),
    ],
    outcome="...",
    success=True,
)
```

### `org` shape

```python
from vstack.aar import OrgTrace, AgentSample

trace = OrgTrace(
    shape="org",
    fleet_id="support-fleet-prod",
    samples=[
        AgentSample(agent_id="bot-1", sample="..."),
        AgentSample(agent_id="bot-2", sample="..."),
        # ... 30+ samples typically
    ],
    target_profile={...},
    fleet_system_prompt="...",
)
```

---

## Patterns by shape

### Patterns that accept `individual` only

- `lewin` (#01)
- `goleman_ei` (#02)
- `johari` (#03)
- `danva_emotion` (#04)
- `cognitive_reappraisal` (#05)
- `yerkes_dodson` (#06)
- `hexaco` (#07) (also accepts team-shape for cross-agent profiling)
- `grant_strengths` (#08)
- `motivation_traps` (#09)
- `sdt_reward` (#10)
- `vroom_expectancy` (#12)

### Patterns that accept `team` only

- `grpi` (#13)
- `process_gain_loss` (#14)
- `social_loafing` (#15)
- `superflocks` (#16)
- `lencioni` (#17)
- `trust_triangle` (#18)
- `mcallister_trust` (#19)
- `psych_safety` (#20)
- `plus_delta` (#23)
- `smart_goal` (#24)
- `group_decision` (#25)
- `debate_pathology` (#26)
- `bias_stack` (#27)
- `devils_advocate` (#28)
- `thomas_kilmann` (#29)

### Patterns that accept either

- `mcgregor` (#11) — individual orchestrator or team-shape with orchestrator role.
- `glaser_conversation` (#21)
- `feedback_triggers` (#22)
- `aar` (#30)

### Patterns that accept `org` only

- `schein_culture` (#31)
- `robbins_culture` (#32)
- `org_structure` (#33)
- `span_of_control` (#34)

---

## Shape transitions

Some patterns aggregate across shapes:

### Individual → org

`schein_culture` can take many `individual` traces from across a
fleet and surface the *culture* layer:

```python
from vstack.schein_culture import SchemaIcebergDetector

individual_traces = [trace1, trace2, trace3, ...]  # 30+ traces
fleet_trace = build_org_trace_from_individuals(individual_traces)

result = SchemaIcebergDetector(llm).run(fleet_trace)
```

### Team → org

Multiple `team` traces from the same orchestration template can
aggregate into an `org` trace for `org_structure` and
`span_of_control` analysis:

```python
team_traces = [t1, t2, t3, ...]
org_trace = aggregate_team_traces(team_traces)

result = OrgStructureDetector(llm).run(org_trace)
```

### Individual → team

Multiple individual agent traces from the same multi-agent run
can be assembled into a team trace:

```python
agent_traces = {
    "planner": trace_planner,
    "coder": trace_coder,
    "reviewer": trace_reviewer,
}

team_trace = assemble_team_trace(
    individual_traces=agent_traces,
    handoffs=captured_handoffs,
    shared_goal="...",
)
```

---

## Choosing the right shape

**Use `individual`** when:
- The failure is in one agent's reasoning.
- You want to surface model vs prompt locus.
- You want to audit affect / personality / capability claim.

**Use `team`** when:
- The failure involves coordination between agents.
- You want to audit handoffs / roles / trust.
- The team's output is worse than the strongest solo agent.

**Use `org`** when:
- The same pattern appears across many agents.
- You want to surface culture-level drift.
- You're comparing two fleets / two prompt variants.

---

## Common modeling mistakes

### Treating a multi-agent failure as `individual`

If you only diagnose the *failing* agent in a multi-agent system,
you'll miss the coordination failure that drove the agent into
the failure mode. Always use `team` when the failure is downstream
of a handoff.

### Treating an `org` problem as `team`

If you have a recurring issue across 5+ teams, it's culture, not
coordination. Run `schein_culture` first, not `grpi`.

### Mixing shapes in `diagnose()`

`diagnose()` runs one shape at a time. To run patterns across
shapes (e.g., individual + team), call `diagnose()` twice or use
the multi-shape `diagnose_compound()` helper.

```python
from vstack.diagnose import diagnose_compound

report = diagnose_compound(
    individual_trace=individual,
    team_trace=team,
    org_trace=org,
    llm_client=llm,
)

# report.individual_findings, report.team_findings, report.org_findings
```

---

## See also

- Pattern overview: `docs/PATTERNS_OVERVIEW.md`
- Recipes overview: `docs/RECIPES_OVERVIEW.md`
- Concept: composition (`docs/concepts/composition.md`)
