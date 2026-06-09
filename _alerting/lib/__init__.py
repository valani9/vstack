"""vstack.alerting — multi-channel alert dispatching.

The alerting module ships pluggable sinks for delivering vstack
findings as alerts across multiple channels:

  - **SlackSink** — POST a webhook-formatted message.
  - **PagerDutySink** — emit an Events API v2 payload.
  - **WebhookSink** — generic JSON POST.
  - **EmailSink** — assemble an RFC 5322 envelope.
  - **ConsoleSink** — print to stdout (debugging).
  - **NullSink** — no-op (testing).

All sinks share a common ``AlertSink`` protocol; ``AlertDispatcher``
fans out a single alert across many sinks with per-sink filters,
retry, and a thread-local dry-run mode for tests.

Quick start
-----------

    from vstack.alerting import (
        Alert,
        AlertDispatcher,
        SlackSink,
        PagerDutySink,
        ConsoleSink,
    )

    dispatcher = AlertDispatcher(sinks=[
        SlackSink(webhook_url="https://hooks.slack.com/services/..."),
        PagerDutySink(routing_key="...", severity_floor="high"),
        ConsoleSink(),
    ])

    alert = Alert(
        title="High-severity Lewin finding",
        body="...",
        severity="high",
        source="vstack",
    )
    receipts = dispatcher.dispatch(alert)
    for r in receipts:
        print(r.sink_name, r.delivered)
"""

from __future__ import annotations

from ._alerting import (
    Alert,
    AlertDispatcher,
    AlertReceipt,
    AlertSink,
    ConsoleSink,
    EmailSink,
    NullSink,
    PagerDutySink,
    SlackSink,
    WebhookSink,
)

__all__ = [
    "Alert",
    "AlertDispatcher",
    "AlertReceipt",
    "AlertSink",
    "ConsoleSink",
    "EmailSink",
    "NullSink",
    "PagerDutySink",
    "SlackSink",
    "WebhookSink",
]
