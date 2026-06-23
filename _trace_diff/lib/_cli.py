"""vstack-trace-diff CLI — structurally diff two agent traces.

Loads two ``AgentTrace``-shaped JSON files (a ``--before`` run and an
``--after`` run), computes the structural delta with the public
``diff_traces`` function, and prints what changed: added / removed / changed
steps plus any outcome and success-flag flips. This is the "what changed
between a passing and a failing run" debugger.

It is a thin shell over the public ``vstack.trace_diff`` API; it adds no
business logic and changes no library behavior. Human-readable Markdown is
printed by default; ``--json`` emits the machine-readable delta.

Examples
--------

    vstack-trace-diff --before before.json --after after.json
    vstack-trace-diff --before before.json --after after.json --json
    cat after.json | vstack-trace-diff --before before.json --after -
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ._diff import diff_traces


def _read_input(source: str) -> str:
    """Read raw text from a file path or, when ``source`` is ``-``, from stdin."""
    if source == "-":
        return sys.stdin.read()
    path = Path(source)
    if not path.is_file():
        raise FileNotFoundError(f"trace file not found: {source}")
    return path.read_text(encoding="utf-8")


def _parse_trace(raw: str, *, source: str) -> dict[str, Any]:
    """Parse raw JSON text into a trace object ``diff_traces`` accepts.

    A trace is a JSON object (an ``AgentTrace``-shaped dict, typically with
    ``goal``, ``steps``, ``outcome`` and ``success`` keys). Anything else is a
    usage error.
    """
    try:
        data: Any = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {source}: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(
            f"expected a JSON object (AgentTrace) in {source}, got {type(data).__name__}"
        )
    return data


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vstack-trace-diff",
        description=(
            "Diff two agent traces and print the structural delta: added / "
            "removed / changed steps, plus outcome and success-flag changes. "
            "The 'what changed between a passing and a failing run' debugger."
        ),
    )
    parser.add_argument(
        "--before",
        required=True,
        metavar="PATH",
        help="Path to the BEFORE trace JSON. Use '-' to read from stdin.",
    )
    parser.add_argument(
        "--after",
        required=True,
        metavar="PATH",
        help="Path to the AFTER trace JSON. Use '-' to read from stdin.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit the delta as machine-readable JSON instead of Markdown.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``vstack-trace-diff`` CLI.

    Returns 0 on success, 2 on usage / validation / input errors.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.before == "-" and args.after == "-":
        print(
            "vstack-trace-diff: error: only one of --before/--after may read from stdin ('-')",
            file=sys.stderr,
        )
        return 2

    try:
        before = _parse_trace(_read_input(args.before), source=args.before)
        after = _parse_trace(_read_input(args.after), source=args.after)
    except (FileNotFoundError, ValueError) as exc:
        print(f"vstack-trace-diff: error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"vstack-trace-diff: error: {exc}", file=sys.stderr)
        return 2

    delta = diff_traces(before, after)

    if args.as_json:
        rendered = json.dumps(delta.to_dict(), indent=2)
    else:
        rendered = delta.to_markdown()

    try:
        sys.stdout.write(rendered)
        if not rendered.endswith("\n"):
            sys.stdout.write("\n")
    except OSError as exc:
        print(f"vstack-trace-diff: error: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
