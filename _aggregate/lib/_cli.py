"""vstack-aggregate CLI — roll up many diagnose reports into a fleet summary.

Reads a JSON file (or stdin) containing a list of reports — or an object with a
``reports`` key — and prints the top patterns, top agents, and severity
distribution. Pass ``--json`` for machine-readable output.

This module wires the public ``vstack.aggregate`` functions to a shell surface.
It adds no business logic and changes no library behavior.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, cast

from . import (
    aggregate_reports,
    severity_distribution,
    top_n_agents,
    top_n_patterns,
)


class _CLIError(Exception):
    """Raised for user-facing errors (bad input/usage). Maps to exit code 2."""


def _read_raw(source: str) -> str:
    """Read raw text from a path, or from stdin when ``source`` is '-'."""
    if source == "-":
        return sys.stdin.read()
    path = Path(source)
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise _CLIError(f"input file not found: {source}") from exc
    except OSError as exc:
        raise _CLIError(f"could not read input file {source}: {exc}") from exc


def _load_reports(source: str) -> list[Any]:
    """Load a JSON list of reports from a path or stdin ('-').

    Accepts either a top-level JSON array, or an object with a ``reports`` key
    holding an array (matching the house scorecard convention).
    """
    raw = _read_raw(source)
    try:
        data: object = json.loads(raw)
    except json.JSONDecodeError as exc:
        loc = source if source != "-" else "<stdin>"
        raise _CLIError(f"invalid JSON in {loc}: {exc}") from exc

    if isinstance(data, dict) and "reports" in data:
        reports = data["reports"]
        if not isinstance(reports, list):
            raise _CLIError("the 'reports' key must hold a JSON array")
        return reports
    if isinstance(data, list):
        return data
    raise _CLIError("expected a JSON array of reports, or an object with a 'reports' array")


def _build_payload(reports: list[Any], top: int) -> dict[str, Any]:
    """Compute the full machine-readable payload from the public API."""
    summary = aggregate_reports(reports)
    return {
        "total_reports": summary.total_reports,
        "total_findings": summary.total_findings,
        "unique_patterns": summary.unique_patterns,
        "top_patterns": [
            {"pattern": pattern, "count": count}
            for pattern, count in top_n_patterns(reports, n=top)
        ],
        "top_agents": [
            {"agent_id": agent, "count": count} for agent, count in top_n_agents(reports, n=top)
        ],
        "severity_distribution": severity_distribution(reports),
    }


def _render_text(payload: dict[str, Any], top: int) -> str:
    """Render the human-readable report."""
    lines: list[str] = []
    lines.append("Aggregate report summary")
    lines.append("========================")
    lines.append(f"Reports:         {payload['total_reports']}")
    lines.append(f"Total findings:  {payload['total_findings']}")
    lines.append(f"Unique patterns: {payload['unique_patterns']}")
    lines.append("")

    lines.append(f"Top {top} patterns")
    lines.append("-" * 14)
    top_patterns = cast(list[dict[str, Any]], payload["top_patterns"])
    if top_patterns:
        for entry in top_patterns:
            lines.append(f"  {entry['count']:>6}  {entry['pattern']}")
    else:
        lines.append("  (none)")
    lines.append("")

    lines.append(f"Top {top} agents")
    lines.append("-" * 12)
    top_agents = cast(list[dict[str, Any]], payload["top_agents"])
    if top_agents:
        for entry in top_agents:
            lines.append(f"  {entry['count']:>6}  {entry['agent_id']}")
    else:
        lines.append("  (none)")
    lines.append("")

    lines.append("Severity distribution")
    lines.append("---------------------")
    dist = cast(dict[str, int], payload["severity_distribution"])
    for severity in ("high", "medium", "low"):
        lines.append(f"  {severity:<8} {dist.get(severity, 0)}")
    # Surface any non-standard severity buckets the library recorded.
    for severity in sorted(dist):
        if severity not in ("high", "medium", "low"):
            lines.append(f"  {severity:<8} {dist[severity]}")

    return "\n".join(lines)


def _write_output(text: str, out: str | None) -> None:
    """Write ``text`` to ``--out`` (or stdout when ``out`` is None or '-')."""
    if out is None or out == "-":
        print(text)
        return
    try:
        Path(out).write_text(text + "\n", encoding="utf-8")
    except OSError as exc:
        raise _CLIError(f"could not write output file {out}: {exc}") from exc
    print(f"Wrote aggregate summary to {out}", file=sys.stderr)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vstack-aggregate",
        description=(
            "Roll up multiple diagnose reports into a fleet-level summary: "
            "top patterns, noisiest agents, and severity distribution."
        ),
    )
    parser.add_argument(
        "--reports",
        default="-",
        help=(
            "Path to a JSON file with a list of reports (or an object with a "
            "'reports' array). Use '-' for stdin. Default: stdin."
        ),
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        metavar="N",
        help="Show the top N patterns and agents. Default: 10.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit machine-readable JSON instead of a text report.",
    )
    parser.add_argument(
        "--out",
        help="Write output to this path instead of stdout. Use '-' for stdout.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``vstack-aggregate`` console script.

    Returns 0 on success and 2 on usage/validation errors. User errors are
    reported as a clear message on stderr; no raw traceback is shown.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.top < 1:
        print("error: --top must be a positive integer", file=sys.stderr)
        return 2

    try:
        reports = _load_reports(args.reports)
        payload = _build_payload(reports, args.top)
        if args.as_json:
            text = json.dumps(payload, indent=2)
        else:
            text = _render_text(payload, args.top)
        _write_output(text, args.out)
    except _CLIError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
