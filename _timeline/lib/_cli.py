"""vstack-timeline CLI — chronological bucketed view of findings.

Reads a JSON report (a ``DiagnoseReport``-shaped object with a ``findings`` key,
or a bare list of findings) from a file or stdin, buckets the findings by time,
and renders the result as either a Markdown timeline or a compact ASCII
sparkline. This is a thin shell over the public ``vstack.timeline`` functions;
it adds no business logic and changes no library behavior.

Each finding is expected to carry a ``timestamp`` (epoch seconds) and a
``severity`` (``high`` / ``medium`` / ``low``); findings without a positive
timestamp are ignored by the underlying ``build_timeline``.

Examples
--------

    vstack-timeline --reports reports.json
    vstack-timeline --reports reports.json --format sparkline
    vstack-timeline --reports reports.json --bucket day --out timeline.md
    cat reports.json | vstack-timeline --format markdown
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast, get_args

from ._timeline import (
    BucketGranularity,
    build_timeline,
    render_markdown_timeline,
    render_sparkline,
)

_FORMATS = ("markdown", "sparkline")
_BUCKETS: tuple[str, ...] = get_args(BucketGranularity)


def _read_input(source: str) -> str:
    """Read raw text from a file path or, when ``source`` is ``-``, from stdin."""
    if source == "-":
        return sys.stdin.read()
    path = Path(source)
    if not path.is_file():
        raise FileNotFoundError(f"reports file not found: {source}")
    return path.read_text(encoding="utf-8")


def _parse_findings(raw: str, *, source: str) -> list[Any]:
    """Parse raw JSON into a list of findings the timeline functions accept.

    Accepts a bare JSON array of findings, a report dict with a ``findings``
    key, or a dict with a ``reports`` key holding a list of findings. Anything
    else is a usage error.
    """
    try:
        data: Any = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {source}: {exc}") from exc

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("findings", "reports"):
            if key in data:
                value = data[key]
                if not isinstance(value, list):
                    raise ValueError(
                        f"'{key}' in {source} must be a JSON array, got {type(value).__name__}"
                    )
                return value
        raise ValueError(
            f"JSON object in {source} has no 'findings' or 'reports' key; "
            "expected a report dict or a list of findings"
        )
    raise ValueError(f"expected a JSON object or array in {source}, got {type(data).__name__}")


def _render(findings: list[Any], fmt: str, bucket: BucketGranularity) -> str:
    """Render the findings in the requested format via the public functions."""
    timeline = build_timeline(findings, bucket=bucket)
    if fmt == "markdown":
        return render_markdown_timeline(timeline)
    if fmt == "sparkline":
        return render_sparkline(timeline)
    # Unreachable: argparse constrains --format to _FORMATS.
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
        prog="vstack-timeline",
        description=(
            "Render a chronological, time-bucketed view of vstack findings "
            "as a Markdown timeline or a compact ASCII sparkline."
        ),
    )
    parser.add_argument(
        "--reports",
        default="-",
        metavar="PATH",
        help="Path to the reports JSON (a dict with 'findings'/'reports', or a "
        "list of findings). Use '-' or omit to read from stdin.",
    )
    parser.add_argument(
        "--format",
        choices=_FORMATS,
        default="markdown",
        help="Output format. Default: markdown.",
    )
    parser.add_argument(
        "--bucket",
        choices=_BUCKETS,
        default="hour",
        help="Time-bucket granularity. Default: hour.",
    )
    parser.add_argument(
        "--out",
        metavar="PATH",
        help="Write output to this file. Omit (or use '-') to write to stdout.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the ``vstack-timeline`` CLI.

    Returns 0 on success, 2 on usage / validation / input errors.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    bucket = cast(BucketGranularity, args.bucket)

    try:
        raw = _read_input(args.reports)
        findings = _parse_findings(raw, source=args.reports)
        rendered = _render(findings, args.format, bucket)
    except (FileNotFoundError, ValueError) as exc:
        print(f"vstack-timeline: error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"vstack-timeline: error: {exc}", file=sys.stderr)
        return 2

    try:
        _write_output(rendered, args.out)
    except OSError as exc:
        print(f"vstack-timeline: error: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
