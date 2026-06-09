# Concept — LLM Clients

> vstack patterns are LLM-provider agnostic. The client abstraction
> lets you swap between Anthropic / OpenAI / Ollama / stub / custom
> without changing pattern code. This doc explains the client
> protocol and how to integrate a new provider.

---

## The protocol

Every LLM client implements two methods (sync + async variants):

```python
class LLMClient(Protocol):
    def chat(
        self,
        messages: list[dict],
        *,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        response_format: dict | None = None,
        timeout: float | None = None,
    ) -> ChatResult:
        ...


class AsyncLLMClient(Protocol):
    async def chat(
        self,
        messages: list[dict],
        *,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        response_format: dict | None = None,
        timeout: float | None = None,
    ) -> ChatResult:
        ...
```

`ChatResult` carries:
- `content` — string or structured JSON.
- `tokens_in` / `tokens_out` — for cost tracking.
- `cost_usd` — pre-computed cost.
- `model` — actual model used (handles provider-side fallback).

---

## Built-in clients

### Anthropic

```python
from vstack.aar.clients import AnthropicClient

client = AnthropicClient(
    api_key=...,  # default from VSTACK_ANTHROPIC_API_KEY
    model="anthropic-flagship",
    max_retries=3,
    timeout=60.0,
)
```

### OpenAI

```python
from vstack.aar.clients import OpenAIClient

client = OpenAIClient(
    api_key=...,
    model="gpt-flagship",
    max_retries=3,
)
```

### Ollama (local)

```python
from vstack.aar.clients import OllamaClient

client = OllamaClient(
    base_url="http://localhost:11434",
    model="llama-3-70b",
)
```

### Stub (testing)

```python
from vstack.aar.clients import StubClient

# Pre-program responses:
client = StubClient([
    '{"finding": "..."}',
    '{"finding": "..."}',
])
```

---

## Async clients

Every sync client has an async mirror with the `Async` prefix:

```python
from vstack.aar.clients import (
    AsyncAnthropicClient,
    AsyncOpenAIClient,
    AsyncOllamaClient,
    AsyncStubClient,
)
```

The async clients share the same constructor arguments as sync.

---

## Cost tracking

Cost is tracked automatically via `record_llm_call()`. Each client
calls this hook after every LLM response:

```python
from vstack.aar import record_llm_call, get_cost_summary

# Done automatically by the client:
record_llm_call(
    provider="anthropic",
    model="flagship",
    tokens_in=1500,
    tokens_out=300,
    cost_usd=0.022,
    pattern="lewin",
)

# Inspect aggregated cost:
summary = get_cost_summary()
print(f"Total cost: ${summary.total_cost:.2f}")
```

---

## Retry semantics

Each client has retry semantics for transient failures:

| Error class               | Retry?  | Backoff             |
|---------------------------|---------|---------------------|
| RateLimitError            | Yes     | Exponential 1s-32s |
| ServerError (5xx)         | Yes     | Exponential 1s-16s  |
| ConnectionError           | Yes     | Exponential 1s-8s   |
| TimeoutError              | Yes (once) | Fixed 5s          |
| InvalidRequestError (4xx) | No      | -                   |
| AuthenticationError       | No      | -                   |

Configure via `max_retries=` on the client.

---

## Prompt-injection guards

vstack's free-text input fields pass through input guards before
hitting the LLM client. The guards detect:

- `vstack`-style override instructions (e.g., `"Ignore previous
  instructions"`).
- Multi-line prompt-injection sequences.
- Excessively long single-line inputs.

The guards reject inputs that match patterns from
`_security/lib/_input_guards.py`. To customize:

```python
from vstack.security import add_input_guard

add_input_guard(pattern=r"DROP TABLE", action="reject")
```

---

## Implementing a custom client

To integrate a provider not bundled, implement the `LLMClient`
protocol:

```python
from vstack.aar import ChatResult, record_llm_call


class MyCustomClient:
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def chat(
        self,
        messages: list[dict],
        *,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        response_format: dict | None = None,
        timeout: float | None = None,
    ) -> ChatResult:
        # 1. Translate messages to provider format.
        provider_payload = self._translate(messages)

        # 2. Call the provider's API.
        response = self._http_post(
            url=PROVIDER_URL,
            json=provider_payload,
            timeout=timeout or 60.0,
        )

        # 3. Translate the response.
        content = response["text"]
        tokens_in = response["usage"]["prompt_tokens"]
        tokens_out = response["usage"]["completion_tokens"]
        cost_usd = self._compute_cost(tokens_in, tokens_out)

        # 4. Record cost.
        record_llm_call(
            provider="my-custom",
            model=model or self.model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
        )

        # 5. Return result.
        return ChatResult(
            content=content,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
            model=model or self.model,
        )
```

Then pass to any analyzer:

```python
from vstack.lewin import LewinAttributionDetector

client = MyCustomClient(api_key="...", model="my-model")
detection = LewinAttributionDetector(client).run(trace)
```

---

## Structured output

Some patterns ask for JSON-structured output. The client should
support a `response_format=` argument:

```python
def chat(self, messages, *, response_format=None, ...):
    if response_format and response_format.get("type") == "json_object":
        # Use the provider's JSON-mode API.
        return self._chat_json_mode(messages, ...)
    return self._chat_text(messages, ...)
```

If the provider doesn't natively support JSON mode, vstack falls
back to regex-extracting JSON from the response.

---

## Selecting a client per pattern

By default, all patterns share one client. To use different clients
per pattern (e.g., a cheaper model for quick mode, a flagship for
forensic):

```python
from vstack.aar.clients import AnthropicClient, OpenAIClient

fast_client = AnthropicClient(model="anthropic-haiku")
deep_client = OpenAIClient(model="gpt-flagship")

# Quick mode = fast client.
quick = LewinAttributionDetector(fast_client, mode="quick").run(trace)

# Forensic mode = deep client.
forensic = LewinAttributionDetector(deep_client, mode="forensic").run(trace)
```

Or per-pattern in `diagnose()`:

```python
from vstack import diagnose

report = diagnose(
    trace=trace,
    llm_client_per_pattern={
        "lewin": deep_client,
        "aar": deep_client,
        "yerkes_dodson": fast_client,
    },
)
```

---

## See also

- Concept: pattern shapes (`docs/concepts/pattern-shape.md`)
- Tutorial 9: async fan-out
- Tutorial 10: observability
- Client source: `_aar/lib/clients/`
