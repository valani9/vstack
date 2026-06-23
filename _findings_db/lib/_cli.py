"""vstack-findings-db CLI — track diagnose findings over time in a SQLite store.

A thin shell over the public ``vstack.findings_db`` API (``FindingsDB`` +
``FindingRecord``). It adds no business logic and changes no library behavior;
every subcommand calls an existing public method.

Subcommands
-----------

    add     Ingest findings from a diagnose report JSON into a db file.
    list    Query stored findings (filter by pattern / severity / agent / run).
    stats   Count stored findings (grouped, plus a total).

Every subcommand takes a ``--db PATH`` flag pointing at the SQLite file
(default: ``~/.vstack/findings.db``).

Examples
--------

    vstack-findings-db add --report report.json --run-id run-1 --agent-id bot-1
    cat report.json | vstack-findings-db add --run-id run-1
    vstack-findings-db list --pattern lewin --severity high --limit 20
    vstack-findings-db stats --group-by severity
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, cast

from ._db import FindingsDB

_DEFAULT_DB = Path.home() / ".vstack" / "findings.db"
_GROUP_BY_CHOICES = ("pattern", "severity", "agent_id", "run_id")


class _CLIError(Exception):
    """A clean, user-facing error. Raised for bad input; never leaks a traceback."""


def _read_input(source: str) -> str:
    """Read raw text from a file path or, when ``source`` is ``-``, from stdin."""
    if source == "-":
        return sys.stdin.read()
    path = Path(source)
    if not path.is_file():
        raise _CLIError(f"report file not found: {source}")
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise _CLIError(f"cannot read {source}: {exc}") from exc


def _parse_report(raw: str, *, source: str) -> Any:
    """Parse raw JSON into a report object ``store_report`` accepts.

    ``store_report`` accepts a dict with a ``findings`` key or a bare list of
    findings; both are valid here. Anything else is a usage error.
    """
    try:
        data: Any = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise _CLIError(f"invalid JSON in {source}: {exc}") from exc

    if isinstance(data, dict):
        if "findings" not in data:
            raise _CLIError(
                f"JSON object in {source} has no 'findings' key; "
                "expected a report dict or a list of findings"
            )
        return data
    if isinstance(data, list):
        return data
    raise _CLIError(f"expected a JSON object or array in {source}, got {type(data).__name__}")


def _open_db(db_path: str, *, must_exist: bool = False) -> FindingsDB:
    """Open (or create) the SQLite store, ensuring the parent directory exists."""
    path = Path(db_path)
    if must_exist and not path.is_file():
        raise _CLIError(f"db file not found: {db_path}")
    try:
        if not must_exist:
            path.parent.mkdir(parents=True, exist_ok=True)
        return FindingsDB(path)
    except OSError as exc:
        raise _CLIError(f"cannot open db {db_path}: {exc}") from exc


def cmd_add(args: argparse.Namespace) -> int:
    """Ingest findings from a report JSON into the db file."""
    raw = _read_input(args.report)
    report = _parse_report(raw, source=args.report)
    with _open_db(args.db) as db:
        ids = db.store_report(
            report=report,
            run_id=args.run_id or "",
            agent_id=args.agent_id or "",
        )
    print(f"Stored {len(ids)} finding(s) in {args.db}", file=sys.stderr)
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """Query stored findings and print them as a JSON array."""
    with _open_db(args.db, must_exist=True) as db:
        records = db.find(
            pattern=args.pattern or None,
            severity=args.severity or None,
            agent_id=args.agent_id,
            run_id=args.run_id,
            since_ts=args.since,
            until_ts=args.until,
            limit=args.limit,
        )
    print(json.dumps([r.to_dict() for r in records], indent=2))
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    """Count stored findings, grouped by a column, plus a total."""
    with _open_db(args.db, must_exist=True) as db:
        try:
            counts = db.count_by(group_by=args.group_by, since_ts=args.since)
        except ValueError as exc:
            # Defensive: argparse already constrains --group-by.
            raise _CLIError(str(exc)) from exc
        total = db.total_count()
    payload = {"group_by": args.group_by, "total": total, "counts": counts}
    print(json.dumps(payload, indent=2))
    return 0


def _add_db_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--db",
        default=str(_DEFAULT_DB),
        metavar="PATH",
        help=f"Path to the SQLite findings db. Default: {_DEFAULT_DB}.",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vstack-findings-db",
        description=(
            "Track vstack diagnose findings over time in a SQLite store: "
            "ingest reports, query by filter, and aggregate counts."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser(
        "add",
        help="Ingest findings from a diagnose report JSON into the db.",
    )
    _add_db_flag(p_add)
    p_add.add_argument(
        "--report",
        default="-",
        metavar="PATH",
        help="Path to the report JSON (a dict with 'findings', or a list of "
        "findings). Use '-' or omit to read from stdin.",
    )
    p_add.add_argument("--run-id", help="Run ID to tag the stored findings with.")
    p_add.add_argument("--agent-id", help="Agent ID to tag the stored findings with.")
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser(
        "list",
        help="Query stored findings; print as a JSON array.",
    )
    _add_db_flag(p_list)
    p_list.add_argument(
        "--pattern",
        action="append",
        metavar="NAME",
        help="Filter by pattern. Repeat to match any of several patterns.",
    )
    p_list.add_argument(
        "--severity",
        action="append",
        metavar="LEVEL",
        help="Filter by severity. Repeat to match any of several severities.",
    )
    p_list.add_argument("--agent-id", help="Filter by agent ID.")
    p_list.add_argument("--run-id", help="Filter by run ID.")
    p_list.add_argument(
        "--since",
        type=float,
        metavar="TS",
        help="Only findings with timestamp >= TS (Unix seconds).",
    )
    p_list.add_argument(
        "--until",
        type=float,
        metavar="TS",
        help="Only findings with timestamp <= TS (Unix seconds).",
    )
    p_list.add_argument(
        "--limit",
        type=int,
        default=1000,
        metavar="N",
        help="Maximum number of findings to return. Default: 1000.",
    )
    p_list.set_defaults(func=cmd_list)

    p_stats = sub.add_parser(
        "stats",
        help="Count stored findings, grouped by a column.",
    )
    _add_db_flag(p_stats)
    p_stats.add_argument(
        "--group-by",
        choices=_GROUP_BY_CHOICES,
        default="pattern",
        help="Column to group counts by. Default: pattern.",
    )
    p_stats.add_argument(
        "--since",
        type=float,
        metavar="TS",
        help="Only count findings with timestamp >= TS (Unix seconds).",
    )
    p_stats.set_defaults(func=cmd_stats)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the ``vstack-findings-db`` CLI.

    Returns 0 on success, 2 on usage / validation / input errors.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    func = cast("Callable[[argparse.Namespace], int]", args.func)

    try:
        return func(args)
    except _CLIError as exc:
        print(f"vstack-findings-db: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
