"""``vstack-dashboard`` CLI.

Two modes:

  - ``render``: reads a DiagnoseReport JSON from a file or stdin and
    emits a self-contained HTML dashboard to stdout (or ``--out``).

      vstack-diagnose --trace trace.json --json | vstack-dashboard render > report.html
      vstack-dashboard render --in report.json --out dashboard.html

  - ``serve``: starts the FastAPI dashboard server.

      vstack-dashboard serve --port 8001

The ``render`` path is dependency-light (pure Python). The ``serve``
path requires ``fastapi`` + ``uvicorn`` to be installed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable, cast

from .render import DashboardConfig, render_report


def _cmd_render(args: argparse.Namespace) -> int:
    if args.infile and args.infile != "-":
        text = Path(args.infile).read_text()
    else:
        text = sys.stdin.read()
    if not text.strip():
        print("vstack-dashboard render: empty input", file=sys.stderr)
        return 2
    try:
        payload: Any = json.loads(text)
    except Exception as exc:  # noqa: BLE001
        print(f"vstack-dashboard render: invalid JSON: {exc}", file=sys.stderr)
        return 2

    cfg = DashboardConfig(
        title=args.title or "vstack diagnose",
        subtitle=args.subtitle or "Cross-pattern agent diagnostic dashboard",
    )
    html_out = render_report(payload, config=cfg, report_id=args.report_id)
    if args.outfile and args.outfile != "-":
        Path(args.outfile).write_text(html_out)
        print(f"wrote {args.outfile}", file=sys.stderr)
    else:
        sys.stdout.write(html_out)
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    try:
        import uvicorn
    except ImportError:
        print(
            "vstack-dashboard serve: uvicorn is required. "
            "Install with: pip install valanistack[fastapi]",
            file=sys.stderr,
        )
        return 2
    from .server import app

    uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vstack-dashboard",
        description="Render or serve vstack diagnose dashboards.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_render = sub.add_parser("render", help="render one report to HTML")
    p_render.add_argument(
        "--in", dest="infile", default="-", help="JSON report file (default: stdin)"
    )
    p_render.add_argument(
        "--out", dest="outfile", default="-", help="HTML output (default: stdout)"
    )
    p_render.add_argument("--title", default=None)
    p_render.add_argument("--subtitle", default=None)
    p_render.add_argument("--report-id", default="run")
    p_render.set_defaults(func=_cmd_render)

    p_serve = sub.add_parser("serve", help="start the FastAPI dashboard server")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8001)
    p_serve.add_argument("--log-level", default="info")
    p_serve.set_defaults(func=_cmd_serve)

    args = parser.parse_args(argv)
    func = cast(Callable[[argparse.Namespace], int], args.func)
    return func(args)


if __name__ == "__main__":
    raise SystemExit(main())
