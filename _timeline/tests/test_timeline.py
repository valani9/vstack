"""Tests for the timeline module."""

from __future__ import annotations

from datetime import datetime, timezone


from vstack.timeline import (
    Bucket,
    Timeline,
    build_timeline,
    render_markdown_timeline,
    render_sparkline,
)


def _ts(year=2026, month=1, day=1, hour=0, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc).timestamp()


def _f(severity="high", timestamp=None):
    return {
        "pattern": "test",
        "severity": severity,
        "timestamp": timestamp if timestamp is not None else _ts(),
    }


class TestBucket:
    def test_total_sums_severities(self):
        b = Bucket(start_ts=0, end_ts=3600, high=2, medium=1, low=3)
        assert b.total == 6

    def test_label_hour(self):
        b = Bucket(start_ts=_ts(2026, 6, 9, 14), end_ts=0)
        assert b.label("hour") == "2026-06-09 14:00"

    def test_label_day(self):
        b = Bucket(start_ts=_ts(2026, 6, 9), end_ts=0)
        assert b.label("day") == "2026-06-09"


class TestBuildTimeline:
    def test_empty_findings(self):
        tl = build_timeline([])
        assert tl.total_findings == 0
        assert tl.buckets == []

    def test_findings_without_timestamps(self):
        tl = build_timeline([{"severity": "high"}])
        assert tl.buckets == []

    def test_single_finding(self):
        tl = build_timeline([_f("high", _ts())])
        assert len(tl.buckets) == 1
        assert tl.buckets[0].high == 1

    def test_findings_in_same_bucket(self):
        ts = _ts(2026, 1, 1, 14)
        tl = build_timeline(
            [
                _f("high", ts),
                _f("medium", ts + 60),
                _f("low", ts + 120),
            ],
            bucket="hour",
        )
        assert len(tl.buckets) == 1
        assert tl.buckets[0].high == 1
        assert tl.buckets[0].medium == 1
        assert tl.buckets[0].low == 1
        assert tl.buckets[0].total == 3

    def test_findings_in_different_buckets(self):
        ts1 = _ts(2026, 1, 1, 14)
        ts2 = _ts(2026, 1, 1, 15)
        tl = build_timeline([_f("high", ts1), _f("high", ts2)], bucket="hour")
        # Should have 2 buckets.
        non_empty = [b for b in tl.buckets if b.total > 0]
        assert len(non_empty) == 2

    def test_fill_empty_inserts_zero_buckets(self):
        ts1 = _ts(2026, 1, 1, 14)
        ts2 = _ts(2026, 1, 1, 17)  # 3 hours later
        tl = build_timeline([_f("high", ts1), _f("high", ts2)], bucket="hour")
        # Should have 4 buckets (14, 15, 16, 17), 2 with findings.
        assert len(tl.buckets) == 4
        assert tl.quiet_buckets() == 2

    def test_no_fill_empty_skips_zero_buckets(self):
        ts1 = _ts(2026, 1, 1, 14)
        ts2 = _ts(2026, 1, 1, 17)
        tl = build_timeline(
            [_f("high", ts1), _f("high", ts2)],
            bucket="hour",
            fill_empty=False,
        )
        assert len(tl.buckets) == 2

    def test_day_granularity(self):
        tl = build_timeline(
            [
                _f("high", _ts(2026, 1, 1, 9)),
                _f("high", _ts(2026, 1, 1, 18)),
            ],
            bucket="day",
        )
        # Same day = 1 bucket.
        assert len(tl.buckets) == 1
        assert tl.buckets[0].total == 2

    def test_custom_start_end(self):
        ts = _ts(2026, 1, 1, 14)
        tl = build_timeline(
            [_f("high", ts)],
            bucket="hour",
            start_ts=_ts(2026, 1, 1, 12),
            end_ts=_ts(2026, 1, 1, 16),
        )
        # 12, 13, 14, 15, 16 = 5 buckets.
        assert len(tl.buckets) == 5


class TestVelocity:
    def test_velocity_per_period(self):
        tl = build_timeline(
            [
                _f("high", _ts(2026, 1, 1, 14)),
                _f("high", _ts(2026, 1, 1, 14)),
                _f("high", _ts(2026, 1, 1, 15)),
            ],
            bucket="hour",
        )
        # 2 buckets: 14 (2 findings), 15 (1 finding) = mean 1.5.
        assert tl.velocity_per_period() == 1.5

    def test_velocity_per_hour_with_hour_bucket(self):
        tl = build_timeline([_f("high", _ts(2026, 1, 1, 14))], bucket="hour")
        # 1 finding in 1 hour bucket = 1.0/hr.
        assert tl.velocity_per_hour() == 1.0

    def test_velocity_per_day_with_hour_bucket(self):
        tl = build_timeline([_f("high", _ts(2026, 1, 1, 14))], bucket="hour")
        # 1.0/hr × 24 = 24/day.
        assert tl.velocity_per_day() == 24.0

    def test_empty_velocity(self):
        tl = Timeline()
        assert tl.velocity_per_period() == 0.0


class TestPeakBucket:
    def test_peak_returns_highest_total(self):
        tl = build_timeline(
            [
                _f("high", _ts(2026, 1, 1, 14)),
                _f("high", _ts(2026, 1, 1, 15)),
                _f("high", _ts(2026, 1, 1, 15)),
            ],
            bucket="hour",
        )
        peak = tl.peak_bucket
        assert peak.total == 2

    def test_peak_empty(self):
        tl = Timeline()
        assert tl.peak_bucket is None


class TestSparkline:
    def test_empty(self):
        assert render_sparkline(Timeline()) == "(empty)"

    def test_uniform_buckets(self):
        tl = build_timeline(
            [
                _f("high", _ts(2026, 1, 1, 14)),
                _f("high", _ts(2026, 1, 1, 15)),
            ],
            bucket="hour",
        )
        sp = render_sparkline(tl)
        assert len(sp) == len(tl.buckets)

    def test_zero_value_shows_lowest_char(self):
        tl = build_timeline([_f("high", _ts(2026, 1, 1, 14))], bucket="hour")
        # Single bucket.
        sp = render_sparkline(tl)
        # Should have at least one non-empty char.
        assert sp != ""


class TestMarkdownRender:
    def test_empty(self):
        md = render_markdown_timeline(Timeline())
        assert "Timeline" in md
        assert "No data" in md

    def test_non_empty(self):
        tl = build_timeline([_f("high", _ts(2026, 1, 1, 14))], bucket="hour")
        md = render_markdown_timeline(tl)
        assert "Total" in md
        assert "Sparkline" in md
        assert "Period" in md


class TestSerialization:
    def test_to_dict(self):
        tl = build_timeline([_f("high", _ts(2026, 1, 1, 14))], bucket="hour")
        data = tl.to_dict()
        assert "granularity" in data
        assert "total_findings" in data
        assert "buckets" in data

    def test_bucket_to_dict(self):
        b = Bucket(start_ts=0, end_ts=3600, high=1, medium=2, low=3)
        data = b.to_dict()
        assert data["total"] == 6


class TestAggregates:
    def test_total_high(self):
        tl = build_timeline(
            [
                _f("high", _ts(2026, 1, 1, 14)),
                _f("high", _ts(2026, 1, 1, 14)),
                _f("low", _ts(2026, 1, 1, 14)),
            ],
            bucket="hour",
        )
        assert tl.total_high == 2

    def test_quiet_buckets(self):
        ts1 = _ts(2026, 1, 1, 10)
        ts2 = _ts(2026, 1, 1, 15)
        tl = build_timeline([_f("high", ts1), _f("high", ts2)], bucket="hour")
        # Buckets 10, 11, 12, 13, 14, 15 = 6 total; 4 quiet.
        assert tl.quiet_buckets() == 4
