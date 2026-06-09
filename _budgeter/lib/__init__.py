"""vstack.budgeter — cost projection + budget alerts.

A higher-level companion to ``vstack.budget`` that adds:

  - **Cost projection** based on historical run rate.
  - **Multi-tier alerting** at configurable thresholds (50/75/90%).
  - **Forecast** — given current burn, estimate when budget hits limit.
  - **Monthly rollup** — aggregate spend across many `Budget`s.

Quick start
-----------

    from vstack.budgeter import (
        Budgeter,
        BudgetForecast,
        forecast_burn,
    )

    budgeter = Budgeter(monthly_budget_usd=1000.0)

    # Record spend over time:
    budgeter.record_spend(usd=12.50)
    budgeter.record_spend(usd=8.30)
    # ...

    forecast = budgeter.forecast()
    print(f"Projected month total: ${forecast.projected_total_usd:.2f}")
    print(f"Days until budget hit: {forecast.days_until_limit}")

    # Multi-tier alert check:
    alert = budgeter.check_alert()
    if alert:
        print(f"Budget alert: {alert.threshold * 100:.0f}% reached")
"""

from __future__ import annotations

from ._budgeter import (
    BudgetAlert,
    BudgetForecast,
    Budgeter,
    forecast_burn,
)

__all__ = [
    "BudgetAlert",
    "BudgetForecast",
    "Budgeter",
    "forecast_burn",
]
