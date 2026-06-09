"""vstack.cost_sim — what-if cost scenarios for budget planning.

The cost_sim module projects vstack production cost under different
configurations:

  - Per-pattern cost × pattern count.
  - Per-mode cost (quick / standard / forensic).
  - Per-trace sampling rate.
  - Multiple scenarios compared side-by-side.

Quick start
-----------

    from vstack.cost_sim import (
        Scenario,
        simulate,
        compare_scenarios,
        baseline_pricing,
    )

    scenario = Scenario(
        traces_per_day=10000,
        sample_rate=0.10,
        mode="standard",
        patterns=["lewin", "yerkes_dodson", "aar"],
    )

    result = simulate(scenario)
    print(f"Daily cost: ${result.daily_cost_usd:.2f}")
    print(f"Monthly cost: ${result.monthly_cost_usd:.2f}")

    # Compare scenarios:
    quick = Scenario(traces_per_day=10000, sample_rate=1.0, mode="quick",
                     patterns=["lewin"])
    forensic = Scenario(traces_per_day=10000, sample_rate=0.10, mode="forensic",
                        patterns=["lewin", "aar"])
    comparison = compare_scenarios([quick, forensic])
    print(comparison.to_markdown())
"""

from __future__ import annotations

from ._cost_sim import (
    PerPatternCost,
    Scenario,
    ScenarioComparison,
    SimulationResult,
    baseline_pricing,
    compare_scenarios,
    simulate,
)

__all__ = [
    "PerPatternCost",
    "Scenario",
    "ScenarioComparison",
    "SimulationResult",
    "baseline_pricing",
    "compare_scenarios",
    "simulate",
]
