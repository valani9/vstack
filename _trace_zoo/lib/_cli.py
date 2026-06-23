"""vstack-trace-zoo CLI — browse and fetch canonical synthetic traces."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Callable, cast

from ._catalog import (
    CATALOG,
    get_trace,
    get_trace_info,
    list_traces,
    list_traces_by_category,
    list_traces_by_shape,
    trace_to_dict,
)


def cmd_list(args: argparse.Namespace) -> int:
    """vstack-trace-zoo list [--category X] [--shape Y]"""
    if args.category:
        infos = list_traces_by_category(args.category)
    elif args.shape:
        infos = list_traces_by_shape(args.shape)
    else:
        infos = [info for _, info in list_traces()]

    if args.json:
        out = [
            {
                "name": info.name,
                "shape": info.shape,
                "category": info.category,
                "description": info.description,
                "expected_severity": info.expected_severity,
                "expected_dominant_pattern": info.expected_dominant_pattern,
            }
            for info in infos
        ]
        print(json.dumps(out, indent=2))
    else:
        print(f"{'Name':30s}  {'Shape':12s}  {'Category':14s}  Description")
        print(f"{'-' * 30}  {'-' * 12}  {'-' * 14}  {'-' * 30}")
        for info in infos:
            print(
                f"{info.name:30s}  {info.shape:12s}  {info.category:14s}  {info.description[:50]}"
            )
        print()
        print(f"{len(infos)} trace(s)")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    """vstack-trace-zoo show <name>"""
    try:
        info = get_trace_info(args.name)
    except KeyError as e:
        print(str(e), file=sys.stderr)
        return 1

    if args.json:
        print(
            json.dumps(
                {
                    "name": info.name,
                    "shape": info.shape,
                    "category": info.category,
                    "description": info.description,
                    "expected_severity": info.expected_severity,
                    "expected_dominant_pattern": info.expected_dominant_pattern,
                    "citation": info.citation,
                },
                indent=2,
            )
        )
    else:
        print(f"Trace: {info.name}")
        print(f"  Shape: {info.shape}")
        print(f"  Category: {info.category}")
        print(f"  Severity expected: {info.expected_severity}")
        if info.expected_dominant_pattern:
            print(f"  Dominant pattern: {info.expected_dominant_pattern}")
        print(f"  Description: {info.description}")
        if info.citation:
            print(f"  Citation: {info.citation}")
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    """vstack-trace-zoo get <name> — print the trace as JSON."""
    try:
        trace = get_trace(args.name)
    except KeyError as e:
        print(str(e), file=sys.stderr)
        return 1

    payload = trace_to_dict(trace)
    print(json.dumps(payload, indent=2, default=str))
    return 0


def cmd_categories(_args: argparse.Namespace) -> int:
    """vstack-trace-zoo categories — list all categories with counts."""
    counts: dict[str, int] = {}
    for info in CATALOG.values():
        counts[info.category] = counts.get(info.category, 0) + 1

    for cat in ("reasoning", "coordination", "trust", "workload", "culture"):
        n = counts.get(cat, 0)
        print(f"  {cat:14s} {n} trace(s)")
    return 0


def cmd_shapes(_args: argparse.Namespace) -> int:
    """vstack-trace-zoo shapes — list all shapes with counts."""
    counts: dict[str, int] = {}
    for info in CATALOG.values():
        counts[info.shape] = counts.get(info.shape, 0) + 1

    for sh in ("individual", "team", "org"):
        n = counts.get(sh, 0)
        print(f"  {sh:14s} {n} trace(s)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vstack-trace-zoo",
        description="Browse and fetch canonical synthetic agent traces.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="List traces.")
    p_list.add_argument(
        "--category",
        choices=["reasoning", "coordination", "trust", "workload", "culture"],
    )
    p_list.add_argument(
        "--shape",
        choices=["individual", "team", "org"],
    )
    p_list.add_argument("--json", action="store_true", help="JSON output.")
    p_list.set_defaults(func=cmd_list)

    p_show = sub.add_parser("show", help="Show metadata for one trace.")
    p_show.add_argument("name")
    p_show.add_argument("--json", action="store_true")
    p_show.set_defaults(func=cmd_show)

    p_get = sub.add_parser("get", help="Fetch the trace JSON.")
    p_get.add_argument("name")
    p_get.set_defaults(func=cmd_get)

    p_cat = sub.add_parser("categories", help="List categories with counts.")
    p_cat.set_defaults(func=cmd_categories)

    p_sh = sub.add_parser("shapes", help="List shapes with counts.")
    p_sh.set_defaults(func=cmd_shapes)

    args = parser.parse_args(argv)
    func = cast(Callable[[argparse.Namespace], int], args.func)
    return func(args)


if __name__ == "__main__":
    sys.exit(main())
