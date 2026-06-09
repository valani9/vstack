"""Replay primitives — load + match canned LLM responses."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class ReplayMissError(Exception):
    """Raised when a request can't be matched against any replay entry."""

    def __init__(self, request_hash: str, available_hashes: int):
        self.request_hash = request_hash
        self.available_hashes = available_hashes
        super().__init__(
            f"No replay entry matches request hash {request_hash[:16]}... "
            f"({available_hashes} entries in log)"
        )


@dataclass
class ReplayEntry:
    """A single replay entry: a request → response pair."""

    request_hash: str
    request: dict[str, Any]
    response: dict[str, Any]
    timestamp: str | None = None
    pattern: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReplayEntry:
        return cls(
            request_hash=data["request_hash"],
            request=data["request"],
            response=data["response"],
            timestamp=data.get("timestamp"),
            pattern=data.get("pattern"),
            extras={
                k: v
                for k, v in data.items()
                if k
                not in {
                    "request_hash",
                    "request",
                    "response",
                    "timestamp",
                    "pattern",
                }
            },
        )

    def to_dict(self) -> dict[str, Any]:
        result = {
            "request_hash": self.request_hash,
            "request": self.request,
            "response": self.response,
        }
        if self.timestamp:
            result["timestamp"] = self.timestamp
        if self.pattern:
            result["pattern"] = self.pattern
        result.update(self.extras)
        return result


def hash_request(messages: list[dict], **kwargs: Any) -> str:
    """Canonical hash of an LLM request.

    The hash is stable across runs of the same script: messages are
    JSON-serialized with sorted keys, kwargs are filtered to those
    that affect the response (model, temperature, max_tokens), and
    the result is SHA-256.
    """
    canonical = {
        "messages": _canonicalize_messages(messages),
        "model": kwargs.get("model"),
        "temperature": kwargs.get("temperature", 0.0),
        "max_tokens": kwargs.get("max_tokens", 4096),
        "response_format": kwargs.get("response_format"),
    }
    body = json.dumps(canonical, sort_keys=True, default=str)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _canonicalize_messages(messages: list[dict]) -> list[dict]:
    """Normalize message shape for hashing — strip extras, sort keys."""
    out = []
    for m in messages:
        if not isinstance(m, dict):
            out.append({"content": str(m)})
            continue
        normalized = {}
        for k in sorted(m.keys()):
            v = m[k]
            if isinstance(v, list):
                normalized[k] = [_canonicalize_part(p) for p in v]
            else:
                normalized[k] = v
        out.append(normalized)
    return out


def _canonicalize_part(part: Any) -> Any:
    if isinstance(part, dict):
        return {k: part[k] for k in sorted(part.keys())}
    return part


def load_run_log(path: str | Path) -> list[ReplayEntry]:
    """Read a JSONL run log into a list of ReplayEntry."""
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            entries.append(ReplayEntry.from_dict(data))
    return entries


@dataclass
class _ChatResult:
    """Minimal chat result type for replay."""

    content: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    model: str = "replay"


class ReplayClient:
    """LLM client that returns canned responses from a recorded log.

    Match policy:
      - Default: strict hash match. Raises ReplayMissError if no
        match found.
      - ``permissive=True``: returns the *next* unconsumed entry on
        a miss (useful for testing scaffolds where the request
        hashes won't be stable).
    """

    def __init__(
        self,
        entries: list[ReplayEntry],
        *,
        permissive: bool = False,
    ):
        self._entries_by_hash: dict[str, list[ReplayEntry]] = {}
        for entry in entries:
            self._entries_by_hash.setdefault(entry.request_hash, []).append(entry)
        self._entries_sequential = list(entries)
        self._sequential_idx = 0
        self.permissive = permissive
        self.hits = 0
        self.misses = 0

    @classmethod
    def from_file(cls, path: str | Path, **kwargs: Any) -> ReplayClient:
        entries = load_run_log(path)
        return cls(entries, **kwargs)

    def chat(self, messages: list[dict], **kwargs: Any) -> _ChatResult:
        h = hash_request(messages, **kwargs)
        entries = self._entries_by_hash.get(h)

        if entries:
            entry = entries.pop(0)
            self.hits += 1
            return _result_from_entry(entry)

        # Strict miss.
        if not self.permissive:
            self.misses += 1
            raise ReplayMissError(
                request_hash=h,
                available_hashes=len(self._entries_by_hash),
            )

        # Permissive: take the next unconsumed sequential entry.
        if self._sequential_idx >= len(self._entries_sequential):
            self.misses += 1
            raise ReplayMissError(
                request_hash=h,
                available_hashes=0,
            )

        entry = self._entries_sequential[self._sequential_idx]
        self._sequential_idx += 1
        self.hits += 1
        return _result_from_entry(entry)

    async def achat(self, messages: list[dict], **kwargs: Any) -> _ChatResult:
        return self.chat(messages, **kwargs)

    def stats(self) -> dict[str, int]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "remaining_entries": sum(len(es) for es in self._entries_by_hash.values()),
        }


def _result_from_entry(entry: ReplayEntry) -> _ChatResult:
    response = entry.response
    return _ChatResult(
        content=response.get("content", ""),
        tokens_in=response.get("tokens_in", 0),
        tokens_out=response.get("tokens_out", 0),
        cost_usd=response.get("cost_usd", 0.0),
        model=response.get("model", "replay"),
    )
