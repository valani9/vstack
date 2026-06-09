"""Tests for the markers module."""

from __future__ import annotations

import pytest

from vstack.markers import (
    CustomMarker,
    Marker,
    analyze_markers,
    attach_marker,
    cost_marker,
    latency_marker,
    quality_marker,
    safety_marker,
)


class TestMarkerConstructors:
    def test_cost_marker(self):
        m = cost_marker(usd=0.01, tokens_in=100, tokens_out=50)
        assert m.kind == "cost"
        assert m.payload["usd"] == 0.01

    def test_latency_marker(self):
        m = latency_marker(ms=500)
        assert m.kind == "latency"
        assert m.payload["ms"] == 500

    def test_quality_marker(self):
        m = quality_marker(score=0.8)
        assert m.kind == "quality"
        assert m.payload["score"] == 0.8

    def test_quality_marker_clamps(self):
        m = quality_marker(score=1.5)
        assert m.payload["score"] == 1.0
        m = quality_marker(score=-0.5)
        assert m.payload["score"] == 0.0

    def test_safety_marker_blocked(self):
        m = safety_marker(blocked=True, reason="dangerous")
        assert m.payload["blocked"] is True
        assert m.payload["reason"] == "dangerous"

    def test_custom_marker(self):
        m = CustomMarker("my_metric", value=42)
        assert m.kind == "custom"
        assert m.payload["name"] == "my_metric"
        assert m.payload["value"] == 42


class TestMarkerSerialization:
    def test_to_dict(self):
        m = cost_marker(usd=0.02)
        data = m.to_dict()
        assert data["kind"] == "cost"
        assert data["usd"] == 0.02

    def test_from_dict_roundtrip(self):
        m = cost_marker(usd=0.02)
        data = m.to_dict()
        m2 = Marker.from_dict(data)
        assert m2.kind == m.kind
        assert m2.payload == m.payload


class TestAttachMarker:
    def test_attach_to_dict_step(self):
        step = {"type": "thought", "content": "x"}
        attach_marker(step, latency_marker(ms=100))
        assert "_vstack_markers" in step
        assert len(step["_vstack_markers"]) == 1

    def test_attach_multiple(self):
        step = {"type": "thought", "content": "x"}
        attach_marker(step, cost_marker(usd=0.01))
        attach_marker(step, latency_marker(ms=50))
        assert len(step["_vstack_markers"]) == 2

    def test_attach_to_object_step(self):
        class FakeStep:
            pass

        step = FakeStep()
        attach_marker(step, latency_marker(ms=200))
        assert hasattr(step, "_vstack_markers")
        assert len(step._vstack_markers) == 1


class TestAnalyzeMarkers:
    def test_empty_trace(self):
        trace = {"steps": []}
        report = analyze_markers(trace)
        assert report.total_cost_usd == 0.0
        assert report.n_steps_analyzed == 0

    def test_cost_aggregation(self):
        trace = {
            "steps": [
                {
                    "type": "thought",
                    "content": "a",
                    "_vstack_markers": [
                        cost_marker(usd=0.01, tokens_in=100, tokens_out=50),
                    ],
                },
                {
                    "type": "thought",
                    "content": "b",
                    "_vstack_markers": [
                        cost_marker(usd=0.02, tokens_in=200, tokens_out=100),
                    ],
                },
            ]
        }
        report = analyze_markers(trace)
        assert report.total_cost_usd == 0.03
        assert report.total_tokens_in == 300
        assert report.total_tokens_out == 150

    def test_latency_aggregation(self):
        trace = {
            "steps": [
                {"_vstack_markers": [latency_marker(ms=100)]},
                {"_vstack_markers": [latency_marker(ms=200)]},
                {"_vstack_markers": [latency_marker(ms=1500)]},
            ]
        }
        report = analyze_markers(trace)
        assert report.total_latency_ms == 1800
        assert report.max_step_latency_ms == 1500
        # Default threshold = 1000 ms.
        assert len(report.slow_steps) == 1
        assert report.slow_steps[0] == 2

    def test_quality_aggregation(self):
        trace = {
            "steps": [
                {"_vstack_markers": [quality_marker(score=0.9)]},
                {"_vstack_markers": [quality_marker(score=0.5)]},
                {"_vstack_markers": [quality_marker(score=0.7)]},
            ]
        }
        report = analyze_markers(trace)
        assert len(report.quality_scores) == 3
        assert report.avg_quality == pytest.approx(0.7)

    def test_safety_aggregation(self):
        trace = {
            "steps": [
                {"_vstack_markers": [safety_marker(blocked=True)]},
                {"_vstack_markers": [safety_marker(blocked=False)]},
                {"_vstack_markers": [safety_marker(blocked=True)]},
            ]
        }
        report = analyze_markers(trace)
        assert report.blocked_step_count == 2

    def test_custom_markers(self):
        trace = {
            "steps": [
                {"_vstack_markers": [CustomMarker("my_metric", value=1)]},
                {"_vstack_markers": [CustomMarker("my_metric", value=2)]},
                {"_vstack_markers": [CustomMarker("other_metric", value=3)]},
            ]
        }
        report = analyze_markers(trace)
        assert "my_metric" in report.custom_markers
        assert len(report.custom_markers["my_metric"]) == 2
        assert "other_metric" in report.custom_markers

    def test_multiple_markers_per_step(self):
        trace = {
            "steps": [
                {
                    "_vstack_markers": [
                        cost_marker(usd=0.01),
                        latency_marker(ms=50),
                        quality_marker(score=0.8),
                    ]
                },
            ]
        }
        report = analyze_markers(trace)
        assert report.total_cost_usd == 0.01
        assert report.total_latency_ms == 50
        assert report.quality_scores == [0.8]

    def test_custom_slow_threshold(self):
        trace = {
            "steps": [
                {"_vstack_markers": [latency_marker(ms=300)]},
                {"_vstack_markers": [latency_marker(ms=600)]},
            ]
        }
        report = analyze_markers(trace, slow_step_threshold_ms=500)
        assert len(report.slow_steps) == 1
        assert report.slow_steps[0] == 1

    def test_to_dict(self):
        trace = {"steps": [{"_vstack_markers": [cost_marker(usd=0.01)]}]}
        report = analyze_markers(trace)
        data = report.to_dict()
        assert "total_cost_usd" in data
        assert "n_steps_analyzed" in data


class TestN_steps_analyzed:
    def test_counts_all_steps_with_or_without_markers(self):
        trace = {
            "steps": [
                {"type": "x", "_vstack_markers": [cost_marker(usd=0.01)]},
                {"type": "y"},
                {"type": "z", "_vstack_markers": [latency_marker(ms=100)]},
            ]
        }
        report = analyze_markers(trace)
        assert report.n_steps_analyzed == 3
