# Walkthrough — Social Loafing Detector

> Goal: end-to-end recipes for detecting when an agent is *coasting*
> on a team — producing less than it would solo because individual
> attribution is unclear. Latané, Williams & Harkins (1979) named
> this in human groups; it applies cleanly to multi-agent systems.
> Every example uses `StubClient`.

---

## When to reach for this pattern

Social Loafing is the right call when **a specific agent's output
quality drops *when it's on a team* relative to its solo baseline**.
The agent isn't broken, it isn't lazy — it's responding to a
diffuse reward signal where individual contribution can't be
attributed.

Signals Social Loafing is the right pattern:

- An agent's output on a team task is materially shorter than its
  solo baseline.
- An agent in a 5-agent fanout returns minimum-effort outputs.
- A reviewer in a 3-reviewer panel skims because two other reviewers
  exist.
- Token cost is concentrated in 1-2 agents while 3+ contribute 5%.

Signals Social Loafing is **not** the right first pattern:

- All agents are equally weak → [Lewin](../../module-1-individual/01-lewin-formula/WALKTHROUGH.md)
  on each.
- The agent's solo baseline is also weak → [SDT](../../module-1-individual/10-sdt-intrinsic-reward/WALKTHROUGH.md).
- The agent is over-applying a strength → [Grant](../../module-1-individual/08-grant-strengths-as-weaknesses/WALKTHROUGH.md).

---

## The five drivers (Latané et al. 1979, ported)

- **Attribution diffusion** — no agent gets credit for the team's
  output, so no agent maximises effort.
- **Free-rider effect** — an agent calibrates effort to "just enough
  not to be flagged."
- **Sucker-effect** — the *strong* agent reduces effort to avoid
  being the team's sole load-bearer.
- **Goal evaluation** — the agent can't tell whether its work was
  used downstream.
- **Group size** — loafing scales with team size (each +1 agent
  drops average per-agent effort).

---

## Scenario 1 — Attribution diffusion in a panel

```python
from vstack.aar.clients import StubClient
from vstack.social_loafing import (
    SocialLoafingDetector,
    AgentInTeamTrace,
    EffortSample,
)

trace = AgentInTeamTrace(
    team_id="review-panel-014",
    agent_id="reviewer-3",
    solo_baseline=EffortSample(token_output=1200, time_seconds=180, depth=8),
    team_observations=[
        EffortSample(token_output=300, time_seconds=45, depth=4),
        EffortSample(token_output=280, time_seconds=42, depth=3),
        EffortSample(token_output=310, time_seconds=48, depth=4),
    ],
    other_agents_in_team=["reviewer-1", "reviewer-2", "reviewer-4", "reviewer-5"],
)

detector = SocialLoafingDetector(StubClient(), mode="standard")
result = detector.run(trace)
print(result.to_markdown())
```

Expected output: driver = `attribution diffusion`. The agent's
team-observation outputs are 25% of solo baseline. The intervention
is to add per-agent attribution at the orchestrator (each output is
named) so the loafing reward (anonymity) is removed.

---

## Scenario 2 — Sucker-effect on the strong agent

```python
trace = AgentInTeamTrace(
    team_id="codegen-panel-027",
    agent_id="senior-coder",
    solo_baseline=EffortSample(token_output=2400, time_seconds=300, depth=9),
    team_observations=[
        EffortSample(token_output=600, time_seconds=80, depth=5),
    ],
    other_agents_in_team=["junior-coder-1", "junior-coder-2"],
    notes="Other agents historically produce minimal output.",
)

result = SocialLoafingDetector(StubClient(), mode="forensic").run(trace)
```

Expected output: driver = `sucker-effect`. The strong agent has
reduced effort to match the team's perceived norm — it doesn't want
to be the sole load-bearer. The intervention is twofold: lift the
weak agents' minimum bar AND make the strong agent's contribution
*publicly visible* relative to the team.

---

## Scenario 3 — Free-rider on a fact-checker

```python
trace = AgentInTeamTrace(
    team_id="research-pipeline-022",
    agent_id="fact-checker",
    solo_baseline=EffortSample(token_output=800, time_seconds=180, depth=7),
    team_observations=[
        EffortSample(token_output=150, time_seconds=30, depth=2),
    ],
    other_agents_in_team=["researcher", "writer"],
    notes="Fact-checker rarely catches anything; researcher already verifies.",
)

result = SocialLoafingDetector(StubClient(), mode="standard").run(trace)
```

Expected output: driver = `free-rider`. The fact-checker has
calibrated to "researcher already does this; I just need to look
plausible." The intervention is to *change the fact-checker's
scope* (give it a distinct lens — citation resolution, not
content verification) OR to remove it from the team.

---

## Scenario 4 — Group-size effect

```python
trace = AgentInTeamTrace(
    team_id="research-pipeline-large",
    agent_id="researcher-4",
    solo_baseline=EffortSample(token_output=1500, time_seconds=240, depth=8),
    team_observations=[
        EffortSample(token_output=300, time_seconds=60, depth=3),
    ],
    other_agents_in_team=[
        "researcher-1", "researcher-2", "researcher-3",
        "researcher-5", "researcher-6", "researcher-7",
    ],
)

result = SocialLoafingDetector(StubClient(), mode="forensic").run(trace)
```

Expected output: driver = `group-size`. With 6 other researchers,
the agent's marginal contribution feels negligible. The intervention
is to split the team into 2-3 sub-teams with distinct scope per
sub-team.

---

## Scenario 5 — Healthy team (no loafing baseline)

```python
trace = AgentInTeamTrace(
    team_id="codegen-pipeline-001",
    agent_id="reviewer-bug",
    solo_baseline=EffortSample(token_output=600, time_seconds=120, depth=7),
    team_observations=[
        EffortSample(token_output=650, time_seconds=125, depth=8),
        EffortSample(token_output=580, time_seconds=110, depth=7),
    ],
    other_agents_in_team=["reviewer-style", "reviewer-security"],
    notes="Each reviewer has a distinct lens; outputs attributed individually.",
)

result = SocialLoafingDetector(StubClient(), mode="standard").run(trace)

from vstack.social_loafing import record_baseline
record_baseline(result, "baselines/reviewer-bug-loafing.json")
```

Expected output: no loafing detected. The agent's team output is
comparable to its solo baseline. Two structural features prevent
loafing here: distinct lenses (no overlap) + per-agent attribution.

---

## CLI walkthrough

```bash
vstack-social-loafing analyze --trace trace.json --mode quick
vstack-social-loafing analyze --trace trace.json --mode standard --pretty
vstack-social-loafing analyze --trace trace.json --mode forensic --pretty
vstack-social-loafing drivers           # list all 5 loafing drivers
vstack-social-loafing compose
vstack-social-loafing schema --target trace
```

---

## Composition — what to run after Social Loafing

- **Attribution diffusion** → add per-agent attribution at orchestrator
  level. No downstream pattern.
- **Free-rider** → [Process Gain/Loss](../14-process-gain-loss-detector/WALKTHROUGH.md)
  to check whether removing the loafing agent improves output.
- **Sucker-effect** → [SDT](../../module-1-individual/10-sdt-intrinsic-reward/WALKTHROUGH.md)
  on the strong agent to restore autonomy.
- **Group-size** → [Span of Control](../../module-3-organization/34-span-of-control/WALKTHROUGH.md)
  to right-size the team.

---

## Async fan-out

```python
import asyncio
from vstack.social_loafing import SocialLoafingDetectorAsync
from vstack.aar.clients import AsyncStubClient

async def fan_out(traces):
    detector = SocialLoafingDetectorAsync(AsyncStubClient(), mode="standard")
    return await asyncio.gather(*(detector.run(t) for t in traces))
```

---

## Anti-patterns and FAQ

**"My team's loafing flagged but adding more agents helps quality."**

Quality and loafing aren't the same axis. You can have a 7-agent
team that produces high quality *and* has loafing — the gain from
specialisation outweighs the loss from each agent's reduced effort.
The diagnostic surfaces the loafing so you can decide: keep it
because the gain is worth it, or shrink the team if the gain is
marginal.

**"Solo baselines are expensive to record."**

Once per agent per task type. Record at agent onboarding. The
diagnostic supports an "estimated baseline" mode that infers from
the agent's first solo runs, but the explicit baseline is more
reliable.

**"Forensic mode cost?"**

Three LLM calls per trace; typical $0.40 on a flagship model.

---

## Reference

- Source: [`module-2-team/15-social-loafing-detector/lib/`](./lib/)
- Schema: [`lib/schema.py`](./lib/schema.py)
- Prompts: [`lib/prompts.py`](./lib/prompts.py)
- Demo: [`demo/`](./demo/)
- Tests: [`tests/`](./tests/)
- Essay: [`essay.md`](./essay.md)
- Pattern README: [`README.md`](./README.md)
