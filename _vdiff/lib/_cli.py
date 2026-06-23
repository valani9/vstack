"""vstack-vdiff CLI — diff two DiagnoseReports and surface what changed.

Loads two ``DiagnoseReport``-shaped JSON files (a ``--before`` report and an
``--after`` report), computes the delta with the public ``diff_reports``
function, and prints what changed: findings added / removed, severity shifts,
intervention changes, plus the per-pattern set delta. This is the "did the new
pattern version / model / release regress?" check.

It is a thin shell over the public ``vstack.vdiff`` API; it adds no business
logic and changes no library behavior. Human-readable Markdown is printed by
default; ``--json`` emits the machine-readable delta.

Examples
--------

    vstack-vdiff --before before.json --after after.json
    vstack-vdiff --before before.json --after after.json --json
    cat after.json | vstack-vdiff --before before.json --after -
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ._diff import diff_reports


def _read_input(source: str) -> str:
    """Read raw text from a file path or, when ``source`` is ``-``, from stdin."""
    if source == "-":
        return sys.stdin.read()
    path = Path(source)
    if not path.is_file():
        raise FileNotFoundError(f"report file not found: {source}")
    return path.read_text(encoding="utf-8")


def _parse_report(raw: str, *, source: str) -> dict[str, Any]:
    """Parse raw JSON text into a report object ``diff_reports`` accepts.

    A report is a JSON object (a ``DiagnoseReport``-shaped dict, typically with
    ``findings`` and ``per_pattern`` keys). Anything else is a usage error.
    """
    try:
        data: Any = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {source}: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(
            f"expected a JSON object (DiagnoseReport) in {source}, got {type(data).__name__}"
        )
    return data


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vstack-vdiff",
        description=(
            "Diff two DiagnoseReports and print the delta: findings added / "
            "removed / changed, severity shifts, and per-pattern set changes. "
            "The 'did this version regress?' check."
        ),
    )
    parser.add_argument(
        "--before",
        required=True,
        metavar="PATH",
        help="Path to the BEFORE report JSON. Use '-' to read from stdin.",
    )
    parser.add_argument(
        "--after",
        required=True,
        metavar="PATH",
        help="Path to the AFTER report JSON. Use '-' to read from stdin.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit the delta as machine-readable JSON instead of Markdown.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``vstack-vdiff`` CLI.

    Returns 0 on success, 2 on usage / validation / input errors.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.before == "-" and args.after == "-":
        print(
            "vstack-vdiff: error: only one of --before/--after may read from stdin ('-')",
            file=sys.stderr,
        )
        return 2

    try:
        before = _parse_report(_read_input(args.before), source=args.before)
        after = _parse_report(_read_input(args.after), source=args.after)
    except (FileNotFoundError, ValueError) as exc:
        print(f"vstack-vdiff: error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"vstack-vdiff: error: {exc}", file=sys.stderr)
        return 2

    delta = diff_reports(before, after)

    if args.as_json:
        rendered = json.dumps(delta.to_dict(), indent=2)
    else:
        rendered = delta.to_markdown()

    try:
        sys.stdout.write(rendered)
        if not rendered.endswith("\n"):
            sys.stdout.write("\n")
    except OSError as exc:
        print(f"vstack-vdiff: error: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
