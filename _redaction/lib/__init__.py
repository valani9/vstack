"""vstack.redaction — PII / secret scrubbing for traces.

The redaction module removes or replaces sensitive content from
agent traces before they're submitted to a remote LLM for
diagnosis. Built-in patterns cover:

  - Email addresses
  - Phone numbers (US/E.164)
  - SSNs (US)
  - Credit card numbers
  - AWS access keys / secret keys
  - Generic API keys (sk-... / Bearer tokens)
  - IP addresses (IPv4/IPv6)
  - URLs with credentials
  - JWT tokens

Custom patterns are supported via `add_pattern()`.

Quick start
-----------

    from vstack.redaction import (
        Redactor,
        DEFAULT_PATTERNS,
        redact_trace,
    )

    redactor = Redactor(patterns=DEFAULT_PATTERNS)
    safe_trace = redactor.scrub_trace(trace)

    # Or use the convenience function:
    safe_trace = redact_trace(trace)
"""

from __future__ import annotations

from ._redaction import (
    DEFAULT_PATTERNS,
    RedactionPattern,
    Redactor,
    redact_text,
    redact_trace,
)

__all__ = [
    "DEFAULT_PATTERNS",
    "RedactionPattern",
    "Redactor",
    "redact_text",
    "redact_trace",
]
