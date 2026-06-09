"""Tests for the cost simulator."""

from __future__ import annotations


from vstack.cost_sim import (
    PerPatternCost,
    Scenario,
    baseline_pricing,
    compare_scenarios,
    simulate,
)


class TestBaselinePricing:
    def test_returns_dict(self):
        pricing = baseline_pricing()
        assert isinstance(pricing, dict)
        assert "lewin" in pricing

    def test_per_pattern_cost_fields(self):
        pricing = baseline_pricing()
        lewin = pricing["lewin"]
        assert lewin.pattern == "lewin"
        assert lewin.quick_usd > 0
        assert lewin.standard_usd > lewin.quick_usd
        assert lewin.forensic_usd > lewin.standard_usd

    def test_baseline_is_copy(self):
        pricing = baseline_pricing()
        pricing["lewin"].quick_usd = 999.0
        pricing2 = baseline_pricing()
        # Should not be polluted.
        assert pricing2["lewin"].quick_usd < 1.0


class TestScenario:
    def test_default_scenario(self):
        s = Scenario()
        assert s.traces_per_day == 0
        assert s.sample_rate == 1.0
        assert s.mode == "standard"
        assert s.patterns == []

    def test_diagnosed_per_day(self):
        s = Scenario(traces_per_day=10000, sample_rate=0.1)
        assert s.diagnosed_per_day() == 1000

    def test_cost_per_pattern_uses_mode(self):
        s = Scenario(mode="quick", patterns=["lewin"])
        cost = s.cost_per_pattern("lewin")
        assert cost == 0.02  # quick price

        s2 = Scenario(mode="forensic", patterns=["lewin"])
        cost2 = s2.cost_per_pattern("lewin")
        assert cost2 == 0.55

    def test_cost_per_pattern_unknown(self):
        s = Scenario(patterns=["nonexistent"])
        cost = s.cost_per_pattern("nonexistent")
        assert cost == 0.0

    def test_cost_per_trace_sums_patterns(self):
        s = Scenario(mode="quick", patterns=["lewin", "aar"])
        # lewin quick=0.02, aar quick=0.02 → 0.04.
        assert s.cost_per_trace() == 0.04

    def test_failure_upgrade_adds_forensic_cost(self):
        s = Scenario(
            mode="standard",
            patterns=["lewin"],
            failure_upgrade=True,
            failure_rate_assumed=0.10,
        )
        # standard=0.05 + 0.10 × forensic(0.55) = 0.05 + 0.055 = 0.105.
        assert abs(s.cost_per_trace() - 0.105) < 0.001

    def test_custom_pricing_overrides_baseline(self):
        custom = {"lewin": PerPatternCost("lewin", 1.0, 2.0, 5.0)}
        s = Scenario(mode="quick", patterns=["lewin"], custom_pricing=custom)
        assert s.cost_per_pattern("lewin") == 1.0


class TestSimulate:
    def test_basic_simulation(self):
        s = Scenario(
            name="test",
            traces_per_day=10000,
            sample_rate=0.1,
            mode="standard",
            patterns=["lewin"],
        )
        result = simulate(s)
        # 1000 diagnosed × 0.05 = $50/day.
        assert result.daily_diagnosed == 1000
        assert abs(result.daily_cost_usd - 50.0) < 0.01

    def test_monthly_30x_daily(self):
        s = Scenario(
            traces_per_day=100,
            sample_rate=1.0,
            mode="standard",
            patterns=["lewin"],
        )
        result = simulate(s)
        assert result.monthly_cost_usd == result.daily_cost_usd * 30

    def test_annual_365x_daily(self):
        s = Scenario(
            traces_per_day=100,
            sample_rate=1.0,
            mode="standard",
            patterns=["lewin"],
        )
        result = simulate(s)
        assert result.annual_cost_usd == result.daily_cost_usd * 365

    def test_multi_pattern(self):
        s = Scenario(
            traces_per_day=1000,
            sample_rate=1.0,
            mode="quick",
            patterns=["lewin", "aar", "yerkes_dodson"],
        )
        result = simulate(s)
        # 3 patterns × $0.02 = $0.06/trace × 1000 = $60/day.
        assert result.daily_diagnosed == 1000
        assert abs(result.daily_cost_usd - 60.0) < 0.01

    def test_per_pattern_breakdown(self):
        s = Scenario(
            traces_per_day=1000,
            sample_rate=1.0,
            mode="quick",
            patterns=["lewin", "aar"],
        )
        result = simulate(s)
        assert "lewin" in result.cost_per_pattern
        assert "aar" in result.cost_per_pattern
        # Each $0.02 × 1000 = $20.
        assert abs(result.cost_per_pattern["lewin"] - 20.0) < 0.01

    def test_failure_upgrade(self):
        s = Scenario(
            traces_per_day=1000,
            sample_rate=1.0,
            mode="quick",
            patterns=["lewin"],
            failure_upgrade=True,
            failure_rate_assumed=0.10,
        )
        result = simulate(s)
        # base $0.02 + 0.10 × forensic(0.55) = $0.075 × 1000 = $75/day.
        assert abs(result.daily_cost_usd - 75.0) < 0.01

    def test_zero_diagnosis_zero_cost(self):
        s = Scenario(traces_per_day=0)
        result = simulate(s)
        assert result.daily_cost_usd == 0.0


class TestSimulationResultSerialization:
    def test_to_dict(self):
        s = Scenario(traces_per_day=100, sample_rate=1.0, patterns=["lewin"])
        result = simulate(s)
        data = result.to_dict()
        assert "daily_cost_usd" in data
        assert "monthly_cost_usd" in data


class TestCompareScenarios:
    def test_empty_comparison(self):
        comp = compare_scenarios([])
        assert comp.cheapest is None
        assert comp.most_expensive is None

    def test_single_scenario(self):
        s = Scenario(traces_per_day=100, sample_rate=1.0, patterns=["lewin"])
        comp = compare_scenarios([s])
        assert comp.cheapest is comp.most_expensive

    def test_multiple_scenarios(self):
        s1 = Scenario(
            name="quick",
            traces_per_day=1000,
            sample_rate=1.0,
            mode="quick",
            patterns=["lewin"],
        )
        s2 = Scenario(
            name="forensic",
            traces_per_day=1000,
            sample_rate=1.0,
            mode="forensic",
            patterns=["lewin"],
        )
        comp = compare_scenarios([s1, s2])
        assert comp.cheapest.scenario.name == "quick"
        assert comp.most_expensive.scenario.name == "forensic"

    def test_to_markdown(self):
        s = Scenario(name="test", traces_per_day=1000, sample_rate=1.0, patterns=["lewin"])
        comp = compare_scenarios([s])
        md = comp.to_markdown()
        assert "Scenario Comparison" in md
        assert "test" in md

    def test_to_dict(self):
        s = Scenario(traces_per_day=1000, sample_rate=1.0, patterns=["lewin"])
        comp = compare_scenarios([s])
        data = comp.to_dict()
        assert "results" in data
        assert len(data["results"]) == 1
