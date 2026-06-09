# Tutorial 9 — Async Fan-Out for High-Volume Production

> Goal: run vstack diagnostics in parallel across thousands of
> traces. Covers the async API surface, batching, rate-limiting,
> and back-pressure handling.

---

## When you need async fan-out

You have:
- 1000+ traces per hour to diagnose.
- A bounded LLM rate limit (e.g., 100 req/min on Anthropic).
- A latency budget (e.g., diagnostics must finish within 5 min
  of the trace arriving).

You don't need async fan-out for:
- < 100 traces per hour. Sync is fine.
- Single-trace user-facing diagnostics. Async adds complexity
  without benefit.

---

## Part 1 — The async surface

Every analyzer has an async mirror class. The naming convention
is `XAnalyzerAsync` for the async variant of `XAnalyzer`.

```python
from vstack.lewin import LewinAttributionDetectorAsync
from vstack.aar.clients import AsyncStubClient

detector = LewinAttributionDetectorAsync(AsyncStubClient(), mode="standard")
result = await detector.run(trace)
```

The async client must be passed to async detectors:
- `AsyncStubClient` — stub.
- `AsyncAnthropicClient` — wraps the async Anthropic SDK.
- `AsyncOpenAIClient` — wraps the async OpenAI SDK.
- `AsyncOllamaClient` — wraps async Ollama.

---

## Part 2 — Fan-out pattern

The canonical fan-out shape:

```python
import asyncio
from vstack.lewin import LewinAttributionDetectorAsync
from vstack.aar.clients import AsyncAnthropicClient


async def fan_out_lewin(traces: list) -> list:
    detector = LewinAttributionDetectorAsync(AsyncAnthropicClient(), mode="standard")
    return await asyncio.gather(*(detector.run(t) for t in traces))


# Use:
results = asyncio.run(fan_out_lewin(traces))
```

This works for small batches but doesn't respect rate limits.

---

## Part 3 — Rate-limited fan-out

For production volume, you need a rate limiter:

```python
import asyncio
from vstack.lewin import LewinAttributionDetectorAsync
from vstack.aar.clients import AsyncAnthropicClient


class RateLimiter:
    """Simple token-bucket rate limiter."""

    def __init__(self, rate: float):
        """rate = requests per second"""
        self.rate = rate
        self.tokens = 1.0
        self.last_refill = asyncio.get_event_loop().time()

    async def acquire(self) -> None:
        while True:
            now = asyncio.get_event_loop().time()
            elapsed = now - self.last_refill
            self.tokens = min(1.0, self.tokens + elapsed * self.rate)
            self.last_refill = now

            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return

            await asyncio.sleep(0.05)


async def rate_limited_fan_out(traces: list, rate: float = 1.5) -> list:
    """Fan-out at most `rate` requests per second."""
    detector = LewinAttributionDetectorAsync(AsyncAnthropicClient())
    limiter = RateLimiter(rate)

    async def run_one(trace):
        await limiter.acquire()
        return await detector.run(trace)

    return await asyncio.gather(*(run_one(t) for t in traces))
```

For Anthropic's typical 50 req/min, set `rate=0.83` (50 / 60).
Leave headroom for retries (e.g., `rate=0.7`).

---

## Part 4 — Bounded concurrency

Even with rate limiting, you may want to bound how many tasks are
*in flight* at once (to bound memory usage):

```python
async def bounded_fan_out(
    traces: list,
    rate: float = 1.5,
    max_concurrent: int = 10,
) -> list:
    detector = LewinAttributionDetectorAsync(AsyncAnthropicClient())
    limiter = RateLimiter(rate)
    semaphore = asyncio.Semaphore(max_concurrent)

    async def run_one(trace):
        async with semaphore:
            await limiter.acquire()
            return await detector.run(trace)

    return await asyncio.gather(*(run_one(t) for t in traces))
```

`max_concurrent=10` is a good default. Higher values risk memory
issues on large LLM payloads; lower values waste capacity.

---

## Part 5 — Multi-pattern fan-out

To diagnose multiple patterns per trace in parallel:

```python
from vstack.diagnose import diagnose_async


async def diagnose_many(traces: list) -> list:
    """Diagnose many traces with the default bundle, in parallel."""
    return await asyncio.gather(*(
        diagnose_async(trace=t, llm_client=AsyncAnthropicClient())
        for t in traces
    ))


results = asyncio.run(diagnose_many(traces))
```

`diagnose_async` runs the bundle's patterns in parallel internally
AND scales out across traces externally. The bundle's parallel
capacity is bounded by `max_concurrent_patterns`:

```python
await diagnose_async(
    trace=trace,
    llm_client=client,
    max_concurrent_patterns=4,  # max 4 patterns running at once
)
```

---

## Part 6 — Back-pressure handling

When the LLM rate-limits you, the async client surfaces a
`RateLimitError`. You can either retry or shed load:

```python
from vstack.aar.errors import RateLimitError


async def with_backoff(coro, max_retries: int = 3, base_delay: float = 1.0):
    for attempt in range(max_retries):
        try:
            return await coro
        except RateLimitError:
            delay = base_delay * (2 ** attempt)
            await asyncio.sleep(delay)
    raise RuntimeError("Exhausted retries")


async def safe_fan_out(traces: list) -> list:
    detector = LewinAttributionDetectorAsync(AsyncAnthropicClient())
    results = await asyncio.gather(*(
        with_backoff(detector.run(t))
        for t in traces
    ), return_exceptions=True)

    # Separate successes from failures.
    successes = [r for r in results if not isinstance(r, Exception)]
    failures = [r for r in results if isinstance(r, Exception)]

    return successes, failures
```

`return_exceptions=True` prevents one failure from aborting the
batch.

---

## Part 7 — Streaming results

For very large batches, you don't want to wait for all to finish
before processing any:

```python
async def stream_results(traces: list):
    detector = LewinAttributionDetectorAsync(AsyncAnthropicClient())

    tasks = [asyncio.create_task(detector.run(t)) for t in traces]

    for completed in asyncio.as_completed(tasks):
        result = await completed
        yield result


async def main():
    async for result in stream_results(traces):
        process(result)
```

`asyncio.as_completed` yields results in completion order. Useful
for pipelines that want to surface findings as they arrive rather
than batched.

---

## Part 8 — Cost tracking

Async runs share the same cost-tracking surface as sync:

```python
from vstack.aar import record_llm_call, get_cost_summary

await detector.run(trace)
summary = get_cost_summary()
print(f"Total cost: ${summary.total_cost:.2f}")
print(f"Total tokens: {summary.total_tokens}")
print(f"Calls: {summary.call_count}")
```

The thread-safe counter aggregates costs across all async runs.

---

## Part 9 — Production wiring example

```python
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from vstack import diagnose_async
from vstack.aar.clients import AsyncAnthropicClient

LLM = AsyncAnthropicClient()
LIMITER = RateLimiter(rate=0.7)  # 42 req/min, leaves headroom
SEMAPHORE = asyncio.Semaphore(10)


@asynccontextmanager
async def lifespan(app):
    yield


app = FastAPI(lifespan=lifespan)


@app.post("/v1/diagnose")
async def diagnose_endpoint(trace_payload: dict):
    trace = AgentTrace.model_validate(trace_payload)

    async with SEMAPHORE:
        await LIMITER.acquire()
        report = await diagnose_async(trace=trace, llm_client=LLM)

    return report.model_dump()
```

---

## See also

- Tutorial 6: FastAPI deployment
- Tutorial 7: Dashboard deployment
- Async client source: `_aar/lib/clients/async_*`
