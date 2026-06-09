"""Tests for the BudgetEnforcer + BudgetRegistry."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from vstack.budget import (
    Budget,
    BudgetEnforcer,
    BudgetExceeded,
    BudgetRegistry,
)


@dataclass
class FakeChatResult:
    """A minimal LLM result for testing."""

    content: str = "response"
    tokens_in: int = 100
    tokens_out: int = 50
    cost_usd: float = 0.10
    model: str = "fake-model"


class FakeClient:
    """Minimal client that returns a fake result."""

    def __init__(self, result: FakeChatResult | None = None):
        self.result = result or FakeChatResult()
        self.calls = 0

    def chat(self, messages, **kwargs):
        self.calls += 1
        return self.result


class TestBudgetEnforcerWrap:
    def test_wrap_returns_callable(self):
        client = FakeClient()
        enforcer = BudgetEnforcer(Budget(max_cost_usd_per_hour=10.0))
        wrapped = enforcer.wrap(client)
        assert hasattr(wrapped, "chat")

    def test_chat_passes_through_within_budget(self):
        client = FakeClient(FakeChatResult(cost_usd=0.10))
        enforcer = BudgetEnforcer(Budget(max_cost_usd_per_hour=10.0))
        wrapped = enforcer.wrap(client)
        result = wrapped.chat([{"role": "user", "content": "hi"}])
        assert result.cost_usd == 0.10
        assert client.calls == 1

    def test_chat_raises_when_projected_over(self):
        client = FakeClient(FakeChatResult(cost_usd=0.05))
        enforcer = BudgetEnforcer(Budget(max_cost_usd_per_hour=0.001))
        wrapped = enforcer.wrap(client)
        with pytest.raises(BudgetExceeded):
            # Default projected cost for prompt_tokens=1, max_response=4096
            # is high enough to exceed 0.001.
            wrapped.chat([{"role": "user", "content": "hi"}])
        # The wrapped client should NOT have called the real client.
        assert client.calls == 0

    def test_actual_cost_recorded(self):
        client = FakeClient(FakeChatResult(cost_usd=0.20))
        enforcer = BudgetEnforcer(Budget(max_cost_usd_per_hour=100.0))
        wrapped = enforcer.wrap(client)
        wrapped.chat([{"role": "user", "content": "hi"}])
        report = enforcer.report()
        assert report.cost_per_hour == 0.20

    def test_multiple_calls_accumulate(self):
        client = FakeClient(FakeChatResult(cost_usd=0.10))
        enforcer = BudgetEnforcer(Budget(max_cost_usd_per_hour=100.0))
        wrapped = enforcer.wrap(client)
        for _ in range(5):
            wrapped.chat([{"role": "user", "content": "hi"}])
        report = enforcer.report()
        assert report.cost_per_hour == 0.50  # 5 * 0.10

    def test_attribute_passthrough(self):
        """Non-chat attributes should forward to the wrapped client."""
        client = FakeClient()
        client.custom_attr = "test"
        enforcer = BudgetEnforcer(Budget(max_cost_usd_per_hour=10.0))
        wrapped = enforcer.wrap(client)
        assert wrapped.custom_attr == "test"


class TestProjectedCost:
    def test_default_pricing(self):
        enforcer = BudgetEnforcer(Budget(max_cost_usd_per_hour=10.0))
        cost = enforcer.projected_cost(prompt_tokens=1000, max_response_tokens=500)
        # 1000 tokens * $3/M = $0.003 + 500 * $15/M = $0.0075 → $0.0105.
        assert abs(cost - 0.0105) < 0.0001

    def test_custom_pricing(self):
        enforcer = BudgetEnforcer(Budget(max_cost_usd_per_hour=10.0))
        cost = enforcer.projected_cost(
            prompt_tokens=1000,
            max_response_tokens=500,
            cost_per_million_in=1.0,
            cost_per_million_out=1.0,
        )
        # 1000 * 1/M = 0.001 + 500 * 1/M = 0.0005 → 0.0015.
        assert abs(cost - 0.0015) < 0.0001


class TestBudgetRegistry:
    def test_register_and_get(self):
        registry = BudgetRegistry()
        b = Budget(max_cost_usd_per_hour=10.0)
        registry.register("client-a", b)
        assert registry.get("client-a") is b

    def test_get_unknown_returns_none(self):
        registry = BudgetRegistry()
        assert registry.get("unknown") is None

    def test_context_sets_active_budget(self):
        registry = BudgetRegistry()
        budget_a = Budget(max_cost_usd_per_hour=10.0)
        registry.register("client-a", budget_a)

        with registry.context("client-a"):
            assert registry.active_budget() is budget_a

    def test_context_unsets_after_exit(self):
        registry = BudgetRegistry()
        budget_a = Budget(max_cost_usd_per_hour=10.0)
        registry.register("client-a", budget_a)

        with registry.context("client-a"):
            assert registry.active_budget() is budget_a
        assert registry.active_budget() is None

    def test_nested_contexts(self):
        registry = BudgetRegistry()
        budget_a = Budget(max_cost_usd_per_hour=10.0)
        budget_b = Budget(max_cost_usd_per_hour=20.0)
        registry.register("client-a", budget_a)
        registry.register("client-b", budget_b)

        with registry.context("client-a"):
            assert registry.active_budget() is budget_a
            with registry.context("client-b"):
                assert registry.active_budget() is budget_b
            assert registry.active_budget() is budget_a

    def test_unregister(self):
        registry = BudgetRegistry()
        registry.register("client-a", Budget(max_cost_usd_per_hour=10.0))
        registry.unregister("client-a")
        assert registry.get("client-a") is None


class TestRegistryWrap:
    def test_wrap_uses_active_budget(self):
        registry = BudgetRegistry()
        registry.register("a", Budget(max_cost_usd_per_hour=100.0))
        registry.register("b", Budget(max_cost_usd_per_hour=100.0))

        client = FakeClient(FakeChatResult(cost_usd=0.10))
        wrapped = registry.wrap(client)

        with registry.context("a"):
            wrapped.chat([{"role": "user", "content": "hi"}])

        # Budget A should have a recorded call.
        report_a = registry.get("a").report()
        report_b = registry.get("b").report()
        assert report_a.cost_per_hour == 0.10
        assert report_b.cost_per_hour == 0.0

    def test_wrap_without_context_passes_through(self):
        registry = BudgetRegistry()
        registry.register("a", Budget(max_cost_usd_per_hour=100.0))

        client = FakeClient()
        wrapped = registry.wrap(client)

        # Without a context, the call passes through with no budget.
        wrapped.chat([{"role": "user", "content": "hi"}])
        assert client.calls == 1


class TestBudgetExceededMetadata:
    def test_exception_carries_metadata(self):
        b = Budget(max_cost_usd_per_hour=10.0)
        try:
            b.check(projected_cost_usd=20.0)
        except BudgetExceeded as exc:
            assert exc.kind == "cost_usd"
            assert exc.window == "hour"
            assert exc.limit == 10.0
            assert exc.current >= 20.0

    def test_exception_message_useful(self):
        b = Budget(max_cost_usd_per_hour=10.0)
        try:
            b.check(projected_cost_usd=20.0)
        except BudgetExceeded as exc:
            assert "cost_usd" in str(exc)
            assert "hour" in str(exc)
