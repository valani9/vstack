"""Tests for the budgeter module."""

from __future__ import annotations


from vstack.budgeter import (
    BudgetAlert,
    Budgeter,
    forecast_burn,
)


class TestForecastBurn:
    def test_zero_elapsed(self):
        f = forecast_burn(
            current_spend_usd=0.0,
            monthly_budget_usd=100.0,
            elapsed_seconds=0,
        )
        assert f.projected_total_usd == 0.0
        assert f.days_until_limit is None

    def test_simple_burn_rate(self):
        # $10 in 1 day → $300 in 30 days.
        f = forecast_burn(
            current_spend_usd=10.0,
            monthly_budget_usd=100.0,
            elapsed_seconds=86400,
        )
        assert f.burn_rate_usd_per_day == 10.0
        assert f.projected_total_usd == 300.0
        # $90 remaining at $10/day = 9 days.
        assert f.days_until_limit == 9.0

    def test_projected_overrun(self):
        f = forecast_burn(
            current_spend_usd=50.0,
            monthly_budget_usd=100.0,
            elapsed_seconds=86400 * 10,  # 10 days
        )
        # $50 in 10 days = $5/day → $150 in 30 days.
        assert f.projected_total_usd == 150.0
        assert f.projected_overrun_usd == 50.0

    def test_utilization(self):
        f = forecast_burn(
            current_spend_usd=25.0,
            monthly_budget_usd=100.0,
            elapsed_seconds=86400,
        )
        assert f.utilization == 0.25

    def test_to_dict(self):
        f = forecast_burn(
            current_spend_usd=10.0,
            monthly_budget_usd=100.0,
            elapsed_seconds=86400,
        )
        data = f.to_dict()
        assert "current_spend_usd" in data
        assert "projected_total_usd" in data


class TestBudgeter:
    def test_record_spend(self):
        b = Budgeter(monthly_budget_usd=100.0, started_at=0.0)
        b.record_spend(usd=10.0, now=100.0)
        b.record_spend(usd=5.0, now=200.0)
        assert b.current_spend_usd(now=300.0) == 15.0
        assert b.event_count() == 2

    def test_elapsed_seconds(self):
        b = Budgeter(monthly_budget_usd=100.0, started_at=100.0)
        assert b.elapsed_seconds(now=200.0) == 100.0

    def test_utilization(self):
        b = Budgeter(monthly_budget_usd=100.0, started_at=0.0)
        b.record_spend(usd=25.0, now=86400)
        assert b.utilization(now=86400) == 0.25

    def test_zero_budget_utilization(self):
        b = Budgeter(monthly_budget_usd=0.0, started_at=0.0)
        assert b.utilization(now=86400) == 0.0


class TestAlerts:
    def test_no_alert_below_threshold(self):
        b = Budgeter(monthly_budget_usd=100.0, started_at=0.0)
        b.record_spend(usd=10.0, now=86400)
        alert = b.check_alert(now=86400)
        assert alert is None

    def test_50_pct_alert(self):
        b = Budgeter(monthly_budget_usd=100.0, started_at=0.0)
        b.record_spend(usd=55.0, now=86400)
        alert = b.check_alert(now=86400)
        assert alert is not None
        assert alert.threshold == 0.5

    def test_alert_not_re_fired(self):
        b = Budgeter(monthly_budget_usd=100.0, started_at=0.0)
        b.record_spend(usd=55.0, now=86400)
        first = b.check_alert(now=86400)
        second = b.check_alert(now=86400)
        assert first is not None
        assert second is None  # already fired.

    def test_higher_threshold_fires_after_lower(self):
        b = Budgeter(monthly_budget_usd=100.0, started_at=0.0)
        b.record_spend(usd=55.0, now=86400)
        a1 = b.check_alert(now=86400)
        b.record_spend(usd=25.0, now=2 * 86400)
        a2 = b.check_alert(now=2 * 86400)
        assert a1.threshold == 0.5
        assert a2.threshold == 0.75

    def test_all_thresholds_fired(self):
        b = Budgeter(monthly_budget_usd=100.0, started_at=0.0)
        b.record_spend(usd=120.0, now=86400)
        # Should fire all thresholds in order.
        alerts = []
        while True:
            alert = b.check_alert(now=86400)
            if alert is None:
                break
            alerts.append(alert)
        assert len(alerts) == 4  # 0.5, 0.75, 0.9, 1.0

    def test_reset_alerts(self):
        b = Budgeter(monthly_budget_usd=100.0, started_at=0.0)
        b.record_spend(usd=55.0, now=86400)
        b.check_alert(now=86400)
        b.reset_alerts()
        # Now the same threshold should fire again.
        alert = b.check_alert(now=86400)
        assert alert is not None

    def test_custom_thresholds(self):
        b = Budgeter(
            monthly_budget_usd=100.0,
            alert_thresholds=(0.25, 0.5),
            started_at=0.0,
        )
        b.record_spend(usd=30.0, now=86400)
        alert = b.check_alert(now=86400)
        assert alert.threshold == 0.25

    def test_alert_to_dict(self):
        alert = BudgetAlert(
            threshold=0.5,
            current_utilization=0.55,
            current_spend_usd=55.0,
            monthly_budget_usd=100.0,
            message="test",
        )
        data = alert.to_dict()
        assert data["threshold"] == 0.5
        assert "message" in data


class TestForecastViaBudgeter:
    def test_forecast_with_no_spend(self):
        b = Budgeter(monthly_budget_usd=100.0, started_at=0.0)
        f = b.forecast(now=86400)
        assert f.current_spend_usd == 0.0
        assert f.burn_rate_usd_per_day == 0.0

    def test_forecast_with_spend(self):
        b = Budgeter(monthly_budget_usd=100.0, started_at=0.0)
        b.record_spend(usd=10.0, now=86400)
        f = b.forecast(now=86400)
        assert f.burn_rate_usd_per_day == 10.0
