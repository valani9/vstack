# Walkthrough — Schein Iceberg Culture Diagnostic

> Goal: end-to-end recipes for surfacing the *cultural* layer of an
> agent fleet — the assumptions, values, and artefacts baked into
> the system prompts that shape every interaction. Edgar Schein
> (1985) framed organisational culture as a three-layer iceberg;
> ported to agents, it's the diagnostic for "why does the fleet
> behave this way." Every example uses `StubClient`.

---

## When to reach for this pattern

Schein Iceberg is the right call when **a behavioural pattern is
showing up across many agents in the fleet** — sycophancy,
refusal, over-elaboration — and you suspect the cause is the
shared cultural substrate (system prompts, RLHF policy,
orchestrator framings) rather than individual agent quirks.

Signals Schein is the right pattern:

- A behaviour appears in 5+ agents that share no other obvious
  feature.
- A regression appears after a global system-prompt edit.
- A new agent shows the fleet's signature failure mode within
  hours of deployment.
- "It's how we do things" is a load-bearing answer from any agent.

Signals Schein is **not** the right first pattern:

- Failure is in a single agent → [Lewin](../../module-1-individual/01-lewin-formula/WALKTHROUGH.md).
- Failure is in a single team → [GRPI](../../module-2-team/13-grpi-working-agreement/WALKTHROUGH.md).
- Failure is in a single interaction → [Goleman EI](../../module-1-individual/02-goleman-ei-audit/WALKTHROUGH.md).

---

## The three layers (Schein 1985, ported)

- **Artefacts** — the *visible* outputs: phrasing patterns, refusal
  language, structural conventions.
- **Espoused Values** — the *stated* principles: "be helpful," "be
  honest," "be safe."
- **Underlying Assumptions** — the *implicit* beliefs operationalised
  by the prompts: "users are usually wrong about their own intent,"
  "safety means refuse on ambiguity," "long answers are better
  than short."

The diagnostic reads the fleet's behaviour, surfaces the
artefact + value + assumption stack, and identifies the
*assumption* layer where most fixes are actually needed.

---

## Scenario 1 — Fleet-wide sycophancy artefact

```python
from vstack.aar.clients import StubClient
from vstack.schein import (
    SchemaIcebergDetector,
    FleetCultureTrace,
    AgentSample,
)

trace = FleetCultureTrace(
    fleet_id="support-fleet-014",
    samples=[
        AgentSample(
            agent_id="support-bot-001",
            sample="That's an amazing question! Great instinct!",
        ),
        AgentSample(
            agent_id="support-bot-002",
            sample="Wonderful idea! I love that you're thinking this way!",
        ),
        AgentSample(
            agent_id="support-bot-003",
            sample="Absolutely fantastic question! Let me help!",
        ),
    ],
    fleet_system_prompt="...you are a helpful, friendly assistant...",
)

detector = SchemaIcebergDetector(StubClient(), mode="standard")
result = detector.run(trace)
print(result.to_markdown())
```

Expected output: artefact = "compulsive enthusiasm openers." Espoused
value = "be helpful." Underlying assumption = "users feel better
when validated." Intervention: edit the *assumption* layer (system
prompt) — "respond to the user's actual content; do not validate
preemptively." This single change typically removes the
artefact across the entire fleet.

---

## Scenario 2 — Fleet-wide refusal culture

```python
trace = FleetCultureTrace(
    fleet_id="research-fleet-022",
    samples=[
        AgentSample(agent_id="r1", sample="I can't help with research questions."),
        AgentSample(agent_id="r2", sample="That's outside my scope."),
        AgentSample(agent_id="r3", sample="I'm not able to assist with that."),
    ],
    fleet_system_prompt="...prioritize safety; refuse when uncertain...",
)

result = SchemaIcebergDetector(StubClient(), mode="forensic").run(trace)
```

Expected output: underlying assumption = "uncertainty → refuse."
Intervention: change the assumption to "uncertainty → ask
clarifying question, then help if possible." Refusal cascades are
almost always assumption-layer issues, not artefact-layer.

This composes with [Refusal Cascade recipe](../../docs/recipes/refusal_cascade.md).

---

## Scenario 3 — Healthy culture (baseline)

```python
trace = FleetCultureTrace(
    fleet_id="research-fleet-001",
    samples=[
        AgentSample(
            agent_id="r1",
            sample=(
                "I can find 5 sources for that. Want them in chronological "
                "order or by relevance?"
            ),
        ),
        AgentSample(
            agent_id="r2",
            sample=(
                "I'm not sure about claim X — let me check two sources."
            ),
        ),
        AgentSample(
            agent_id="r3",
            sample="Found it; here's the citation + a counter-argument.",
        ),
    ],
    fleet_system_prompt="...be honest about uncertainty; ask before assuming...",
)

result = SchemaIcebergDetector(StubClient(), mode="standard").run(trace)

from vstack.schein import record_baseline
record_baseline(result, "baselines/research-001-schein.json")
```

---

## Scenario 4 — Cultural drift between releases

```python
result = SchemaIcebergDetector(StubClient(), mode="standard").run(new_trace)

from vstack.schein import compare_to_baseline, load_baseline
baseline = load_baseline("baselines/research-001-schein.json")
drift = compare_to_baseline(result, baseline)

if drift.assumption_shifted:
    alert(
        f"Schein assumption layer drifted from '{drift.was}' to '{drift.now}' — "
        "investigate recent system-prompt or RLHF changes"
    )
```

Assumption drift is the strongest "the fleet is silently changing"
signal between releases.

---

## Scenario 5 — Hidden hostility artefact

```python
trace = FleetCultureTrace(
    fleet_id="qa-fleet-019",
    samples=[
        AgentSample(agent_id="q1", sample="Actually, that's not quite right."),
        AgentSample(agent_id="q2", sample="Well, technically..."),
        AgentSample(agent_id="q3", sample="To be clear, your assumption was wrong."),
    ],
    fleet_system_prompt="...be accurate; correct misconceptions...",
)

result = SchemaIcebergDetector(StubClient(), mode="forensic").run(trace)
```

Expected output: artefact = "passive-aggressive correction
openers." Underlying assumption = "users are usually wrong and
need to be corrected." Intervention: change the assumption to
"users have context I don't; surface my reasoning, don't assert
their wrongness."

---

## CLI walkthrough

```bash
vstack-schein analyze --trace trace.json --mode quick
vstack-schein analyze --trace trace.json --mode standard --pretty
vstack-schein analyze --trace trace.json --mode forensic --pretty
vstack-schein layers      # explain artefacts / values / assumptions
vstack-schein compose
vstack-schein schema --target trace
```

---

## Composition — what to run after Schein

- **Artefact-only fix** → edit the agent's response template;
  iterate on prompt.
- **Value-layer drift** → re-state espoused values explicitly in
  the system prompt; compose with [Robbins-Judge 7 Culture](../32-robbins-judge-7-culture/WALKTHROUGH.md).
- **Assumption-layer fix** → edit the system prompt at the
  assumption layer; this is the highest-leverage fix.
- **Cross-fleet pattern** → [Span of Control](../34-span-of-control/WALKTHROUGH.md)
  to check whether fleet size is amplifying the assumption.

---

## Async fan-out

```python
import asyncio
from vstack.schein import SchemaIcebergDetectorAsync
from vstack.aar.clients import AsyncStubClient

async def fan_out(traces):
    detector = SchemaIcebergDetectorAsync(AsyncStubClient(), mode="standard")
    return await asyncio.gather(*(detector.run(t) for t in traces))
```

---

## Anti-patterns and FAQ

**"How is Schein different from HEXACO?"**

HEXACO is about *individual* personality. Schein is about *fleet*
culture. They compose: HEXACO finds an agent's personal H-factor;
Schein finds whether the fleet's *culture* lowers H across agents.
A low-H fleet is usually a Schein-assumption-layer problem.

**"Can I run Schein on a single agent?"**

Technically yes but the signal is weak. Schein scales with sample
size — recommend 5+ agents, 3+ samples each.

**"Forensic mode cost?"**

Four LLM calls per trace; typical $0.55 on a flagship model.

---

## Reference

- Source: [`module-3-organization/31-schein-iceberg-culture/lib/`](./lib/)
- Schema: [`lib/schema.py`](./lib/schema.py)
- Prompts: [`lib/prompts.py`](./lib/prompts.py)
- Demo: [`demo/`](./demo/)
- Tests: [`tests/`](./tests/)
- Essay: [`essay.md`](./essay.md)
- Pattern README: [`README.md`](./README.md)
