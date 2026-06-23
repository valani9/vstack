"""Budget enforcement — wraps LLM clients to gate calls against budgets."""

from __future__ import annotations

import contextvars
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from ._budget import Budget


_active_client: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "_active_budget_client",
    default=None,
)


class BudgetEnforcer:
    """Wraps an LLM client to enforce a single budget.

    Usage:

        from vstack.budget import Budget, BudgetEnforcer
        from vstack.aar.clients import AnthropicClient

        budget = Budget(max_cost_usd_per_hour=10.0)
        enforcer = BudgetEnforcer(budget)
        client = enforcer.wrap(AnthropicClient())

    The wrapped client behaves identically to the unwrapped one
    except it raises ``BudgetExceeded`` when a call would exceed the
    budget.

    Budget checking is *projected*: an estimated cost is computed
    before the call and checked against the limit. After the call
    succeeds, the *actual* cost is recorded against the budget.
    """

    def __init__(self, budget: Budget):
        self.budget = budget

    def wrap(self, client: Any) -> Any:
        """Return a wrapped version of ``client`` that enforces the budget."""
        return _BudgetEnforcedClient(client=client, enforcer=self)

    def projected_cost(
        self,
        prompt_tokens: int,
        max_response_tokens: int = 4096,
        *,
        cost_per_million_in: float = 3.0,
        cost_per_million_out: float = 15.0,
    ) -> float:
        """Estimate the cost of a call before making it.

        Uses default pricing typical for flagship models. Override
        ``cost_per_million_in`` / ``cost_per_million_out`` for your
        provider's pricing.
        """
        return (
            prompt_tokens * cost_per_million_in / 1_000_000
            + max_response_tokens * cost_per_million_out / 1_000_000
        )

    def report(self) -> Any:
        """Snapshot the current budget utilization."""
        return self.budget.report()


class _BudgetEnforcedClient:
    """Forwards every method call to the wrapped client; gates ``chat``."""

    def __init__(self, client: Any, enforcer: BudgetEnforcer):
        self._client = client
        self._enforcer = enforcer

    def chat(self, messages: list[dict[str, Any]], **kwargs: Any) -> Any:
        # Estimate prompt token size.
        prompt_tokens = _estimate_prompt_tokens(messages)
        max_response_tokens: int = kwargs.get("max_tokens", 4096)

        projected_cost = self._enforcer.projected_cost(
            prompt_tokens=prompt_tokens,
            max_response_tokens=max_response_tokens,
        )

        # Check budget BEFORE making the call.
        self._enforcer.budget.check(
            projected_tokens=prompt_tokens + max_response_tokens,
            projected_cost_usd=projected_cost,
        )

        # Make the call.
        result = self._client.chat(messages, **kwargs)

        # Record the ACTUAL cost.
        actual_tokens = getattr(result, "tokens_in", 0) + getattr(result, "tokens_out", 0)
        actual_cost = getattr(result, "cost_usd", projected_cost)
        self._enforcer.budget.record(
            tokens=actual_tokens,
            cost_usd=actual_cost,
        )

        return result

    async def achat(self, messages: list[dict[str, Any]], **kwargs: Any) -> Any:
        prompt_tokens = _estimate_prompt_tokens(messages)
        max_response_tokens: int = kwargs.get("max_tokens", 4096)

        projected_cost = self._enforcer.projected_cost(
            prompt_tokens=prompt_tokens,
            max_response_tokens=max_response_tokens,
        )

        self._enforcer.budget.check(
            projected_tokens=prompt_tokens + max_response_tokens,
            projected_cost_usd=projected_cost,
        )

        # Async clients use `chat` as async or `achat`.
        if hasattr(self._client, "achat"):
            result = await self._client.achat(messages, **kwargs)
        else:
            result = await self._client.chat(messages, **kwargs)

        actual_tokens = getattr(result, "tokens_in", 0) + getattr(result, "tokens_out", 0)
        actual_cost = getattr(result, "cost_usd", projected_cost)
        self._enforcer.budget.record(
            tokens=actual_tokens,
            cost_usd=actual_cost,
        )

        return result

    def __getattr__(self, name: str) -> Any:
        """Forward any other attribute access to the wrapped client."""
        return getattr(self._client, name)


def _estimate_prompt_tokens(messages: list[dict[str, Any]]) -> int:
    """Rough token estimate: 1 token per 4 characters."""
    if not messages:
        return 0
    total_chars = sum(
        len(str(m.get("content", ""))) if isinstance(m, dict) else len(str(m)) for m in messages
    )
    return max(1, total_chars // 4)


class BudgetRegistry:
    """Multi-client budget registry.

    Each client name maps to its own Budget. Use as a context to
    set the active client for nested LLM calls.
    """

    def __init__(self) -> None:
        self._budgets: dict[str, Budget] = {}

    def register(self, client_id: str, budget: Budget) -> None:
        self._budgets[client_id] = budget

    def unregister(self, client_id: str) -> None:
        self._budgets.pop(client_id, None)

    def get(self, client_id: str) -> Budget | None:
        return self._budgets.get(client_id)

    @contextmanager
    def context(self, client_id: str) -> Iterator[Budget | None]:
        token = _active_client.set(client_id)
        try:
            yield self._budgets.get(client_id)
        finally:
            _active_client.reset(token)

    def active_budget(self) -> Budget | None:
        client_id = _active_client.get()
        if client_id is None:
            return None
        return self._budgets.get(client_id)

    def wrap(self, client: Any) -> Any:
        """Wrap a client; uses the active budget from context."""
        return _MultiBudgetClient(client=client, registry=self)


class _MultiBudgetClient:
    """Like _BudgetEnforcedClient but resolves the budget from active context."""

    def __init__(self, client: Any, registry: BudgetRegistry):
        self._client = client
        self._registry = registry

    def chat(self, messages: list[dict[str, Any]], **kwargs: Any) -> Any:
        budget = self._registry.active_budget()
        if budget is None:
            return self._client.chat(messages, **kwargs)

        enforcer = BudgetEnforcer(budget)
        wrapped = enforcer.wrap(self._client)
        return wrapped.chat(messages, **kwargs)

    async def achat(self, messages: list[dict[str, Any]], **kwargs: Any) -> Any:
        budget = self._registry.active_budget()
        if budget is None:
            if hasattr(self._client, "achat"):
                return await self._client.achat(messages, **kwargs)
            return await self._client.chat(messages, **kwargs)

        enforcer = BudgetEnforcer(budget)
        wrapped = enforcer.wrap(self._client)
        return await wrapped.achat(messages, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)
