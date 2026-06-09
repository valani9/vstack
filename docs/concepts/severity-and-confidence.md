# Concept — Severity and Confidence

> Every vstack finding carries a `severity` (low / medium / high)
> and a `confidence` (0.0-1.0). This doc explains what each means,
> how they're produced, and how to act on the combination.

---

## Severity

`severity` is a categorical label for *how serious the finding is*
if true:

- `low` — informational; track but don't act.
- `medium` — needs intervention but not blocking.
- `high` — blocks ship / triggers escalation.

Severity is set by the pattern's prompt-level logic. Each pattern
encodes its own severity rules (Lewin maps locus-shifts to severity;
Goleman maps profile-collapse to severity; etc.).

---

## Confidence

`confidence` is a scalar [0.0, 1.0] for *how sure the analysis is*
that the finding is true.

- `0.0-0.4` — uncertain; surface as informational only.
- `0.5-0.7` — moderate; worth investigating.
- `0.8-1.0` — confident; act on it.

Confidence is set by the LLM's self-report + downstream calibration
(see "Calibration" below).

---

## The 2x2 matrix

|                       | Low severity        | High severity         |
|-----------------------|---------------------|-----------------------|
| **Low confidence**    | Discard / observe    | Investigate — manual review |
| **High confidence**   | Track / informational| ACT — blocking         |

---

## How severity is set

Each pattern has a severity-assignment heuristic in its prompt:

### Lewin

- `severity=high` when locus differs from initial attribution
  AND counterfactual swap is testable.
- `severity=medium` when locus agrees with initial attribution
  but interventions point elsewhere.
- `severity=low` when no actionable intervention surfaces.

### Goleman EI

- `severity=high` when a profile collapse mode is detected
  (sycophancy / hollow empathy / over-apology).
- `severity=medium` when one domain is weak but others compensate.
- `severity=low` when all four domains are present at baseline.

### (other patterns)

See each pattern's `prompts.py` for the severity rules. Each
pattern documents the severity heuristic in its WALKTHROUGH.

---

## How confidence is set

Confidence has three sources:

### Source 1: LLM self-report

The pattern's prompt asks the LLM to rate confidence in its
finding. The raw self-report is typically over-confident (a
known LLM calibration issue).

### Source 2: Calibration

vstack applies a calibration curve to LLM self-reports based on
the pattern's `_calibration.py`:

```python
from vstack.lewin import calibrate_confidence

raw_confidence = 0.9
calibrated = calibrate_confidence(raw_confidence, pattern="lewin")
# Typically 0.7-0.8 — LLMs overweight on self-reported confidence.
```

### Source 3: Evidence count

Findings with multiple evidence quotes get a confidence bump:

- 0 quotes → confidence * 0.7
- 1 quote → confidence * 0.9
- 2+ quotes → confidence * 1.0

---

## Calibration

LLM self-reported confidence is poorly calibrated. vstack ships a
calibration curve per pattern + per mode that's been empirically
fit on a held-out eval set.

To inspect the calibration:

```python
from vstack.lewin import get_calibration_curve

curve = get_calibration_curve(pattern="lewin", mode="standard")
for raw, calibrated in curve.items():
    print(f"{raw:.2f} → {calibrated:.2f}")
```

To recalibrate (e.g., for a new model):

```python
from vstack.lewin import fit_calibration_curve

# Run the pattern on a held-out eval set with ground truth.
predictions = [(detection, ground_truth) for ...]

new_curve = fit_calibration_curve(predictions)
save_calibration_curve(new_curve, "calibrations/lewin-2026-Q2.json")
```

---

## Practical thresholds

### Production blocking

Block on findings where `severity=high` AND `confidence >= 0.7`.

```python
def is_blocking(finding):
    return finding.severity == "high" and finding.confidence >= 0.7
```

### Production alerting

Alert on findings where `severity in {medium, high}` AND
`confidence >= 0.5`:

```python
def is_alertable(finding):
    return (
        finding.severity in ("medium", "high")
        and finding.confidence >= 0.5
    )
```

### Dashboard surfacing

Surface findings on the dashboard at any confidence; users can
filter:

```python
# All findings go to the dashboard; filtering is UI-side.
dashboard.submit(report)
```

---

## Severity drift

Tracking severity *changes* over time is more informative than
absolute severity:

```python
def severity_drift_alert(report, baseline):
    """Alert if any pattern's severity escalated."""
    for pattern_name, current in report.per_pattern.items():
        previous = baseline.per_pattern.get(pattern_name)
        if previous and current.severity > previous.severity:
            alert(
                pattern=pattern_name,
                from_=previous.severity,
                to=current.severity,
            )
```

A pattern that was previously `low` and is now `high` is the
canonical "something broke" signal.

---

## Confidence rejection

If your fleet routinely shows high-severity / low-confidence
findings, the LLM is uncertain. Common causes:

- The trace is incomplete (missing fields).
- The pattern is the wrong call for this trace shape.
- The LLM client is rate-limited or returning partial responses.

Handle by:

```python
if any(f.confidence < 0.4 and f.severity == "high" for f in report.findings):
    # Re-run in forensic mode (more LLM calls, higher confidence).
    report = diagnose(trace=trace, llm_client=llm, mode="forensic")
```

---

## See also

- Concept: composition (`docs/concepts/composition.md`)
- Concept: baselines (`docs/concepts/baselines.md`)
- Pattern-specific severity rules: each pattern's WALKTHROUGH.md
