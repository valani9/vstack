"""vstack-redaction CLI — scrub PII / secrets from text and agent traces.

This is the shell surface for the README pipeline's "Sanitize" step. It is a
thin wrapper over the existing public API in :mod:`vstack.redaction` — it adds
no business logic and changes no library behavior. It instantiates a
:class:`~vstack.redaction.Redactor` with :data:`~vstack.redaction.DEFAULT_PATTERNS`
so that per-pattern match counts can be reported (the ``redact_text`` /
``redact_trace`` convenience functions discard the redactor's audit counts).

Surface
-------

    vstack-redaction --trace trace.json [--out scrubbed.json]
        Read an AgentTrace JSON, write a scrubbed copy to --out (or stdout),
        and print per-pattern match counts to stderr.

    vstack-redaction --text "raw string"
    cat secrets.txt | vstack-redaction --text -
        Scrub raw text. Reads from the argument, or from stdin when the value
        is "-" (also the default when neither --text nor --trace is given).

    vstack-redaction --list-patterns [--json]
        Print the built-in DEFAULT_PATTERNS.

Exit codes
----------
    0  success
    2  usage / validation error (bad flags, unreadable input, invalid JSON,
       wrong trace shape)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, cast

from ._redaction import DEFAULT_PATTERNS, Redactor

# A scrubbed trace is the dict form returned by Redactor.scrub_trace.
Trace = dict[str, Any]


class CLIError(Exception):
    """A user-facing error: printed to stderr, mapped to exit code 2.

    Used for bad input (missing files, invalid JSON, wrong shapes) so the CLI
    never surfaces a raw traceback for user mistakes.
    """


def _read_text_input(value: str | None) -> str:
    """Return raw text to scrub, reading stdin when appropriate.

    ``value`` semantics:
      - ``None`` or ``"-"``: read all of stdin.
      - otherwise: treated as the literal text to scrub.

    Trace files are handled by :func:`_load_trace`; this helper covers the
    raw-text path only.
    """
    if value is None or value == "-":
        return sys.stdin.read()
    return value


def _load_trace(path: str) -> Trace:
    """Load and validate an AgentTrace JSON object from ``path`` (or stdin).

    ``path`` of ``"-"`` reads the trace JSON from stdin. The payload must be a
    JSON object; a bare list/scalar is rejected so we fail loudly instead of
    silently passing a non-trace through the scrubber.
    """
    try:
        raw = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise CLIError(f"trace file not found: {path}") from exc
    except OSError as exc:
        raise CLIError(f"could not read trace file {path}: {exc}") from exc

    try:
        data: object = json.loads(raw)
    except json.JSONDecodeError as exc:
        source = "stdin" if path == "-" else path
        raise CLIError(f"invalid JSON in {source}: {exc}") from exc

    if not isinstance(data, dict):
        raise CLIError(
            "expected the trace to be a JSON object "
            f"(got {type(data).__name__}); pass an AgentTrace dict"
        )
    return cast(Trace, data)


def _format_counts(counts: dict[str, int]) -> str:
    """Render per-pattern match counts as aligned ``name: count`` lines.

    Only patterns that matched at least once are shown; a trailing total is
    always emitted so callers can assert on it.
    """
    matched = {name: n for name, n in counts.items() if n}
    total = sum(matched.values())
    if not matched:
        return "no matches"
    width = max(len(name) for name in matched)
    lines = [f"  {name:<{width}}  {n}" for name, n in sorted(matched.items())]
    lines.append(f"  {'total':<{width}}  {total}")
    return "\n".join(lines)


def _write_output(text: str, out: str | None) -> None:
    """Write ``text`` to ``--out`` (file) or to stdout when ``out`` is falsy.

    A trailing newline is added for the file case so the artifact is a tidy
    text file; stdout uses ``print`` to match the other house CLIs.
    """
    if out:
        try:
            Path(out).write_text(text + "\n", encoding="utf-8")
        except OSError as exc:
            raise CLIError(f"could not write output file {out}: {exc}") from exc
    else:
        print(text)


def cmd_list_patterns(args: argparse.Namespace) -> int:
    """Print the built-in DEFAULT_PATTERNS (human table or JSON)."""
    if args.json:
        payload = [
            {
                "name": p.name,
                "pattern": p.pattern,
                "replacement": p.replacement,
                "description": p.description,
            }
            for p in DEFAULT_PATTERNS
        ]
        print(json.dumps(payload, indent=2))
        return 0

    width = max(len(p.name) for p in DEFAULT_PATTERNS)
    for p in DEFAULT_PATTERNS:
        desc = p.description or "(no description)"
        print(f"{p.name:<{width}}  -> {p.replacement:<18}  {desc}")
    print()
    print(f"{len(DEFAULT_PATTERNS)} pattern(s)")
    return 0


def cmd_text(args: argparse.Namespace) -> int:
    """Scrub raw text from --text / stdin; report counts to stderr."""
    text = _read_text_input(args.text)
    redactor = Redactor(patterns=DEFAULT_PATTERNS)
    scrubbed = redactor.scrub(text)
    _write_output(scrubbed, args.out)
    print("Match counts:", file=sys.stderr)
    print(_format_counts(redactor.match_counts()), file=sys.stderr)
    return 0


def cmd_trace(args: argparse.Namespace) -> int:
    """Scrub an AgentTrace JSON; write a scrubbed copy; report counts."""
    trace = _load_trace(args.trace)
    redactor = Redactor(patterns=DEFAULT_PATTERNS)
    scrubbed = redactor.scrub_trace(trace)
    serialized = json.dumps(scrubbed, indent=2, default=str)

    if args.out:
        _write_output(serialized, args.out)
        print(f"Wrote scrubbed trace to {args.out}", file=sys.stderr)
    else:
        print(serialized)

    print("Match counts:", file=sys.stderr)
    print(_format_counts(redactor.match_counts()), file=sys.stderr)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vstack-redaction",
        description=(
            "Scrub PII / secrets from raw text or an agent trace before it "
            "leaves the machine. Completes the 'Sanitize' step of the vstack "
            "pipeline at the shell."
        ),
        epilog=(
            "examples:\n"
            "  vstack-redaction --trace trace.json --out scrubbed.json\n"
            '  vstack-redaction --text "email me at a@b.com"\n'
            "  cat notes.txt | vstack-redaction --text -\n"
            "  vstack-redaction --list-patterns --json"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--trace",
        metavar="PATH",
        help="Path to an AgentTrace JSON file (use '-' for stdin).",
    )
    mode.add_argument(
        "--text",
        metavar="STR",
        nargs="?",
        const="-",
        help=(
            "Raw text to scrub. Pass the string directly, or '-' (or no value) to read from stdin."
        ),
    )
    mode.add_argument(
        "--list-patterns",
        action="store_true",
        help="Print the built-in DEFAULT_PATTERNS and exit.",
    )
    parser.add_argument(
        "--out",
        metavar="PATH",
        help="Write scrubbed output here instead of stdout.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON (applies to --list-patterns).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns a process exit code (0 ok, 2 usage/validation)."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.list_patterns:
            return cmd_list_patterns(args)
        if args.trace is not None:
            return cmd_trace(args)
        # Default (and explicit --text): scrub raw text, reading stdin when
        # no value was supplied.
        return cmd_text(args)
    except CLIError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
