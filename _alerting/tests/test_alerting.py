"""Tests for the alerting module."""

from __future__ import annotations

import io


from vstack.alerting import (
    Alert,
    AlertDispatcher,
    AlertReceipt,
    ConsoleSink,
    EmailSink,
    NullSink,
    PagerDutySink,
    SlackSink,
    WebhookSink,
)
from vstack.alerting._alerting import is_dry_run, set_dry_run


def _make_alert(severity="high"):
    return Alert(
        title="Test alert",
        body="Test body",
        severity=severity,
        source="vstack-test",
    )


class TestAlert:
    def test_default_severity_medium(self):
        a = Alert()
        assert a.severity == "medium"

    def test_to_dict(self):
        a = _make_alert()
        data = a.to_dict()
        assert data["title"] == "Test alert"
        assert data["severity"] == "high"


class TestNullSink:
    def test_always_delivered(self):
        sink = NullSink()
        receipt = sink.send(_make_alert())
        assert receipt.delivered is True


class TestConsoleSink:
    def test_writes_to_stream(self):
        stream = io.StringIO()
        sink = ConsoleSink(stream=stream)
        receipt = sink.send(_make_alert())
        assert receipt.delivered
        assert "HIGH" in stream.getvalue()
        assert "Test alert" in stream.getvalue()

    def test_dry_run_skips_write(self):
        stream = io.StringIO()
        sink = ConsoleSink(stream=stream)
        set_dry_run(True)
        try:
            receipt = sink.send(_make_alert())
            assert receipt.delivered
            assert stream.getvalue() == ""
        finally:
            set_dry_run(False)


class TestSlackSink:
    def test_severity_floor_blocks_low(self):
        sink = SlackSink(severity_floor="high")
        receipt = sink.send(_make_alert(severity="low"))
        assert not receipt.delivered
        assert receipt.error == "below_severity_floor"

    def test_severity_floor_passes_high(self):
        sink = SlackSink(severity_floor="high")
        receipt = sink.send(_make_alert(severity="high"))
        assert receipt.delivered  # default sender None → dry-run-style delivery
        assert receipt.payload is not None

    def test_payload_includes_severity_emoji(self):
        sink = SlackSink()
        receipt = sink.send(_make_alert(severity="critical"))
        text = receipt.payload["text"]
        assert "🚨" in text

    def test_sender_called(self):
        calls = []

        def fake_sender(url, payload):
            calls.append((url, payload))
            return True

        sink = SlackSink(webhook_url="https://example.com/hook", sender=fake_sender)
        receipt = sink.send(_make_alert())
        assert receipt.delivered
        assert calls[0][0] == "https://example.com/hook"

    def test_sender_exception_captured(self):
        def bad_sender(url, payload):
            raise RuntimeError("net down")

        sink = SlackSink(webhook_url="...", sender=bad_sender)
        receipt = sink.send(_make_alert())
        assert not receipt.delivered
        assert "net down" in receipt.error


class TestPagerDutySink:
    def test_default_floor_high(self):
        sink = PagerDutySink()
        # medium should be filtered out by default floor=high.
        receipt = sink.send(_make_alert(severity="medium"))
        assert not receipt.delivered

    def test_critical_mapped(self):
        sink = PagerDutySink()
        receipt = sink.send(_make_alert(severity="critical"))
        assert receipt.delivered
        assert receipt.payload["payload"]["severity"] == "critical"

    def test_high_mapped_to_error(self):
        sink = PagerDutySink()
        receipt = sink.send(_make_alert(severity="high"))
        assert receipt.payload["payload"]["severity"] == "error"

    def test_dedup_key_included(self):
        sink = PagerDutySink()
        receipt = sink.send(_make_alert(severity="high"))
        assert "dedup_key" in receipt.payload


class TestWebhookSink:
    def test_payload_is_full_alert(self):
        sink = WebhookSink(url="https://example.com/hook")
        receipt = sink.send(_make_alert())
        assert receipt.payload["title"] == "Test alert"

    def test_severity_floor(self):
        sink = WebhookSink(severity_floor="critical")
        receipt = sink.send(_make_alert(severity="high"))
        assert not receipt.delivered


class TestEmailSink:
    def test_subject_includes_severity(self):
        sink = EmailSink(from_address="a@x.com", to_addresses=["b@x.com"])
        receipt = sink.send(_make_alert(severity="high"))
        assert "HIGH" in receipt.payload["subject"]
        assert "Test alert" in receipt.payload["subject"]

    def test_to_addresses_propagated(self):
        sink = EmailSink(from_address="a@x.com", to_addresses=["b@x.com", "c@x.com"])
        receipt = sink.send(_make_alert())
        assert "b@x.com" in receipt.payload["to"]
        assert "c@x.com" in receipt.payload["to"]


class TestAlertDispatcher:
    def test_dispatches_to_all_sinks(self):
        d = AlertDispatcher(sinks=[NullSink(), NullSink()])
        receipts = d.dispatch(_make_alert())
        assert len(receipts) == 2

    def test_dispatch_many(self):
        d = AlertDispatcher(sinks=[NullSink()])
        results = d.dispatch_many([_make_alert(), _make_alert()])
        assert len(results) == 2
        assert len(results[0]) == 1

    def test_add_sink_immutable(self):
        d1 = AlertDispatcher(sinks=[NullSink()])
        d2 = d1.add_sink(NullSink())
        assert len(d1.sinks) == 1
        assert len(d2.sinks) == 2

    def test_failed_sink_doesnt_stop_others(self):
        class BadSink:
            @property
            def name(self):
                return "bad"

            def send(self, alert):
                raise ValueError("boom")

        d = AlertDispatcher(sinks=[BadSink(), NullSink()])
        receipts = d.dispatch(_make_alert())
        assert receipts[0].delivered is False
        assert "boom" in receipts[0].error
        assert receipts[1].delivered is True

    def test_retry(self):
        attempts = {"n": 0}

        class FlakeySink:
            @property
            def name(self):
                return "flakey"

            def send(self, alert):
                attempts["n"] += 1
                if attempts["n"] < 3:
                    return AlertReceipt(sink_name="flakey", delivered=False, error="transient")
                return AlertReceipt(sink_name="flakey", delivered=True)

        d = AlertDispatcher(sinks=[FlakeySink()], max_retries_per_sink=2)
        receipts = d.dispatch(_make_alert())
        assert receipts[0].delivered
        assert attempts["n"] == 3

    def test_severity_floor_does_not_retry(self):
        attempts = {"n": 0}

        class CountingSink:
            @property
            def name(self):
                return "counting"

            def send(self, alert):
                attempts["n"] += 1
                return AlertReceipt(
                    sink_name="counting",
                    delivered=False,
                    error="below_severity_floor",
                )

        d = AlertDispatcher(sinks=[CountingSink()], max_retries_per_sink=5)
        d.dispatch(_make_alert())
        # below_severity_floor should short-circuit retries.
        assert attempts["n"] == 1


class TestDryRunMode:
    def test_is_dry_run_false_by_default(self):
        assert not is_dry_run()

    def test_set_dry_run(self):
        set_dry_run(True)
        try:
            assert is_dry_run()
        finally:
            set_dry_run(False)
        assert not is_dry_run()


class TestAlertReceiptSerialization:
    def test_to_dict(self):
        r = AlertReceipt(sink_name="x", delivered=True, duration_ms=100)
        data = r.to_dict()
        assert data["sink_name"] == "x"
        assert data["delivered"] is True
        assert data["duration_ms"] == 100
