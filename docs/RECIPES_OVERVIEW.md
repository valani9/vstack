# vstack recipes — catalog overview

A **recipe** is a curated bundle of vstack patterns that together
diagnose one recognizable kind of agent or crew failure. Where the
default bundle picks "all team patterns" for a team trace, a recipe
like `silent_dependency_drop` picks exactly the 4 patterns that
matter for that one failure mode.

v0.19.0 grew the catalog from 8 to 33 named recipes across 5
thematic clusters. The full catalog lives at
`_diagnose/lib/recipes.py`; this page is the human-readable index.

## Browse from the terminal

```bash
vstack-recipes                                  # all 33, grouped by cluster
vstack-recipes --cluster reasoning              # one cluster
vstack-recipes --shape team                     # one trace shape
vstack-recipes --q apology                      # substring search
vstack-recipes --match "agent keeps refusing"   # free-text trigger router
vstack-recipes --show stuck_in_loop             # full detail for one recipe
vstack-recipes --show stuck_in_loop --md        # ready-to-paste Markdown
```

## Catalog

### Reasoning failures (single-agent)

| Recipe                  | Patterns                                          | Triggers (sample) |
|-------------------------|---------------------------------------------------|--------------------|
| `stuck_in_loop`         | aar, lewin, bias_stack, yerkes_dodson             | stuck in loop, keeps making the same mistake |
| `hallucination_cascade` | bias_stack, trust_triangle, aar, devils_advocate  | hallucination, fabricated citation, confidently wrong |
| `overconfidence_spiral` | trust_triangle, bias_stack, hexaco, johari        | overconfident, false certainty, under-hedged |
| `sycophancy_drift`      | cognitive_reappraisal, trust_triangle, grant_strengths, feedback_triggers | caved under pressure, abandoned correct answer |
| `refusal_cascade`       | grant_strengths, hexaco, yerkes_dodson, trust_triangle | over-refusal, refuses safe request, reflexive refusal |
| `plan_collapse`         | smart_goal, yerkes_dodson, lewin, aar             | plan fell apart, execution broke |
| `premature_completion`  | grant_strengths, devils_advocate, smart_goal, johari | shipped half-done, skipped verification |
| `tool_misuse`           | lewin, aar, bias_stack, yerkes_dodson             | wrong tool, bad tool args, tool hallucination |
| `over_apology_loop`     | feedback_triggers, cognitive_reappraisal, goleman_ei, trust_triangle | apology spiral, won't stop apologizing |
| `anxious_overhedge`     | grant_strengths, cognitive_reappraisal, danva_emotion, yerkes_dodson | over-hedged, every claim qualified |
| `motivation_collapse`   | motivation_traps, sdt_reward, vroom_expectancy, yerkes_dodson | motivation collapse, stopped trying |
| `goal_misalignment`     | smart_goal, vroom_expectancy, motivation_traps, sdt_reward | wrong problem, scope drift, lost the goal |

### Multi-agent coordination failures (team)

| Recipe                       | Patterns                                          | Triggers (sample) |
|------------------------------|---------------------------------------------------|--------------------|
| `agents_arguing`             | debate_pathology, devils_advocate, thomas_kilmann, lencioni | won't agree, decision paralysis, infighting |
| `bottleneck_agent`           | superflocks, process_gain_loss, span_of_control, mcgregor | bottleneck, one agent does everything |
| `bad_feedback_loop`          | feedback_triggers, plus_delta, glaser_conversation, cognitive_reappraisal | feedback ignored, won't take feedback |
| `silent_dependency_drop`     | process_gain_loss, psych_safety, grpi, aar       | silent dependency drop, info loss across agents |
| `handoff_loss`               | process_gain_loss, grpi, span_of_control, plus_delta | leaky handoff, info dropped between agents |
| `consensus_dilution`         | process_gain_loss, group_decision, devils_advocate, debate_pathology | averaged the answer, lowest common denominator |
| `deference_cascade`          | psych_safety, devils_advocate, lencioni, glaser_conversation | junior agents defer, no one pushes back |
| `expert_loafing`             | social_loafing, process_gain_loss, superflocks, grpi | specialist phoning in, underused expert |

### Trust + relationship failures (team)

| Recipe                  | Patterns                                          | Triggers (sample) |
|-------------------------|---------------------------------------------------|--------------------|
| `silent_failure`        | psych_safety, trust_triangle, social_loafing, aar | reported success but broke, no one raised the issue |
| `trust_collapse`        | trust_triangle, mcallister_trust, lencioni, grpi  | over-verification, redoing each other's work |
| `cold_handoff`          | mcallister_trust, glaser_conversation, goleman_ei, trust_triangle | passed around, no warm transfer |
| `performative_empathy`  | mcallister_trust, trust_triangle, goleman_ei, danva_emotion | template warmth, fake empathy |
| `blame_spiral`          | lewin, lencioni, trust_triangle, cognitive_reappraisal | finger pointing, scapegoating |

### Workload + structural failures (individual/team)

| Recipe                    | Patterns                                          | Triggers (sample) |
|---------------------------|---------------------------------------------------|--------------------|
| `context_saturation`      | yerkes_dodson, lewin, aar, smart_goal             | lost in the middle, context bloat |
| `decision_paralysis`      | group_decision, lencioni, debate_pathology, devils_advocate | over-deliberation, can't pick |
| `bottleneck_orchestrator` | span_of_control, mcgregor, process_gain_loss, grpi | theory-x orchestrator, approves everything |
| `hub_spoke_fragility`     | superflocks, org_structure, span_of_control, process_gain_loss | one node failure broke everything |
| `role_thrash`             | grpi, devils_advocate, lencioni, process_gain_loss | role thrash, no stable role |

### Culture + org failures (org)

| Recipe                      | Patterns                                          | Triggers (sample) |
|-----------------------------|---------------------------------------------------|--------------------|
| `culture_drift`             | schein_culture, robbins_culture, org_structure, span_of_control | drift, policy not followed |
| `espoused_actual_drift`     | schein_culture, robbins_culture, org_structure, aar | espoused vs actual drift, behavior contradicts policy |
| `policy_decay`              | schein_culture, robbins_culture, span_of_control, org_structure | policy decay, exception became the norm |
| `hyper_specialization`      | org_structure, superflocks, span_of_control, robbins_culture | hyper-specialization, single-skill agents |

## Invoking a recipe

In Python:

```python
from vstack.aar.clients import AnthropicClient
from vstack.diagnose import diagnose

report = diagnose(
    trace=your_trace,
    llm_client=AnthropicClient(),
    recipe="stuck_in_loop",
)
print(report.to_markdown())
```

From the CLI:

```bash
vstack-diagnose --trace your-trace.json --recipe stuck_in_loop
```

Through MCP (Claude Desktop / Cursor / Cline):

```
Use vstack_diagnose with trace=... and recipe="stuck_in_loop"
```

Through HTTP (`vstack-api`):

```bash
curl -X POST http://localhost:8000/v1/diagnose \
  -H 'content-type: application/json' \
  -d '{"trace": {...}, "recipe": "stuck_in_loop"}'
```

## Free-text trigger routing

You don't need to remember slugs. If you can describe the failure in
plain English, `recipe_for_trigger()` matches:

```python
from vstack.diagnose import recipe_for_trigger

r = recipe_for_trigger("the orchestrator is approving every spoke action")
# -> Recipe(name='bottleneck_orchestrator', ...)
```

The CLI exposes the same:

```bash
vstack-recipes --match "the orchestrator is approving every spoke action"
```

Matching is keyword-based; each recipe ships 4–6 trigger phrases and
the first hit wins. Returns `None` if no trigger matches — fall back
to the shape-default bundle (`diagnose(trace=t, llm_client=...)` with
no `recipe=` argument) in that case.

## Adding a new recipe

Open `_diagnose/lib/recipes.py`, append a `Recipe(...)` entry to
`_CATALOG`. The construction validates every named pattern at import
time, so a typo fails immediately:

```python
Recipe(
    name="my_new_recipe",
    description="...",
    patterns=("pattern_a", "pattern_b"),
    shape="team",
    triggers=("...", "..."),
    cluster="reasoning",  # or coordination/trust/workload/culture/general
)
```

Run `pytest _diagnose/tests/ -q` to confirm; the catalog validation
is part of the test suite.

## See also

- `_diagnose/lib/recipes.py` — source
- `docs/tutorials/01_first_diagnosis.md` — when to use recipes
- `docs/PATTERNS_OVERVIEW.md` — pattern catalog
- The cookbook scripts under `examples/cookbook/` — end-to-end demos
