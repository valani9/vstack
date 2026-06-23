"""vstack-heatmap CLI — build + render a severity heatmap from diagnose reports.

Reads a JSON list of ``DiagnoseReport``-shaped objects (each a dict with a
``findings`` key, or the wrapper form ``{"reports": [...]}``) from a file or
stdin, builds either a pattern x dimension or pattern x trace grid, and renders
it as ASCII or an HTML table. This is a thin shell over the public
``vstack.heatmap`` functions; it adds no business logic and changes no library
behavior.

Examples
--------

    vstack-heatmap --reports reports.json
    vstack-heatmap --reports reports.json --by trace --format html --out grid.html
    cat reports.json | vstack-heatmap --reports - --by dimension

"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ._heatmap import (
    HeatmapGrid,
    build_pattern_dimension_grid,
    build_pattern_trace_grid,
    render_heatmap,
    render_heatmap_html,
)

_BY_CHOICES = ("dimension", "trace")
_FORMAT_CHOICES = ("ascii", "html")


def _read_input(source: str) -> str:
    """Read raw text from a file path or, when ``source`` is ``-``, from stdin."""
    if source == "-":
        return sys.stdin.read()
    path = Path(source)
    if not path.is_file():
        raise FileNotFoundError(f"reports file not found: {source}")
    return path.read_text(encoding="utf-8")


def _parse_reports(raw: str, *, source: str) -> list[Any]:
    """Parse raw JSON into the list of reports the builders accept.

    Accepts a bare JSON array of reports, or a wrapper object of the form
    ``{"reports": [...]}``. Anything else is a usage error.
    """
    try:
        data: Any = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {source}: {exc}") from exc

    if isinstance(data, dict):
        if "reports" not in data:
            raise ValueError(
                f"JSON object in {source} has no 'reports' key; "
                "expected a list of reports or a {{'reports': [...]}} wrapper"
            )
        reports = data["reports"]
        if not isinstance(reports, list):
            raise ValueError(f"'reports' in {source} must be a JSON array")
        return list(reports)
    if isinstance(data, list):
        return data
    raise ValueError(f"expected a JSON array or object in {source}, got {type(data).__name__}")


def _parse_trace_names(spec: str | None) -> list[str] | None:
    """Parse the optional comma-separated --trace-names spec into a list."""
    if spec is None:
        return None
    names = [n.strip() for n in spec.split(",")]
    if not all(names):
        raise ValueError("--trace-names must be non-empty, comma-separated labels")
    return names


def _build_grid(reports: list[Any], *, by: str, trace_names: list[str] | None) -> HeatmapGrid:
    """Build the requested grid via the public builder functions."""
    if by == "dimension":
        return build_pattern_dimension_grid(reports)
    if by == "trace":
        return build_pattern_trace_grid(reports, trace_names=trace_names)
    # Unreachable: argparse constrains --by to _BY_CHOICES.
    raise ValueError(f"unknown grid axis: {by}")


def _render(grid: HeatmapGrid, fmt: str) -> str:
    """Render the grid in the requested format via the public render functions."""
    if fmt == "ascii":
        return render_heatmap(grid)
    if fmt == "html":
        return render_heatmap_html(grid)
    # Unreachable: argparse constrains --format to _FORMAT_CHOICES.
    raise ValueError(f"unknown format: {fmt}")


def _write_output(text: str, out: str | None) -> None:
    """Write rendered text to ``out`` (a path) or stdout when ``out`` is None."""
    if out is None or out == "-":
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")
        return
    Path(out).write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    print(f"Wrote {out}", file=sys.stderr)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vstack-heatmap",
        description=(
            "Build and render a severity heatmap from vstack diagnose reports. "
            "Rows are patterns; columns are dimensions or traces."
        ),
    )
    parser.add_argument(
        "--reports",
        default="-",
        metavar="PATH",
        help="Path to reports JSON (a list of reports, or a {'reports': [...]} "
        "wrapper). Use '-' or omit to read from stdin.",
    )
    parser.add_argument(
        "--by",
        choices=_BY_CHOICES,
        default="dimension",
        help="Column axis: 'dimension' (pattern x dimension) or 'trace' "
        "(pattern x trace). Default: dimension.",
    )
    parser.add_argument(
        "--format",
        choices=_FORMAT_CHOICES,
        default="ascii",
        help="Output format. Default: ascii.",
    )
    parser.add_argument(
        "--trace-names",
        metavar="A,B,C",
        help="Comma-separated trace labels (only used with --by trace). One per "
        "report, in order. Defaults to trace-0, trace-1, ...",
    )
    parser.add_argument(
        "--out",
        metavar="PATH",
        help="Write output to this file. Omit (or use '-') to write to stdout.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the ``vstack-heatmap`` CLI.

    Returns 0 on success, 2 on usage / validation / input errors.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        trace_names = _parse_trace_names(args.trace_names)
        raw = _read_input(args.reports)
        reports = _parse_reports(raw, source=args.reports)
        grid = _build_grid(reports, by=args.by, trace_names=trace_names)
        rendered = _render(grid, args.format)
    except (FileNotFoundError, ValueError) as exc:
        print(f"vstack-heatmap: error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"vstack-heatmap: error: {exc}", file=sys.stderr)
        return 2

    try:
        _write_output(rendered, args.out)
    except OSError as exc:
        print(f"vstack-heatmap: error: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
