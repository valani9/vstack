"""vstack.vcache — LLM response cache with TTL + LRU eviction.

The vcache module wraps an LLM client with an in-memory cache.
Identical requests return cached responses without re-spending
LLM calls.

Key features:
  - TTL-based expiration (default 1 hour).
  - LRU eviction at configurable capacity.
  - Stats tracking (hits / misses / cost saved).
  - Per-pattern cache namespacing.
  - Optional Redis backend for cross-process caching.

Use cases
---------

* **Development.** Cache LLM responses during iteration so you
  don't re-pay on every test run.
* **Batched workloads.** A pipeline that diagnoses 1000 traces
  often has duplicate trace shapes; cache eliminates the dupes.
* **Server-side dedupe.** Multiple users diagnosing the same
  popular failure get the cached response.

Quick start
-----------

    from vstack.vcache import LLMCache
    from vstack.aar.clients import AnthropicClient

    cache = LLMCache(ttl_seconds=3600, capacity=1000)
    client = cache.wrap(AnthropicClient())

    # Use as normal:
    from vstack.lewin import LewinAttributionDetector
    detector = LewinAttributionDetector(client)

    # The cache transparently dedupes:
    detector.run(trace1)  # MISS — calls LLM
    detector.run(trace1)  # HIT — cache hit, no LLM call

    print(cache.stats())
    # {'hits': 1, 'misses': 1, 'cost_saved_usd': 0.022}
"""

from __future__ import annotations

from ._cache import (
    CacheEntry,
    CacheStats,
    LLMCache,
)

__all__ = [
    "CacheEntry",
    "CacheStats",
    "LLMCache",
]
