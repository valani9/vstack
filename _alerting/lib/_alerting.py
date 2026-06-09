"""Alert primitives + sink protocol + built-in sinks + dispatcher."""

from __future__ import annotations

import contextvars
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol


_SEVERITY_RANK = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


# Thread-local dry-run mode. When True, sinks must not perform
# actual I/O; they should just record the payload.
_dry_run: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "_vstack_alerting_dry_run", default=False
)


def is_dry_run() -> bool:
    return _dry_run.get()


def set_dry_run(value: bool) -> None:
    _dry_run.set(value)


@dataclass
class Alert:
    """A single alert to be dispatched."""

    title: str = ""
    body: str = ""
    severity: str = "medium"
    source: str = "vstack"
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)
    finding: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "body": self.body,
            "severity": self.severity,
            "source": self.source,
            "timestamp": self.timestamp,
            "metadata": dict(self.metadata),
            "finding": dict(self.finding) if self.finding else None,
        }


@dataclass
class AlertReceipt:
    """Result of dispatching one alert through one sink."""

    sink_name: str
    delivered: bool
    payload: dict[str, Any] | None = None
    error: str | None = None
    duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "sink_name": self.sink_name,
            "delivered": self.delivered,
            "payload": self.payload,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


class AlertSink(Protocol):
    """Protocol every alert sink implements."""

    @property
    def name(self) -> str: ...

    def send(self, alert: Alert) -> AlertReceipt:  # pragma: no cover - protocol stub
        ...


@dataclass
class NullSink:
    """No-op sink. Always succeeds. Useful for tests."""

    _name: str = "null"

    @property
    def name(self) -> str:
        return self._name

    def send(self, alert: Alert) -> AlertReceipt:
        return AlertReceipt(sink_name=self.name, delivered=True)


@dataclass
class ConsoleSink:
    """Print alerts to stdout. Always 'delivered'."""

    _name: str = "console"
    stream: Any = None
    """File-like object; defaults to sys.stdout."""

    @property
    def name(self) -> str:
        return self._name

    def send(self, alert: Alert) -> AlertReceipt:
        stream = self.stream if self.stream is not None else sys.stdout
        line = f"[{alert.severity.upper()}] {alert.source} :: {alert.title}\n  {alert.body}"
        if not is_dry_run():
            try:
                stream.write(line + "\n")
                stream.flush()
            except Exception as exc:
                return AlertReceipt(sink_name=self.name, delivered=False, error=str(exc))
        return AlertReceipt(
            sink_name=self.name,
            delivered=True,
            payload={"text": line},
        )


@dataclass
class SlackSink:
    """Build a Slack-webhook payload for an alert.

    Network I/O is delegated to ``sender`` so the sink is testable
    without a real Slack webhook.
    """

    webhook_url: str = ""
    severity_floor: str = "low"
    sender: Callable[[str, dict[str, Any]], bool] | None = None
    """Callable(url, payload) → bool. None = default (no real send)."""

    _name: str = "slack"

    @property
    def name(self) -> str:
        return self._name

    def _build_payload(self, alert: Alert) -> dict[str, Any]:
        emoji = {
            "critical": "🚨",
            "high": "🔴",
            "medium": "🟡",
            "low": "🔵",
            "info": "ℹ️",
        }.get(alert.severity, "⚪")
        return {
            "text": f"{emoji} *[{alert.severity.upper()}]* {alert.title}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{emoji} *[{alert.severity.upper()}]* {alert.title}",
                    },
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": alert.body},
                },
            ],
        }

    def send(self, alert: Alert) -> AlertReceipt:
        if _SEVERITY_RANK.get(alert.severity, 0) < _SEVERITY_RANK.get(self.severity_floor, 0):
            return AlertReceipt(sink_name=self.name, delivered=False, error="below_severity_floor")

        payload = self._build_payload(alert)

        if is_dry_run() or self.sender is None:
            return AlertReceipt(sink_name=self.name, delivered=True, payload=payload)

        try:
            ok = self.sender(self.webhook_url, payload)
            return AlertReceipt(sink_name=self.name, delivered=bool(ok), payload=payload)
        except Exception as exc:
            return AlertReceipt(
                sink_name=self.name, delivered=False, payload=payload, error=str(exc)
            )


@dataclass
class PagerDutySink:
    """Build a PagerDuty Events API v2 payload."""

    routing_key: str = ""
    severity_floor: str = "high"
    sender: Callable[[str, dict[str, Any]], bool] | None = None
    _name: str = "pagerduty"

    @property
    def name(self) -> str:
        return self._name

    def _build_payload(self, alert: Alert) -> dict[str, Any]:
        # Map vstack severity → PD severity (pd: critical/error/warning/info).
        pd_sev = {
            "critical": "critical",
            "high": "error",
            "medium": "warning",
            "low": "info",
            "info": "info",
        }.get(alert.severity, "warning")
        return {
            "routing_key": self.routing_key,
            "event_action": "trigger",
            "dedup_key": f"vstack:{alert.source}:{alert.title[:64]}",
            "payload": {
                "summary": alert.title,
                "source": alert.source,
                "severity": pd_sev,
                "custom_details": {
                    "body": alert.body,
                    "metadata": alert.metadata,
                },
            },
        }

    def send(self, alert: Alert) -> AlertReceipt:
        if _SEVERITY_RANK.get(alert.severity, 0) < _SEVERITY_RANK.get(self.severity_floor, 0):
            return AlertReceipt(sink_name=self.name, delivered=False, error="below_severity_floor")

        payload = self._build_payload(alert)
        url = "https://events.pagerduty.com/v2/enqueue"

        if is_dry_run() or self.sender is None:
            return AlertReceipt(sink_name=self.name, delivered=True, payload=payload)

        try:
            ok = self.sender(url, payload)
            return AlertReceipt(sink_name=self.name, delivered=bool(ok), payload=payload)
        except Exception as exc:
            return AlertReceipt(
                sink_name=self.name, delivered=False, payload=payload, error=str(exc)
            )


@dataclass
class WebhookSink:
    """Generic JSON-POST webhook sink."""

    url: str = ""
    severity_floor: str = "low"
    extra_headers: dict[str, str] = field(default_factory=dict)
    sender: Callable[[str, dict[str, Any]], bool] | None = None
    _name: str = "webhook"

    @property
    def name(self) -> str:
        return self._name

    def send(self, alert: Alert) -> AlertReceipt:
        if _SEVERITY_RANK.get(alert.severity, 0) < _SEVERITY_RANK.get(self.severity_floor, 0):
            return AlertReceipt(sink_name=self.name, delivered=False, error="below_severity_floor")

        payload = alert.to_dict()

        if is_dry_run() or self.sender is None:
            return AlertReceipt(sink_name=self.name, delivered=True, payload=payload)

        try:
            ok = self.sender(self.url, payload)
            return AlertReceipt(sink_name=self.name, delivered=bool(ok), payload=payload)
        except Exception as exc:
            return AlertReceipt(
                sink_name=self.name, delivered=False, payload=payload, error=str(exc)
            )


@dataclass
class EmailSink:
    """Assemble RFC 5322 email envelope for an alert.

    Does not send; emits the envelope as the payload so a downstream
    transport (SES, SMTP, Postmark) can dispatch.
    """

    from_address: str = ""
    to_addresses: list[str] = field(default_factory=list)
    subject_prefix: str = "[vstack] "
    severity_floor: str = "low"
    sender: Callable[[dict[str, Any]], bool] | None = None
    _name: str = "email"

    @property
    def name(self) -> str:
        return self._name

    def _build_payload(self, alert: Alert) -> dict[str, Any]:
        subject = f"{self.subject_prefix}[{alert.severity.upper()}] {alert.title}"
        return {
            "from": self.from_address,
            "to": list(self.to_addresses),
            "subject": subject,
            "body": alert.body,
            "headers": {
                "X-vstack-severity": alert.severity,
                "X-vstack-source": alert.source,
            },
        }

    def send(self, alert: Alert) -> AlertReceipt:
        if _SEVERITY_RANK.get(alert.severity, 0) < _SEVERITY_RANK.get(self.severity_floor, 0):
            return AlertReceipt(sink_name=self.name, delivered=False, error="below_severity_floor")

        payload = self._build_payload(alert)

        if is_dry_run() or self.sender is None:
            return AlertReceipt(sink_name=self.name, delivered=True, payload=payload)

        try:
            ok = self.sender(payload)
            return AlertReceipt(sink_name=self.name, delivered=bool(ok), payload=payload)
        except Exception as exc:
            return AlertReceipt(
                sink_name=self.name, delivered=False, payload=payload, error=str(exc)
            )


@dataclass
class AlertDispatcher:
    """Fan out an alert across multiple sinks."""

    sinks: list[AlertSink] = field(default_factory=list)
    max_retries_per_sink: int = 0

    def add_sink(self, sink: AlertSink) -> AlertDispatcher:
        return AlertDispatcher(
            sinks=[*self.sinks, sink],
            max_retries_per_sink=self.max_retries_per_sink,
        )

    def dispatch(self, alert: Alert) -> list[AlertReceipt]:
        receipts = []
        for sink in self.sinks:
            receipt = self._send_with_retry(sink, alert)
            receipts.append(receipt)
        return receipts

    def dispatch_many(self, alerts: list[Alert]) -> list[list[AlertReceipt]]:
        return [self.dispatch(a) for a in alerts]

    def _send_with_retry(self, sink: AlertSink, alert: Alert) -> AlertReceipt:
        last_receipt: AlertReceipt | None = None
        attempts = self.max_retries_per_sink + 1
        for attempt in range(attempts):
            start = time.time()
            try:
                receipt = sink.send(alert)
            except Exception as exc:
                receipt = AlertReceipt(
                    sink_name=getattr(sink, "name", "unknown"),
                    delivered=False,
                    error=str(exc),
                )
            receipt.duration_ms = int((time.time() - start) * 1000)
            last_receipt = receipt
            if receipt.delivered or receipt.error == "below_severity_floor":
                break
        assert last_receipt is not None
        return last_receipt
