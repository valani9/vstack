"""Redaction patterns + Redactor."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RedactionPattern:
    """A named regex pattern + replacement."""

    name: str
    pattern: str
    replacement: str
    description: str = ""

    def __post_init__(self) -> None:
        # Pre-compile for fast scrubbing.
        self._compiled = re.compile(self.pattern)

    def sub(self, text: str) -> tuple[str, int]:
        """Substitute matches; return (new_text, match_count)."""
        new_text, count = self._compiled.subn(self.replacement, text)
        return new_text, count


# Default built-in patterns. Order matters: more-specific patterns
# come first so a generic email regex doesn't eat the user portion of
# `https://admin:hunter2@db.example.com` before the URL pattern can match.
DEFAULT_PATTERNS: list[RedactionPattern] = [
    RedactionPattern(
        name="url_credentials",
        pattern=r"https?://[^:\s]+:[^@\s]+@[^\s]+",
        replacement="[URL_WITH_CREDS]",
        description="URLs containing user:pass@ credentials",
    ),
    RedactionPattern(
        name="email",
        pattern=r"\b[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}\b",
        replacement="[EMAIL]",
        description="Email addresses",
    ),
    RedactionPattern(
        name="phone_us",
        pattern=r"\b(?:\+?1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        replacement="[PHONE]",
        description="US/CA phone numbers",
    ),
    RedactionPattern(
        name="ssn",
        pattern=r"\b\d{3}-\d{2}-\d{4}\b",
        replacement="[SSN]",
        description="US SSN",
    ),
    RedactionPattern(
        name="credit_card",
        pattern=r"\b(?:\d[ -]*?){13,16}\b",
        replacement="[CC]",
        description="Credit card numbers (13-16 digit runs)",
    ),
    RedactionPattern(
        name="aws_access_key",
        pattern=r"\bAKIA[0-9A-Z]{16}\b",
        replacement="[AWS_KEY]",
        description="AWS access key IDs",
    ),
    RedactionPattern(
        name="aws_secret_key",
        pattern=r"\b[A-Za-z0-9/+=]{40}\b(?=.{0,200}aws)",
        replacement="[AWS_SECRET]",
        description="AWS secret access keys (40-char base64 near 'aws')",
    ),
    RedactionPattern(
        name="api_key_sk",
        pattern=r"\bsk-[A-Za-z0-9_-]{20,}\b",
        replacement="[API_KEY]",
        description="sk-prefixed API keys",
    ),
    RedactionPattern(
        name="bearer_token",
        pattern=r"\b[Bb]earer\s+[A-Za-z0-9._~+/=-]{20,}",
        replacement="Bearer [TOKEN]",
        description="HTTP Bearer authorization",
    ),
    RedactionPattern(
        name="jwt",
        pattern=r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b",
        replacement="[JWT]",
        description="JSON Web Tokens",
    ),
    RedactionPattern(
        name="ipv4",
        pattern=r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        replacement="[IPV4]",
        description="IPv4 addresses",
    ),
]


@dataclass
class Redactor:
    """Scrub text and traces against a set of patterns.

    Counts matches per pattern across scrubs for auditing.
    """

    patterns: list[RedactionPattern] = field(default_factory=list)
    _match_counts: dict[str, int] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        # Don't share state across instances.
        self._match_counts = {p.name: 0 for p in self.patterns}

    def scrub(self, text: str) -> str:
        if not text:
            return text
        out = text
        for pattern in self.patterns:
            out, count = pattern.sub(out)
            if count:
                self._match_counts[pattern.name] = self._match_counts.get(pattern.name, 0) + count
        return out

    def add_pattern(self, pattern: RedactionPattern) -> Redactor:
        return Redactor(patterns=[*self.patterns, pattern])

    def match_counts(self) -> dict[str, int]:
        return dict(self._match_counts)

    def reset_counts(self) -> None:
        self._match_counts = {p.name: 0 for p in self.patterns}

    def scrub_trace(self, trace: Any) -> Any:
        """Return a redacted copy of the trace (dict form).

        Field-level scrub: goal, outcome, and each step's content
        are scrubbed. Original trace not mutated.
        """
        if isinstance(trace, dict):
            new_trace = dict(trace)
        elif hasattr(trace, "model_dump"):
            new_trace = trace.model_dump()
        else:
            return trace  # unknown type; passthrough

        if "goal" in new_trace and isinstance(new_trace["goal"], str):
            new_trace["goal"] = self.scrub(new_trace["goal"])
        if "outcome" in new_trace and isinstance(new_trace["outcome"], str):
            new_trace["outcome"] = self.scrub(new_trace["outcome"])

        steps = new_trace.get("steps", [])
        new_steps = []
        for step in steps:
            if isinstance(step, dict):
                new_step = dict(step)
                if "content" in new_step and isinstance(new_step["content"], str):
                    new_step["content"] = self.scrub(new_step["content"])
                new_steps.append(new_step)
            else:
                new_steps.append(step)
        new_trace["steps"] = new_steps
        return new_trace


def redact_text(text: str, *, patterns: list[RedactionPattern] | None = None) -> str:
    """Convenience: scrub a single string with default patterns."""
    redactor = Redactor(patterns=patterns or DEFAULT_PATTERNS)
    return redactor.scrub(text)


def redact_trace(trace: Any, *, patterns: list[RedactionPattern] | None = None) -> Any:
    """Convenience: scrub a trace with default patterns."""
    redactor = Redactor(patterns=patterns or DEFAULT_PATTERNS)
    return redactor.scrub_trace(trace)
