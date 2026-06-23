"""Budget primitives — Budget, BudgetWindow, BudgetReport.

These are pure data classes with no side effects. Enforcement is in
``_enforcer.py``.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Literal

# Each recorded event: (timestamp_seconds, tokens, cost_usd).
BudgetEvent = tuple[float, int, float]


class BudgetExceeded(Exception):
    """Raised when an LLM call would exceed the configured budget."""

    def __init__(
        self,
        kind: str,
        current: float,
        limit: float,
        window: str,
    ):
        self.kind = kind
        self.current = current
        self.limit = limit
        self.window = window
        super().__init__(f"Budget exceeded for {kind}: {current:.2f} / {limit:.2f} per {window}.")


WindowKind = Literal["minute", "hour", "day"]
_WINDOW_SECONDS = {
    "minute": 60,
    "hour": 3600,
    "day": 86400,
}


@dataclass
class BudgetWindow:
    """A rolling window tracking calls/tokens/cost over a time period."""

    kind: WindowKind
    """``minute`` / ``hour`` / ``day``."""

    events: deque[BudgetEvent] = field(default_factory=deque)
    """Each event: (timestamp_seconds, tokens, cost_usd)."""

    @property
    def window_seconds(self) -> int:
        return _WINDOW_SECONDS[self.kind]

    def _evict_old(self, now: float | None = None) -> None:
        now = now if now is not None else time.time()
        cutoff = now - self.window_seconds
        while self.events and self.events[0][0] < cutoff:
            self.events.popleft()

    def record(
        self,
        *,
        tokens: int = 0,
        cost_usd: float = 0.0,
        now: float | None = None,
    ) -> None:
        ts = now if now is not None else time.time()
        self.events.append((ts, tokens, cost_usd))

    def current_calls(self, now: float | None = None) -> int:
        self._evict_old(now)
        return len(self.events)

    def current_tokens(self, now: float | None = None) -> int:
        self._evict_old(now)
        return sum(e[1] for e in self.events)

    def current_cost_usd(self, now: float | None = None) -> float:
        self._evict_old(now)
        return sum(e[2] for e in self.events)


@dataclass
class Budget:
    """Budget configuration.

    All limits are optional; an unset limit means no cap on that
    dimension. At least one limit must be set or the budget is
    effectively no-op.
    """

    max_cost_usd_per_minute: float | None = None
    max_cost_usd_per_hour: float | None = None
    max_cost_usd_per_day: float | None = None

    max_calls_per_minute: int | None = None
    max_calls_per_hour: int | None = None
    max_calls_per_day: int | None = None

    max_tokens_per_minute: int | None = None
    max_tokens_per_hour: int | None = None
    max_tokens_per_day: int | None = None

    # Internal: rolling windows for each enforced limit.
    _minute_window: BudgetWindow = field(
        default_factory=lambda: BudgetWindow(kind="minute"),
        init=False,
        repr=False,
    )
    _hour_window: BudgetWindow = field(
        default_factory=lambda: BudgetWindow(kind="hour"),
        init=False,
        repr=False,
    )
    _day_window: BudgetWindow = field(
        default_factory=lambda: BudgetWindow(kind="day"),
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        if not self.has_any_limit():
            raise ValueError(
                "Budget requires at least one limit set "
                "(max_cost_usd_per_*, max_calls_per_*, or max_tokens_per_*)."
            )

    def has_any_limit(self) -> bool:
        return any(
            limit is not None
            for limit in (
                self.max_cost_usd_per_minute,
                self.max_cost_usd_per_hour,
                self.max_cost_usd_per_day,
                self.max_calls_per_minute,
                self.max_calls_per_hour,
                self.max_calls_per_day,
                self.max_tokens_per_minute,
                self.max_tokens_per_hour,
                self.max_tokens_per_day,
            )
        )

    def record(
        self,
        *,
        tokens: int = 0,
        cost_usd: float = 0.0,
        now: float | None = None,
    ) -> None:
        """Record a call against all enforced windows."""
        self._minute_window.record(tokens=tokens, cost_usd=cost_usd, now=now)
        self._hour_window.record(tokens=tokens, cost_usd=cost_usd, now=now)
        self._day_window.record(tokens=tokens, cost_usd=cost_usd, now=now)

    def check(
        self,
        *,
        projected_tokens: int = 0,
        projected_cost_usd: float = 0.0,
        now: float | None = None,
    ) -> None:
        """Check whether a projected call would exceed any limit.

        Raises ``BudgetExceeded`` on the first violation found.
        Does NOT record the call — call ``record()`` after the call
        succeeds.
        """
        # Cost limits.
        if self.max_cost_usd_per_minute is not None:
            current = self._minute_window.current_cost_usd(now)
            if current + projected_cost_usd > self.max_cost_usd_per_minute:
                raise BudgetExceeded(
                    kind="cost_usd",
                    current=current + projected_cost_usd,
                    limit=self.max_cost_usd_per_minute,
                    window="minute",
                )
        if self.max_cost_usd_per_hour is not None:
            current = self._hour_window.current_cost_usd(now)
            if current + projected_cost_usd > self.max_cost_usd_per_hour:
                raise BudgetExceeded(
                    kind="cost_usd",
                    current=current + projected_cost_usd,
                    limit=self.max_cost_usd_per_hour,
                    window="hour",
                )
        if self.max_cost_usd_per_day is not None:
            current = self._day_window.current_cost_usd(now)
            if current + projected_cost_usd > self.max_cost_usd_per_day:
                raise BudgetExceeded(
                    kind="cost_usd",
                    current=current + projected_cost_usd,
                    limit=self.max_cost_usd_per_day,
                    window="day",
                )

        # Call limits.
        if self.max_calls_per_minute is not None:
            current_calls = self._minute_window.current_calls(now)
            if current_calls + 1 > self.max_calls_per_minute:
                raise BudgetExceeded(
                    kind="calls",
                    current=current_calls + 1,
                    limit=self.max_calls_per_minute,
                    window="minute",
                )
        if self.max_calls_per_hour is not None:
            current_calls = self._hour_window.current_calls(now)
            if current_calls + 1 > self.max_calls_per_hour:
                raise BudgetExceeded(
                    kind="calls",
                    current=current_calls + 1,
                    limit=self.max_calls_per_hour,
                    window="hour",
                )
        if self.max_calls_per_day is not None:
            current_calls = self._day_window.current_calls(now)
            if current_calls + 1 > self.max_calls_per_day:
                raise BudgetExceeded(
                    kind="calls",
                    current=current_calls + 1,
                    limit=self.max_calls_per_day,
                    window="day",
                )

        # Token limits.
        if self.max_tokens_per_minute is not None:
            current = self._minute_window.current_tokens(now)
            if current + projected_tokens > self.max_tokens_per_minute:
                raise BudgetExceeded(
                    kind="tokens",
                    current=current + projected_tokens,
                    limit=self.max_tokens_per_minute,
                    window="minute",
                )
        if self.max_tokens_per_hour is not None:
            current = self._hour_window.current_tokens(now)
            if current + projected_tokens > self.max_tokens_per_hour:
                raise BudgetExceeded(
                    kind="tokens",
                    current=current + projected_tokens,
                    limit=self.max_tokens_per_hour,
                    window="hour",
                )
        if self.max_tokens_per_day is not None:
            current = self._day_window.current_tokens(now)
            if current + projected_tokens > self.max_tokens_per_day:
                raise BudgetExceeded(
                    kind="tokens",
                    current=current + projected_tokens,
                    limit=self.max_tokens_per_day,
                    window="day",
                )

    def report(self, now: float | None = None) -> BudgetReport:
        """Snapshot the current budget utilization."""
        return BudgetReport(
            cost_per_minute=self._minute_window.current_cost_usd(now),
            cost_per_hour=self._hour_window.current_cost_usd(now),
            cost_per_day=self._day_window.current_cost_usd(now),
            calls_per_minute=self._minute_window.current_calls(now),
            calls_per_hour=self._hour_window.current_calls(now),
            calls_per_day=self._day_window.current_calls(now),
            tokens_per_minute=self._minute_window.current_tokens(now),
            tokens_per_hour=self._hour_window.current_tokens(now),
            tokens_per_day=self._day_window.current_tokens(now),
            max_cost_usd_per_minute=self.max_cost_usd_per_minute,
            max_cost_usd_per_hour=self.max_cost_usd_per_hour,
            max_cost_usd_per_day=self.max_cost_usd_per_day,
            max_calls_per_minute=self.max_calls_per_minute,
            max_calls_per_hour=self.max_calls_per_hour,
            max_calls_per_day=self.max_calls_per_day,
            max_tokens_per_minute=self.max_tokens_per_minute,
            max_tokens_per_hour=self.max_tokens_per_hour,
            max_tokens_per_day=self.max_tokens_per_day,
        )


@dataclass
class BudgetReport:
    """Snapshot of budget utilization at a moment in time.

    For each (cost / calls / tokens) × (minute / hour / day):
      - current value
      - configured limit (or None)
      - utilization fraction (current / limit)
    """

    cost_per_minute: float = 0.0
    cost_per_hour: float = 0.0
    cost_per_day: float = 0.0
    calls_per_minute: int = 0
    calls_per_hour: int = 0
    calls_per_day: int = 0
    tokens_per_minute: int = 0
    tokens_per_hour: int = 0
    tokens_per_day: int = 0

    max_cost_usd_per_minute: float | None = None
    max_cost_usd_per_hour: float | None = None
    max_cost_usd_per_day: float | None = None
    max_calls_per_minute: int | None = None
    max_calls_per_hour: int | None = None
    max_calls_per_day: int | None = None
    max_tokens_per_minute: int | None = None
    max_tokens_per_hour: int | None = None
    max_tokens_per_day: int | None = None

    def _utilization(self, current: float, limit: float | None) -> float | None:
        if limit is None or limit == 0:
            return None
        return current / limit

    def utilization(self) -> dict[str, float | None]:
        return {
            "cost_per_minute": self._utilization(
                self.cost_per_minute, self.max_cost_usd_per_minute
            ),
            "cost_per_hour": self._utilization(self.cost_per_hour, self.max_cost_usd_per_hour),
            "cost_per_day": self._utilization(self.cost_per_day, self.max_cost_usd_per_day),
            "calls_per_minute": self._utilization(self.calls_per_minute, self.max_calls_per_minute),
            "calls_per_hour": self._utilization(self.calls_per_hour, self.max_calls_per_hour),
            "calls_per_day": self._utilization(self.calls_per_day, self.max_calls_per_day),
            "tokens_per_minute": self._utilization(
                self.tokens_per_minute, self.max_tokens_per_minute
            ),
            "tokens_per_hour": self._utilization(self.tokens_per_hour, self.max_tokens_per_hour),
            "tokens_per_day": self._utilization(self.tokens_per_day, self.max_tokens_per_day),
        }

    def is_over_threshold(self, threshold: float = 0.9) -> bool:
        """True if any utilization exceeds the threshold (e.g. 0.9 = 90%)."""
        return any((u is not None and u >= threshold) for u in self.utilization().values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "current": {
                "cost_per_minute": self.cost_per_minute,
                "cost_per_hour": self.cost_per_hour,
                "cost_per_day": self.cost_per_day,
                "calls_per_minute": self.calls_per_minute,
                "calls_per_hour": self.calls_per_hour,
                "calls_per_day": self.calls_per_day,
                "tokens_per_minute": self.tokens_per_minute,
                "tokens_per_hour": self.tokens_per_hour,
                "tokens_per_day": self.tokens_per_day,
            },
            "limits": {
                "cost_per_minute": self.max_cost_usd_per_minute,
                "cost_per_hour": self.max_cost_usd_per_hour,
                "cost_per_day": self.max_cost_usd_per_day,
                "calls_per_minute": self.max_calls_per_minute,
                "calls_per_hour": self.max_calls_per_hour,
                "calls_per_day": self.max_calls_per_day,
                "tokens_per_minute": self.max_tokens_per_minute,
                "tokens_per_hour": self.max_tokens_per_hour,
                "tokens_per_day": self.max_tokens_per_day,
            },
            "utilization": self.utilization(),
            "over_threshold_90": self.is_over_threshold(0.9),
        }
