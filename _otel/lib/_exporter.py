"""OTel exporter setup + span helpers.

The module is structured so it gracefully degrades when OTel isn't
installed. All public functions are safe to call without OTel.
"""

from __future__ import annotations

from contextlib import AbstractContextManager, contextmanager
from types import TracebackType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator

    from opentelemetry.trace import Span, Tracer

# Lazy import — OTel is optional.
_tracer: Tracer | None = None
_otel_available: bool | None = None


def _otel_check_available() -> bool:
    global _otel_available
    if _otel_available is not None:
        return _otel_available
    try:
        import opentelemetry.trace  # noqa: F401

        _otel_available = True
    except ImportError:
        _otel_available = False
    return _otel_available


def setup_otel(
    *,
    service_name: str = "vstack",
    otlp_endpoint: str | None = None,
    additional_attributes: dict[str, str] | None = None,
) -> bool:
    """Configure OpenTelemetry for vstack.

    Returns True if OTel was configured successfully, False if OTel
    isn't installed.

    Args:
        service_name: The OTel service.name attribute.
        otlp_endpoint: Optional OTLP gRPC endpoint
            (e.g., "http://otel-collector:4317"). If not provided,
            falls back to the OTEL_EXPORTER_OTLP_ENDPOINT env var.
        additional_attributes: Extra resource attributes to attach
            to every span (e.g., {"env": "prod", "version": "1.2.3"}).
    """
    global _tracer

    if not _otel_check_available():
        return False

    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor,
        ConsoleSpanExporter,
    )

    attrs = {"service.name": service_name}
    if additional_attributes:
        attrs.update(additional_attributes)
    resource = Resource.create(attrs)
    provider = TracerProvider(resource=resource)

    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )

            exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        except ImportError:
            # OTLP exporter not installed — fall back to console.
            exporter = ConsoleSpanExporter()
    else:
        exporter = ConsoleSpanExporter()

    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer("vstack")
    return True


def is_enabled() -> bool:
    """True if OTel has been configured."""
    return _tracer is not None


class OTelSpanContext:
    """Context manager wrapping an OTel span.

    Safe to use even if OTel isn't configured (becomes a no-op).
    """

    def __init__(self, name: str, attributes: dict[str, Any] | None = None):
        self.name = name
        self.attributes = attributes or {}
        self._span: Span | None = None
        self._cm: AbstractContextManager[Span] | None = None

    def __enter__(self) -> OTelSpanContext:
        if _tracer is None:
            return self

        self._cm = _tracer.start_as_current_span(self.name)
        self._span = self._cm.__enter__()
        for k, v in self.attributes.items():
            self._span.set_attribute(k, _coerce_attr(v))
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._cm is not None:
            if self._span is not None and exc_val is not None:
                self._span.record_exception(exc_val)
            self._cm.__exit__(exc_type, exc_val, exc_tb)

    def set_attribute(self, key: str, value: Any) -> None:
        if self._span is not None:
            self._span.set_attribute(key, _coerce_attr(value))

    def set_attributes(self, attrs: dict[str, Any]) -> None:
        if self._span is not None:
            for k, v in attrs.items():
                self._span.set_attribute(k, _coerce_attr(v))


def _coerce_attr(value: Any) -> Any:
    """Coerce attribute value to an OTel-compatible primitive."""
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


@contextmanager
def start_run_span(
    *,
    recipe: str | None = None,
    pattern_count: int | None = None,
    shape: str | None = None,
    run_id: str | None = None,
) -> Iterator[OTelSpanContext]:
    """Start a span for a diagnose() run."""
    attrs: dict[str, Any] = {"vstack.span_type": "run"}
    if recipe:
        attrs["vstack.recipe"] = recipe
    if pattern_count is not None:
        attrs["vstack.pattern_count"] = pattern_count
    if shape:
        attrs["vstack.shape"] = shape
    if run_id:
        attrs["vstack.run_id"] = run_id

    with OTelSpanContext("vstack.diagnose", attrs) as span:
        yield span


@contextmanager
def start_pattern_span(
    *,
    pattern: str,
    mode: str = "standard",
    run_id: str | None = None,
) -> Iterator[OTelSpanContext]:
    """Start a span for a single pattern analyzer call."""
    attrs: dict[str, Any] = {
        "vstack.span_type": "pattern",
        "vstack.pattern": pattern,
        "vstack.mode": mode,
    }
    if run_id:
        attrs["vstack.run_id"] = run_id

    with OTelSpanContext(f"vstack.pattern.{pattern}", attrs) as span:
        yield span


@contextmanager
def start_llm_span(
    *,
    provider: str | None = None,
    model: str | None = None,
) -> Iterator[OTelSpanContext]:
    """Start a span for a single LLM call (child of a pattern span)."""
    attrs: dict[str, Any] = {"vstack.span_type": "llm_call"}
    if provider:
        attrs["vstack.llm.provider"] = provider
    if model:
        attrs["vstack.llm.model"] = model

    with OTelSpanContext("vstack.llm.chat", attrs) as span:
        yield span
