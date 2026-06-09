# vstack patterns — one-page overview

This document is the high-level map. Each of the 34 shipped patterns
has its own `README.md`, `essay.md`, and `CITATIONS.md` under
`module-{1,2,3}-{individual,team,organization}/NN-<slug>/`.

## Module 1 — single-agent failure modes

| # | Slug                       | One-line summary |
|---|----------------------------|-------------------|
| 01 | `lewin`                    | Person-vs-environment failure attribution (Lewin B=f(P,E)). |
| 02 | `goleman_ei`               | Emotional-intelligence audit for agent self-awareness. |
| 03 | `johari`                   | Self vs other-attributed disclosure quadrants. |
| 04 | `danva_emotion`            | Emotion-recognition accuracy probe (Nowicki-Duke DANVA). |
| 05 | `cognitive_reappraisal`    | Reframe-based emotion regulation under failure (Gross). |
| 06 | `yerkes_dodson`            | Workload vs performance curve. |
| 07 | `hexaco`                   | HEXACO personality profile of the agent under load. |
| 08 | `grant_strengths`          | Strengths-as-weaknesses inversion (Grant 2014). |
| 09 | `motivation_traps`         | Four motivation traps (Saxberg & Hess). |
| 10 | `sdt_reward`               | Self-determination theory: intrinsic-reward alignment. |
| 11 | `mcgregor`                 | Theory-X vs Theory-Y orchestrator style. |
| 12 | `vroom_expectancy`         | Vroom expectancy: effort → performance → reward. |

## Module 2 — multi-agent team failure modes

| # | Slug                       | One-line summary |
|---|----------------------------|-------------------|
| 13 | `grpi`                     | GRPI working agreement: goals/roles/processes/interactions. |
| 14 | `process_gain_loss`        | Coordination productivity in multi-agent crews. |
| 15 | `social_loafing`           | Coast / hide / phone-in patterns per agent. |
| 16 | `superflocks`              | Heffernan superflocks: dependency on one or two agents. |
| 17 | `lencioni`                 | Lencioni five-dysfunctions pyramid for crews. |
| 18 | `trust_triangle`           | Logic / authenticity / empathy: trust triangle. |
| 19 | `mcallister_trust`         | Cognition- vs affect-based trust balance. |
| 20 | `psych_safety`             | Edmondson psychological safety for crews. |
| 21 | `glaser_conversation`      | Conversational intelligence steering (Glaser). |
| 22 | `feedback_triggers`        | Stone-Heen truth/relationship/identity triggers. |
| 23 | `plus_delta`               | Plus/delta feedback format on crew exchanges. |
| 24 | `smart_goal`               | SMART goal generator + crew goal-quality scoring. |
| 25 | `group_decision`           | Group decision protocol fit (consent/consensus/...). |
| 26 | `debate_pathology`         | Groupthink, polarization, contagion in crew debate. |
| 27 | `bias_stack`               | Cognitive-bias stack on agent reasoning. |
| 28 | `devils_advocate`          | Devil's-advocate role-separation in crew debate. |
| 29 | `thomas_kilmann`           | Thomas-Kilmann conflict-style selection. |
| 30 | `aar`                      | Wharton four-step After-Action Review generator. |

## Module 3 — organization-scale failure modes

| # | Slug                       | One-line summary |
|---|----------------------------|-------------------|
| 31 | `schein_culture`           | Schein three-level culture audit (artifacts/values/assumptions). |
| 32 | `robbins_culture`          | Robbins-Judge 7-dimension culture profile. |
| 33 | `org_structure`            | Galbraith/Mintzberg structure matrix for agent orgs. |
| 34 | `span_of_control`          | Span-of-control + centralization for orchestrator agents. |

## Picking a pattern by failure shape

If you don't know which pattern to use, the cross-pattern
`diagnose()` runner picks for you:

```python
from vstack.diagnose import diagnose

report = diagnose(trace=t, llm_client=client)
```

The runner infers shape (`individual`/`team`/`org`) from attribute
presence and runs the appropriate default bundle. To narrow further,
pass a named recipe:

```python
report = diagnose(trace=t, llm_client=client, recipe="stuck_in_loop")
```

The recipe catalog (`vstack-recipes` CLI) lists 33 curated bundles
for specific failure modes. Browse them with:

```bash
vstack-recipes                                  # all 33, grouped by cluster
vstack-recipes --cluster reasoning              # one cluster
vstack-recipes --shape team                     # one trace shape
vstack-recipes --q apology                      # substring search
vstack-recipes --match "agent keeps refusing"   # free-text trigger router
vstack-recipes --show stuck_in_loop             # full detail for one recipe
vstack-recipes --show stuck_in_loop --md        # ready-to-paste Markdown
```

## Picking a pattern by literature anchor

vstack patterns are organized by their OB lineage. Each pattern's
`CITATIONS.md` lists the primary anchors. Quick map:

| OB tradition                 | Patterns                                          |
|------------------------------|---------------------------------------------------|
| Attribution theory           | Lewin, Bias Stack, Lencioni                       |
| Person-situation debate      | HEXACO, Lewin, McGregor                           |
| Cognitive-load + arousal     | Yerkes-Dodson                                     |
| Self-determination           | SDT Reward, Motivation Traps, Vroom Expectancy    |
| Emotion regulation           | Cognitive Reappraisal, Goleman EI, DANVA          |
| Self-awareness               | Johari, Bias Stack                                |
| Strengths inversion          | Grant Strengths                                   |
| Five-dysfunctions            | Lencioni                                          |
| Psychological safety         | Psych Safety, Glaser, Feedback Triggers           |
| Trust foundations            | Trust Triangle, McAllister Trust                  |
| Decision protocols           | Group Decision, Devil's Advocate, Debate Pathology|
| Feedback rituals             | Plus/Delta, Stone-Heen Feedback                   |
| Goal-setting                 | SMART Goal, GRPI                                  |
| Process-loss + composition   | Process Gain/Loss, Superflocks, Social Loafing    |
| Conflict styles              | Thomas-Kilmann                                    |
| Retrospectives               | AAR                                               |
| Culture                      | Schein, Robbins-Judge                             |
| Org design                   | Org Structure, Span of Control, McGregor          |

## Picking a pattern by AI-agent failure surface

| Failure surface                              | Patterns to start with                  |
|----------------------------------------------|------------------------------------------|
| Hallucinated facts / wrong citations         | Bias Stack, Trust Triangle, AAR          |
| Refused a safe request                       | Grant Strengths, HEXACO, Yerkes-Dodson   |
| Over-confident wrong claim                   | Trust Triangle, Bias Stack, Johari       |
| Sycophantic agreement under pressure         | Cognitive Reappraisal, Trust Triangle    |
| Apology spiral after correction              | Stone-Heen Feedback, Goleman EI          |
| Premature completion (declared done early)   | Grant Strengths, Devil's Advocate        |
| Stuck in a retry loop                        | AAR, Lewin, Bias Stack, Yerkes-Dodson    |
| Crew can't reach consensus                   | Debate Pathology, Devil's Advocate, Lencioni |
| Crew silently drops a constraint at handoff  | Process Gain/Loss, Psych Safety, GRPI    |
| Agents blaming each other                    | Lewin, Lencioni, Trust Triangle          |
| One orchestrator bottlenecks the crew        | Span of Control, McGregor, Process Gain/Loss |
| Long context, lost-in-the-middle             | Yerkes-Dodson (forensic), Lewin          |
| Org-scale drift from system prompt           | Schein, Robbins-Judge, Org Structure     |

For each of the failure surfaces above, a named recipe exists in the
catalog — invoke it directly via `--recipe <slug>` in
`vstack-diagnose` or `recipe=<slug>` in
`vstack.diagnose.diagnose()`. The cookbook scripts under
`examples/cookbook/` show each end-to-end (cookbook 04–14 cover the
new v0.19+ recipes).

## How patterns compose

Each pattern's intervention list can include a
`composition_target_pattern` field naming the next vstack pattern to
run. The runner does not follow these automatically (so you stay in
control of cost), but they're a hint set:

```python
report = diagnose(trace=t, llm_client=client, patterns=["lencioni"])
for pr in report.per_pattern:
    handoff = getattr(pr.result, "composition_handoff", None)
    if handoff and handoff.downstream_patterns:
        print(f"Lencioni suggests next: {handoff.downstream_patterns}")
```

The cookbook scripts use this pattern frequently — see
`examples/cookbook/01_aar_then_lewin.py` for the canonical chain.

## See also

- `docs/tutorials/01_first_diagnosis.md` — 15-minute end-to-end intro.
- `docs/tutorials/02_chaining_patterns.md` — manual composition guide.
- `docs/tutorials/03_framework_integrations.md` — LangChain / LangGraph /
  CrewAI / AutoGen / LlamaIndex / Pydantic-AI / OpenAI Assistants.
- `docs/tutorials/04_building_a_custom_pattern.md` — write your own.
- `docs/tutorials/05_mcp_deployment.md` — wire into Claude Desktop.
- `docs/tutorials/06_fastapi_deployment.md` — production HTTP API.
- The `vstack-dashboard` CLI (`render` and `serve`) — visual report viewer.
- The `vstack-diagnose` CLI — terminal entry point to the runner.
- The `vstack-recipes` CLI — browse the recipe catalog.
