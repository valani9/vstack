"""vstack.heatmap — ASCII heatmap visualization for finding distributions.

The heatmap module renders pattern × dimension heatmaps for
fleet-wide diagnostics. ASCII output works in terminals, log
aggregators, and markdown contexts.

Quick start
-----------

    from vstack.heatmap import (
        build_pattern_dimension_grid,
        render_heatmap,
    )

    # Build a grid from multiple reports:
    grid = build_pattern_dimension_grid(reports)

    # Render to ASCII:
    print(render_heatmap(grid))
"""

from __future__ import annotations

from ._heatmap import (
    HeatmapCell,
    HeatmapGrid,
    build_pattern_dimension_grid,
    build_pattern_trace_grid,
    render_heatmap,
    render_heatmap_html,
)

__all__ = [
    "HeatmapCell",
    "HeatmapGrid",
    "build_pattern_dimension_grid",
    "build_pattern_trace_grid",
    "render_heatmap",
    "render_heatmap_html",
]
