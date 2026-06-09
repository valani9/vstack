"""Replay recording — wrap an LLM client to capture requests + responses."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ._replay import ReplayEntry, hash_request


class ReplayRecorder:
    """Wraps an LLM client to record every request/response pair.

    Usage:

        from vstack.replay import ReplayRecorder
        from vstack.aar.clients import AnthropicClient

        recorder = ReplayRecorder("runs/2026-06-09.jsonl")
        client = recorder.wrap(AnthropicClient())

        # Use the wrapped client as normal:
        result = client.chat([...])

        recorder.close()

    The recorder writes one JSONL line per LLM call. The wrapped
    client behaves identically to the unwrapped one.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        pattern: str | None = None,
        flush_every: bool = True,
    ):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.pattern = pattern
        self.flush_every = flush_every
        self._file = open(self.path, "a")
        self._call_count = 0

    def wrap(self, client: Any) -> Any:
        return _RecordingClient(client=client, recorder=self)

    def record(
        self,
        *,
        messages: list[dict],
        kwargs: dict[str, Any],
        response: Any,
    ) -> None:
        request_hash = hash_request(messages, **kwargs)
        entry = ReplayEntry(
            request_hash=request_hash,
            request={
                "messages": messages,
                **{k: v for k, v in kwargs.items() if v is not None},
            },
            response=_response_to_dict(response),
            timestamp=datetime.now(timezone.utc).isoformat(),
            pattern=self.pattern,
        )
        self._file.write(json.dumps(entry.to_dict(), default=str) + "\n")
        if self.flush_every:
            self._file.flush()
        self._call_count += 1

    def call_count(self) -> int:
        return self._call_count

    def close(self) -> None:
        if not self._file.closed:
            self._file.flush()
            self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def _response_to_dict(response: Any) -> dict[str, Any]:
    """Serialize a chat result to a JSON-safe dict."""
    if isinstance(response, dict):
        return response

    return {
        "content": getattr(response, "content", ""),
        "tokens_in": getattr(response, "tokens_in", 0),
        "tokens_out": getattr(response, "tokens_out", 0),
        "cost_usd": getattr(response, "cost_usd", 0.0),
        "model": getattr(response, "model", "unknown"),
    }


class _RecordingClient:
    """Wraps a client; records every chat call to the recorder."""

    def __init__(self, client: Any, recorder: ReplayRecorder):
        self._client = client
        self._recorder = recorder

    def chat(self, messages: list[dict], **kwargs: Any) -> Any:
        result = self._client.chat(messages, **kwargs)
        self._recorder.record(messages=messages, kwargs=kwargs, response=result)
        return result

    async def achat(self, messages: list[dict], **kwargs: Any) -> Any:
        if hasattr(self._client, "achat"):
            result = await self._client.achat(messages, **kwargs)
        else:
            result = await self._client.chat(messages, **kwargs)
        self._recorder.record(messages=messages, kwargs=kwargs, response=result)
        return result

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)
