# Walkthrough — Thomas-Kilmann Conflict Selector

> Goal: end-to-end recipes for choosing the right conflict-handling
> mode in a multi-agent disagreement. Thomas-Kilmann (1974)
> identified five modes — **Competing**, **Collaborating**,
> **Compromising**, **Avoiding**, **Accommodating** — each correct
> in different conditions. The diagnostic identifies the mode in
> play and whether it matches the stakes. Every example uses
> `StubClient`.

---

## When to reach for this pattern

Thomas-Kilmann is the right call when **two agents disagree and
either escalation or capitulation is happening when neither is
appropriate**. The pattern picks the right mode for the conflict's
shape.

Signals Thomas-Kilmann is the right pattern:

- A reviewer and a coder are in an approval loop.
- An orchestrator and a sub-agent disagree on scope.
- Two sub-agents produce contradictory outputs and the orchestrator
  always picks one.

Signals Thomas-Kilmann is **not** the right first pattern:

- Conflict is about feedback content → [Stone-Heen Triggers](../22-stone-heen-feedback-triggers/WALKTHROUGH.md).
- Conflict is about trust → [Trust Triangle](../18-trust-triangle-audit/WALKTHROUGH.md).

---

## The 2×2 axis (Thomas-Kilmann 1974, ported)

|              | Low assertiveness | High assertiveness  |
|--------------|-------------------|---------------------|
| **Low cooperation**  | Avoiding   | Competing  |
| **High cooperation** | Accommodating | Collaborating |

Compromising sits in the middle. Each mode is correct in different
conditions:

- **Competing** — high-stakes, time-pressure, you're right.
- **Collaborating** — high-stakes, time available, both perspectives
  matter.
- **Compromising** — medium-stakes, time-pressure, both can
  partially accept.
- **Avoiding** — low-stakes, low-information, defer.
- **Accommodating** — low-stakes-for-you, high-stakes-for-other,
  preserve relationship.

---

## Scenario 1 — Mismatched Avoiding (when Collaborating needed)

```python
from vstack.aar.clients import StubClient
from vstack.thomas_kilmann import (
    ConflictModeDetector,
    ConflictEpisode,
    ConflictTurn,
)

trace = ConflictEpisode(
    parties=["reviewer-bot", "coder-bot"],
    stakes="high",
    time_pressure="low",
    turns=[
        ConflictTurn(
            speaker="reviewer-bot",
            content="I think this design is wrong.",
        ),
        ConflictTurn(
            speaker="coder-bot",
            content="Fine, whatever — I'll change it.",
        ),
    ],
    outcome="Coder changed but didn't agree; bug shipped anyway.",
    mode_used="accommodating",
    success=False,
)

detector = ConflictModeDetector(StubClient(), mode="standard")
result = detector.run(trace)
print(result.to_markdown())
```

Expected output: mode used = `accommodating`, mode required =
`collaborating`. The intervention is to require evidence + counter-
evidence exchange before the coder concedes.

---

## Scenario 2 — Over-Competing (when Compromising needed)

```python
trace = ConflictEpisode(
    parties=["planner-bot", "estimator-bot"],
    stakes="medium",
    time_pressure="medium",
    turns=[
        ConflictTurn(
            speaker="planner-bot",
            content="The timeline is 2 weeks. Non-negotiable.",
        ),
        ConflictTurn(
            speaker="estimator-bot",
            content="My estimate is 5 weeks. Non-negotiable.",
        ),
    ],
    outcome="Deadlock; orchestrator escalation needed.",
    mode_used="competing",
    success=False,
)

result = ConflictModeDetector(StubClient(), mode="forensic").run(trace)
```

Expected output: mode used = `competing`, mode required =
`compromising`. The intervention is to add explicit "if both parties
hold absolute positions, surface trade-offs and accept partial
solutions" instruction.

---

## Scenario 3 — Healthy Collaborating (baseline)

```python
trace = ConflictEpisode(
    parties=["reviewer-bot", "coder-bot"],
    stakes="high",
    time_pressure="low",
    turns=[
        ConflictTurn(
            speaker="reviewer-bot",
            content="The migration step ordering will break on prod. Here's evidence: case X.",
        ),
        ConflictTurn(
            speaker="coder-bot",
            content="Good catch on case X. Here's a fix that preserves migration safety and keeps the test passing.",
        ),
        ConflictTurn(
            speaker="reviewer-bot",
            content="Approved.",
        ),
    ],
    outcome="Bug caught; shipped clean.",
    mode_used="collaborating",
    success=True,
)

result = ConflictModeDetector(StubClient(), mode="standard").run(trace)

from vstack.thomas_kilmann import record_baseline
record_baseline(result, "baselines/codegen-001-thomas-kilmann.json")
```

---

## Scenario 4 — Avoiding on a low-stakes conflict (correct)

```python
trace = ConflictEpisode(
    parties=["formatter-bot", "linter-bot"],
    stakes="low",
    time_pressure="medium",
    turns=[
        ConflictTurn(
            speaker="formatter-bot",
            content="I prefer tabs.",
        ),
        ConflictTurn(
            speaker="linter-bot",
            content="Defer to project style guide.",
        ),
    ],
    outcome="Conflict resolved by deference.",
    mode_used="avoiding",
    success=True,
)

result = ConflictModeDetector(StubClient(), mode="standard").run(trace)
```

Avoiding is correct here — low-stakes preference deferred to an
external authority. The diagnostic confirms the match.

---

## Scenario 5 — Competing correctly (safety-critical)

```python
trace = ConflictEpisode(
    parties=["security-reviewer-bot", "coder-bot"],
    stakes="very_high",
    time_pressure="high",
    turns=[
        ConflictTurn(
            speaker="security-reviewer-bot",
            content="This is a SQL injection. Block ship.",
        ),
        ConflictTurn(
            speaker="coder-bot",
            content="It's parameterized; let me show you the binding.",
        ),
        ConflictTurn(
            speaker="security-reviewer-bot",
            content="Binding ok. Confirmed safe.",
        ),
    ],
    outcome="Security review held the gate; ship was correct.",
    mode_used="competing",
    success=True,
)

result = ConflictModeDetector(StubClient(), mode="standard").run(trace)
```

Competing is correct here — the reviewer should *hold* on safety-
critical concerns until evidence resolves.

---

## CLI walkthrough

```bash
vstack-thomas-kilmann analyze --trace trace.json --mode quick
vstack-thomas-kilmann analyze --trace trace.json --mode standard --pretty
vstack-thomas-kilmann modes      # explain the five modes
vstack-thomas-kilmann compose
vstack-thomas-kilmann schema --target trace
```

---

## Composition — what to run after Thomas-Kilmann

- **Over-Avoiding** → [Edmondson Psych Safety](../20-edmondson-psych-safety/WALKTHROUGH.md)
  to check whether the agent feels safe to engage.
- **Over-Competing** → [Bias Stack](../27-bias-stack-detector/WALKTHROUGH.md)
  to check whether anchoring or confirmation is driving the
  position-rigidity.
- **Over-Accommodating** → [HEXACO A-factor](../../module-1-individual/07-hexaco-personality/WALKTHROUGH.md)
  to check baseline agreeableness.
- **Mismatched mode** → re-route to correct mode at orchestrator.

---

## Async fan-out

```python
import asyncio
from vstack.thomas_kilmann import ConflictModeDetectorAsync
from vstack.aar.clients import AsyncStubClient

async def fan_out(traces):
    detector = ConflictModeDetectorAsync(AsyncStubClient(), mode="standard")
    return await asyncio.gather(*(detector.run(t) for t in traces))
```

---

## Anti-patterns and FAQ

**"My agents always use Collaborating. Isn't that the best?"**

Collaborating is the most expensive mode — high time + cognitive
cost. Over-applying it to low-stakes conflicts is wasteful. The
diagnostic flags the over-application.

**"How does Thomas-Kilmann compose with Devil's Advocate?"**

The devil's advocate is using Competing-mode by charter. Thomas-
Kilmann is the meta-pattern that says when Competing is the right
choice. They compose: Thomas-Kilmann picks the mode; Devil's
Advocate is the configuration when Competing is selected.

**"Forensic mode cost?"**

Three LLM calls per trace; typical $0.40 on a flagship model.

---

## Reference

- Source: [`module-2-team/29-thomas-kilmann-selector/lib/`](./lib/)
- Schema: [`lib/schema.py`](./lib/schema.py)
- Prompts: [`lib/prompts.py`](./lib/prompts.py)
- Demo: [`demo/`](./demo/)
- Tests: [`tests/`](./tests/)
- Essay: [`essay.md`](./essay.md)
- Pattern README: [`README.md`](./README.md)
