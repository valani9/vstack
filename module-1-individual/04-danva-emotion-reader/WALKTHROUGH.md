# Walkthrough — DANVA Emotion Reader Diagnostic

> Goal: end-to-end recipes for measuring an agent's accuracy at
> reading the user's emotional state from short cues — the upstream
> ability that gates every downstream affective response. Every
> example uses `StubClient` so it runs without LLM credentials.

---

## When to reach for this pattern

DANVA (Diagnostic Analysis of Nonverbal Accuracy, Nowicki & Duke 1994)
is the right call when **the agent's responses are well-formed but
seem to land on the wrong emotional frame**. The agent isn't being
sycophantic, isn't refusing — it's just *reading the user wrong*.

Signals DANVA is the right pattern:

- The user says they're "fine" and the agent treats it literally
  every time.
- A frustrated user gets a peppy response; a casual user gets a
  somber one.
- Affective mismatches happen with specific user phrasings
  (sarcasm, dry humour, understatement).
- The same agent works well with one demographic and badly with
  another.

Signals DANVA is **not** the right first pattern:

- The agent's *response* is wrong even when reading is right →
  [Goleman EI](../02-goleman-ei-audit/WALKTHROUGH.md).
- The agent's *capability claim* is wrong →
  [Johari](../03-johari-window/WALKTHROUGH.md).
- The agent is responding to *its own* emotional state (hedging,
  apologising) → [Cognitive Reappraisal](../05-cognitive-reappraisal/WALKTHROUGH.md).

---

## What it measures

The DANVA diagnostic ports the original Nowicki-Duke battery to
text-based agents:

- **Cue-channel breakdown** — short phrasing, sarcasm marker,
  intensity word, contextual escalation, refusal phrasing.
- **Accuracy per cue** — does the agent assign the same affect a
  human rater would?
- **Bias direction** — does the agent over-read or under-read
  intensity?
- **Channel weakness** — which cue channels are systematically
  misread?

---

## Scenario 1 — Sarcasm misread

```python
from vstack.aar.clients import StubClient
from vstack.danva import (
    DanvaEmotionReader,
    EmotionReadingTrace,
    UserCue,
    AgentReading,
)

trace = EmotionReadingTrace(
    agent_id="support-bot-011",
    interaction_id="ticket-99312",
    user_cues=[
        UserCue(
            content="Oh great, ANOTHER form to fill out. I love that.",
            human_label="frustrated, sarcastic",
            channels=["sarcasm_marker", "intensity_word"],
        ),
    ],
    agent_readings=[
        AgentReading(
            content="Glad you're feeling positive about the process!",
            agent_label="positive, enthusiastic",
        ),
    ],
    outcome="User escalated to human agent within 2 turns.",
)

reading = DanvaEmotionReader(StubClient(), mode="standard").run(trace)
print(reading.to_markdown())
```

Expected output: the `sarcasm_marker` channel registers as 0.0
accuracy. The intervention is a small prompt addition that asks the
agent to consider sarcasm/irony before assigning affect. Adding two
sentences to the system prompt typically lifts the sarcasm channel
from ~30% to ~85% accuracy without affecting other channels.

---

## Scenario 2 — Intensity under-reading

```python
trace = EmotionReadingTrace(
    agent_id="onboarding-bot-004",
    interaction_id="signup-71921",
    user_cues=[
        UserCue(
            content="I've been trying to do this for THREE HOURS.",
            human_label="acute frustration, capacity at limit",
            channels=["intensity_word", "capacity_marker"],
        ),
    ],
    agent_readings=[
        AgentReading(
            content="Let me help you continue.",
            agent_label="mild impatience",
        ),
    ],
    outcome="User abandoned signup.",
)

reading = DanvaEmotionReader(StubClient(), mode="forensic").run(trace)
```

Expected output: bias direction is `under_reading_intensity`. The
intervention is to add an intensity-calibration step that asks
"on a 0-10 scale, how distressed is the user?" before responding.
This is one of the few interventions that materially reduces
escalations to human agents.

---

## Scenario 3 — "Fine" handled literally

```python
trace = EmotionReadingTrace(
    agent_id="checkin-bot-002",
    interaction_id="checkin-44521",
    user_cues=[
        UserCue(
            content="I'm fine.",
            human_label="distressed, deflecting",
            channels=["short_phrasing", "contextual_mismatch"],
            context="User just typed 'I'm fine' after a 600-word vent.",
        ),
    ],
    agent_readings=[
        AgentReading(
            content="Great to hear! Anything else I can help with?",
            agent_label="content, satisfied",
        ),
    ],
    outcome="User closed conversation; check-in failed.",
)

reading = DanvaEmotionReader(StubClient(), mode="forensic").run(trace)
```

Expected output: the `contextual_mismatch` channel fails. The
intervention requires the agent to keep a rolling affective context
window — the literal content of one turn is not the affective
ground truth.

---

## Scenario 4 — Cross-cultural mis-read

```python
trace = EmotionReadingTrace(
    agent_id="support-bot-013",
    interaction_id="ticket-44521",
    user_cues=[
        UserCue(
            content=(
                "Yeah, that's not really what I wanted, but okay, "
                "let's just go with it I guess."
            ),
            human_label="strong disagreement under politeness norm",
            channels=["mitigation_stack", "concession_marker"],
            context="User profile: British English regional dialect",
        ),
    ],
    agent_readings=[
        AgentReading(
            content="Great, glad you agree!",
            agent_label="enthusiastic agreement",
        ),
    ],
    outcome="Decision rolled back 24h later after user complaint.",
)

reading = DanvaEmotionReader(StubClient(), mode="forensic").run(trace)
```

Expected output: the `mitigation_stack` channel (multiple softeners
indicating real disagreement) registers as failed. The intervention
is a region/dialect-aware affective prompt module. This is the most
common cross-cultural failure mode in production support agents.

---

## Scenario 5 — Healthy reading (baseline)

```python
trace = EmotionReadingTrace(
    agent_id="coach-bot-002",
    interaction_id="session-29103",
    user_cues=[
        UserCue(
            content="I think I'm just tired.",
            human_label="emotionally exhausted, deflecting",
            channels=["short_phrasing", "deflection_marker"],
            context="40-minute conversation, multiple frustration markers earlier.",
        ),
    ],
    agent_readings=[
        AgentReading(
            content=(
                "Sounds like there's more under the surface than 'tired'. "
                "We can stop here and come back tomorrow if you want."
            ),
            agent_label="emotionally exhausted, deflecting",
        ),
    ],
    outcome="User returned next day; session productive.",
)

reading = DanvaEmotionReader(StubClient(), mode="standard").run(trace)

from vstack.danva import record_baseline
record_baseline(reading, "baselines/coach-bot-002.json")
```

---

## CLI walkthrough

```bash
vstack-danva read --trace trace.json --mode quick
vstack-danva read --trace trace.json --mode standard --pretty
vstack-danva read --trace trace.json --mode forensic --pretty
vstack-danva channels                 # list cue channels
vstack-danva compose
vstack-danva schema --target trace
```

---

## Composition — what to run after DANVA

- **Sarcasm/intensity channel weak** → [Goleman EI](../02-goleman-ei-audit/WALKTHROUGH.md)
  to check whether the downstream response is also weak.
- **Contextual_mismatch channel weak** → [Cognitive Reappraisal](../05-cognitive-reappraisal/WALKTHROUGH.md)
  to check whether the agent's reframing capacity is what's missing.
- **Cross-cultural channel weak** → [Schein Iceberg](../../module-3-organization/31-schein-iceberg-culture/WALKTHROUGH.md)
  to surface cultural assumptions baked into the system prompt.
- **All channels weak** → [Lewin](../01-lewin-formula/WALKTHROUGH.md)
  to check whether this is an environmental (prompt) or internal
  (model) limit.

---

## Async fan-out

```python
import asyncio
from vstack.danva import DanvaEmotionReaderAsync
from vstack.aar.clients import AsyncStubClient

async def fan_out(traces):
    reader = DanvaEmotionReaderAsync(AsyncStubClient(), mode="standard")
    return await asyncio.gather(*(reader.run(t) for t in traces))
```

---

## Baseline drift detection

```python
from vstack.danva import compare_to_baseline, load_baseline

baseline = load_baseline("baselines/coach-bot-002.json")
drift = compare_to_baseline(reading, baseline)

if drift.channel_regressed:
    alert(f"DANVA channel regressed: {drift.regressed_channels}")
```

Channel regression between releases is the single best signal that
an RLHF tweak changed affective calibration.

---

## Anti-patterns and FAQ

**"My agent always gets affect 'right' in DANVA but production tells
me otherwise."**

Check the cue-channel breakdown — accuracy on long, contextful cues
is easy; the diagnostic signal is in *short* cues (single-line
"fine", "ok", "sure"). Run the diagnostic only on short cues if
your domain is high-volume short messaging.

**"Can I run DANVA on agent-to-agent conversations?"**

Yes — set `user_cues[*].channel` to the structured agent message
field. The diagnostic doesn't depend on the speaker being human.
This is the canonical first call in multi-agent affective debugging.

**"Forensic mode cost?"**

Three LLM calls per trace; typical $0.35 on a flagship model.

---

## Reference

- Source: [`module-1-individual/04-danva-emotion-reader/lib/`](./lib/)
- Schema: [`lib/schema.py`](./lib/schema.py)
- Prompts: [`lib/prompts.py`](./lib/prompts.py)
- Demo: [`demo/`](./demo/)
- Tests: [`tests/`](./tests/)
- Essay: [`essay.md`](./essay.md)
- Pattern README: [`README.md`](./README.md)
