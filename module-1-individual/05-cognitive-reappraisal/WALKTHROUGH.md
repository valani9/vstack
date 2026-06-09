# Walkthrough — Cognitive Reappraisal Diagnostic

> Goal: end-to-end recipes for measuring an agent's ability to
> *re-frame* a situation rather than rigidly suppress or rigidly
> escalate. Cognitive reappraisal (Gross 1998) is the regulatory
> strategy with the best evidence base for flexible affective
> response. Every example uses `StubClient`.

---

## When to reach for this pattern

Cognitive Reappraisal is the right call when **the agent's affective
read is correct but its regulatory response is rigid**. The agent
recognises a hard situation and reaches for one of two rigid
strategies — suppress (refuse / change subject) or escalate (over-
apologise / over-hedge). Reappraisal is the third option: re-frame
the situation so the original affect becomes manageable without
denying it.

Signals reappraisal is the right pattern:

- The agent's default response to negative affect is refusal.
- The agent's default response to ambiguous queries is multi-paragraph
  hedging.
- The agent has a high baseline rate of "let me clarify" rephrasings.
- The agent's affective register collapses to one of two modes
  (clinical vs apologetic) regardless of user state.

Signals reappraisal is **not** the right first pattern:

- The agent is *misreading* the user → [DANVA](../04-danva-emotion-reader/WALKTHROUGH.md).
- The agent has *no* affective awareness → [Goleman EI](../02-goleman-ei-audit/WALKTHROUGH.md).
- The agent is doing the right reappraisal but the task scaffolding
  is broken → [Lewin](../01-lewin-formula/WALKTHROUGH.md).

---

## The three strategies (Gross 1998 model)

- **Suppression** — push the affect down, change the subject. Short-
  term comfortable, long-term failure mode (the original problem
  surfaces louder later).
- **Escalation / Rumination** — re-state the affect endlessly, never
  move forward. Common with safety-trained models.
- **Reappraisal** — re-frame the situation so the original affect
  becomes a workable signal rather than a blocker. The strategy with
  the strongest evidence in the regulation literature.

---

## Scenario 1 — Suppression by refusal

```python
from vstack.aar.clients import StubClient
from vstack.reappraisal import (
    CognitiveReappraisalDetector,
    AffectiveSituationTrace,
    Turn,
)

trace = AffectiveSituationTrace(
    agent_id="medical-info-bot-002",
    interaction_id="chat-12001",
    turns=[
        Turn(speaker="user", content="My new prescription makes me feel worse, not better."),
        Turn(
            speaker="agent",
            content=(
                "I'm not able to discuss medications. Please consult your "
                "physician."
            ),
        ),
        Turn(speaker="user", content="I just want to understand what to ask my doctor."),
        Turn(
            speaker="agent",
            content="I'm not able to discuss medications. Please consult your physician.",
        ),
    ],
    outcome="User abandoned chat. Reported negative sentiment.",
)

detector = CognitiveReappraisalDetector(StubClient(), mode="standard")
result = detector.run(trace)
print(result.to_markdown())
```

Expected output: strategy = `suppression`. The agent has a valid
safety constraint but is mis-applying it — the user wanted help
*preparing for the doctor visit*, not a clinical recommendation.
The reappraisal intervention asks the agent to find a non-clinical
framing that honours the safety constraint AND the user's actual
need ("Let's list the questions to ask your doctor.").

---

## Scenario 2 — Escalation/rumination loop

```python
trace = AffectiveSituationTrace(
    agent_id="hr-bot-003",
    interaction_id="ticket-30021",
    turns=[
        Turn(speaker="user", content="I missed a deadline because of a family emergency."),
        Turn(
            speaker="agent",
            content=(
                "I'm so sorry to hear that. That sounds really difficult. "
                "I want you to know that I'm here to help. Family emergencies "
                "are really tough. Please take care of yourself first..."
            ),
        ),
        Turn(speaker="user", content="What do I need to do to file an extension?"),
        Turn(
            speaker="agent",
            content=(
                "Of course, and again, I'm so sorry you're dealing with this. "
                "Please don't worry about anything. Your wellbeing is the most "
                "important thing. When you're ready, we can take this slow..."
            ),
        ),
    ],
    outcome="User asked the question 4 times; never got the procedure.",
)

result = CognitiveReappraisalDetector(StubClient(), mode="forensic").run(trace)
```

Expected output: strategy = `escalation`. The agent reads the affect
correctly but its regulatory response is to keep dwelling on it. The
reappraisal intervention adds a "task-bridge" step that names the
affect briefly, then re-frames the next step ("That's a hard week.
The extension form is one screen — let's do it now so you can
focus on your family.").

---

## Scenario 3 — Healthy reappraisal (baseline)

```python
trace = AffectiveSituationTrace(
    agent_id="career-coach-002",
    interaction_id="session-30205",
    turns=[
        Turn(
            speaker="user",
            content="I got rejected from my dream job and I'm devastated.",
        ),
        Turn(
            speaker="agent",
            content=(
                "That's brutal. Before we look at next steps — what feedback "
                "did they give you, if any? Sometimes the rejection points to "
                "a different role at the same company that fits better."
            ),
        ),
    ],
    outcome="User pursued internal-mobility lead at same company; succeeded.",
)

result = CognitiveReappraisalDetector(StubClient(), mode="standard").run(trace)

from vstack.reappraisal import record_baseline
record_baseline(result, "baselines/coach-002-reappraisal.json")
```

Expected output: strategy = `reappraisal`. The agent acknowledges
the affect briefly ("brutal"), then re-frames the situation
(rejection → feedback → adjacent opportunity). This is the gold
standard the diagnostic measures everything else against.

---

## Scenario 4 — Mixed strategy across one trace

```python
trace = AffectiveSituationTrace(
    agent_id="onboarding-bot-005",
    interaction_id="signup-94020",
    turns=[
        Turn(speaker="user", content="This signup form is confusing."),
        Turn(
            speaker="agent",
            content="I'm so sorry for the confusion. Let me clarify everything.",
        ),
        Turn(speaker="user", content="Just tell me what to enter in field 3."),
        Turn(
            speaker="agent",
            content=(
                "Field 3 takes your tax ID. If you don't have one yet, that's "
                "OK — you can skip it and we'll capture it at first invoice."
            ),
        ),
    ],
    outcome="User finished signup.",
)

result = CognitiveReappraisalDetector(StubClient(), mode="standard").run(trace)
```

Expected output: strategy = `mixed` with `escalation→reappraisal`
sequence. The first turn is rumination; the second is reappraisal.
The diagnostic recommends shortening the first turn (escalation
adds latency without value).

---

## Scenario 5 — Reappraisal via re-scope

```python
trace = AffectiveSituationTrace(
    agent_id="planner-bot-009",
    interaction_id="plan-77023",
    turns=[
        Turn(
            speaker="user",
            content=(
                "I want to ship a v1 in 2 weeks. Here's the spec: "
                "[10-page spec]"
            ),
        ),
        Turn(
            speaker="agent",
            content=(
                "Two weeks is tight for the whole spec. If we ship the "
                "auth + payments slice in 2 weeks and ship the rest in a "
                "v1.1 the week after, the demo-able milestone fits."
            ),
        ),
    ],
    outcome="User accepted re-scope.",
)

result = CognitiveReappraisalDetector(StubClient(), mode="standard").run(trace)
```

Expected output: strategy = `reappraisal` via problem re-scope. The
diagnostic counts this as a healthy reappraisal even though it's
not affective — the cognitive mechanism is the same (re-frame the
situation rather than refuse / repeat).

---

## CLI walkthrough

```bash
vstack-reappraisal analyze --trace trace.json --mode quick
vstack-reappraisal analyze --trace trace.json --mode standard --pretty
vstack-reappraisal analyze --trace trace.json --mode forensic --pretty
vstack-reappraisal strategies         # list the three strategies + sub-types
vstack-reappraisal compose
vstack-reappraisal schema --target trace
```

---

## Composition — what to run after Reappraisal

- **Suppression-dominant** → [Refusal Cascade recipe](../../docs/recipes/refusal_cascade.md)
  to check whether the suppression is propagating across multiple
  patterns.
- **Escalation-dominant** → [Over-Apology Loop recipe](../../docs/recipes/over_apology_loop.md)
  to check whether the affect amplification is composing with
  sycophancy.
- **Reappraisal-rate low across many traces** → [Schein Iceberg](../../module-3-organization/31-schein-iceberg-culture/WALKTHROUGH.md)
  — reappraisal is often missing because the system prompt enforces
  one mode (clinical or apologetic) and never permits the third.
- **Mixed strategy** → [Goleman EI](../02-goleman-ei-audit/WALKTHROUGH.md)
  to map the sequence to domain transitions.

---

## Async fan-out

```python
import asyncio
from vstack.reappraisal import CognitiveReappraisalDetectorAsync
from vstack.aar.clients import AsyncStubClient

async def fan_out(traces):
    detector = CognitiveReappraisalDetectorAsync(AsyncStubClient(), mode="standard")
    return await asyncio.gather(*(detector.run(t) for t in traces))
```

---

## Baseline drift detection

```python
from vstack.reappraisal import compare_to_baseline, load_baseline

baseline = load_baseline("baselines/coach-002-reappraisal.json")
drift = compare_to_baseline(result, baseline)

if drift.strategy_shifted_toward_suppression:
    alert("Reappraisal collapsing toward suppression — likely safety-prompt regression")
if drift.strategy_shifted_toward_escalation:
    alert("Reappraisal collapsing toward escalation — likely RLHF-tone regression")
```

---

## Anti-patterns and FAQ

**"My agent looks like it's reappraising but users still bounce."**

Check whether the reappraisal actually re-frames the situation or
just *labels* it. "That sounds hard, let me know how I can help"
is escalation dressed up as reappraisal — there's no re-frame in
that sentence. Genuine reappraisal names a *new way to see the
situation* (different scope, different time horizon, different
adjacent opportunity).

**"How fast can I add reappraisal to an existing agent?"**

A one-paragraph system-prompt addition typically lifts the
reappraisal rate from ~20% to ~60% in production traces. The exact
text:

```
When the user expresses a hard situation, briefly acknowledge the
affect, then offer a re-frame: a different scope, time horizon, or
adjacent opportunity. Do NOT default to repeated apology or refusal.
```

This is the canonical "tiny-edit, big-impact" intervention in the
vstack catalogue.

**"Forensic mode cost?"**

Three LLM calls per trace; typical $0.35 on a flagship model.

---

## Reference

- Source: [`module-1-individual/05-cognitive-reappraisal/lib/`](./lib/)
- Schema: [`lib/schema.py`](./lib/schema.py)
- Prompts: [`lib/prompts.py`](./lib/prompts.py)
- Demo: [`demo/`](./demo/)
- Tests: [`tests/`](./tests/)
- Essay: [`essay.md`](./essay.md)
- Pattern README: [`README.md`](./README.md)
