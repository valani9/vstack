"""Tests for the replay module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vstack.replay import (
    ReplayClient,
    ReplayEntry,
    ReplayMissError,
    ReplayRecorder,
    load_run_log,
)
from vstack.replay._replay import hash_request


class TestHashRequest:
    def test_same_request_same_hash(self):
        h1 = hash_request([{"role": "user", "content": "hi"}], model="m1")
        h2 = hash_request([{"role": "user", "content": "hi"}], model="m1")
        assert h1 == h2

    def test_different_content_different_hash(self):
        h1 = hash_request([{"role": "user", "content": "hi"}], model="m1")
        h2 = hash_request([{"role": "user", "content": "hello"}], model="m1")
        assert h1 != h2

    def test_different_model_different_hash(self):
        h1 = hash_request([{"role": "user", "content": "hi"}], model="m1")
        h2 = hash_request([{"role": "user", "content": "hi"}], model="m2")
        assert h1 != h2

    def test_extra_kwargs_ignored(self):
        """Kwargs that don't affect the response shouldn't change the hash."""
        h1 = hash_request([{"role": "user", "content": "hi"}], model="m1")
        h2 = hash_request(
            [{"role": "user", "content": "hi"}],
            model="m1",
            unrelated_kwarg="foo",
        )
        assert h1 == h2

    def test_key_order_irrelevant(self):
        h1 = hash_request([{"role": "user", "content": "hi"}], model="m1")
        h2 = hash_request([{"content": "hi", "role": "user"}], model="m1")
        assert h1 == h2


class TestReplayEntry:
    def test_from_dict_roundtrip(self):
        original = {
            "request_hash": "abc123",
            "request": {"messages": [{"role": "user", "content": "hi"}]},
            "response": {"content": "hello"},
            "timestamp": "2026-06-09T00:00:00Z",
            "pattern": "lewin",
        }
        entry = ReplayEntry.from_dict(original)
        assert entry.request_hash == "abc123"
        assert entry.pattern == "lewin"
        assert entry.to_dict()["request_hash"] == "abc123"

    def test_from_dict_with_extras(self):
        data = {
            "request_hash": "abc",
            "request": {},
            "response": {},
            "extra_field": "custom",
        }
        entry = ReplayEntry.from_dict(data)
        assert entry.extras["extra_field"] == "custom"


class TestReplayClient:
    def test_strict_hit(self):
        messages = [{"role": "user", "content": "hi"}]
        h = hash_request(messages, model="m1")
        entries = [
            ReplayEntry(
                request_hash=h,
                request={},
                response={"content": "hello", "tokens_in": 10},
            )
        ]
        client = ReplayClient(entries)
        result = client.chat(messages, model="m1")
        assert result.content == "hello"
        assert client.hits == 1
        assert client.misses == 0

    def test_strict_miss_raises(self):
        client = ReplayClient([])
        with pytest.raises(ReplayMissError):
            client.chat([{"role": "user", "content": "hi"}], model="m1")
        assert client.misses == 1

    def test_permissive_falls_back_to_next(self):
        entry = ReplayEntry(
            request_hash="zzz",
            request={},
            response={"content": "fallback"},
        )
        client = ReplayClient([entry], permissive=True)
        # Hash won't match, but permissive returns next sequential.
        result = client.chat([{"role": "user", "content": "different"}], model="m1")
        assert result.content == "fallback"

    def test_permissive_runs_out(self):
        client = ReplayClient([], permissive=True)
        with pytest.raises(ReplayMissError):
            client.chat([{"role": "user", "content": "hi"}], model="m1")

    def test_repeat_hash_returns_each_response(self):
        messages = [{"role": "user", "content": "hi"}]
        h = hash_request(messages, model="m1")
        entries = [
            ReplayEntry(request_hash=h, request={}, response={"content": "first"}),
            ReplayEntry(request_hash=h, request={}, response={"content": "second"}),
        ]
        client = ReplayClient(entries)
        r1 = client.chat(messages, model="m1")
        r2 = client.chat(messages, model="m1")
        assert r1.content == "first"
        assert r2.content == "second"

    def test_stats(self):
        messages = [{"role": "user", "content": "hi"}]
        h = hash_request(messages, model="m1")
        entries = [
            ReplayEntry(request_hash=h, request={}, response={"content": "x"}),
        ]
        client = ReplayClient(entries)
        client.chat(messages, model="m1")
        stats = client.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 0
        assert stats["remaining_entries"] == 0


class TestRecorderAndReplay:
    def test_record_then_replay(self, tmp_path: Path):
        from dataclasses import dataclass

        @dataclass
        class FakeResult:
            content: str = "captured"
            tokens_in: int = 10
            tokens_out: int = 5
            cost_usd: float = 0.01
            model: str = "fake-model"

        class FakeClient:
            def chat(self, messages, **kwargs):
                return FakeResult()

        log_path = tmp_path / "run.jsonl"

        with ReplayRecorder(log_path) as recorder:
            client = recorder.wrap(FakeClient())
            result = client.chat([{"role": "user", "content": "hello"}], model="m1")
            assert result.content == "captured"

        # Verify log file written.
        lines = log_path.read_text().strip().split("\n")
        assert len(lines) == 1

        # Replay against the log.
        replay = ReplayClient.from_file(log_path)
        replayed = replay.chat([{"role": "user", "content": "hello"}], model="m1")
        assert replayed.content == "captured"
        assert replay.hits == 1

    def test_recorder_context_closes(self, tmp_path: Path):
        log_path = tmp_path / "run.jsonl"

        class FakeClient:
            def chat(self, messages, **kwargs):
                class R:
                    content = "x"
                    tokens_in = 1
                    tokens_out = 1
                    cost_usd = 0.0
                    model = "m"

                return R()

        with ReplayRecorder(log_path) as recorder:
            client = recorder.wrap(FakeClient())
            client.chat([{"role": "user", "content": "a"}], model="m1")

        # File should be closed after context exit.
        assert recorder._file.closed

    def test_call_count(self, tmp_path: Path):
        log_path = tmp_path / "run.jsonl"

        class FakeClient:
            def chat(self, messages, **kwargs):
                class R:
                    content = "x"
                    tokens_in = 1
                    tokens_out = 1
                    cost_usd = 0.0
                    model = "m"

                return R()

        recorder = ReplayRecorder(log_path)
        client = recorder.wrap(FakeClient())
        for _ in range(5):
            client.chat([{"role": "user", "content": "a"}], model="m1")
        assert recorder.call_count() == 5
        recorder.close()


class TestLoadRunLog:
    def test_loads_jsonl(self, tmp_path: Path):
        log_path = tmp_path / "run.jsonl"
        log_path.write_text(
            json.dumps(
                {
                    "request_hash": "h1",
                    "request": {},
                    "response": {"content": "a"},
                }
            )
            + "\n"
            + json.dumps(
                {
                    "request_hash": "h2",
                    "request": {},
                    "response": {"content": "b"},
                }
            )
            + "\n"
        )
        entries = load_run_log(log_path)
        assert len(entries) == 2
        assert entries[0].response["content"] == "a"
        assert entries[1].response["content"] == "b"

    def test_skips_empty_lines(self, tmp_path: Path):
        log_path = tmp_path / "run.jsonl"
        log_path.write_text(
            json.dumps({"request_hash": "h1", "request": {}, "response": {"content": "a"}})
            + "\n\n\n"
            + json.dumps({"request_hash": "h2", "request": {}, "response": {"content": "b"}})
            + "\n"
        )
        entries = load_run_log(log_path)
        assert len(entries) == 2
