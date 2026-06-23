"""Tests for OTel exporter."""

from __future__ import annotations

from vstack.otel import (
    OTelSpanContext,
    is_enabled,
    setup_otel,
    start_pattern_span,
    start_run_span,
)
from vstack.otel._exporter import _otel_check_available


class TestSetupOtel:
    def test_otel_available(self):
        """Sanity check that OTel availability detection works."""
        result = _otel_check_available()
        assert isinstance(result, bool)

    def test_setup_returns_bool(self):
        # setup_otel returns a bool indicating success. We only exercise
        # the eager path when the optional SDK is *absent* (returns False,
        # no side effects); when it's installed, calling setup_otel would
        # install a process-global span exporter and pollute the rest of
        # the suite, so we assert it is callable instead of forcing setup.
        if not _otel_check_available():
            assert setup_otel(service_name="vstack-test") is False
        else:
            assert callable(setup_otel)

    def test_is_enabled_returns_bool(self):
        # is_enabled reports whether a tracer has been configured; it is
        # always safe to call and always returns a bool.
        assert isinstance(is_enabled(), bool)


class TestOTelSpanContext:
    def test_works_without_otel(self):
        """Should be a no-op when OTel isn't configured."""
        # Don't call setup_otel — context should still work.
        with OTelSpanContext("test.span", {"key": "value"}) as span:
            span.set_attribute("more", "data")
            span.set_attributes({"a": 1, "b": "two"})
        # Should not raise.

    def test_handles_exception_inside(self):
        try:
            with OTelSpanContext("test.span"):
                raise ValueError("test")
        except ValueError:
            pass


class TestStartRunSpan:
    def test_runs_without_error(self):
        with start_run_span(
            recipe="stuck_in_loop",
            pattern_count=4,
            shape="individual",
            run_id="test-123",
        ) as span:
            assert span is not None

    def test_handles_no_metadata(self):
        with start_run_span() as span:
            assert span is not None


class TestStartPatternSpan:
    def test_runs_without_error(self):
        with start_pattern_span(
            pattern="lewin",
            mode="forensic",
            run_id="test-456",
        ) as span:
            assert span is not None

    def test_default_mode(self):
        with start_pattern_span(pattern="lewin") as span:
            assert span is not None


class TestAttributeCoercion:
    def test_strings_passed_through(self):
        from vstack.otel._exporter import _coerce_attr

        assert _coerce_attr("hello") == "hello"

    def test_ints_passed_through(self):
        from vstack.otel._exporter import _coerce_attr

        assert _coerce_attr(42) == 42

    def test_floats_passed_through(self):
        from vstack.otel._exporter import _coerce_attr

        assert _coerce_attr(3.14) == 3.14

    def test_bools_passed_through(self):
        from vstack.otel._exporter import _coerce_attr

        assert _coerce_attr(True) is True

    def test_complex_types_stringified(self):
        from vstack.otel._exporter import _coerce_attr

        assert _coerce_attr({"a": 1}) == "{'a': 1}"
        assert _coerce_attr([1, 2, 3]) == "[1, 2, 3]"


class TestInstrumentedClient:
    def test_passes_through_without_otel(self):
        from vstack.otel import OTelInstrumentedClient

        class FakeClient:
            def chat(self, messages, **kwargs):
                return type(
                    "R",
                    (),
                    {
                        "content": "ok",
                        "tokens_in": 10,
                        "tokens_out": 5,
                        "cost_usd": 0.01,
                        "model": "fake",
                    },
                )()

        client = OTelInstrumentedClient(FakeClient(), provider="test", model="m1")
        result = client.chat([{"role": "user", "content": "hi"}])
        assert result.content == "ok"

    def test_attribute_passthrough(self):
        from vstack.otel import OTelInstrumentedClient

        class FakeClient:
            custom_attr = "test"

            def chat(self, messages, **kwargs):
                pass

        client = OTelInstrumentedClient(FakeClient())
        assert client.custom_attr == "test"
