"""``vstack-recipes`` CLI.

A small terminal browser for the recipe catalog. Lets users:

  - List all recipes (default).
  - Filter by cluster (--cluster reasoning).
  - Filter by shape (--shape team).
  - Search by free-text trigger (--match "stuck in loop").
  - Show details for a single recipe (--show stuck_in_loop).

Output formats: a human-readable table (default), JSON
(``--json``), or a single-recipe Markdown block (``--md``).

The CLI is callable as ``vstack-recipes`` after install. The
``vstack-diagnose`` CLI's ``--recipe`` flag accepts the same slugs.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from .recipes import RECIPES, Recipe, recipe_for_trigger


# ---------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.show:
        return _show(args.show, args)

    # List / filter / search mode
    recipes = list(RECIPES.values())

    if args.cluster:
        recipes = [r for r in recipes if r.cluster == args.cluster]
    if args.shape:
        recipes = [r for r in recipes if r.shape == args.shape]
    if args.match:
        hit = recipe_for_trigger(args.match)
        if hit is None:
            print(
                f"vstack-recipes: no recipe matched '{args.match}'",
                file=sys.stderr,
            )
            return 1
        recipes = [hit]
    if args.q:
        q = args.q.lower()
        recipes = [
            r
            for r in recipes
            if q in r.name.lower()
            or q in r.description.lower()
            or any(q in t.lower() for t in r.triggers)
        ]

    if not recipes:
        print("vstack-recipes: no recipes matched the filters", file=sys.stderr)
        return 1

    if args.json:
        _print_json(recipes)
        return 0
    if args.compact:
        _print_compact(recipes)
        return 0
    _print_grouped(recipes)
    return 0


def _show(name: str, args: argparse.Namespace) -> int:
    r = RECIPES.get(name)
    if r is None:
        print(f"vstack-recipes: unknown recipe '{name}'", file=sys.stderr)
        print(
            "  hint: list recipes with `vstack-recipes` or search with `vstack-recipes --q <term>`",
            file=sys.stderr,
        )
        return 1
    if args.json:
        print(
            json.dumps(
                {
                    "name": r.name,
                    "description": r.description,
                    "shape": r.shape,
                    "cluster": r.cluster,
                    "patterns": list(r.patterns),
                    "triggers": list(r.triggers),
                },
                indent=2,
            )
        )
        return 0
    if args.md:
        _print_markdown(r)
        return 0
    _print_detail(r)
    return 0


# ---------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------


def _print_grouped(recipes: Sequence[Recipe]) -> None:
    by_cluster: dict[str, list[Recipe]] = {}
    for r in recipes:
        by_cluster.setdefault(r.cluster, []).append(r)

    cluster_order = ["reasoning", "coordination", "trust", "workload", "culture"]
    seen_clusters: list[str] = []
    for c in cluster_order:
        if c in by_cluster:
            seen_clusters.append(c)
    for c in by_cluster:
        if c not in seen_clusters:
            seen_clusters.append(c)

    width = max((len(r.name) for r in recipes), default=20)
    for cluster in seen_clusters:
        print(f"\n  {cluster.upper()}")
        for r in by_cluster[cluster]:
            line = f"    {r.name:<{width}}  [{r.shape:>11}]  {r.description[:70]}"
            print(line)
    print(f"\n  {len(recipes)} recipes total across {len(seen_clusters)} clusters.")


def _print_compact(recipes: Sequence[Recipe]) -> None:
    for r in recipes:
        print(r.name)


def _print_json(recipes: Sequence[Recipe]) -> None:
    out = [
        {
            "name": r.name,
            "description": r.description,
            "shape": r.shape,
            "cluster": r.cluster,
            "patterns": list(r.patterns),
            "triggers": list(r.triggers),
        }
        for r in recipes
    ]
    print(json.dumps(out, indent=2))


def _print_detail(r: Recipe) -> None:
    print(f"\n  RECIPE: {r.name}")
    print(f"  Cluster:    {r.cluster}")
    print(f"  Shape:      {r.shape}")
    print("  Description:")
    for line in _wrap(r.description, 76, prefix="    "):
        print(line)
    print("\n  Patterns:")
    for p in r.patterns:
        print(f"    - {p}")
    if r.triggers:
        print("\n  Triggers (any of these in a free-text query routes here):")
        for t in r.triggers:
            print(f"    - {t!r}")
    print()


def _print_markdown(r: Recipe) -> None:
    print(f"# Recipe: `{r.name}`")
    print()
    print(f"- **Cluster:** `{r.cluster}`")
    print(f"- **Shape:** `{r.shape}`")
    print()
    print("## Description")
    print()
    print(r.description)
    print()
    print("## Patterns")
    print()
    for p in r.patterns:
        print(f"- `{p}`")
    print()
    if r.triggers:
        print("## Triggers")
        print()
        for t in r.triggers:
            print(f"- {t!r}")
        print()
    print("## Invoke")
    print()
    print(f"```bash\nvstack-diagnose --trace your-trace.json --recipe {r.name}\n```\n")
    print(
        "```python\n"
        "from vstack.diagnose import diagnose\n"
        "from vstack.aar.clients import AnthropicClient\n\n"
        "report = diagnose(\n"
        "    trace=your_trace,\n"
        "    llm_client=AnthropicClient(),\n"
        f'    recipe="{r.name}",\n'
        ")\n"
        "print(report.to_markdown())\n"
        "```"
    )


def _wrap(text: str, width: int, prefix: str = "") -> list[str]:
    """Word-wrap text to ``width`` columns with optional indent."""
    words = text.split()
    lines: list[str] = []
    cur = prefix
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur.rstrip())
            cur = prefix
        cur += w + " "
    if cur.strip():
        lines.append(cur.rstrip())
    return lines


# ---------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="vstack-recipes",
        description="Browse the vstack.diagnose recipe catalog.",
    )

    list_grp = p.add_argument_group("listing / filtering")
    list_grp.add_argument(
        "--cluster",
        choices=sorted({r.cluster for r in RECIPES.values()}),
        help="filter recipes by thematic cluster",
    )
    list_grp.add_argument(
        "--shape",
        choices=("individual", "team", "org"),
        help="filter recipes by trace shape",
    )
    list_grp.add_argument(
        "--match",
        metavar="PHRASE",
        help="route a free-text failure description to a single recipe",
    )
    list_grp.add_argument(
        "--q",
        metavar="TERM",
        help="substring search across recipe name + description + triggers",
    )

    show_grp = p.add_argument_group("single-recipe inspection")
    show_grp.add_argument(
        "--show",
        metavar="SLUG",
        help="show full detail for one recipe by slug",
    )

    out_grp = p.add_argument_group("output format")
    out_grp.add_argument("--json", action="store_true", help="emit JSON")
    out_grp.add_argument(
        "--md",
        action="store_true",
        help="emit Markdown (single-recipe; requires --show)",
    )
    out_grp.add_argument(
        "--compact",
        action="store_true",
        help="emit one slug per line (no headers)",
    )
    return p


if __name__ == "__main__":
    raise SystemExit(main())
