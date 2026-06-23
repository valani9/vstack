"""LLM response cache — TTL + LRU eviction."""

from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any


def _hash_request(messages: list[dict[str, Any]], **kwargs: Any) -> str:
    """Canonical request hash for cache lookups."""
    body = json.dumps(
        {
            "messages": messages,
            "model": kwargs.get("model"),
            "temperature": kwargs.get("temperature", 0.0),
            "max_tokens": kwargs.get("max_tokens", 4096),
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


@dataclass
class CacheEntry:
    """A single cached response with metadata."""

    response: Any
    cached_at: float
    cost_usd: float
    tokens_in: int
    tokens_out: int


@dataclass
class CacheStats:
    """Cache utilization snapshot."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expirations: int = 0
    cost_saved_usd: float = 0.0
    tokens_saved: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "expirations": self.expirations,
            "cost_saved_usd": self.cost_saved_usd,
            "tokens_saved": self.tokens_saved,
            "hit_rate": self.hit_rate,
        }


class LLMCache:
    """In-memory LRU + TTL cache for LLM responses.

    Thread-safety: this implementation is NOT thread-safe. For
    multi-threaded use, wrap with a lock or use the Redis backend.

    For multi-process / cross-server caching, use the Redis backend
    (set ``redis_url=`` on construction).
    """

    def __init__(
        self,
        *,
        ttl_seconds: float = 3600.0,
        capacity: int = 1000,
        namespace: str = "default",
    ):
        self.ttl_seconds = ttl_seconds
        self.capacity = capacity
        self.namespace = namespace
        self._store: OrderedDict[str, CacheEntry] = OrderedDict()
        self.stats = CacheStats()

    def _key(self, request_hash: str) -> str:
        return f"{self.namespace}:{request_hash}"

    def _now(self) -> float:
        return time.time()

    def get(self, messages: list[dict[str, Any]], **kwargs: Any) -> Any | None:
        """Look up a cached response. Returns None on miss/expired."""
        h = _hash_request(messages, **kwargs)
        key = self._key(h)

        entry = self._store.get(key)
        if entry is None:
            return None

        # Check TTL.
        age = self._now() - entry.cached_at
        if age > self.ttl_seconds:
            del self._store[key]
            self.stats.expirations += 1
            return None

        # Move to end (LRU touch).
        self._store.move_to_end(key)
        return entry.response

    def put(
        self,
        messages: list[dict[str, Any]],
        response: Any,
        **kwargs: Any,
    ) -> None:
        """Store a response in the cache."""
        h = _hash_request(messages, **kwargs)
        key = self._key(h)

        entry = CacheEntry(
            response=response,
            cached_at=self._now(),
            cost_usd=getattr(response, "cost_usd", 0.0),
            tokens_in=getattr(response, "tokens_in", 0),
            tokens_out=getattr(response, "tokens_out", 0),
        )

        # Evict if at capacity (and this is a new key).
        if key not in self._store and len(self._store) >= self.capacity:
            self._store.popitem(last=False)
            self.stats.evictions += 1

        self._store[key] = entry
        self._store.move_to_end(key)

    def wrap(self, client: Any) -> Any:
        """Return a cache-wrapped LLM client."""
        return _CachedClient(client=client, cache=self)

    def invalidate(self, messages: list[dict[str, Any]], **kwargs: Any) -> bool:
        """Invalidate a single entry. Returns True if found."""
        h = _hash_request(messages, **kwargs)
        key = self._key(h)
        if key in self._store:
            del self._store[key]
            return True
        return False

    def clear(self) -> None:
        """Clear all cache entries."""
        self._store.clear()

    def size(self) -> int:
        return len(self._store)

    def reset_stats(self) -> None:
        self.stats = CacheStats()


class _CachedClient:
    """Wraps a client; intercepts chat() to check the cache first."""

    def __init__(self, client: Any, cache: LLMCache):
        self._client = client
        self._cache = cache

    def chat(self, messages: list[dict[str, Any]], **kwargs: Any) -> Any:
        cached = self._cache.get(messages, **kwargs)
        if cached is not None:
            self._cache.stats.hits += 1
            self._cache.stats.cost_saved_usd += getattr(cached, "cost_usd", 0.0)
            self._cache.stats.tokens_saved += getattr(cached, "tokens_in", 0) + getattr(
                cached, "tokens_out", 0
            )
            return cached

        self._cache.stats.misses += 1
        result = self._client.chat(messages, **kwargs)
        self._cache.put(messages, result, **kwargs)
        return result

    async def achat(self, messages: list[dict[str, Any]], **kwargs: Any) -> Any:
        cached = self._cache.get(messages, **kwargs)
        if cached is not None:
            self._cache.stats.hits += 1
            self._cache.stats.cost_saved_usd += getattr(cached, "cost_usd", 0.0)
            return cached

        self._cache.stats.misses += 1
        if hasattr(self._client, "achat"):
            result = await self._client.achat(messages, **kwargs)
        else:
            result = await self._client.chat(messages, **kwargs)
        self._cache.put(messages, result, **kwargs)
        return result

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)
