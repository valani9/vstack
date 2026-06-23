"""Shared LLM-response cache for one ``diagnose()`` run.

When a bundle of patterns runs against one trace, the analyzers often
hit the LLM with overlapping or identical prompts: the same system
prompt across patterns, or two patterns asking the same question
about the same trace from different angles. Without coordination,
each pattern pays separately.

The wrapper in this module sits between the user-supplied LLM client
and the pattern analyzers. It hashes ``(prompt, system, model)`` and
returns cached completions on hit. The cache is local to one
``diagnose()`` invocation; we deliberately do not share across calls
because traces change and stale entries would be silently wrong.

This is opt-in via ``diagnose(cache=True, ...)``. Default is no cache
so existing behavior is unchanged.

The wrapper preserves the LLM-client protocol:

    def complete(prompt: str, system: str | None = None) -> str

so it slots in anywhere the original client was used. Token-usage
accounting (``last_usage`` etc.) is forwarded to the underlying
client on a miss and reused on a hit.
"""

from __future__ import annotations

import hashlib
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, cast


@dataclass
class CachingClientStats:
    """Counters for one cache wrapper. Read after a diagnose() run to
    see how many calls the bundle saved."""

    hits: int = 0
    misses: int = 0
    inserts: int = 0
    bytes_saved: int = 0  # heuristic: length of cached response strings

    @property
    def total_lookups(self) -> int:
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        n = self.total_lookups
        return self.hits / n if n else 0.0


def _hash_key(prompt: str, system: str | None, model: str | None) -> str:
    """Stable cache key. We hash both prompt and system because two
    patterns might send the same user prompt with different system
    prompts and they should NOT collide.
    """
    h = hashlib.sha256()
    h.update(b"vstack-cache-v1")
    h.update(b"\x00")
    h.update((model or "").encode("utf-8", errors="replace"))
    h.update(b"\x00")
    h.update((system or "").encode("utf-8", errors="replace"))
    h.update(b"\x00")
    h.update(prompt.encode("utf-8", errors="replace"))
    return h.hexdigest()


@dataclass
class CachingLLMClient:
    """Thin wrapper around an LLM client that memoizes ``complete()``
    calls by ``(prompt, system, model)``.

    The wrapper exposes the same ``complete()`` signature as the
    underlying client and forwards every other attribute access via
    ``__getattr__``, so analyzers that read e.g.
    ``client.last_usage`` continue to work transparently.

    Bounded size: ``maxsize`` controls how many distinct entries the
    cache holds before evicting the oldest (LRU). Default 256 is
    big enough for any realistic single-trace bundle and small enough
    to never matter for memory.
    """

    inner: Any
    maxsize: int = 256
    _store: "OrderedDict[str, str]" = field(default_factory=OrderedDict)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    stats: CachingClientStats = field(default_factory=CachingClientStats)

    def complete(self, prompt: str, system: str | None = None) -> str:
        model = getattr(self.inner, "model", None)
        key = _hash_key(prompt, system, model)
        with self._lock:
            cached = self._store.get(key)
            if cached is not None:
                # Refresh LRU position.
                self._store.move_to_end(key)
                self.stats.hits += 1
                return cached
            self.stats.misses += 1
        # Miss: call the inner client outside the lock so we don't
        # serialize concurrent traffic on slow API calls.
        result = cast(str, self.inner.complete(prompt, system=system))
        with self._lock:
            self._store[key] = result
            self.stats.inserts += 1
            self.stats.bytes_saved += len(result)
            # Evict oldest if over capacity.
            while len(self._store) > self.maxsize:
                self._store.popitem(last=False)
        return result

    async def complete_async(self, prompt: str, system: str | None = None) -> str:
        """Async variant: same caching semantics, used when the runner
        operates in the asyncio path."""
        model = getattr(self.inner, "model", None)
        key = _hash_key(prompt, system, model)
        with self._lock:
            cached = self._store.get(key)
            if cached is not None:
                self._store.move_to_end(key)
                self.stats.hits += 1
                return cached
            self.stats.misses += 1
        result = cast(str, await self.inner.complete(prompt, system=system))
        with self._lock:
            self._store[key] = result
            self.stats.inserts += 1
            self.stats.bytes_saved += len(result)
            while len(self._store) > self.maxsize:
                self._store.popitem(last=False)
        return result

    def __getattr__(self, name: str) -> Any:
        # Delegate unknown attributes to the inner client so analyzers
        # that read e.g. ``model`` or ``last_usage`` keep working.
        if name.startswith("_") or name in {"inner", "maxsize", "stats"}:
            raise AttributeError(name)
        return getattr(self.__dict__["inner"], name)
