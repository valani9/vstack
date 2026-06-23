"""vstack-synth CLI — generate synthetic agent traces.

A thin shell over the public ``vstack.synth`` API for producing
``AgentTrace``-shaped JSON without an LLM. Use it to seed tests, demos and
onboarding fixtures, or to stress-test pattern detectors at scale.

Two subcommands:

* ``list`` — print the registered templates (one per failure/health shape)
  with their descriptions and default parameters. ``--json`` emits the same
  information machine-readably.
* ``gen`` — invoke a template's generator and emit the resulting trace(s) as
  JSON. ``--count`` produces a batch (a JSON array); ``--seed`` makes the
  output deterministic; ``--param key=value`` overrides a generator argument;
  ``--out`` writes to a file instead of stdout (``-`` for stdout).

The emitted JSON is the canonical ``AgentTrace`` serialization
(``model_dump(mode="json")``), so it can be piped straight into the other
vstack trace tools (e.g. ``vstack-trace-diff``).

This module adds no business logic and changes no library behavior; it only
calls existing public functions.

Examples
--------

    vstack-synth list
    vstack-synth list --json
    vstack-synth gen --template stuck_in_loop --seed 42
    vstack-synth gen --template stuck_in_loop --param retry_count=10 --out trace.json
    vstack-synth gen --template healthy --count 100 --seed 1 --out batch.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from vstack.aar import AgentTrace

from . import (
    generate_batch,
    get_template,
    list_templates,
)

_PROG = "vstack-synth"


class _UsageError(Exception):
    """Raised for clean (no-traceback) usage / validation failures."""


def _coerce_param(raw: str) -> Any:
    """Coerce a ``key=value`` value string into an int/float/bool/None/str.

    Generator parameters are typed (e.g. ``retry_count: int``); CLI values
    arrive as strings, so we apply a small, predictable coercion ladder. JSON
    is tried first so explicit forms like ``true``/``42``/``"text"`` work, then
    we fall back to the bare string.
    """
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _parse_params(pairs: list[str]) -> dict[str, Any]:
    """Parse repeated ``--param key=value`` pairs into a kwargs dict."""
    params: dict[str, Any] = {}
    for pair in pairs:
        if "=" not in pair:
            raise _UsageError(f"invalid --param {pair!r}: expected key=value")
        key, _, value = pair.partition("=")
        key = key.strip()
        if not key:
            raise _UsageError(f"invalid --param {pair!r}: empty key")
        params[key] = _coerce_param(value)
    return params


def _trace_to_jsonable(trace: AgentTrace) -> dict[str, Any]:
    """Serialize an ``AgentTrace`` to a JSON-ready dict."""
    return trace.model_dump(mode="json")


def _write_output(text: str, out: str | None) -> None:
    """Write ``text`` to ``--out`` (a path), or to stdout for ``None``/``-``."""
    if out is None or out == "-":
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")
        return
    Path(out).write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    print(f"{_PROG}: wrote {out}", file=sys.stderr)


def cmd_list(args: argparse.Namespace) -> int:
    """``vstack-synth list`` — print available templates."""
    names = list_templates()
    templates = [get_template(name) for name in names]

    if args.as_json:
        payload = [
            {
                "name": t.name,
                "description": t.description,
                "default_params": t.default_params,
            }
            for t in templates
        ]
        _write_output(json.dumps(payload, indent=2), None)
        return 0

    lines = [f"Available templates ({len(templates)}):", ""]
    for t in templates:
        params = ", ".join(f"{k}={v!r}" for k, v in t.default_params.items()) or "(none)"
        lines.append(f"  {t.name}")
        lines.append(f"      {t.description}")
        lines.append(f"      defaults: {params}")
    _write_output("\n".join(lines), None)
    return 0


def cmd_gen(args: argparse.Namespace) -> int:
    """``vstack-synth gen`` — generate a trace (or batch) and emit JSON."""
    try:
        template = get_template(args.template)
    except KeyError:
        known = ", ".join(list_templates())
        raise _UsageError(f"unknown template {args.template!r}. Available: {known}") from None

    if args.count < 1:
        raise _UsageError(f"--count must be >= 1, got {args.count}")

    overrides = _parse_params(args.param)
    # Start from the template's defaults, then apply user overrides so callers
    # only have to specify what they want to change.
    params: dict[str, Any] = {**template.default_params, **overrides}

    try:
        if args.count == 1:
            trace = template.generator(seed=args.seed, **params)
            jsonable: Any = _trace_to_jsonable(trace)
        else:
            traces = generate_batch(
                template.generator,
                count=args.count,
                seed=args.seed,
                **params,
            )
            jsonable = [_trace_to_jsonable(t) for t in traces]
    except TypeError as exc:
        # An unknown / wrong-typed generator parameter surfaces here.
        raise _UsageError(f"cannot generate {args.template!r}: {exc}") from exc

    _write_output(json.dumps(jsonable, indent=2), args.out)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=_PROG,
        description=(
            "Generate synthetic agent traces (AgentTrace JSON) for tests, "
            "demos and onboarding. Pure generation, no LLM required."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser(
        "list",
        help="List available trace templates and their default parameters.",
    )
    p_list.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit the template list as machine-readable JSON.",
    )
    p_list.set_defaults(func=cmd_list)

    p_gen = sub.add_parser(
        "gen",
        help="Generate a trace (or batch) from a template and emit JSON.",
    )
    p_gen.add_argument(
        "--template",
        required=True,
        metavar="NAME",
        help="Template name (see 'vstack-synth list').",
    )
    p_gen.add_argument(
        "--count",
        type=int,
        default=1,
        metavar="N",
        help="Number of traces to generate. >1 emits a JSON array. Default: 1.",
    )
    p_gen.add_argument(
        "--seed",
        type=int,
        default=None,
        metavar="S",
        help="Seed for deterministic output. For a batch, each trace uses seed+i.",
    )
    p_gen.add_argument(
        "--param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Override a generator parameter (repeatable). Value is JSON-parsed.",
    )
    p_gen.add_argument(
        "--out",
        default=None,
        metavar="PATH",
        help="Write JSON to PATH instead of stdout. Use '-' for stdout.",
    )
    p_gen.set_defaults(func=cmd_gen)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``vstack-synth`` CLI.

    Returns 0 on success, 2 on usage / validation / IO errors.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        rc: int = args.func(args)
    except _UsageError as exc:
        print(f"{_PROG}: error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"{_PROG}: error: {exc}", file=sys.stderr)
        return 2
    return rc


if __name__ == "__main__":
    sys.exit(main())
