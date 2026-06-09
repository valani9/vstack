"""vstack.budget — token-bucket cost-budget enforcement for vstack.

The budget module provides:

  - **Budget**: a configurable cost/token/call limit per time window.
  - **BudgetEnforcer**: middleware that gates LLM calls against the
    budget; raises ``BudgetExceeded`` when over the limit.
  - **BudgetReport**: utilization snapshot for dashboards.

Use cases
---------

* **Cost ceiling** — hard-limit hourly cost on a production fleet.
* **Per-client quotas** — each API client gets its own budget.
* **Per-pattern caps** — bound cost per pattern to prevent runaway.

Quick start
-----------

    from vstack.budget import Budget, BudgetEnforcer

    budget = Budget(
        max_cost_usd_per_hour=10.0,
        max_calls_per_minute=60,
    )

    enforcer = BudgetEnforcer(budget=budget)

    # Wrap your LLM client:
    from vstack.aar.clients import AnthropicClient
    raw_client = AnthropicClient()
    client = enforcer.wrap(raw_client)

    # Use as any client:
    from vstack.lewin import LewinAttributionDetector
    detector = LewinAttributionDetector(client)
    detection = detector.run(trace)
    # ^ raises BudgetExceeded if the budget would be busted.

Per-client budgets
------------------

    from vstack.budget import BudgetRegistry

    registry = BudgetRegistry()
    registry.register("client-a", Budget(max_cost_usd_per_hour=10.0))
    registry.register("client-b", Budget(max_cost_usd_per_hour=2.0))

    # Wrap calls with the client ID:
    with registry.context("client-a"):
        detector.run(trace)  # uses client-a's budget
"""

from __future__ import annotations

from ._budget import (
    Budget,
    BudgetExceeded,
    BudgetReport,
    BudgetWindow,
)
from ._enforcer import (
    BudgetEnforcer,
    BudgetRegistry,
)

__all__ = [
    "Budget",
    "BudgetEnforcer",
    "BudgetExceeded",
    "BudgetRegistry",
    "BudgetReport",
    "BudgetWindow",
]
