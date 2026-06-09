# Concept — Recipes vs Bundles

> vstack has three ways to compose patterns: explicit pattern lists,
> named recipes, and shape-default bundles. This doc explains the
> distinction and when to use each.

---

## The three composition modes

### Mode 1: Explicit patterns

You name the patterns to run.

```python
from vstack import diagnose

report = diagnose(
    trace=trace,
    llm_client=llm,
    patterns=["lewin", "aar", "bias_stack"],
)
```

**Use when:** you know exactly which patterns you want.

**Cost:** sum of per-pattern costs.

### Mode 2: Named recipe

You name a recipe; the recipe picks the patterns.

```python
report = diagnose(
    trace=trace,
    llm_client=llm,
    recipe="stuck_in_loop",
)
```

**Use when:** the failure mode is named in the recipe catalog.

**Cost:** sum of the recipe's patterns' costs.

### Mode 3: Shape default

You name nothing; the trace shape picks a default bundle.

```python
report = diagnose(trace=trace, llm_client=llm)
```

**Use when:** you want a "best-default" diagnostic without thinking.

**Cost:** sum of the default bundle's patterns' costs.

---

## Recipes

A **recipe** is a named bundle of patterns curated for a specific
failure mode. Each recipe has:

```python
@dataclass
class Recipe:
    name: str                 # canonical name
    description: str           # one-paragraph description
    patterns: list[str]        # pattern slugs to run
    shape: str                 # individual / team / org
    cluster: str               # reasoning / coordination / trust / workload / culture
    triggers: list[str]        # free-text triggers for routing
    intervention_hint: str     # what the intervention pattern looks like
```

The catalog ships 33 recipes across 5 clusters. Browse:

```bash
vstack-recipes list
vstack-recipes list --cluster reasoning
vstack-recipes show stuck_in_loop
```

---

## Default bundles

A **bundle** is a *shape-specific default* pattern list that runs
when no recipe is specified. The default bundles:

### Individual shape

```python
DEFAULT_INDIVIDUAL = [
    "lewin",
    "goleman_ei",
    "yerkes_dodson",
    "motivation_traps",
    "johari",
    "aar",
]
```

### Team shape

```python
DEFAULT_TEAM = [
    "grpi",
    "trust_triangle",
    "process_gain_loss",
    "lencioni",
    "social_loafing",
    "aar",
]
```

### Org shape

```python
DEFAULT_ORG = [
    "schein_culture",
    "robbins_culture",
    "org_structure",
    "span_of_control",
]
```

These are the *load-bearing* patterns for each shape — what you'd
run if you only had budget for 4-6 patterns.

---

## When to use each mode

| You know...                          | Use mode             |
|--------------------------------------|----------------------|
| The specific patterns to run         | Mode 1 (explicit)    |
| The named failure mode               | Mode 2 (recipe)      |
| Nothing yet — want a triage          | Mode 3 (shape default)|
| The failure cluster but not recipe   | Mode 2 with `cluster=` filter |

---

## Building a custom bundle

If you have a domain-specific failure pattern not in the catalog,
build a custom recipe:

```python
from vstack.diagnose import register_recipe, Recipe

register_recipe(Recipe(
    name="my_domain_failure",
    description="Failure mode specific to my domain.",
    patterns=["lewin", "yerkes_dodson", "motivation_traps", "aar"],
    shape="individual",
    cluster="reasoning",
    triggers=[
        "my domain symptom 1",
        "my domain symptom 2",
    ],
    intervention_hint=(
        "1. Identify the locus (Lewin). 2. Check for load issues "
        "(Yerkes-Dodson). 3. Inspect reward signals (Motivation Traps). "
        "4. Record lessons (AAR)."
    ),
))

# Now use it:
report = diagnose(trace=trace, llm_client=llm, recipe="my_domain_failure")
```

Custom recipes are *not* persisted across processes. To make them
permanent, contribute them to the catalog via PR.

---

## Free-text recipe routing

If you don't know the recipe name but you can describe the
symptom, use free-text routing:

```python
from vstack.diagnose import route_recipe

trigger_text = "Our agent keeps trying the same fix over and over."
recipe_name = route_recipe(trigger_text)
# Returns: "stuck_in_loop"

report = diagnose(trace=trace, llm_client=llm, recipe=recipe_name)
```

Or directly via the CLI:

```bash
vstack-recipes match "agents keep arguing about who's right"
# Returns: "agents_arguing"
```

---

## Recipe composition

Recipes can be combined to handle multi-symptom failures:

```python
from vstack.diagnose import diagnose

reports = []
for recipe in ["stuck_in_loop", "overconfidence_spiral"]:
    reports.append(diagnose(
        trace=trace,
        llm_client=llm,
        recipe=recipe,
    ))

# Merge.
from vstack.diagnose import merge_reports
combined = merge_reports(reports)
print(combined.to_markdown())
```

The merge dedupes patterns that ran in both recipes and aggregates
findings.

---

## Recipe vs WALKTHROUGH

A **recipe** is a *runnable bundle*. A **WALKTHROUGH** is a
*documentation* deep-dive on a single pattern. They're
complementary:

- The recipe tells you *what to run*.
- The WALKTHROUGH tells you *what to expect* from each pattern.

Every pattern has a WALKTHROUGH. Every named failure mode has a
recipe. They cross-reference each other.

---

## Production usage patterns

### Quick triage

```python
# Mode 3 — shape default. Cheap, generic.
report = diagnose(trace=trace, llm_client=fast_client, mode="quick")
```

### Targeted diagnosis

```python
# Mode 2 — named recipe. Targeted, full mode.
report = diagnose(
    trace=trace,
    llm_client=client,
    recipe="stuck_in_loop",
    mode="standard",
)
```

### Forensic deep-dive

```python
# Mode 1 — explicit patterns + forensic mode. Most expensive.
report = diagnose(
    trace=trace,
    llm_client=deep_client,
    patterns=["lewin", "yerkes_dodson", "motivation_traps", "bias_stack", "aar"],
    mode="forensic",
)
```

---

## See also

- Recipes overview: `docs/RECIPES_OVERVIEW.md`
- Concept: composition (`docs/concepts/composition.md`)
- Per-recipe cookbook scripts: `examples/cookbook/`
- Per-cluster combined demos: `examples/clusters/`
