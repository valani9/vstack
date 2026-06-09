"""vstack.intervention_tracker — track applied interventions + outcomes.

An intervention is a remediation surfaced by a vstack finding (e.g.
"add explicit termination criterion to prompt"). The tracker module
records:

  - When an intervention was applied.
  - The finding that triggered it.
  - The outcome — did the finding recur? Did severity drop?
  - Whether the intervention was rolled back.

Use cases
---------

* **Compounding learning** — over time, which interventions actually
  work for your fleet?
* **Audit trail** — explain why a prompt change was made.
* **Effectiveness scoring** — rank intervention types by efficacy.

Quick start
-----------

    from vstack.intervention_tracker import (
        InterventionTracker,
        Intervention,
        InterventionOutcome,
    )

    tracker = InterventionTracker()

    iv = tracker.record(
        title="Add explicit termination criterion",
        finding={"pattern": "yerkes_dodson", "severity": "high"},
        applied_by="alice",
    )

    # Later, mark whether it worked:
    tracker.set_outcome(iv.id, InterventionOutcome.RESOLVED)

    # Or roll back:
    tracker.set_outcome(iv.id, InterventionOutcome.ROLLED_BACK)

    # Query effectiveness:
    score = tracker.effectiveness_score("yerkes_dodson")
    print(f"yerkes_dodson interventions: {score:.0%} resolved")
"""

from __future__ import annotations

from ._tracker import (
    Intervention,
    InterventionOutcome,
    InterventionTracker,
    OutcomeStats,
)

__all__ = [
    "Intervention",
    "InterventionOutcome",
    "InterventionTracker",
    "OutcomeStats",
]
