"""Tests for the shared LLM-response cache in vstack.diagnose.

The cache is opt-in via ``diagnose(cache=True, ...)``. When enabled,
the runner wraps the user's LLM client in a CachingLLMClient and
threads that wrapper through to every pattern. A hit returns the
previous completion without paying again; a miss forwards to the
underlying client.

These tests use a tiny in-memory stub client that counts calls so we
can verify the wrapper actually short-circuits on hit.
"""

from __future__ import annotations

import sys
import types

from vstack.diagnose import CachingLLMClient, diagnose
from vstack.diagnose.cache import CachingClientStats, _hash_key
from vstack.diagnose.registry import PatternInfo


class _CountingClient:
    """LLM-client stub that records every ``complete()`` call."""

    def __init__(self, model: str = "test-model") -> None:
        self.model = model
        self.calls: list[tuple[str, str | None]] = []

    def complete(self, prompt: str, system: str | None = None) -> str:
        self.calls.append((prompt, system))
        return f"reply-to:{prompt[:24]}"


def test_hash_key_is_stable_and_collision_resistant() -> None:
    a = _hash_key("hello", "sys", "m1")
    a2 = _hash_key("hello", "sys", "m1")
    assert a == a2
    assert _hash_key("hello", "sys", "m1") != _hash_key("hello", "sys2", "m1")
    assert _hash_key("hello", "sys", "m1") != _hash_key("hello", "sys", "m2")


def test_wrapper_returns_cached_on_second_call() -> None:
    inner = _CountingClient()
    w = CachingLLMClient(inner=inner)
    a = w.complete("ping", system="sys")
    b = w.complete("ping", system="sys")
    assert a == b
    assert len(inner.calls) == 1
    assert w.stats.hits == 1
    assert w.stats.misses == 1
    assert w.stats.inserts == 1


def test_wrapper_misses_on_different_prompt() -> None:
    inner = _CountingClient()
    w = CachingLLMClient(inner=inner)
    w.complete("ping", system="sys")
    w.complete("pong", system="sys")
    assert len(inner.calls) == 2
    assert w.stats.misses == 2
    assert w.stats.hits == 0


def test_wrapper_evicts_when_maxsize_exceeded() -> None:
    inner = _CountingClient()
    w = CachingLLMClient(inner=inner, maxsize=2)
    w.complete("a")
    w.complete("b")
    w.complete("c")  # Evicts "a"
    # Re-asking for "a" should miss again because it was evicted.
    w.complete("a")
    assert w.stats.misses == 4
    assert w.stats.hits == 0


def test_wrapper_forwards_unknown_attributes() -> None:
    inner = _CountingClient(model="explicit-model")
    inner.custom_attr = "value-on-inner"  # type: ignore[attr-defined]
    w = CachingLLMClient(inner=inner)
    assert w.model == "explicit-model"
    assert w.custom_attr == "value-on-inner"  # type: ignore[attr-defined]


def _fake_pattern_calling_llm(slug: str, pattern_id: int, prompt: str = "shared-prompt") -> PatternInfo:
    """Synthetic pattern whose analyzer issues one ``complete()`` call
    with a configurable prompt. Used to verify cache hit/miss behavior
    across two patterns in the same diagnose() run.
    """
    module_name = f"_test_cache_synth.{slug}"
    cls_name = f"{slug.title()}Analyzer"
    mod = types.ModuleType(module_name)

    class _Analyzer:
        def __init__(self, *, llm_client=None, mode="standard") -> None:
            self.client = llm_client

        def run(self, trace):  # noqa: ARG002
            text = self.client.complete(prompt, system="diagnose-test")
            return types.SimpleNamespace(
                findings=[
                    {
                        "severity": "low",
                        "title": f"{slug}: {text}",
                    }
                ]
            )

    _Analyzer.__name__ = cls_name
    setattr(mod, cls_name, _Analyzer)
    sys.modules[module_name] = mod

    return PatternInfo(
        name=slug,
        module=module_name,
        analyzer=cls_name,
        analyzer_async=None,
        shapes=("individual",),
        module_id=9,
        pattern_id=pattern_id,
        summary="cache-test pattern",
    )


class _Trace:
    goal = "test"
    steps = ()


def test_diagnose_without_cache_calls_client_twice_for_two_patterns() -> None:
    inner = _CountingClient()
    a = _fake_pattern_calling_llm("cachea", pattern_id=300)
    b = _fake_pattern_calling_llm("cacheb", pattern_id=301)
    report = diagnose(_Trace(), llm_client=inner, patterns=[a, b])
    assert len(inner.calls) == 2
    assert report.cache_stats is None


def test_diagnose_with_cache_short_circuits_identical_prompts() -> None:
    """Two patterns sending IDENTICAL prompts under cache=True should
    only hit the inner client once."""
    inner = _CountingClient()
    a = _fake_pattern_calling_llm("cachec", pattern_id=302)
    b = _fake_pattern_calling_llm("cached", pattern_id=303)
    report = diagnose(_Trace(), llm_client=inner, patterns=[a, b], cache=True)
    assert len(inner.calls) == 1
    assert report.cache_stats is not None
    assert isinstance(report.cache_stats, CachingClientStats)
    assert report.cache_stats.hits == 1
    assert report.cache_stats.misses == 1
    assert report.cache_stats.hit_rate == 0.5


def test_diagnose_cache_disabled_when_no_client() -> None:
    """cache=True with llm_client=None is a no-op (we have nothing to
    wrap), and report.cache_stats stays None."""
    a = _fake_pattern_calling_llm("cachee", pattern_id=304)
    report = diagnose(_Trace(), llm_client=None, patterns=[a], cache=True)
    assert report.cache_stats is None
