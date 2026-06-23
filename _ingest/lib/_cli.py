"""``vstack-import`` — convert real traces into a vstack ``AgentTrace``.

Reads chat-completion message logs or OpenTelemetry spans (JSON, from a file or
stdin) and writes an ``AgentTrace`` JSON ready for ``vstack-diagnose``::

    vstack-import --format messages chat.json --goal "ship auth" | \\
        vstack-diagnose --trace - --client anthropic --fail-on high
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from . import from_chat_messages, from_otel_spans


def _load(path: str | None) -> Any:
    raw = (
        sys.stdin.read()
        if (path is None or path == "-")
        else Path(path).read_text(encoding="utf-8")
    )
    return json.loads(raw)


def _items(payload: Any, key: str) -> list[dict[str, Any]]:
    """Accept a bare list, or a dict wrapping the list under ``key``."""
    if isinstance(payload, list):
        return list(payload)
    if isinstance(payload, dict) and isinstance(payload.get(key), list):
        return list(payload[key])
    raise ValueError(f"expected a JSON list of {key} (or {{'{key}': [...]}}).")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vstack-import",
        description=(
            "Convert chat-completion message logs or OpenTelemetry spans into a "
            "vstack AgentTrace JSON (pipe into vstack-diagnose)."
        ),
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="-",
        help="Input JSON file (omit or '-' for stdin).",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=("messages", "otel"),
        required=True,
        help="messages = OpenAI/Anthropic chat log; otel = OpenTelemetry spans.",
    )
    parser.add_argument("--goal", default="", help="The agent's goal (else inferred).")
    parser.add_argument("--outcome", default="", help="What happened (else inferred).")
    parser.add_argument(
        "--success",
        action="store_true",
        help="Mark the run successful (default: failed — you usually diagnose failures).",
    )
    parser.add_argument("--agent-id", default=None, help="Agent id to record.")
    parser.add_argument("--out", "-o", default=None, help="Write to a file (default: stdout).")
    args = parser.parse_args(argv)

    try:
        payload = _load(args.input)
        if args.format == "messages":
            trace = from_chat_messages(
                _items(payload, "messages"),
                goal=args.goal,
                outcome=args.outcome,
                success=args.success,
                agent_id=args.agent_id,
            )
        else:
            trace = from_otel_spans(
                _items(payload, "spans"),
                goal=args.goal,
                outcome=args.outcome,
                success=args.success,
                agent_id=args.agent_id,
            )
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print(f"vstack-import: {e}", file=sys.stderr)
        return 2

    out_json = trace.model_dump_json(indent=2)
    if args.out and args.out != "-":
        Path(args.out).write_text(out_json + "\n", encoding="utf-8")
        print(f"Wrote {args.out} ({len(trace.steps)} steps)", file=sys.stderr)
    else:
        sys.stdout.write(out_json + "\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
