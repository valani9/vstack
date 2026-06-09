"""Cost simulator — what-if scenarios for vstack diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PerPatternCost:
    """Per-pattern × mode cost in USD."""

    pattern: str
    quick_usd: float = 0.02
    standard_usd: float = 0.05
    forensic_usd: float = 0.50


# Default pricing table, calibrated against typical Anthropic flagship-model usage.
# Per-call cost in USD; override via Scenario(custom_pricing=...) for your provider.
_DEFAULT_PRICING: dict[str, PerPatternCost] = {
    "lewin": PerPatternCost("lewin", 0.02, 0.05, 0.55),
    "goleman_ei": PerPatternCost("goleman_ei", 0.02, 0.05, 0.50),
    "johari": PerPatternCost("johari", 0.02, 0.05, 0.45),
    "danva_emotion": PerPatternCost("danva_emotion", 0.02, 0.05, 0.35),
    "cognitive_reappraisal": PerPatternCost("cognitive_reappraisal", 0.02, 0.05, 0.35),
    "yerkes_dodson": PerPatternCost("yerkes_dodson", 0.02, 0.05, 0.55),
    "hexaco": PerPatternCost("hexaco", 0.02, 0.04, 0.40),
    "grant_strengths": PerPatternCost("grant_strengths", 0.02, 0.04, 0.40),
    "motivation_traps": PerPatternCost("motivation_traps", 0.02, 0.04, 0.40),
    "sdt_reward": PerPatternCost("sdt_reward", 0.02, 0.04, 0.40),
    "mcgregor": PerPatternCost("mcgregor", 0.02, 0.04, 0.40),
    "vroom_expectancy": PerPatternCost("vroom_expectancy", 0.02, 0.04, 0.40),
    "grpi": PerPatternCost("grpi", 0.03, 0.06, 0.55),
    "process_gain_loss": PerPatternCost("process_gain_loss", 0.03, 0.06, 0.55),
    "social_loafing": PerPatternCost("social_loafing", 0.02, 0.05, 0.40),
    "superflocks": PerPatternCost("superflocks", 0.02, 0.05, 0.40),
    "lencioni": PerPatternCost("lencioni", 0.03, 0.06, 0.55),
    "trust_triangle": PerPatternCost("trust_triangle", 0.03, 0.06, 0.55),
    "mcallister_trust": PerPatternCost("mcallister_trust", 0.02, 0.05, 0.40),
    "psych_safety": PerPatternCost("psych_safety", 0.02, 0.05, 0.45),
    "glaser_conversation": PerPatternCost("glaser_conversation", 0.02, 0.05, 0.40),
    "feedback_triggers": PerPatternCost("feedback_triggers", 0.02, 0.05, 0.55),
    "plus_delta": PerPatternCost("plus_delta", 0.02, 0.04, 0.35),
    "smart_goal": PerPatternCost("smart_goal", 0.02, 0.04, 0.35),
    "group_decision": PerPatternCost("group_decision", 0.02, 0.04, 0.35),
    "debate_pathology": PerPatternCost("debate_pathology", 0.02, 0.05, 0.55),
    "bias_stack": PerPatternCost("bias_stack", 0.02, 0.05, 0.55),
    "devils_advocate": PerPatternCost("devils_advocate", 0.02, 0.05, 0.40),
    "thomas_kilmann": PerPatternCost("thomas_kilmann", 0.02, 0.05, 0.40),
    "aar": PerPatternCost("aar", 0.02, 0.05, 0.55),
    "schein_culture": PerPatternCost("schein_culture", 0.03, 0.06, 0.55),
    "robbins_culture": PerPatternCost("robbins_culture", 0.02, 0.04, 0.40),
    "org_structure": PerPatternCost("org_structure", 0.02, 0.04, 0.40),
    "span_of_control": PerPatternCost("span_of_control", 0.02, 0.04, 0.35),
}


def baseline_pricing() -> dict[str, PerPatternCost]:
    """Return a copy of the baseline pricing table."""
    return {
        k: PerPatternCost(v.pattern, v.quick_usd, v.standard_usd, v.forensic_usd)
        for k, v in _DEFAULT_PRICING.items()
    }


@dataclass
class Scenario:
    """A what-if cost scenario."""

    name: str = "scenario"
    traces_per_day: int = 0
    sample_rate: float = 1.0
    """Fraction of traces actually diagnosed (0.0-1.0)."""

    mode: str = "standard"
    """quick / standard / forensic"""

    patterns: list[str] = field(default_factory=list)
    """Patterns to run per sampled trace."""

    custom_pricing: dict[str, PerPatternCost] | None = None

    failure_upgrade: bool = False
    """If True, failed traces (10% assumed) get re-run in forensic mode."""

    failure_rate_assumed: float = 0.10
    """Assumed rate of failures that trigger forensic upgrade."""

    def get_pricing(self) -> dict[str, PerPatternCost]:
        return self.custom_pricing or _DEFAULT_PRICING

    def cost_per_pattern(self, pattern: str, *, mode: str | None = None) -> float:
        pricing = self.get_pricing()
        mode = mode or self.mode
        entry = pricing.get(pattern)
        if entry is None:
            return 0.0
        return getattr(entry, f"{mode}_usd", entry.standard_usd)

    def cost_per_trace(self) -> float:
        """Cost per single diagnosed trace, accounting for failure upgrade."""
        base = sum(self.cost_per_pattern(p) for p in self.patterns)
        if self.failure_upgrade:
            forensic_cost = sum(self.cost_per_pattern(p, mode="forensic") for p in self.patterns)
            base += self.failure_rate_assumed * forensic_cost
        return base

    def diagnosed_per_day(self) -> int:
        return int(self.traces_per_day * self.sample_rate)


@dataclass
class SimulationResult:
    """Result of simulating a scenario."""

    scenario: Scenario
    daily_diagnosed: int
    daily_cost_usd: float
    monthly_cost_usd: float
    annual_cost_usd: float
    cost_per_pattern: dict[str, float] = field(default_factory=dict)
    cost_per_trace: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_name": self.scenario.name,
            "daily_diagnosed": self.daily_diagnosed,
            "daily_cost_usd": self.daily_cost_usd,
            "monthly_cost_usd": self.monthly_cost_usd,
            "annual_cost_usd": self.annual_cost_usd,
            "cost_per_trace": self.cost_per_trace,
            "cost_per_pattern": dict(self.cost_per_pattern),
        }


def simulate(scenario: Scenario) -> SimulationResult:
    """Run the scenario; return the cost projection."""
    diagnosed = scenario.diagnosed_per_day()
    per_trace = scenario.cost_per_trace()

    daily = diagnosed * per_trace
    monthly = daily * 30
    annual = daily * 365

    per_pattern: dict[str, float] = {}
    for p in scenario.patterns:
        per_pattern[p] = diagnosed * scenario.cost_per_pattern(p)
        if scenario.failure_upgrade:
            per_pattern[p] += (
                diagnosed
                * scenario.failure_rate_assumed
                * scenario.cost_per_pattern(p, mode="forensic")
            )

    return SimulationResult(
        scenario=scenario,
        daily_diagnosed=diagnosed,
        daily_cost_usd=daily,
        monthly_cost_usd=monthly,
        annual_cost_usd=annual,
        cost_per_pattern=per_pattern,
        cost_per_trace=per_trace,
    )


@dataclass
class ScenarioComparison:
    """Compare multiple scenarios."""

    results: list[SimulationResult] = field(default_factory=list)

    @property
    def cheapest(self) -> SimulationResult | None:
        if not self.results:
            return None
        return min(self.results, key=lambda r: r.daily_cost_usd)

    @property
    def most_expensive(self) -> SimulationResult | None:
        if not self.results:
            return None
        return max(self.results, key=lambda r: r.daily_cost_usd)

    def to_dict(self) -> dict[str, Any]:
        return {"results": [r.to_dict() for r in self.results]}

    def to_markdown(self) -> str:
        lines = ["# Scenario Comparison", ""]
        if not self.results:
            lines.append("_No scenarios._")
            return "\n".join(lines)

        lines.append("| Scenario | Diagnosed/day | $/trace | $/day | $/month | $/year |")
        lines.append("|----------|---------------:|--------:|------:|--------:|-------:|")
        for r in self.results:
            lines.append(
                f"| {r.scenario.name} | {r.daily_diagnosed:,} | "
                f"${r.cost_per_trace:.4f} | ${r.daily_cost_usd:,.2f} | "
                f"${r.monthly_cost_usd:,.0f} | ${r.annual_cost_usd:,.0f} |"
            )

        cheapest = self.cheapest
        most_exp = self.most_expensive
        if cheapest and most_exp and cheapest is not most_exp:
            ratio = most_exp.daily_cost_usd / max(cheapest.daily_cost_usd, 0.0001)
            lines.append("")
            lines.append(
                f"_Cheapest: **{cheapest.scenario.name}** "
                f"(${cheapest.daily_cost_usd:.2f}/day). "
                f"Most expensive: **{most_exp.scenario.name}** "
                f"(${most_exp.daily_cost_usd:.2f}/day, {ratio:.1f}× cheapest)._"
            )
        return "\n".join(lines)


def compare_scenarios(scenarios: list[Scenario]) -> ScenarioComparison:
    """Simulate each scenario; return a comparison."""
    results = [simulate(s) for s in scenarios]
    return ScenarioComparison(results=results)
