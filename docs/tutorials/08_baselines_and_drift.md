# Tutorial 8 — Baselines and Drift Detection

> Goal: use vstack's baseline + drift detection to catch silent
> regressions between releases. Covers per-pattern baselines,
> aggregate fleet baselines, and CI integration.

---

## What you'll build

By the end of this tutorial you'll have:

1. A recorded baseline for one production agent.
2. A drift-detection CI gate that flags regressions.
3. A multi-pattern fleet baseline for tracking culture drift.

---

## Part 1 — Per-pattern baselines

Every pattern ships with `record_baseline()` + `load_baseline()` +
`compare_to_baseline()` helpers. They follow the same shape across
patterns.

### Recording a baseline

After a successful run that you want to lock as the gold standard:

```python
from vstack.lewin import (
    LewinAttributionDetector,
    record_baseline,
)
from vstack.aar.clients import AnthropicClient

detection = LewinAttributionDetector(AnthropicClient()).run(trace)
record_baseline(detection, "baselines/qa-bot-001-v4.6-lewin.json")
```

The baseline file is JSON and human-readable. Commit it to your
repo so future runs can compare against it.

### Comparing against a baseline

```python
from vstack.lewin import compare_to_baseline, load_baseline

baseline = load_baseline("baselines/qa-bot-001-v4.6-lewin.json")
drift = compare_to_baseline(detection, baseline)

if drift.locus_shifted:
    print(f"Locus shifted from {drift.from_locus} to {drift.to_locus}")
if drift.severity_increased:
    print(f"Severity increased: {drift.delta}")
```

### Per-pattern drift fields

Each pattern reports the dimensions that matter for *its* axis:

| Pattern              | Drift dimensions                                                |
|----------------------|------------------------------------------------------------------|
| Lewin                | `locus_shifted`, `intervention_changed`, `severity_increased`   |
| Goleman EI           | `profile_shifted`, `domain_dropped`, `axis_collapsed`           |
| Johari               | `arena_shrunk`, `blind_spot_grew`, `facade_grew`                |
| HEXACO               | `factor_shifted`, `h_dropped`, `a_jumped`                       |
| Yerkes-Dodson        | `optimal_load_shifted_down`, `arousal_region_changed`           |
| Trust Triangle       | `leg_broken`, `leg_repaired`                                    |
| Schein Iceberg       | `assumption_shifted`, `value_drifted`, `artefact_changed`       |
| Robbins-Judge        | `any_dimension_shifted_by`, `target_profile_mismatch`           |
| (etc.)               | (see each pattern's `_calibration.py` for the full list)        |

---

## Part 2 — CI gate

Wire the drift detection into your CI so regressions block the
build.

### Example: GitHub Actions

```yaml
name: vstack drift gate

on: [pull_request]

jobs:
  drift-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install
        run: pip install valanistack

      - name: Run drift check
        env:
          VSTACK_LLM_KEY: ${{ secrets.LLM_KEY }}
        run: |
          python scripts/drift_check.py
```

### `scripts/drift_check.py`

```python
"""Run the agent on a fixed regression suite + compare to baseline."""

import sys
from pathlib import Path

from vstack import diagnose
from vstack.aar.clients import AnthropicClient

REGRESSION_SUITE = [
    ("regression-traces/case-001.json", "baselines/lewin-001.json"),
    ("regression-traces/case-002.json", "baselines/lewin-002.json"),
    # ... 8 more cases
]


def main() -> int:
    failures = []
    for trace_path, baseline_path in REGRESSION_SUITE:
        trace = load_trace(trace_path)
        report = diagnose(trace=trace, llm_client=AnthropicClient())

        # Get the Lewin per-pattern result.
        lewin_result = report.per_pattern["lewin"]

        # Compare against the baseline.
        from vstack.lewin import compare_to_baseline, load_baseline
        baseline = load_baseline(baseline_path)
        drift = compare_to_baseline(lewin_result, baseline)

        if drift.locus_shifted or drift.severity_increased:
            failures.append(f"{trace_path}: {drift}")

    if failures:
        print("DRIFT DETECTED:")
        for f in failures:
            print(f"  {f}")
        return 1
    print(f"OK: {len(REGRESSION_SUITE)} cases passed drift check")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### What to baseline

- High-volume production tasks (catch regressions before users do).
- Known-good benchmark suite (lock in the eval performance).
- Critical safety-relevant interactions (catch silent safety
  regressions).

### When to update baselines

- After a successful release where you've verified the new
  behaviour is intended.
- Never auto-update baselines on drift — that defeats the purpose.
- Use a separate workflow that requires explicit approval to update.

---

## Part 3 — Aggregate fleet baselines

Per-pattern baselines catch single-agent regression. Aggregate
baselines catch *culture* drift across the fleet.

### Recording an aggregate baseline

```python
from vstack.schein_culture import (
    SchemaIcebergDetector,
    record_baseline as record_schein_baseline,
)
from vstack.robbins_culture import (
    CultureProfileDetector,
    record_baseline as record_robbins_baseline,
)

# Sample 30 agents from the fleet.
fleet_samples = collect_fleet_samples(n=30)

# Schein baseline: artefact / value / assumption layers.
schein_result = SchemaIcebergDetector(llm).run(fleet_samples)
record_schein_baseline(schein_result, "baselines/fleet-2026-Q2-schein.json")

# Robbins-Judge baseline: 7-dimension culture profile.
robbins_result = CultureProfileDetector(llm).run(fleet_samples)
record_robbins_baseline(robbins_result, "baselines/fleet-2026-Q2-robbins.json")
```

### Weekly drift check

```python
def weekly_culture_drift_check():
    """Check whether the fleet's culture has drifted from the
    quarterly baseline.
    """
    current_samples = collect_fleet_samples(n=30)
    current_schein = SchemaIcebergDetector(llm).run(current_samples)
    current_robbins = CultureProfileDetector(llm).run(current_samples)

    schein_baseline = load_schein_baseline("baselines/fleet-2026-Q2-schein.json")
    robbins_baseline = load_robbins_baseline("baselines/fleet-2026-Q2-robbins.json")

    schein_drift = compare_schein(current_schein, schein_baseline)
    robbins_drift = compare_robbins(current_robbins, robbins_baseline)

    if schein_drift.assumption_shifted:
        alert("Schein assumption layer drifted")
    if robbins_drift.any_dimension_shifted_by(threshold=2):
        alert("Robbins-Judge culture drift")
```

### What drift to treat as P1

| Drift kind                          | Severity                              |
|-------------------------------------|---------------------------------------|
| Schein assumption-layer shift       | P1 — investigate prompt changes       |
| Robbins-Judge H-factor drop > 1.5pt | P1 — likely sycophancy regression     |
| HEXACO H-factor drop > 1pt          | P1 — fleet honesty regression         |
| Johari ARENA shrinkage > 20%        | P1 — fleet capability claim regression |
| Lewin locus shift                   | P1 — silent regression mode change    |
| Goleman EI profile collapse         | P2 — affective regression             |
| Yerkes-Dodson optimal load shift    | P2 — model capacity regression        |
| (other shifts within threshold)     | P3 — track over time                  |

---

## Part 4 — Baselining anti-patterns

### Anti-pattern 1: baseline on a single run

A single run isn't a baseline. The agent's variance across runs
is real signal. Baseline on N=10+ runs and record statistics
(median + IQR).

### Anti-pattern 2: auto-update on drift

If your CI auto-updates the baseline when drift detected, drift
detection is useless. The baseline is supposed to be sticky.

### Anti-pattern 3: baseline at first release

The first release usually isn't the gold standard. Baseline after
you've shipped a release you're happy with — not at the start.

### Anti-pattern 4: too many baselines

If every agent has 34 baselines (one per pattern), you'll never
update them. Baseline the *3-5 patterns that matter* for that agent.

---

## See also

- Tutorial 7: Dashboard Deployment
- Pattern WALKTHROUGHs (every pattern has a "Baseline drift detection"
  section)
- Concepts: `docs/concepts/baselines.md`
