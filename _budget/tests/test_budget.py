"""Tests for the Budget primitive."""

from __future__ import annotations

import pytest

from vstack.budget import Budget, BudgetExceeded


class TestBudgetValidation:
    def test_requires_at_least_one_limit(self):
        with pytest.raises(ValueError):
            Budget()

    def test_cost_per_hour_alone_is_valid(self):
        b = Budget(max_cost_usd_per_hour=10.0)
        assert b.has_any_limit()

    def test_calls_per_minute_alone_is_valid(self):
        b = Budget(max_calls_per_minute=60)
        assert b.has_any_limit()

    def test_tokens_per_day_alone_is_valid(self):
        b = Budget(max_tokens_per_day=1_000_000)
        assert b.has_any_limit()


class TestCostLimits:
    def test_cost_within_limit_passes(self):
        b = Budget(max_cost_usd_per_hour=10.0)
        b.check(projected_cost_usd=5.0)  # should not raise

    def test_cost_at_limit_passes(self):
        b = Budget(max_cost_usd_per_hour=10.0)
        b.check(projected_cost_usd=10.0)  # exactly at limit

    def test_cost_over_limit_raises(self):
        b = Budget(max_cost_usd_per_hour=10.0)
        with pytest.raises(BudgetExceeded) as exc:
            b.check(projected_cost_usd=10.01)
        assert exc.value.kind == "cost_usd"
        assert exc.value.window == "hour"

    def test_accumulated_cost_over_limit_raises(self):
        b = Budget(max_cost_usd_per_hour=10.0)
        b.record(cost_usd=5.0)
        b.record(cost_usd=4.0)
        # Already at $9 of $10 budget.
        with pytest.raises(BudgetExceeded):
            b.check(projected_cost_usd=2.0)  # would push to $11

    def test_per_minute_separate_from_per_hour(self):
        b = Budget(
            max_cost_usd_per_minute=1.0,
            max_cost_usd_per_hour=10.0,
        )
        # Within minute limit.
        b.check(projected_cost_usd=0.5)

        # Exceeds minute limit even though hour is fine.
        with pytest.raises(BudgetExceeded) as exc:
            b.check(projected_cost_usd=1.1)
        assert exc.value.window == "minute"


class TestCallLimits:
    def test_calls_within_limit_passes(self):
        b = Budget(max_calls_per_minute=10)
        for _ in range(9):
            b.check()
            b.record()

    def test_calls_at_limit_passes(self):
        b = Budget(max_calls_per_minute=10)
        for _ in range(10):
            b.check()
            b.record()

    def test_calls_over_limit_raises(self):
        b = Budget(max_calls_per_minute=10)
        for _ in range(10):
            b.check()
            b.record()
        with pytest.raises(BudgetExceeded) as exc:
            b.check()
        assert exc.value.kind == "calls"


class TestTokenLimits:
    def test_tokens_within_limit_passes(self):
        b = Budget(max_tokens_per_minute=1000)
        b.check(projected_tokens=500)

    def test_tokens_over_limit_raises(self):
        b = Budget(max_tokens_per_minute=1000)
        with pytest.raises(BudgetExceeded) as exc:
            b.check(projected_tokens=1001)
        assert exc.value.kind == "tokens"


class TestRollingWindow:
    def test_old_events_evicted(self):
        b = Budget(max_cost_usd_per_minute=1.0)
        # Record events at t=0.
        b.record(cost_usd=0.5, now=0.0)
        b.record(cost_usd=0.4, now=0.0)
        # At t=0, $0.9 of $1 used.
        b.check(projected_cost_usd=0.1, now=0.0)

        # At t=100 (past the minute window), old events are evicted.
        b.check(projected_cost_usd=0.9, now=100.0)

    def test_recent_events_retained(self):
        b = Budget(max_cost_usd_per_minute=1.0)
        b.record(cost_usd=0.5, now=0.0)
        b.record(cost_usd=0.4, now=30.0)
        # At t=30, both events still in window.
        with pytest.raises(BudgetExceeded):
            b.check(projected_cost_usd=0.2, now=30.0)


class TestBudgetReport:
    def test_empty_report(self):
        b = Budget(max_cost_usd_per_hour=10.0)
        report = b.report(now=0.0)
        assert report.cost_per_hour == 0.0
        assert report.max_cost_usd_per_hour == 10.0

    def test_report_after_recording(self):
        b = Budget(max_cost_usd_per_hour=10.0)
        b.record(cost_usd=3.0, tokens=500, now=0.0)
        report = b.report(now=0.0)
        assert report.cost_per_hour == 3.0
        assert report.calls_per_hour == 1
        assert report.tokens_per_hour == 500

    def test_report_utilization(self):
        b = Budget(max_cost_usd_per_hour=10.0)
        b.record(cost_usd=5.0, now=0.0)
        report = b.report(now=0.0)
        util = report.utilization()
        assert util["cost_per_hour"] == 0.5

    def test_report_no_limit_returns_none(self):
        b = Budget(max_cost_usd_per_hour=10.0)
        report = b.report()
        util = report.utilization()
        # No minute limit set.
        assert util["cost_per_minute"] is None

    def test_over_threshold(self):
        b = Budget(max_cost_usd_per_hour=10.0)
        b.record(cost_usd=9.5, now=0.0)
        report = b.report(now=0.0)
        assert report.is_over_threshold(0.9)
        assert not report.is_over_threshold(0.99)

    def test_to_dict(self):
        b = Budget(max_cost_usd_per_hour=10.0)
        b.record(cost_usd=3.0, now=0.0)
        data = b.report(now=0.0).to_dict()
        assert "current" in data
        assert "limits" in data
        assert "utilization" in data
        assert data["current"]["cost_per_hour"] == 3.0


class TestMultipleLimits:
    def test_first_violation_wins(self):
        b = Budget(
            max_cost_usd_per_minute=1.0,
            max_calls_per_minute=10,
            max_tokens_per_minute=100,
        )
        # Exceed cost first.
        with pytest.raises(BudgetExceeded) as exc:
            b.check(projected_cost_usd=2.0)
        assert exc.value.kind == "cost_usd"

    def test_independent_dimensions(self):
        b = Budget(
            max_cost_usd_per_hour=10.0,
            max_calls_per_hour=100,
        )
        # Use up cost without hitting call limit.
        for _ in range(5):
            b.record(cost_usd=1.0)
        # Within call limit but close on cost.
        b.check(projected_cost_usd=4.0)
        with pytest.raises(BudgetExceeded) as exc:
            b.check(projected_cost_usd=6.0)
        assert exc.value.kind == "cost_usd"
