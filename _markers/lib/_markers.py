"""Marker primitives and trace-step analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

MarkerKind = Literal["cost", "latency", "quality", "safety", "custom"]


@dataclass
class Marker:
    """A typed annotation on a trace step.

    Markers don't change analytical semantics; they're metadata
    that vstack analyzers can read when present.
    """

    kind: MarkerKind
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, **self.payload}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Marker:
        kind = data["kind"]
        payload = {k: v for k, v in data.items() if k != "kind"}
        return cls(kind=kind, payload=payload)


def cost_marker(*, usd: float, tokens_in: int = 0, tokens_out: int = 0) -> Marker:
    return Marker(
        kind="cost",
        payload={
            "usd": usd,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
        },
    )


def latency_marker(*, ms: int) -> Marker:
    return Marker(kind="latency", payload={"ms": ms})


def quality_marker(*, score: float, source: str = "human") -> Marker:
    """A quality marker. score is 0.0-1.0."""
    return Marker(
        kind="quality",
        payload={"score": max(0.0, min(1.0, score)), "source": source},
    )


def safety_marker(*, blocked: bool, reason: str = "") -> Marker:
    return Marker(
        kind="safety",
        payload={"blocked": blocked, "reason": reason},
    )


class CustomMarker(Marker):
    """A user-defined marker. Subclass to type-narrow your own."""

    def __init__(self, name: str, **payload: Any):
        super().__init__(kind="custom", payload={"name": name, **payload})


_MARKERS_ATTR = "_vstack_markers"


def attach_marker(step: Any, marker: Marker) -> None:
    """Attach a marker to a trace step.

    The marker is stored on the step's ``_vstack_markers`` list.
    Steps that don't have a markers list get one initialized.
    """
    markers = _get_markers_list(step)
    markers.append(marker)
    # Try to write the list back if the step doesn't have it.
    if not _has_markers_attribute(step):
        _set_markers_list(step, markers)


def get_markers(step: Any) -> list[Marker]:
    return _get_markers_list(step)


def _has_markers_attribute(step: Any) -> bool:
    if isinstance(step, dict):
        return _MARKERS_ATTR in step
    return hasattr(step, _MARKERS_ATTR)


def _get_markers_list(step: Any) -> list[Marker]:
    if isinstance(step, dict):
        return step.setdefault(_MARKERS_ATTR, [])
    try:
        return getattr(step, _MARKERS_ATTR)
    except AttributeError:
        # Attempt to set; if frozen pydantic, will raise.
        try:
            setattr(step, _MARKERS_ATTR, [])
            return getattr(step, _MARKERS_ATTR)
        except Exception:
            return []


def _set_markers_list(step: Any, markers: list[Marker]) -> None:
    if isinstance(step, dict):
        step[_MARKERS_ATTR] = markers
        return
    try:
        setattr(step, _MARKERS_ATTR, markers)
    except Exception:
        pass


@dataclass
class MarkerAnalysisReport:
    """Aggregated analysis of markers across all trace steps."""

    total_cost_usd: float = 0.0
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_latency_ms: int = 0
    max_step_latency_ms: int = 0
    slow_steps: list[int] = field(default_factory=list)  # step indices > p95
    quality_scores: list[float] = field(default_factory=list)
    blocked_step_count: int = 0
    custom_markers: dict[str, list[Any]] = field(default_factory=dict)
    n_steps_analyzed: int = 0

    @property
    def avg_quality(self) -> float:
        if not self.quality_scores:
            return 0.0
        return sum(self.quality_scores) / len(self.quality_scores)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_cost_usd": self.total_cost_usd,
            "total_tokens_in": self.total_tokens_in,
            "total_tokens_out": self.total_tokens_out,
            "total_latency_ms": self.total_latency_ms,
            "max_step_latency_ms": self.max_step_latency_ms,
            "slow_step_count": len(self.slow_steps),
            "avg_quality": self.avg_quality,
            "blocked_step_count": self.blocked_step_count,
            "custom_markers": {k: list(v) for k, v in self.custom_markers.items()},
            "n_steps_analyzed": self.n_steps_analyzed,
        }


def analyze_markers(
    trace: Any,
    *,
    slow_step_threshold_ms: int = 1000,
) -> MarkerAnalysisReport:
    """Aggregate markers across all trace steps."""
    report = MarkerAnalysisReport()

    steps = _get_steps(trace)
    report.n_steps_analyzed = len(steps)

    latencies: list[int] = []

    for i, step in enumerate(steps):
        markers = _get_markers_list(step)
        for m in markers:
            if m.kind == "cost":
                report.total_cost_usd += m.payload.get("usd", 0.0)
                report.total_tokens_in += m.payload.get("tokens_in", 0)
                report.total_tokens_out += m.payload.get("tokens_out", 0)
            elif m.kind == "latency":
                ms = m.payload.get("ms", 0)
                report.total_latency_ms += ms
                if ms > report.max_step_latency_ms:
                    report.max_step_latency_ms = ms
                latencies.append(ms)
                if ms >= slow_step_threshold_ms:
                    report.slow_steps.append(i)
            elif m.kind == "quality":
                report.quality_scores.append(m.payload.get("score", 0.0))
            elif m.kind == "safety":
                if m.payload.get("blocked"):
                    report.blocked_step_count += 1
            elif m.kind == "custom":
                name = m.payload.get("name", "unknown")
                report.custom_markers.setdefault(name, []).append(m.payload)

    return report


def _get_steps(trace: Any) -> list[Any]:
    if isinstance(trace, dict):
        return list(trace.get("steps", []))
    if hasattr(trace, "steps"):
        return list(trace.steps)
    return []
