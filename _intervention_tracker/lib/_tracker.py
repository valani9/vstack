"""Intervention tracker — record applied interventions and their outcomes."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class InterventionOutcome(str, Enum):
    """How an intervention turned out."""

    PENDING = "pending"
    RESOLVED = "resolved"
    PARTIAL = "partial"
    NO_EFFECT = "no_effect"
    REGRESSED = "regressed"
    ROLLED_BACK = "rolled_back"


@dataclass
class Intervention:
    """One recorded intervention."""

    id: str
    title: str
    pattern: str = ""
    severity_at_apply: str = ""
    applied_at: float = 0.0
    applied_by: str = ""
    finding_snapshot: dict[str, Any] = field(default_factory=dict)
    outcome: InterventionOutcome = InterventionOutcome.PENDING
    outcome_set_at: float | None = None
    outcome_notes: str = ""
    rollback_reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        return self.outcome in (
            InterventionOutcome.RESOLVED,
            InterventionOutcome.NO_EFFECT,
            InterventionOutcome.REGRESSED,
            InterventionOutcome.ROLLED_BACK,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "pattern": self.pattern,
            "severity_at_apply": self.severity_at_apply,
            "applied_at": self.applied_at,
            "applied_by": self.applied_by,
            "finding_snapshot": dict(self.finding_snapshot),
            "outcome": self.outcome.value,
            "outcome_set_at": self.outcome_set_at,
            "outcome_notes": self.outcome_notes,
            "rollback_reason": self.rollback_reason,
            "metadata": dict(self.metadata),
        }


@dataclass
class OutcomeStats:
    """Aggregate stats for a slice of interventions."""

    total: int = 0
    pending: int = 0
    resolved: int = 0
    partial: int = 0
    no_effect: int = 0
    regressed: int = 0
    rolled_back: int = 0

    @property
    def closed(self) -> int:
        return self.total - self.pending

    @property
    def effectiveness(self) -> float:
        """Fraction of closed interventions that resolved (full or partial)."""
        if self.closed == 0:
            return 0.0
        return (self.resolved + 0.5 * self.partial) / self.closed

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "pending": self.pending,
            "resolved": self.resolved,
            "partial": self.partial,
            "no_effect": self.no_effect,
            "regressed": self.regressed,
            "rolled_back": self.rolled_back,
            "closed": self.closed,
            "effectiveness": self.effectiveness,
        }


class InterventionTracker:
    """In-memory tracker. Persist via to_dict / from_dict to JSON."""

    def __init__(self):
        self._interventions: dict[str, Intervention] = {}
        self._counter: int = 0

    def record(
        self,
        *,
        title: str,
        finding: dict[str, Any] | None = None,
        applied_by: str = "",
        applied_at: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Intervention:
        """Record a newly-applied intervention; returns the Intervention.

        The returned ID is a synthesized string of the form
        ``"iv-N"`` where N counts up.
        """
        self._counter += 1
        iv_id = f"iv-{self._counter}"
        finding = finding or {}
        iv = Intervention(
            id=iv_id,
            title=title,
            pattern=str(finding.get("pattern", "")),
            severity_at_apply=str(finding.get("severity", "")),
            applied_at=applied_at if applied_at is not None else time.time(),
            applied_by=applied_by,
            finding_snapshot=dict(finding),
            metadata=dict(metadata or {}),
        )
        self._interventions[iv_id] = iv
        return iv

    def get(self, iv_id: str) -> Intervention:
        if iv_id not in self._interventions:
            raise KeyError(f"Unknown intervention id: {iv_id}")
        return self._interventions[iv_id]

    def set_outcome(
        self,
        iv_id: str,
        outcome: InterventionOutcome,
        *,
        notes: str = "",
        rollback_reason: str = "",
        when: float | None = None,
    ) -> Intervention:
        iv = self.get(iv_id)
        iv.outcome = outcome
        iv.outcome_set_at = when if when is not None else time.time()
        iv.outcome_notes = notes
        if outcome == InterventionOutcome.ROLLED_BACK:
            iv.rollback_reason = rollback_reason
        return iv

    def all(self) -> list[Intervention]:
        return list(self._interventions.values())

    def by_pattern(self, pattern: str) -> list[Intervention]:
        return [iv for iv in self._interventions.values() if iv.pattern == pattern]

    def by_applied_by(self, applied_by: str) -> list[Intervention]:
        return [iv for iv in self._interventions.values() if iv.applied_by == applied_by]

    def pending(self) -> list[Intervention]:
        return [
            iv for iv in self._interventions.values() if iv.outcome == InterventionOutcome.PENDING
        ]

    def closed(self) -> list[Intervention]:
        return [iv for iv in self._interventions.values() if iv.is_terminal]

    def stats(self, *, pattern: str | None = None) -> OutcomeStats:
        relevant = self.all()
        if pattern is not None:
            relevant = [iv for iv in relevant if iv.pattern == pattern]

        s = OutcomeStats(total=len(relevant))
        for iv in relevant:
            if iv.outcome == InterventionOutcome.PENDING:
                s.pending += 1
            elif iv.outcome == InterventionOutcome.RESOLVED:
                s.resolved += 1
            elif iv.outcome == InterventionOutcome.PARTIAL:
                s.partial += 1
            elif iv.outcome == InterventionOutcome.NO_EFFECT:
                s.no_effect += 1
            elif iv.outcome == InterventionOutcome.REGRESSED:
                s.regressed += 1
            elif iv.outcome == InterventionOutcome.ROLLED_BACK:
                s.rolled_back += 1
        return s

    def effectiveness_score(self, pattern: str) -> float:
        return self.stats(pattern=pattern).effectiveness

    def rank_patterns_by_effectiveness(self) -> list[tuple[str, float]]:
        patterns = sorted({iv.pattern for iv in self.all() if iv.pattern})
        scores = []
        for pattern in patterns:
            stats = self.stats(pattern=pattern)
            if stats.closed > 0:
                scores.append((pattern, stats.effectiveness))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores

    def to_dict(self) -> dict[str, Any]:
        return {
            "interventions": [iv.to_dict() for iv in self.all()],
            "stats_overall": self.stats().to_dict(),
        }

    def count(self) -> int:
        return len(self._interventions)
