# Per-Cluster Combined Recipe Demos

The 33 named recipes in the catalog organise into 5 thematic
clusters. Each cluster has shared *symptoms* and shared
*intervention patterns*; running the cluster's recipes together
surfaces which dimension is broken before you commit to a specific
recipe.

| Cluster        | Demo                                  | Recipes covered                                                                              |
|----------------|---------------------------------------|----------------------------------------------------------------------------------------------|
| Reasoning      | `01_reasoning_combined.py`            | stuck_in_loop, hallucination_cascade, overconfidence_spiral, context_saturation, tool_misuse |
| Coordination   | `02_coordination_combined.py`         | bottleneck_orchestrator, cold_handoff, consensus_dilution, role_thrash, hub_spoke_fragility, hyper_specialization |
| Trust          | `03_trust_combined.py`                | trust_collapse, silent_failure, deference_cascade, blame_spiral, sycophancy_drift, overconfidence_spiral |
| Workload       | `04_workload_combined.py`             | context_saturation, motivation_collapse, anxious_overhedge, plan_collapse, premature_completion, performative_empathy |
| Culture        | `05_culture_combined.py`              | culture_drift, espoused_actual_drift, policy_decay, refusal_cascade, over_apology_loop      |

## When to use cluster demos vs single recipes

- **Cluster demos**: when the symptom is broad ("our agents feel
  slow" / "users complain about hollow empathy") and you don't yet
  know which specific recipe fits.
- **Single recipes**: when the failure mode is named and you know
  exactly which composition to run.

## Composition with the cluster demos

Each cluster demo prints a side-by-side summary across the
recipes. The pattern overlap surfaces the *common* failure mode —
e.g. if 4 of 5 coordination recipes flag Span of Control, that's
the load-bearing issue.

Once the dominant cluster dimension is identified, branch to the
specific WALKTHROUGH:

- Reasoning → [Lewin](../../module-1-individual/01-lewin-formula/WALKTHROUGH.md), [Yerkes-Dodson](../../module-1-individual/06-yerkes-dodson-workload/WALKTHROUGH.md)
- Coordination → [GRPI](../../module-2-team/13-grpi-working-agreement/WALKTHROUGH.md), [Span of Control](../../module-3-organization/34-span-of-control/WALKTHROUGH.md)
- Trust → [Trust Triangle](../../module-2-team/18-trust-triangle-audit/WALKTHROUGH.md), [Lencioni](../../module-2-team/17-lencioni-diagnostic/WALKTHROUGH.md)
- Workload → [Yerkes-Dodson](../../module-1-individual/06-yerkes-dodson-workload/WALKTHROUGH.md), [Vroom](../../module-1-individual/12-vroom-expectancy/WALKTHROUGH.md)
- Culture → [Schein Iceberg](../../module-3-organization/31-schein-iceberg-culture/WALKTHROUGH.md), [Robbins-Judge](../../module-3-organization/32-robbins-judge-7-culture/WALKTHROUGH.md)
