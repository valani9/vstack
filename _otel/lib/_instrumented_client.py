"""OTel-instrumented LLM client wrapper."""

from __future__ import annotations

from typing import Any

from ._exporter import is_enabled, start_llm_span


class OTelInstrumentedClient:
    """Wraps any LLM client to emit OTel spans on every chat call.

    Example:

        from vstack.otel import setup_otel, OTelInstrumentedClient
        from vstack.aar.clients import AnthropicClient

        setup_otel(service_name="vstack-prod")

        raw = AnthropicClient()
        client = OTelInstrumentedClient(raw, provider="anthropic")

        # All chat() calls now emit OTel spans:
        from vstack.lewin import LewinAttributionDetector
        detector = LewinAttributionDetector(client)
        detector.run(trace)

    Attributes captured on each span:
        - vstack.llm.provider
        - vstack.llm.model
        - vstack.llm.tokens_in
        - vstack.llm.tokens_out
        - vstack.llm.cost_usd
        - vstack.llm.duration_ms
    """

    def __init__(
        self,
        client: Any,
        *,
        provider: str | None = None,
        model: str | None = None,
    ):
        self._client = client
        self._provider = provider
        self._model = model

    def chat(self, messages: list[dict], **kwargs: Any) -> Any:
        if not is_enabled():
            return self._client.chat(messages, **kwargs)

        with start_llm_span(provider=self._provider, model=self._model) as span:
            result = self._client.chat(messages, **kwargs)
            self._set_response_attrs(span, result)
            return result

    async def achat(self, messages: list[dict], **kwargs: Any) -> Any:
        if not is_enabled():
            if hasattr(self._client, "achat"):
                return await self._client.achat(messages, **kwargs)
            return await self._client.chat(messages, **kwargs)

        with start_llm_span(provider=self._provider, model=self._model) as span:
            if hasattr(self._client, "achat"):
                result = await self._client.achat(messages, **kwargs)
            else:
                result = await self._client.chat(messages, **kwargs)
            self._set_response_attrs(span, result)
            return result

    @staticmethod
    def _set_response_attrs(span, result: Any) -> None:
        tokens_in = getattr(result, "tokens_in", 0)
        tokens_out = getattr(result, "tokens_out", 0)
        cost_usd = getattr(result, "cost_usd", 0.0)
        model = getattr(result, "model", None)

        span.set_attribute("vstack.llm.tokens_in", tokens_in)
        span.set_attribute("vstack.llm.tokens_out", tokens_out)
        span.set_attribute("vstack.llm.cost_usd", cost_usd)
        if model:
            span.set_attribute("vstack.llm.model_actual", model)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)
