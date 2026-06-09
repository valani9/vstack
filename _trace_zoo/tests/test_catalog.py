"""Tests for the trace zoo catalog."""

from __future__ import annotations

import pytest

from vstack.aar import AgentTrace
from vstack.trace_zoo import (
    CATALOG,
    TraceInfo,
    get_trace,
    get_trace_info,
    list_traces,
    list_traces_by_category,
    list_traces_by_shape,
)


class TestCatalog:
    def test_catalog_not_empty(self):
        assert len(CATALOG) > 0

    def test_every_entry_is_trace_info(self):
        for info in CATALOG.values():
            assert isinstance(info, TraceInfo)

    def test_every_name_matches_key(self):
        for key, info in CATALOG.items():
            assert info.name == key

    def test_every_trace_builds(self):
        """Every trace builder should return a valid AgentTrace."""
        for name, info in CATALOG.items():
            trace = info.builder()
            assert isinstance(trace, AgentTrace), f"{name} did not return AgentTrace"
            assert trace.goal, f"{name} has empty goal"
            assert len(trace.steps) > 0, f"{name} has no steps"

    def test_every_trace_has_valid_shape(self):
        valid_shapes = {"individual", "team", "org"}
        for info in CATALOG.values():
            assert info.shape in valid_shapes, f"{info.name} has invalid shape {info.shape}"

    def test_every_trace_has_valid_category(self):
        valid_categories = {"reasoning", "coordination", "trust", "workload", "culture"}
        for info in CATALOG.values():
            assert info.category in valid_categories, (
                f"{info.name} has invalid category {info.category}"
            )

    def test_every_trace_has_description(self):
        for info in CATALOG.values():
            assert info.description, f"{info.name} has empty description"


class TestGetTrace:
    def test_get_known_trace(self):
        trace = get_trace("stuck_in_loop")
        assert isinstance(trace, AgentTrace)

    def test_get_unknown_raises_keyerror(self):
        with pytest.raises(KeyError):
            get_trace("nonexistent_trace_name_xyz")

    def test_each_call_returns_fresh_instance(self):
        t1 = get_trace("stuck_in_loop")
        t2 = get_trace("stuck_in_loop")
        # They should be equal in content but separate objects.
        assert t1.goal == t2.goal
        # Mutating one shouldn't affect the other.
        t1.steps.append(t1.steps[0])
        assert len(t1.steps) != len(t2.steps)


class TestGetTraceInfo:
    def test_returns_info(self):
        info = get_trace_info("stuck_in_loop")
        assert info.name == "stuck_in_loop"
        assert info.shape == "individual"
        assert info.category == "reasoning"

    def test_unknown_raises(self):
        with pytest.raises(KeyError):
            get_trace_info("unknown_xyz")


class TestListTraces:
    def test_returns_all(self):
        result = list_traces()
        assert len(result) == len(CATALOG)

    def test_returns_sorted_by_name(self):
        result = list_traces()
        names = [name for name, _ in result]
        assert names == sorted(names)

    def test_each_entry_is_tuple(self):
        for entry in list_traces():
            assert len(entry) == 2
            name, info = entry
            assert isinstance(name, str)
            assert isinstance(info, TraceInfo)


class TestListByCategory:
    def test_reasoning_category(self):
        traces = list_traces_by_category("reasoning")
        for info in traces:
            assert info.category == "reasoning"
        assert len(traces) > 0

    def test_unknown_category_returns_empty(self):
        # Calling with a literal type-violating value still returns empty.
        traces = list_traces_by_category("nonsense")  # type: ignore[arg-type]
        assert traces == []


class TestListByShape:
    def test_individual_shape(self):
        traces = list_traces_by_shape("individual")
        for info in traces:
            assert info.shape == "individual"
        assert len(traces) > 0


class TestSpecificTraces:
    """Sanity checks on individual catalog entries."""

    def test_stuck_in_loop_has_retry_count(self):
        trace = get_trace("stuck_in_loop")
        assert trace.retry_count == 3

    def test_stuck_in_loop_failed(self):
        trace = get_trace("stuck_in_loop")
        assert trace.success is False

    def test_healthy_individual_succeeded(self):
        trace = get_trace("healthy_individual")
        assert trace.success is True

    def test_healthy_individual_has_low_severity(self):
        info = get_trace_info("healthy_individual")
        assert info.expected_severity == "low"

    def test_hallucinated_citation_in_reasoning_category(self):
        info = get_trace_info("hallucinated_citation")
        assert info.category == "reasoning"

    def test_sycophancy_in_trust_category(self):
        info = get_trace_info("sycophancy_drift")
        assert info.category == "trust"

    def test_context_saturation_in_workload(self):
        info = get_trace_info("context_saturation")
        assert info.category == "workload"
