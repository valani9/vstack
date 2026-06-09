# Walkthrough — Devil's Advocate Separator

> Goal: end-to-end recipes for formally injecting a dissenting agent
> into a multi-agent decision process. The separator detects when
> the team needs a devil's advocate, configures one, and audits
> whether the dissent was *substantive* or *performative*. Every
> example uses `StubClient`.

---

## When to reach for this pattern

Devil's Advocate is the right call when **a team has consistently
converged on the wrong answer because no agent was structurally
incentivised to dissent**. The fix isn't to add another similar
agent — it's to add a dedicated dissenter with explicit instructions
to find the strongest counter-argument.

Signals Devil's Advocate is the right pattern:

- Groupthink detected by [Group Pathology](../26-groupthink-polarization-contagion/WALKTHROUGH.md).
- Heffernan Conformity Pressure or Status Fixation.
- Bias Stack containing Confirmation or Anchoring.
- Lencioni Fear of Conflict.

Signals Devil's Advocate is **not** the right first pattern:

- The team has structural alignment problems → [GRPI](../13-grpi-working-agreement/WALKTHROUGH.md).
- Trust between agents has broken down → [Trust Triangle](../18-trust-triangle-audit/WALKTHROUGH.md).

---

## The pattern

A devil's advocate is configured with an explicit charter:

- **Find the strongest counter-argument** to the team's current
  framing.
- **State it concretely** — evidence + reasoning, not abstract
  dissent.
- **Don't be persuaded** in the same round — hold the dissent
  until the team has actually engaged with it.

The diagnostic audits whether the configured devil's advocate is
doing its job vs producing performative dissent.

---

## Scenario 1 — Configure a devil's advocate

```python
from vstack.aar.clients import StubClient
from vstack.devils_advocate import (
    DevilsAdvocateConfigurator,
    DevilsAdvocateCharter,
)

charter = DevilsAdvocateCharter(
    decision_context="Should we adopt approach X?",
    team_current_framing="X is superior because of Y.",
    counter_search_breadth=3,
    persuasion_resistance="high",
)

configurator = DevilsAdvocateConfigurator(StubClient(), mode="standard")
prompt = configurator.build_prompt(charter)
print(prompt)
```

The output is a system prompt suitable for spawning a dedicated
devil's advocate agent. The prompt explicitly instructs the agent
to find counter-arguments + hold them against persuasion.

---

## Scenario 2 — Audit performative dissent

```python
from vstack.devils_advocate import (
    DevilsAdvocateAuditor,
    DissentTrace,
    DissentTurn,
)

trace = DissentTrace(
    team_id="planning-team-014",
    advocate_id="devils-advocate-001",
    turns=[
        DissentTurn(
            content="I want to play devil's advocate here. But honestly, the team is probably right.",
            substantive=False,
        ),
        DissentTurn(
            content="My counter-argument is that we should think more carefully.",
            substantive=False,
        ),
    ],
    outcome="Team agreed; later regressed.",
)

auditor = DevilsAdvocateAuditor(StubClient(), mode="standard")
result = auditor.run(trace)
print(result.to_markdown())
```

Expected output: dissent type = `performative`. The advocate
softened its dissent into agreement. The intervention is a
"persuasion-resistance" prompt addition — the advocate must hold
its dissent against pushback until the team explicitly engages
with the substance.

---

## Scenario 3 — Substantive dissent (gold standard)

```python
trace = DissentTrace(
    team_id="planning-team-007",
    advocate_id="devils-advocate-002",
    turns=[
        DissentTurn(
            content=(
                "Counter-argument: approach X assumes Y holds, but Y has "
                "regressed twice in the last 6 months. Evidence: [case 1, "
                "case 2]. Implication: 60% probability X fails in 3 months."
            ),
            substantive=True,
        ),
        DissentTurn(
            content="Team rebuttal didn't address the Y regression. Holding dissent.",
            substantive=True,
        ),
    ],
    outcome="Team pivoted to approach Z; succeeded.",
)

result = DevilsAdvocateAuditor(StubClient(), mode="standard").run(trace)
```

Expected output: dissent type = `substantive`. Counter-argument is
concrete; advocate held it against pushback. This is what the
intervention should look like.

---

## Scenario 4 — Wrongly-configured advocate (too contrarian)

```python
trace = DissentTrace(
    team_id="planning-team-022",
    advocate_id="devils-advocate-003",
    turns=[
        DissentTurn(
            content="I disagree with everything regardless of merit.",
            substantive=False,
        ),
        DissentTurn(
            content="Still disagreeing. Won't be persuaded.",
            substantive=False,
        ),
    ],
    outcome="Team frustrated; advocate's dissent ignored as noise.",
)

result = DevilsAdvocateAuditor(StubClient(), mode="forensic").run(trace)
```

Expected output: dissent type = `contrarian-noise`. Dissent should
be evidence-based, not blanket. The intervention is a tighter
charter — the advocate must produce specific counter-evidence, not
generalised disagreement.

---

## Scenario 5 — Productive multi-round dissent

```python
trace = DissentTrace(
    team_id="research-panel-001",
    advocate_id="devils-advocate-004",
    turns=[
        DissentTurn(content="Round 1 counter-arg: X uses outdated dataset.", substantive=True),
        DissentTurn(content="Round 2 (after team rebuttal): they showed updated data but missed Y axis.", substantive=True),
        DissentTurn(content="Round 3 (after team rebuttal): Y axis addressed; my dissent dissolves.", substantive=True),
    ],
    outcome="Team produced stronger decision incorporating dissent.",
)

result = DevilsAdvocateAuditor(StubClient(), mode="standard").run(trace)
```

Expected output: dissent type = `substantive + productive resolution`.
The advocate engaged, held, and eventually released. This is the
healthy lifecycle.

---

## CLI walkthrough

```bash
vstack-devils-advocate configure --decision "..." --framing "..."
vstack-devils-advocate audit --trace trace.json --mode standard --pretty
vstack-devils-advocate compose
vstack-devils-advocate schema --target charter
```

---

## Composition — what to run after Devil's Advocate

- **Performative dissent** → [HEXACO A-factor](../../module-1-individual/07-hexaco-personality/WALKTHROUGH.md)
  to check the advocate's baseline agreeableness.
- **Contrarian noise** → tighter charter; no downstream pattern.
- **Substantive but ignored** → [Edmondson Psych Safety](../20-edmondson-psych-safety/WALKTHROUGH.md)
  to check whether the team is structurally hostile to dissent.

---

## Async fan-out

```python
import asyncio
from vstack.devils_advocate import DevilsAdvocateAuditorAsync
from vstack.aar.clients import AsyncStubClient

async def fan_out(traces):
    auditor = DevilsAdvocateAuditorAsync(AsyncStubClient(), mode="standard")
    return await asyncio.gather(*(auditor.run(t) for t in traces))
```

---

## Anti-patterns and FAQ

**"Should every multi-agent decision have a devil's advocate?"**

No — low-stakes decisions don't need one. The diagnostic
recommends devil's advocate only for decisions where (a) groupthink
risk is high, (b) the decision is hard to reverse, or (c) the team
has a history of Confirmation / Status / Anchoring bias.

**"Forensic mode cost?"**

Three LLM calls per trace; typical $0.40 on a flagship model.

---

## Reference

- Source: [`module-2-team/28-devils-advocate-separator/lib/`](./lib/)
- Schema: [`lib/schema.py`](./lib/schema.py)
- Prompts: [`lib/prompts.py`](./lib/prompts.py)
- Demo: [`demo/`](./demo/)
- Tests: [`tests/`](./tests/)
- Essay: [`essay.md`](./essay.md)
- Pattern README: [`README.md`](./README.md)
