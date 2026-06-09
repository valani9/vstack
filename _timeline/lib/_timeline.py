"""Timeline construction + sparkline rendering."""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Literal


BucketGranularity = Literal["minute", "hour", "day", "week"]

_GRANULARITY_SECONDS = {
    "minute": 60.0,
    "hour": 3600.0,
    "day": 86400.0,
    "week": 86400.0 * 7,
}

_SPARKLINE_CHARS = "▁▂▃▄▅▆▇█"


@dataclass
class Bucket:
    """One time bucket on a Timeline."""

    start_ts: float
    end_ts: float
    high: int = 0
    medium: int = 0
    low: int = 0

    @property
    def total(self) -> int:
        return self.high + self.medium + self.low

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_ts": self.start_ts,
            "end_ts": self.end_ts,
            "high": self.high,
            "medium": self.medium,
            "low": self.low,
            "total": self.total,
        }

    def label(self, granularity: BucketGranularity = "hour") -> str:
        """Human-readable label for the bucket (UTC)."""
        dt = datetime.fromtimestamp(self.start_ts, tz=timezone.utc)
        if granularity == "minute":
            return dt.strftime("%H:%M")
        if granularity == "hour":
            return dt.strftime("%Y-%m-%d %H:00")
        if granularity == "day":
            return dt.strftime("%Y-%m-%d")
        if granularity == "week":
            return dt.strftime("%Y-W%V")
        return dt.isoformat()


@dataclass
class Timeline:
    """A bucketed timeline of findings."""

    granularity: BucketGranularity = "hour"
    buckets: list[Bucket] = field(default_factory=list)

    @property
    def bucket_seconds(self) -> float:
        return _GRANULARITY_SECONDS[self.granularity]

    @property
    def total_findings(self) -> int:
        return sum(b.total for b in self.buckets)

    @property
    def total_high(self) -> int:
        return sum(b.high for b in self.buckets)

    @property
    def peak_bucket(self) -> Bucket | None:
        if not self.buckets:
            return None
        return max(self.buckets, key=lambda b: b.total)

    def velocity_per_period(self) -> float:
        """Mean findings per bucket."""
        if not self.buckets:
            return 0.0
        return statistics.mean(b.total for b in self.buckets)

    def velocity_per_minute(self) -> float:
        return self.velocity_per_period() * 60.0 / self.bucket_seconds

    def velocity_per_hour(self) -> float:
        return self.velocity_per_period() * 3600.0 / self.bucket_seconds

    def velocity_per_day(self) -> float:
        return self.velocity_per_period() * 86400.0 / self.bucket_seconds

    def quiet_buckets(self) -> int:
        """Count of buckets with zero findings."""
        return sum(1 for b in self.buckets if b.total == 0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "granularity": self.granularity,
            "buckets": [b.to_dict() for b in self.buckets],
            "total_findings": self.total_findings,
            "total_high": self.total_high,
            "velocity_per_hour": self.velocity_per_hour(),
            "velocity_per_day": self.velocity_per_day(),
            "quiet_buckets": self.quiet_buckets(),
        }

    def to_markdown(self) -> str:
        return render_markdown_timeline(self)


def _get_timestamp(finding: Any) -> float:
    if isinstance(finding, dict):
        ts = finding.get("timestamp", 0.0)
    else:
        ts = getattr(finding, "timestamp", 0.0)
    try:
        return float(ts)
    except (TypeError, ValueError):
        return 0.0


def _get_severity(finding: Any) -> str:
    if isinstance(finding, dict):
        return finding.get("severity", "low")
    return getattr(finding, "severity", "low")


def _floor_to_bucket(ts: float, granularity: BucketGranularity) -> float:
    """Floor a timestamp to the start of its bucket (UTC)."""
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    if granularity == "minute":
        dt = dt.replace(second=0, microsecond=0)
    elif granularity == "hour":
        dt = dt.replace(minute=0, second=0, microsecond=0)
    elif granularity == "day":
        dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    elif granularity == "week":
        dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        # Week start = Monday.
        dt -= timedelta(days=dt.weekday())
    return dt.timestamp()


def build_timeline(
    findings: list[Any],
    *,
    bucket: BucketGranularity = "hour",
    start_ts: float | None = None,
    end_ts: float | None = None,
    fill_empty: bool = True,
) -> Timeline:
    """Bucket findings into a Timeline."""
    if not findings:
        return Timeline(granularity=bucket, buckets=[])

    timestamps = [_get_timestamp(f) for f in findings if _get_timestamp(f) > 0]
    if not timestamps:
        return Timeline(granularity=bucket, buckets=[])

    start = start_ts if start_ts is not None else min(timestamps)
    end = end_ts if end_ts is not None else max(timestamps)

    start_floor = _floor_to_bucket(start, bucket)
    end_floor = _floor_to_bucket(end, bucket)
    seconds = _GRANULARITY_SECONDS[bucket]

    # Build empty buckets.
    bucket_map: dict[float, Bucket] = {}
    current = start_floor
    while current <= end_floor:
        bucket_map[current] = Bucket(start_ts=current, end_ts=current + seconds)
        current += seconds

    # Fill with findings.
    for finding in findings:
        ts = _get_timestamp(finding)
        if ts <= 0:
            continue
        bucket_start = _floor_to_bucket(ts, bucket)
        b = bucket_map.get(bucket_start)
        if b is None:
            continue
        sev = _get_severity(finding)
        if sev == "high":
            b.high += 1
        elif sev == "medium":
            b.medium += 1
        else:
            b.low += 1

    buckets = sorted(bucket_map.values(), key=lambda b: b.start_ts)

    if not fill_empty:
        buckets = [b for b in buckets if b.total > 0]

    return Timeline(granularity=bucket, buckets=buckets)


def _to_sparkline_char(value: int, max_value: int) -> str:
    if max_value <= 0:
        return _SPARKLINE_CHARS[0]
    if value <= 0:
        return _SPARKLINE_CHARS[0]
    norm = value / max_value
    idx = min(len(_SPARKLINE_CHARS) - 1, int(norm * (len(_SPARKLINE_CHARS) - 1)))
    return _SPARKLINE_CHARS[idx]


def render_sparkline(timeline: Timeline) -> str:
    """Render the timeline as a compact ASCII sparkline."""
    if not timeline.buckets:
        return "(empty)"
    max_val = max(b.total for b in timeline.buckets)
    return "".join(_to_sparkline_char(b.total, max_val) for b in timeline.buckets)


def render_markdown_timeline(timeline: Timeline) -> str:
    """Render the timeline as a Markdown table."""
    lines = [f"# Timeline ({timeline.granularity})", ""]
    lines.append(
        f"Total: **{timeline.total_findings}** findings  |  "
        f"High: **{timeline.total_high}**  |  "
        f"Quiet buckets: {timeline.quiet_buckets()}"
    )
    lines.append("")
    lines.append(f"Sparkline: `{render_sparkline(timeline)}`")
    lines.append("")

    if not timeline.buckets:
        lines.append("_No data._")
        return "\n".join(lines)

    peak = timeline.peak_bucket
    if peak and peak.total > 0:
        lines.append(f"**Peak**: {peak.label(timeline.granularity)} — {peak.total} findings")
        lines.append("")

    lines.append("| Period | High | Med | Low | Total |")
    lines.append("|--------|-----:|----:|----:|------:|")
    for b in timeline.buckets:
        if b.total == 0:
            continue
        lines.append(
            f"| {b.label(timeline.granularity)} | {b.high} | {b.medium} | {b.low} | {b.total} |"
        )

    lines.append("")
    lines.append(
        f"_Velocity: {timeline.velocity_per_hour():.2f}/hr, {timeline.velocity_per_day():.2f}/day_"
    )

    return "\n".join(lines)
