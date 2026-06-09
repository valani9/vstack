"""Heatmap grid construction + ASCII/HTML rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ASCII intensity ramp — chars from low to high.
_ASCII_RAMP = "·░▒▓█"

# Severity weights for cell intensity.
_SEVERITY_WEIGHT = {"high": 3, "medium": 2, "low": 1, "none": 0}


@dataclass
class HeatmapCell:
    """One cell in a heatmap grid."""

    row_label: str
    col_label: str
    value: float
    n_findings: int = 0


@dataclass
class HeatmapGrid:
    """A 2D grid of HeatmapCells."""

    row_labels: list[str] = field(default_factory=list)
    col_labels: list[str] = field(default_factory=list)
    cells: dict[tuple[str, str], HeatmapCell] = field(default_factory=dict)
    title: str = ""

    def get(self, row: str, col: str) -> HeatmapCell:
        key = (row, col)
        if key in self.cells:
            return self.cells[key]
        return HeatmapCell(row_label=row, col_label=col, value=0.0)

    def max_value(self) -> float:
        if not self.cells:
            return 0.0
        return max(c.value for c in self.cells.values())

    def min_value(self) -> float:
        if not self.cells:
            return 0.0
        return min(c.value for c in self.cells.values())


def _get_findings(report: Any) -> list[Any]:
    if isinstance(report, dict):
        return list(report.get("findings", []))
    if hasattr(report, "findings"):
        return list(report.findings)
    return []


def _get_pattern(finding: Any) -> str:
    if isinstance(finding, dict):
        return finding.get("pattern", "unknown")
    return getattr(finding, "pattern", "unknown")


def _get_severity(finding: Any) -> str:
    if isinstance(finding, dict):
        return finding.get("severity", "low")
    return getattr(finding, "severity", "low")


# Pattern → dimension mapping (subset of vstack.scorecard mapping).
_PATTERN_DIMENSIONS = {
    "lewin": "reasoning",
    "goleman_ei": "trust",
    "johari": "reasoning",
    "danva_emotion": "trust",
    "cognitive_reappraisal": "workload",
    "yerkes_dodson": "workload",
    "hexaco": "trust",
    "grant_strengths": "reasoning",
    "motivation_traps": "reasoning",
    "sdt_reward": "workload",
    "mcgregor": "coordination",
    "vroom_expectancy": "workload",
    "grpi": "coordination",
    "process_gain_loss": "coordination",
    "social_loafing": "coordination",
    "superflocks": "coordination",
    "lencioni": "trust",
    "trust_triangle": "trust",
    "mcallister_trust": "trust",
    "psych_safety": "trust",
    "glaser_conversation": "coordination",
    "feedback_triggers": "trust",
    "plus_delta": "coordination",
    "smart_goal": "coordination",
    "group_decision": "coordination",
    "debate_pathology": "reasoning",
    "bias_stack": "reasoning",
    "devils_advocate": "reasoning",
    "thomas_kilmann": "trust",
    "aar": "reasoning",
    "schein_culture": "culture",
    "robbins_culture": "culture",
    "org_structure": "coordination",
    "span_of_control": "coordination",
}


def build_pattern_dimension_grid(reports: list[Any]) -> HeatmapGrid:
    """Build a pattern × dimension grid from a list of reports.

    Each cell value is the sum of severity weights for findings
    matching that (pattern, dimension) intersection.
    """
    patterns_seen: set[str] = set()
    dimensions = ["reasoning", "coordination", "trust", "workload", "culture"]

    accumulator: dict[tuple[str, str], list[int]] = {}
    for report in reports:
        for finding in _get_findings(report):
            pattern = _get_pattern(finding)
            dim = _PATTERN_DIMENSIONS.get(pattern)
            if dim is None:
                continue
            patterns_seen.add(pattern)
            sev = _get_severity(finding)
            weight = _SEVERITY_WEIGHT.get(sev, 0)
            key = (pattern, dim)
            accumulator.setdefault(key, []).append(weight)

    cells: dict[tuple[str, str], HeatmapCell] = {}
    for (pattern, dim), weights in accumulator.items():
        cells[(pattern, dim)] = HeatmapCell(
            row_label=pattern,
            col_label=dim,
            value=float(sum(weights)),
            n_findings=len(weights),
        )

    return HeatmapGrid(
        row_labels=sorted(patterns_seen),
        col_labels=dimensions,
        cells=cells,
        title="Pattern × Dimension Heatmap",
    )


def build_pattern_trace_grid(
    reports: list[Any],
    *,
    trace_names: list[str] | None = None,
) -> HeatmapGrid:
    """Build a pattern × trace grid showing severity weight per (pattern, trace)."""
    patterns_seen: set[str] = set()
    accumulator: dict[tuple[str, str], list[int]] = {}

    if trace_names is None:
        trace_names = [f"trace-{i}" for i in range(len(reports))]

    for i, report in enumerate(reports):
        trace_name = trace_names[i] if i < len(trace_names) else f"trace-{i}"
        for finding in _get_findings(report):
            pattern = _get_pattern(finding)
            patterns_seen.add(pattern)
            sev = _get_severity(finding)
            weight = _SEVERITY_WEIGHT.get(sev, 0)
            key = (pattern, trace_name)
            accumulator.setdefault(key, []).append(weight)

    cells: dict[tuple[str, str], HeatmapCell] = {}
    for (pattern, trace_name), weights in accumulator.items():
        cells[(pattern, trace_name)] = HeatmapCell(
            row_label=pattern,
            col_label=trace_name,
            value=float(sum(weights)),
            n_findings=len(weights),
        )

    return HeatmapGrid(
        row_labels=sorted(patterns_seen),
        col_labels=trace_names,
        cells=cells,
        title="Pattern × Trace Heatmap",
    )


def _intensity_char(value: float, max_value: float) -> str:
    if max_value == 0 or value == 0:
        return " "
    norm = value / max_value
    idx = min(len(_ASCII_RAMP) - 1, int(norm * len(_ASCII_RAMP)))
    return _ASCII_RAMP[idx]


def render_heatmap(grid: HeatmapGrid, *, cell_width: int = 4) -> str:
    """Render the grid as ASCII art."""
    lines = []
    if grid.title:
        lines.append(f"=== {grid.title} ===")
        lines.append("")

    if not grid.row_labels or not grid.col_labels:
        lines.append("(empty grid)")
        return "\n".join(lines)

    max_row_label_width = max(len(r) for r in grid.row_labels)

    # Header row.
    header = " " * (max_row_label_width + 2)
    for col in grid.col_labels:
        header += col[:cell_width].center(cell_width)
    lines.append(header)

    # Separator.
    sep = " " * (max_row_label_width + 1) + "+" + ("-" * cell_width) * len(grid.col_labels)
    lines.append(sep)

    max_v = grid.max_value()
    for row in grid.row_labels:
        line = f"{row:>{max_row_label_width}} |"
        for col in grid.col_labels:
            cell = grid.get(row, col)
            ch = _intensity_char(cell.value, max_v)
            line += ch * cell_width
        lines.append(line)

    lines.append("")
    lines.append(f"Legend: ' '=0, '{_ASCII_RAMP[0]}'=low, '{_ASCII_RAMP[-1]}'=max ({max_v:.0f})")

    return "\n".join(lines)


def _hsl_for_value(value: float, max_value: float) -> str:
    """Generate an HSL color for a cell value (green low → red high)."""
    if max_value == 0:
        return "hsl(0, 0%, 95%)"
    norm = min(1.0, value / max_value)
    # Hue from 120 (green) to 0 (red).
    hue = int(120 - 120 * norm)
    return f"hsl({hue}, 70%, 55%)"


def render_heatmap_html(grid: HeatmapGrid, *, cell_size: int = 50) -> str:
    """Render the grid as an HTML table with color cells."""
    if not grid.row_labels or not grid.col_labels:
        return "<p>Empty grid.</p>"

    max_v = grid.max_value()
    lines = [
        '<table style="border-collapse: collapse; font-family: monospace;">',
    ]

    # Header row.
    lines.append("<tr><th></th>")
    for col in grid.col_labels:
        lines.append(
            f'<th style="padding: 8px; min-width: {cell_size}px; '
            f'border: 1px solid #444; background: #222; color: #ddd;">{col}</th>'
        )
    lines.append("</tr>")

    # Data rows.
    for row in grid.row_labels:
        lines.append(
            f'<tr><th style="padding: 8px; text-align: right; '
            f'border: 1px solid #444; background: #222; color: #ddd;">{row}</th>'
        )
        for col in grid.col_labels:
            cell = grid.get(row, col)
            color = _hsl_for_value(cell.value, max_v)
            n = cell.n_findings
            content = f"{cell.value:.0f}" if cell.value > 0 else "&nbsp;"
            title = f"{row} × {col}: {n} finding(s)"
            lines.append(
                f'<td style="padding: 8px; text-align: center; min-width: {cell_size}px; '
                f'border: 1px solid #444; background: {color}; color: #000;" '
                f'title="{title}">{content}</td>'
            )
        lines.append("</tr>")

    lines.append("</table>")
    return "\n".join(lines)
