"""Tests for the heatmap module."""

from __future__ import annotations


from vstack.heatmap import (
    HeatmapCell,
    HeatmapGrid,
    build_pattern_dimension_grid,
    build_pattern_trace_grid,
    render_heatmap,
    render_heatmap_html,
)


def _r(findings):
    return {"findings": findings}


def _f(pattern, severity):
    return {"pattern": pattern, "severity": severity, "title": "test"}


class TestHeatmapCell:
    def test_default_value_zero(self):
        cell = HeatmapCell(row_label="a", col_label="b", value=0.0)
        assert cell.value == 0.0
        assert cell.n_findings == 0


class TestHeatmapGrid:
    def test_empty_grid_max_zero(self):
        grid = HeatmapGrid()
        assert grid.max_value() == 0.0

    def test_get_returns_zero_for_unknown(self):
        grid = HeatmapGrid()
        cell = grid.get("x", "y")
        assert cell.value == 0.0

    def test_max_value(self):
        grid = HeatmapGrid(
            cells={
                ("a", "b"): HeatmapCell("a", "b", 5.0),
                ("c", "d"): HeatmapCell("c", "d", 10.0),
            }
        )
        assert grid.max_value() == 10.0


class TestBuildPatternDimensionGrid:
    def test_empty_reports(self):
        grid = build_pattern_dimension_grid([])
        assert grid.col_labels == ["reasoning", "coordination", "trust", "workload", "culture"]
        assert len(grid.cells) == 0

    def test_single_high_finding(self):
        report = _r([_f("lewin", "high")])
        grid = build_pattern_dimension_grid([report])
        # lewin → reasoning, weight=3 for high.
        cell = grid.get("lewin", "reasoning")
        assert cell.value == 3.0
        assert cell.n_findings == 1

    def test_multiple_severities(self):
        report = _r(
            [
                _f("lewin", "high"),
                _f("lewin", "medium"),
                _f("lewin", "low"),
            ]
        )
        grid = build_pattern_dimension_grid([report])
        cell = grid.get("lewin", "reasoning")
        # high=3 + medium=2 + low=1 = 6.
        assert cell.value == 6.0
        assert cell.n_findings == 3

    def test_multiple_patterns(self):
        report = _r(
            [
                _f("lewin", "high"),
                _f("aar", "medium"),
            ]
        )
        grid = build_pattern_dimension_grid([report])
        assert "lewin" in grid.row_labels
        assert "aar" in grid.row_labels

    def test_unknown_pattern_skipped(self):
        report = _r([_f("nonexistent_pattern", "high")])
        grid = build_pattern_dimension_grid([report])
        # Unknown pattern has no dim mapping.
        assert "nonexistent_pattern" not in grid.row_labels


class TestBuildPatternTraceGrid:
    def test_basic(self):
        reports = [
            _r([_f("lewin", "high")]),
            _r([_f("lewin", "medium")]),
        ]
        grid = build_pattern_trace_grid(
            reports,
            trace_names=["trace-A", "trace-B"],
        )
        assert grid.get("lewin", "trace-A").value == 3.0
        assert grid.get("lewin", "trace-B").value == 2.0

    def test_default_trace_names(self):
        reports = [_r([_f("lewin", "high")])]
        grid = build_pattern_trace_grid(reports)
        assert grid.col_labels == ["trace-0"]


class TestRenderHeatmapAscii:
    def test_renders_title(self):
        grid = HeatmapGrid(
            row_labels=["lewin"],
            col_labels=["reasoning"],
            cells={("lewin", "reasoning"): HeatmapCell("lewin", "reasoning", 3.0, 1)},
            title="Test",
        )
        out = render_heatmap(grid)
        assert "Test" in out

    def test_renders_legend(self):
        grid = HeatmapGrid(
            row_labels=["lewin"],
            col_labels=["reasoning"],
            cells={("lewin", "reasoning"): HeatmapCell("lewin", "reasoning", 3.0, 1)},
        )
        out = render_heatmap(grid)
        assert "Legend" in out

    def test_empty_grid(self):
        grid = HeatmapGrid()
        out = render_heatmap(grid)
        assert "empty" in out.lower()


class TestRenderHeatmapHtml:
    def test_renders_table(self):
        grid = HeatmapGrid(
            row_labels=["lewin"],
            col_labels=["reasoning"],
            cells={("lewin", "reasoning"): HeatmapCell("lewin", "reasoning", 3.0, 1)},
        )
        html = render_heatmap_html(grid)
        assert "<table" in html
        assert "lewin" in html
        assert "reasoning" in html

    def test_renders_colored_cell(self):
        grid = HeatmapGrid(
            row_labels=["lewin"],
            col_labels=["reasoning"],
            cells={("lewin", "reasoning"): HeatmapCell("lewin", "reasoning", 3.0, 1)},
        )
        html = render_heatmap_html(grid)
        assert "hsl(" in html

    def test_empty_html(self):
        grid = HeatmapGrid()
        html = render_heatmap_html(grid)
        assert "Empty" in html


class TestEndToEnd:
    def test_pipeline(self):
        reports = [
            _r([_f("lewin", "high"), _f("aar", "medium")]),
            _r([_f("grpi", "high"), _f("trust_triangle", "low")]),
        ]
        grid = build_pattern_dimension_grid(reports)
        ascii_out = render_heatmap(grid)
        html_out = render_heatmap_html(grid)
        assert "lewin" in ascii_out
        assert "grpi" in html_out
