"""Tests for the LLM cache."""

from __future__ import annotations

from dataclasses import dataclass


from vstack.vcache import CacheStats, LLMCache


@dataclass
class FakeResult:
    content: str = "response"
    tokens_in: int = 100
    tokens_out: int = 50
    cost_usd: float = 0.10
    model: str = "fake-model"


class FakeClient:
    def __init__(self, result: FakeResult | None = None):
        self.result = result or FakeResult()
        self.calls = 0

    def chat(self, messages, **kwargs):
        self.calls += 1
        return self.result


class TestLLMCacheBasic:
    def test_get_miss_returns_none(self):
        cache = LLMCache()
        assert cache.get([{"role": "user", "content": "hi"}], model="m") is None

    def test_put_then_get_hits(self):
        cache = LLMCache()
        msg = [{"role": "user", "content": "hi"}]
        cache.put(msg, FakeResult(content="cached"), model="m")
        result = cache.get(msg, model="m")
        assert result.content == "cached"

    def test_different_messages_separate_entries(self):
        cache = LLMCache()
        cache.put([{"role": "user", "content": "a"}], FakeResult(content="A"))
        cache.put([{"role": "user", "content": "b"}], FakeResult(content="B"))
        assert cache.get([{"role": "user", "content": "a"}]).content == "A"
        assert cache.get([{"role": "user", "content": "b"}]).content == "B"

    def test_size(self):
        cache = LLMCache()
        assert cache.size() == 0
        cache.put([{"role": "user", "content": "a"}], FakeResult())
        assert cache.size() == 1

    def test_clear(self):
        cache = LLMCache()
        cache.put([{"role": "user", "content": "a"}], FakeResult())
        cache.clear()
        assert cache.size() == 0


class TestCacheTTL:
    def test_expiration_evicts(self, monkeypatch):
        cache = LLMCache(ttl_seconds=10.0)

        t = [0.0]

        def fake_now():
            return t[0]

        monkeypatch.setattr(cache, "_now", fake_now)

        msg = [{"role": "user", "content": "hi"}]
        cache.put(msg, FakeResult(content="cached"))

        # 5s later — still cached.
        t[0] = 5.0
        assert cache.get(msg).content == "cached"

        # 15s later — expired.
        t[0] = 15.0
        assert cache.get(msg) is None
        assert cache.stats.expirations == 1


class TestCacheLRUEviction:
    def test_evicts_least_recently_used(self):
        cache = LLMCache(capacity=2)
        cache.put([{"role": "user", "content": "a"}], FakeResult(content="A"))
        cache.put([{"role": "user", "content": "b"}], FakeResult(content="B"))
        # Access "a" to make it more recent.
        cache.get([{"role": "user", "content": "a"}])
        # Put "c" — should evict "b".
        cache.put([{"role": "user", "content": "c"}], FakeResult(content="C"))

        assert cache.get([{"role": "user", "content": "a"}]) is not None
        assert cache.get([{"role": "user", "content": "b"}]) is None
        assert cache.get([{"role": "user", "content": "c"}]) is not None
        assert cache.stats.evictions == 1

    def test_no_eviction_when_replacing_existing(self):
        cache = LLMCache(capacity=2)
        msg = [{"role": "user", "content": "a"}]
        cache.put(msg, FakeResult(content="A1"))
        cache.put(msg, FakeResult(content="A2"))
        # Same key — no eviction.
        assert cache.stats.evictions == 0
        assert cache.get(msg).content == "A2"


class TestNamespace:
    def test_namespaces_isolated(self):
        cache_a = LLMCache(namespace="a")
        cache_b = LLMCache(namespace="b")

        msg = [{"role": "user", "content": "hi"}]
        cache_a.put(msg, FakeResult(content="from_a"))
        cache_b.put(msg, FakeResult(content="from_b"))

        assert cache_a.get(msg).content == "from_a"
        assert cache_b.get(msg).content == "from_b"


class TestWrap:
    def test_wrap_caches_responses(self):
        cache = LLMCache()
        underlying = FakeClient(FakeResult(content="cached_response"))
        wrapped = cache.wrap(underlying)

        msg = [{"role": "user", "content": "hi"}]

        # First call — miss.
        r1 = wrapped.chat(msg, model="m1")
        assert r1.content == "cached_response"
        assert underlying.calls == 1

        # Second call — hit.
        r2 = wrapped.chat(msg, model="m1")
        assert r2.content == "cached_response"
        assert underlying.calls == 1  # Underlying not called.

    def test_stats_tracked(self):
        cache = LLMCache()
        wrapped = cache.wrap(FakeClient(FakeResult(cost_usd=0.10)))
        msg = [{"role": "user", "content": "hi"}]

        wrapped.chat(msg, model="m1")  # miss
        wrapped.chat(msg, model="m1")  # hit
        wrapped.chat(msg, model="m1")  # hit

        assert cache.stats.hits == 2
        assert cache.stats.misses == 1
        # 2 hits × $0.10 = $0.20 saved.
        assert cache.stats.cost_saved_usd == 0.20

    def test_hit_rate(self):
        cache = LLMCache()
        cache.stats.hits = 7
        cache.stats.misses = 3
        assert cache.stats.hit_rate == 0.7

    def test_hit_rate_zero_division(self):
        cache = LLMCache()
        assert cache.stats.hit_rate == 0.0


class TestInvalidate:
    def test_invalidate_removes_entry(self):
        cache = LLMCache()
        msg = [{"role": "user", "content": "hi"}]
        cache.put(msg, FakeResult())
        assert cache.invalidate(msg) is True
        assert cache.get(msg) is None

    def test_invalidate_missing_returns_false(self):
        cache = LLMCache()
        assert cache.invalidate([{"role": "user", "content": "missing"}]) is False


class TestStats:
    def test_reset_stats(self):
        cache = LLMCache()
        cache.stats.hits = 5
        cache.reset_stats()
        assert cache.stats.hits == 0

    def test_stats_to_dict(self):
        stats = CacheStats(hits=5, misses=3, cost_saved_usd=1.5)
        data = stats.to_dict()
        assert data["hits"] == 5
        assert data["hit_rate"] == 5 / 8
        assert data["cost_saved_usd"] == 1.5


class TestAttributePassthrough:
    def test_non_chat_attrs_forward(self):
        cache = LLMCache()
        client = FakeClient()
        client.custom_attr = "hello"
        wrapped = cache.wrap(client)
        assert wrapped.custom_attr == "hello"
