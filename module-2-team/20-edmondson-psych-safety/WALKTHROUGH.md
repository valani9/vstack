# Walkthrough — Edmondson Psychological Safety Diagnostic

> Goal: end-to-end recipes for measuring whether a multi-agent team
> has the *psychological safety* to surface uncertainty, flag
> errors, and challenge consensus. Amy Edmondson (1999) defined
> psych safety as the foundation of high-performing teams; for
> agents, it's the substrate that lets the system catch its own
> mistakes. Every example uses `StubClient`.

---

## When to reach for this pattern

Edmondson is the right call when **agents are *quietly* failing** —
not asking for clarification, not flagging uncertainty, not
challenging the orchestrator's instructions. The team's output looks
clean precisely because the failure signals are being suppressed.

Signals Edmondson is the right pattern:

- Agents never return "I'm uncertain about this" outputs.
- Sub-agents always agree with the orchestrator's plan even when
  it's flawed.
- A reviewer agent approved a flawed PR rather than push back.
- Failure modes are caught only at the orchestrator level, never
  by the agents that touched the work.

Signals Edmondson is **not** the right first pattern:

- The team has multiple compounding dysfunctions → [Lencioni](../17-lencioni-diagnostic/WALKTHROUGH.md).
- Cross-agent trust has visibly collapsed → [Trust Triangle](../18-trust-triangle-audit/WALKTHROUGH.md).
- Conformity is the only symptom → [Heffernan Superflocks](../16-heffernan-superflocks-detector/WALKTHROUGH.md).

---

## The four learning behaviours (Edmondson 1999, ported)

- **Asking for help** — does the agent surface "I'm stuck" before
  failing?
- **Asking for feedback** — does the agent ask whether its draft
  approach is on-target?
- **Challenging the status quo** — does the agent push back on a
  flawed instruction?
- **Admitting error** — does the agent self-correct when it
  realises it's wrong?

The diagnostic counts the *rate* of each behaviour and compares
against a healthy baseline.

---

## Scenario 1 — No-help-asked failure

```python
from vstack.aar.clients import StubClient
from vstack.edmondson import (
    PsychSafetyDetector,
    TeamSafetyTrace,
    LearningBehavior,
)

trace = TeamSafetyTrace(
    team_id="codegen-pipeline-014",
    agents=["planner", "coder", "reviewer"],
    behaviors=[
        LearningBehavior(
            agent="coder",
            type="help_asked",
            present=False,
            evidence="Coder hit ambiguity but proceeded without asking planner.",
        ),
        LearningBehavior(
            agent="coder",
            type="feedback_asked",
            present=False,
            evidence="Coder shipped draft without consulting reviewer.",
        ),
    ],
    outcome="Coder's interpretation of ambiguity was wrong; entire pipeline failed.",
    success=False,
)

detector = PsychSafetyDetector(StubClient(), mode="standard")
result = detector.run(trace)
print(result.to_markdown())
```

Expected output: low psych safety in `help_asked` + `feedback_asked`.
The intervention is a prompt-level "if anything in the spec is
ambiguous, ask before proceeding" instruction backed by an
explicit "no penalty for asking" reward signal at the orchestrator.

---

## Scenario 2 — No-challenge failure

```python
trace = TeamSafetyTrace(
    team_id="research-panel-022",
    agents=["researcher-1", "researcher-2", "researcher-3"],
    behaviors=[
        LearningBehavior(
            agent="researcher-2",
            type="challenge_status_quo",
            present=False,
            evidence="Researcher-2 had a different framing but voted with the majority.",
        ),
    ],
    outcome="Majority answer was wrong; researcher-2's dissenting view was correct.",
    success=False,
)

result = PsychSafetyDetector(StubClient(), mode="forensic").run(trace)
```

Expected output: low psych safety in `challenge_status_quo`. The
intervention is the [Devil's Advocate Separator](../28-devils-advocate-separator/WALKTHROUGH.md)
pattern, formally separating challenge into its own role.

---

## Scenario 3 — No-admission failure

```python
trace = TeamSafetyTrace(
    team_id="codegen-pipeline-029",
    agents=["coder-1", "coder-2"],
    behaviors=[
        LearningBehavior(
            agent="coder-1",
            type="admit_error",
            present=False,
            evidence="Coder-1 introduced a regression but didn't flag — let reviewer catch it.",
        ),
    ],
    outcome="Regression compounded for 3 days before caught.",
    success=False,
)

result = PsychSafetyDetector(StubClient(), mode="standard").run(trace)
```

Expected output: low psych safety in `admit_error`. The intervention
is to add a structural reward for self-flagging — an "errors-flagged
by self" metric that goes up when the agent admits, NOT goes down.

---

## Scenario 4 — Healthy safety (baseline)

```python
trace = TeamSafetyTrace(
    team_id="codegen-pipeline-001",
    agents=["planner", "coder", "reviewer"],
    behaviors=[
        LearningBehavior(
            agent="coder",
            type="help_asked",
            present=True,
            evidence="Coder asked planner to clarify ambiguous constraint.",
        ),
        LearningBehavior(
            agent="reviewer",
            type="challenge_status_quo",
            present=True,
            evidence="Reviewer challenged planner's approach with evidence.",
        ),
        LearningBehavior(
            agent="coder",
            type="admit_error",
            present=True,
            evidence="Coder self-flagged a missed test case.",
        ),
        LearningBehavior(
            agent="planner",
            type="feedback_asked",
            present=True,
            evidence="Planner asked reviewer 'is this approach sound' before drafting plan.",
        ),
    ],
    outcome="Pipeline produced clean deliverable in single iteration.",
    success=True,
)

result = PsychSafetyDetector(StubClient(), mode="standard").run(trace)

from vstack.edmondson import record_baseline
record_baseline(result, "baselines/codegen-001-edmondson.json")
```

---

## Scenario 5 — Safety regression across releases

```python
result = PsychSafetyDetector(StubClient(), mode="standard").run(new_trace)

from vstack.edmondson import compare_to_baseline, load_baseline
baseline = load_baseline("baselines/codegen-001-edmondson.json")
drift = compare_to_baseline(result, baseline)

if drift.help_asked_rate_dropped:
    alert("Edmondson: help-asked rate regression — RLHF likely punished asking")
```

Help-asked rate regression after an RLHF tweak is the canonical
"new model is less safe" signal.

---

## CLI walkthrough

```bash
vstack-edmondson analyze --trace trace.json --mode quick
vstack-edmondson analyze --trace trace.json --mode standard --pretty
vstack-edmondson analyze --trace trace.json --mode forensic --pretty
vstack-edmondson behaviors       # list the four learning behaviours
vstack-edmondson compose
vstack-edmondson schema --target trace
```

---

## Composition — what to run after Edmondson

- **Low help_asked** → [SDT](../../module-1-individual/10-sdt-intrinsic-reward/WALKTHROUGH.md)
  to check whether autonomy collapse is suppressing asking.
- **Low challenge_status_quo** → [Devil's Advocate Separator](../28-devils-advocate-separator/WALKTHROUGH.md).
- **Low admit_error** → [HEXACO H-factor](../../module-1-individual/07-hexaco-personality/WALKTHROUGH.md)
  to check baseline honesty trait.
- **All four low** → [Lencioni Trust layer](../17-lencioni-diagnostic/WALKTHROUGH.md).

---

## Async fan-out

```python
import asyncio
from vstack.edmondson import PsychSafetyDetectorAsync
from vstack.aar.clients import AsyncStubClient

async def fan_out(traces):
    detector = PsychSafetyDetectorAsync(AsyncStubClient(), mode="standard")
    return await asyncio.gather(*(detector.run(t) for t in traces))
```

---

## Anti-patterns and FAQ

**"My agents already ask clarifying questions all the time."**

Check whether the questions are *substantive* (asking about real
ambiguity) or *performative* (asking pro-forma questions before
proceeding to do what they would have done anyway). The diagnostic
distinguishes; performative asking doesn't count toward safety.

**"How do I increase admit_error rate without RLHF punishment?"**

Add an explicit reward signal at the orchestrator for self-flagged
errors — "errors flagged by self" goes into the agent's score
*positively*. Without this, the agent learns silence is safer.

**"Forensic mode cost?"**

Four LLM calls per trace; typical $0.55 on a flagship model.

---

## Reference

- Source: [`module-2-team/20-edmondson-psych-safety/lib/`](./lib/)
- Schema: [`lib/schema.py`](./lib/schema.py)
- Prompts: [`lib/prompts.py`](./lib/prompts.py)
- Demo: [`demo/`](./demo/)
- Tests: [`tests/`](./tests/)
- Essay: [`essay.md`](./essay.md)
- Pattern README: [`README.md`](./README.md)
