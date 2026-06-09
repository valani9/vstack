"""Heap-backed priority queue for findings."""

from __future__ import annotations

import heapq
import time
from dataclasses import dataclass
from typing import Any


_SEVERITY_WEIGHT = {"high": 100.0, "medium": 10.0, "low": 1.0, "none": 0.0}


@dataclass
class QueueEntry:
    """One entry in the priority queue."""

    finding: dict[str, Any]
    inserted_at: float
    manual_boost: float = 0.0
    sequence: int = 0  # tiebreaker for stable ordering

    def base_score(self) -> float:
        sev = self.finding.get("severity", "low") or "low"
        conf = self.finding.get("confidence", 0.5)
        if conf is None:
            conf = 0.5
        try:
            conf_f = float(conf)
        except (TypeError, ValueError):
            conf_f = 0.5
        # Confidence multiplier clamped to [0.5, 1.0]; high conf weights more.
        conf_mult = 0.5 + 0.5 * max(0.0, min(1.0, conf_f))
        return _SEVERITY_WEIGHT.get(sev, 1.0) * conf_mult

    def age_boost(self, now: float, aging_multiplier: float) -> float:
        """Returns an additive boost based on elapsed time."""
        elapsed = max(0.0, now - self.inserted_at)
        hours = elapsed / 3600.0
        return hours * aging_multiplier

    def score(self, now: float, aging_multiplier: float) -> float:
        return self.base_score() + self.age_boost(now, aging_multiplier) + self.manual_boost


class FindingPriorityQueue:
    """Max-priority queue keyed by computed score.

    The heap stores negative scores so Python's min-heap behaves as
    a max-heap. Tiebreaker = insertion sequence (LIFO would be wrong
    — we want FIFO for same-score items so older items pop first).
    """

    def __init__(self, *, aging_multiplier: float = 1.0):
        self.aging_multiplier = aging_multiplier
        self._heap: list[tuple[float, int, int, QueueEntry]] = []
        self._counter: int = 0

    def push(
        self,
        finding: dict[str, Any],
        *,
        manual_boost: float = 0.0,
        inserted_at: float | None = None,
    ) -> QueueEntry:
        ts = inserted_at if inserted_at is not None else time.time()
        self._counter += 1
        entry = QueueEntry(
            finding=dict(finding),
            inserted_at=ts,
            manual_boost=manual_boost,
            sequence=self._counter,
        )
        score = entry.score(now=ts, aging_multiplier=self.aging_multiplier)
        # heap key: (-score, sequence, neg_inserted_at, entry).
        # neg_inserted_at as tiebreaker so older items win when scores tie.
        heapq.heappush(self._heap, (-score, self._counter, -int(ts * 1000), entry))
        return entry

    def pop(self, *, now: float | None = None) -> dict[str, Any] | None:
        """Pop the highest-scoring finding.

        Recomputes score against ``now`` so aging boost is applied
        at pop-time, not push-time. Returns ``None`` if empty.
        """
        if not self._heap:
            return None

        current = now if now is not None else time.time()

        # Recompute scores; pull all entries; rebuild heap.
        entries = [item[3] for item in self._heap]
        best_idx = 0
        best_score = entries[0].score(now=current, aging_multiplier=self.aging_multiplier)
        best_inserted = entries[0].inserted_at
        for i, e in enumerate(entries[1:], 1):
            s = e.score(now=current, aging_multiplier=self.aging_multiplier)
            # Higher score wins; tiebreak on earlier inserted_at.
            if s > best_score or (s == best_score and e.inserted_at < best_inserted):
                best_score = s
                best_inserted = e.inserted_at
                best_idx = i

        chosen = entries.pop(best_idx)
        # Rebuild heap from remaining entries.
        self._heap = []
        for e in entries:
            score = e.score(now=current, aging_multiplier=self.aging_multiplier)
            heapq.heappush(
                self._heap,
                (-score, e.sequence, -int(e.inserted_at * 1000), e),
            )
        return chosen.finding

    def peek(self, *, now: float | None = None) -> dict[str, Any] | None:
        """Look at the top finding without removing it."""
        if not self._heap:
            return None
        current = now if now is not None else time.time()
        # Recompute scores.
        best = max(
            (item[3] for item in self._heap),
            key=lambda e: (
                e.score(now=current, aging_multiplier=self.aging_multiplier),
                -e.inserted_at,
            ),
        )
        return best.finding

    def boost(self, finding_pattern: str, additive_boost: float) -> int:
        """Boost the score of all matching findings by ``additive_boost``.

        Returns the number of findings boosted.
        """
        n = 0
        for item in self._heap:
            entry = item[3]
            if entry.finding.get("pattern") == finding_pattern:
                entry.manual_boost += additive_boost
                n += 1
        return n

    def remove_pattern(self, pattern: str) -> int:
        """Remove all findings for a pattern. Returns count removed."""
        before = len(self._heap)
        self._heap = [item for item in self._heap if item[3].finding.get("pattern") != pattern]
        heapq.heapify(self._heap)
        return before - len(self._heap)

    def clear(self) -> None:
        self._heap.clear()
        self._counter = 0

    def __len__(self) -> int:
        return len(self._heap)

    def is_empty(self) -> bool:
        return len(self._heap) == 0

    def snapshot(self, *, now: float | None = None) -> list[tuple[dict[str, Any], float]]:
        """Return all entries as (finding, score) ordered by descending score."""
        current = now if now is not None else time.time()
        entries = [item[3] for item in self._heap]
        scored = [
            (e.finding, e.score(now=current, aging_multiplier=self.aging_multiplier))
            for e in entries
        ]
        scored.sort(key=lambda kv: kv[1], reverse=True)
        return scored
