"""Budgeter primitives — forecast + multi-tier alerts."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Sequence


@dataclass
class BudgetForecast:
    """Forecast of budget burn."""

    current_spend_usd: float
    monthly_budget_usd: float
    elapsed_seconds: float
    projected_total_usd: float
    """Projected total at end of month at current burn rate."""

    days_until_limit: float | None
    """Days until budget hits 100%. None if zero burn rate."""

    burn_rate_usd_per_day: float

    @property
    def utilization(self) -> float:
        if self.monthly_budget_usd == 0:
            return 0.0
        return self.current_spend_usd / self.monthly_budget_usd

    @property
    def projected_overrun_usd(self) -> float:
        return max(0.0, self.projected_total_usd - self.monthly_budget_usd)

    def to_dict(self) -> dict:
        return {
            "current_spend_usd": self.current_spend_usd,
            "monthly_budget_usd": self.monthly_budget_usd,
            "elapsed_seconds": self.elapsed_seconds,
            "projected_total_usd": self.projected_total_usd,
            "days_until_limit": self.days_until_limit,
            "burn_rate_usd_per_day": self.burn_rate_usd_per_day,
            "utilization": self.utilization,
            "projected_overrun_usd": self.projected_overrun_usd,
        }


@dataclass
class BudgetAlert:
    """A triggered budget alert."""

    threshold: float  # 0.5 / 0.75 / 0.9 / 1.0
    current_utilization: float
    current_spend_usd: float
    monthly_budget_usd: float
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "threshold": self.threshold,
            "current_utilization": self.current_utilization,
            "current_spend_usd": self.current_spend_usd,
            "monthly_budget_usd": self.monthly_budget_usd,
            "message": self.message,
        }


_SECONDS_PER_DAY = 86400.0
_SECONDS_PER_MONTH = 30 * 86400.0


def forecast_burn(
    *,
    current_spend_usd: float,
    monthly_budget_usd: float,
    elapsed_seconds: float,
    month_seconds: float = _SECONDS_PER_MONTH,
) -> BudgetForecast:
    """Project monthly total spend from elapsed-seconds spend."""
    if elapsed_seconds == 0:
        burn_per_day = 0.0
        projected_total = 0.0
        days_until_limit = None
    else:
        burn_per_day = current_spend_usd / elapsed_seconds * _SECONDS_PER_DAY
        days_in_month = month_seconds / _SECONDS_PER_DAY
        projected_total = burn_per_day * days_in_month
        remaining_budget = monthly_budget_usd - current_spend_usd
        if burn_per_day > 0 and remaining_budget > 0:
            days_until_limit = remaining_budget / burn_per_day
        elif remaining_budget <= 0:
            days_until_limit = 0.0
        else:
            days_until_limit = None

    return BudgetForecast(
        current_spend_usd=current_spend_usd,
        monthly_budget_usd=monthly_budget_usd,
        elapsed_seconds=elapsed_seconds,
        projected_total_usd=projected_total,
        days_until_limit=days_until_limit,
        burn_rate_usd_per_day=burn_per_day,
    )


class Budgeter:
    """High-level budget tracking with projection + alerts."""

    def __init__(
        self,
        *,
        monthly_budget_usd: float,
        alert_thresholds: Sequence[float] = (0.5, 0.75, 0.9, 1.0),
        month_seconds: float = _SECONDS_PER_MONTH,
        started_at: float | None = None,
    ):
        self.monthly_budget_usd = monthly_budget_usd
        self.alert_thresholds = tuple(sorted(alert_thresholds))
        self.month_seconds = month_seconds
        self.started_at = started_at if started_at is not None else time.time()
        self._spend_events: list[tuple[float, float]] = []  # (ts, usd)
        self._alerts_fired: set[float] = set()

    def record_spend(self, *, usd: float, now: float | None = None) -> None:
        ts = now if now is not None else time.time()
        self._spend_events.append((ts, usd))

    def current_spend_usd(self, now: float | None = None) -> float:
        cutoff = now if now is not None else time.time()
        # Window: only count spend after started_at.
        return sum(usd for ts, usd in self._spend_events if ts >= self.started_at and ts <= cutoff)

    def elapsed_seconds(self, now: float | None = None) -> float:
        return max(0.0, (now if now is not None else time.time()) - self.started_at)

    def forecast(self, now: float | None = None) -> BudgetForecast:
        return forecast_burn(
            current_spend_usd=self.current_spend_usd(now),
            monthly_budget_usd=self.monthly_budget_usd,
            elapsed_seconds=self.elapsed_seconds(now),
            month_seconds=self.month_seconds,
        )

    def utilization(self, now: float | None = None) -> float:
        if self.monthly_budget_usd == 0:
            return 0.0
        return self.current_spend_usd(now) / self.monthly_budget_usd

    def check_alert(self, now: float | None = None) -> BudgetAlert | None:
        """Return a new alert if a new threshold has been crossed.

        Returns None if no threshold crossed or already-fired thresholds.
        """
        util = self.utilization(now)
        for threshold in self.alert_thresholds:
            if util >= threshold and threshold not in self._alerts_fired:
                self._alerts_fired.add(threshold)
                return BudgetAlert(
                    threshold=threshold,
                    current_utilization=util,
                    current_spend_usd=self.current_spend_usd(now),
                    monthly_budget_usd=self.monthly_budget_usd,
                    message=(
                        f"Budget at {util * 100:.1f}% of monthly limit "
                        f"(threshold: {threshold * 100:.0f}%)"
                    ),
                )
        return None

    def all_alerts_fired(self) -> set[float]:
        return set(self._alerts_fired)

    def reset_alerts(self) -> None:
        self._alerts_fired.clear()

    def event_count(self) -> int:
        return len(self._spend_events)
