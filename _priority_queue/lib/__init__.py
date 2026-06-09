"""vstack.priority_queue — finding priority queue with aging.

A heap-backed priority queue for findings. Computes priority from:

  - Severity weight (high=100, medium=10, low=1)
  - Confidence multiplier (0.5-1.0)
  - Aging boost: older items get higher priority over time
  - Manual boost: caller-specified override

Aging prevents starvation of low-severity findings: by default an
item gets a +1% boost per hour. Tune with ``aging_multiplier``.

Quick start
-----------

    from vstack.priority_queue import FindingPriorityQueue

    queue = FindingPriorityQueue()
    queue.push({"pattern": "lewin", "severity": "high", "confidence": 0.9})
    queue.push({"pattern": "aar", "severity": "medium", "confidence": 0.5})
    queue.push({"pattern": "grpi", "severity": "low", "confidence": 0.9})

    top = queue.pop()  # high-severity lewin
    print(top)
"""

from __future__ import annotations

from ._queue import (
    FindingPriorityQueue,
    QueueEntry,
)

__all__ = [
    "FindingPriorityQueue",
    "QueueEntry",
]
