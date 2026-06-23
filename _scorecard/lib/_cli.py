"""vstack-scorecard CLI — compute, render, compare scorecards."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast, get_args

from ._compare import compare_scorecards, is_blocking_regression
from ._compute import DimensionName, ScoreCard, ScoreCardConfig, compute_scorecard
from ._render import render_html, render_markdown, render_text

_DIMENSION_NAMES: frozenset[str] = frozenset(get_args(DimensionName))


def _load_reports(path: str) -> list[Any]:
    """Load a JSON list of reports from a path."""
    data = json.loads(Path(path).read_text())
    if isinstance(data, dict) and "reports" in data:
        return list(data["reports"])
    if isinstance(data, list):
        return data
    raise ValueError(f"Expected JSON list or dict with 'reports' key in {path}")


def _save_scorecard(scorecard: ScoreCard, path: str) -> None:
    Path(path).write_text(json.dumps(scorecard.to_dict(), indent=2))


def _load_scorecard_dict(path: str) -> dict[str, Any]:
    data: object = json.loads(Path(path).read_text())
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return cast(dict[str, Any], data)


def cmd_compute(args: argparse.Namespace) -> int:
    """vstack-scorecard compute --reports reports.json --out scorecard.json"""
    reports = _load_reports(args.reports)
    config = ScoreCardConfig(
        title=args.title,
        agent_id=args.agent_id,
        fleet_id=args.fleet_id,
    )
    scorecard = compute_scorecard(reports=reports, config=config)

    if args.out:
        _save_scorecard(scorecard, args.out)
        print(f"Wrote scorecard to {args.out}", file=sys.stderr)
    else:
        print(json.dumps(scorecard.to_dict(), indent=2))

    return 0


def cmd_render(args: argparse.Namespace) -> int:
    """vstack-scorecard render scorecard.json --format markdown|html|text"""
    data = _load_scorecard_dict(args.scorecard)

    # Reconstruct a minimal scorecard for rendering. We can't fully
    # round-trip without a custom from_dict, but we can render the
    # already-computed dimensions.
    scorecard = _scorecard_from_dict(data)

    if args.format == "html":
        print(render_html(scorecard))
    elif args.format == "markdown":
        print(render_markdown(scorecard))
    else:
        print(render_text(scorecard))

    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    """vstack-scorecard compare baseline.json current.json"""
    before = _scorecard_from_dict(_load_scorecard_dict(args.baseline))
    after = _scorecard_from_dict(_load_scorecard_dict(args.current))
    comparison = compare_scorecards(before, after)

    if args.format == "json":
        print(json.dumps(comparison.to_dict(), indent=2))
    else:
        print(comparison.to_markdown())

    if args.fail_on_regression:
        if is_blocking_regression(
            comparison,
            grade_threshold=args.fail_grade,
            score_threshold=args.fail_score,
        ):
            print("BLOCKING REGRESSION DETECTED", file=sys.stderr)
            return 1
    return 0


def _scorecard_from_dict(data: dict[str, Any]) -> ScoreCard:
    """Reconstruct a ScoreCard from a dict-serialized form."""
    from ._compute import DimensionScore, PatternContribution

    config = ScoreCardConfig(title=data.get("metadata", {}).get("title"))
    dimensions: dict[DimensionName, DimensionScore] = {}
    for raw_name, d in data.get("dimensions", {}).items():
        if raw_name not in _DIMENSION_NAMES:
            raise ValueError(f"Unknown dimension name: {raw_name!r}")
        name = cast(DimensionName, raw_name)
        dimensions[name] = DimensionScore(
            name=name,
            score=d["score"],
            contributing_patterns=d.get("contributing_patterns", []),
            findings_count=d.get("findings_count", 0),
            top_finding=d.get("top_finding"),
            top_intervention=d.get("top_intervention"),
        )

    contributions = [
        PatternContribution(
            pattern=p["pattern"],
            findings_high=p.get("findings_high", 0),
            findings_medium=p.get("findings_medium", 0),
            findings_low=p.get("findings_low", 0),
            score_delta=p.get("score_delta", 0.0),
            cost_usd=p.get("cost_usd", 0.0),
            duration_ms=p.get("duration_ms", 0),
        )
        for p in data.get("pattern_contributions", [])
    ]

    return ScoreCard(
        dimensions=dimensions,
        pattern_contributions=contributions,
        config=config,
        metadata=data.get("metadata", {}),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vstack-scorecard",
        description=(
            "Aggregate vstack pattern findings into a per-agent or "
            "per-fleet scorecard with letter grades."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_compute = sub.add_parser(
        "compute",
        help="Compute a scorecard from a JSON list of DiagnoseReport(s).",
    )
    p_compute.add_argument(
        "--reports",
        required=True,
        help="Path to JSON file with a list of reports (or {reports: [...]}).",
    )
    p_compute.add_argument(
        "--out",
        help="Optional output path. If omitted, prints to stdout.",
    )
    p_compute.add_argument("--title", help="Scorecard title.")
    p_compute.add_argument("--agent-id", help="Agent ID being scored.")
    p_compute.add_argument("--fleet-id", help="Fleet ID being scored.")
    p_compute.set_defaults(func=cmd_compute)

    p_render = sub.add_parser(
        "render",
        help="Render a scorecard JSON as text/markdown/HTML.",
    )
    p_render.add_argument("scorecard", help="Path to scorecard JSON.")
    p_render.add_argument(
        "--format",
        choices=["text", "markdown", "html"],
        default="text",
    )
    p_render.set_defaults(func=cmd_render)

    p_compare = sub.add_parser(
        "compare",
        help="Compare two scorecards; flag regressions.",
    )
    p_compare.add_argument("baseline", help="Path to baseline scorecard JSON.")
    p_compare.add_argument("current", help="Path to current scorecard JSON.")
    p_compare.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
    )
    p_compare.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="Exit non-zero if a blocking regression detected.",
    )
    p_compare.add_argument(
        "--fail-grade",
        default="C",
        help="Grade threshold for failure. Default: C.",
    )
    p_compare.add_argument(
        "--fail-score",
        type=float,
        default=10.0,
        help="Score-delta threshold for failure. Default: 10.0.",
    )
    p_compare.set_defaults(func=cmd_compare)

    args = parser.parse_args(argv)
    func = cast("Callable[[argparse.Namespace], int]", args.func)
    return func(args)


if __name__ == "__main__":
    sys.exit(main())
