"""vstack-export CLI — convert a diagnose report / findings JSON to another format.

Reads a JSON report (a ``DiagnoseReport``-shaped object with a ``findings`` key,
or a bare list of findings) from a file or stdin, and emits it in the requested
format. This is a thin shell over the public ``vstack.export`` functions; it adds
no business logic and changes no library behavior.

Examples
--------

    vstack-export --report report.json --format markdown
    vstack-export --report report.json --format github --out comment.md
    cat report.json | vstack-export --format csv
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ._export import (
    export_csv,
    export_github_comment,
    export_jira,
    export_json,
    export_markdown,
)

_FORMATS = ("csv", "json", "markdown", "github", "jira")


def _read_input(source: str) -> str:
    """Read raw text from a file path or, when ``source`` is ``-``, from stdin."""
    if source == "-":
        return sys.stdin.read()
    path = Path(source)
    if not path.is_file():
        raise FileNotFoundError(f"report file not found: {source}")
    return path.read_text(encoding="utf-8")


def _parse_report(raw: str, *, source: str) -> Any:
    """Parse the raw JSON text into a report object the export functions accept.

    The export functions accept either a dict with a ``findings`` key or a bare
    list of findings; both are valid here. Anything else is a usage error.
    """
    try:
        data: Any = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {source}: {exc}") from exc

    if isinstance(data, dict):
        if "findings" not in data:
            raise ValueError(
                f"JSON object in {source} has no 'findings' key; "
                "expected a report dict or a list of findings"
            )
        return data
    if isinstance(data, list):
        return data
    raise ValueError(f"expected a JSON object or array in {source}, got {type(data).__name__}")


def _render(report: Any, fmt: str) -> str:
    """Render the report in the requested format via the public export functions."""
    if fmt == "csv":
        return export_csv(report)
    if fmt == "json":
        return export_json(report)
    if fmt == "markdown":
        return export_markdown(report)
    if fmt == "github":
        return export_github_comment(report)
    if fmt == "jira":
        return json.dumps(export_jira(report), indent=2)
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
        prog="vstack-export",
        description=(
            "Convert a vstack diagnose report / findings JSON to another "
            "format (CSV, JSON, Markdown, GitHub PR comment, or Jira ADF)."
        ),
    )
    parser.add_argument(
        "--report",
        default="-",
        metavar="PATH",
        help="Path to the report JSON (a dict with 'findings', or a list of "
        "findings). Use '-' or omit to read from stdin.",
    )
    parser.add_argument(
        "--format",
        required=True,
        choices=_FORMATS,
        help="Output format.",
    )
    parser.add_argument(
        "--out",
        metavar="PATH",
        help="Write output to this file. Omit (or use '-') to write to stdout.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``vstack-export`` CLI.

    Returns 0 on success, 2 on usage / validation / input errors.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        raw = _read_input(args.report)
        report = _parse_report(raw, source=args.report)
        rendered = _render(report, args.format)
    except (FileNotFoundError, ValueError) as exc:
        print(f"vstack-export: error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"vstack-export: error: {exc}", file=sys.stderr)
        return 2

    try:
        _write_output(rendered, args.out)
    except OSError as exc:
        print(f"vstack-export: error: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
