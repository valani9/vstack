"""``vstack-diagnose`` CLI.

Reads an agent trace from a JSON file (or stdin), runs the
cross-pattern :func:`vstack.diagnose.diagnose` against it, and prints
the report as either pretty Markdown (default) or JSON.

The trace JSON format is permissive. The minimum useful shape is one
of:

  - Single-agent trace:
        {"goal": "...", "steps": [{...}, ...],
         "outcome": "...", "success": false}

  - Multi-agent crew trace:
        {"goal": "...", "agents": ["a", "b", "c"],
         "messages": [{...}, ...], "outcome": "...", "success": false}

The CLI converts the JSON into the appropriate vstack trace dataclass
via the AAR or Lencioni constructors. Any extra keys are passed through
untouched so users can add their own metadata.

Exit code is 0 on a clean run regardless of pattern errors (those
appear in the report's errors section); 2 on argument-parse errors;
1 on a runtime failure (unreadable trace, missing client, etc.).
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Literal, Sequence, cast

from .registry import ALL_SHAPES, PATTERNS, SEVERITY_ORDER, severity_rank
from .runner import diagnose as _diagnose

# Mirrors vstack.aar.TraceStep.type. Kept local so the CLI does not import
# the AAR module at load time (it is imported lazily inside the builders).
StepType = Literal["tool_call", "message", "decision", "observation", "thought"]


def _load_trace(path: str | None) -> dict[str, Any]:
    """Read trace JSON from `path` or stdin (when `path` is None or "-").

    Raises :class:`SystemExit` with a clear message on failure rather
    than letting the parser blow up with a stack trace; the CLI runs in
    user-facing contexts where stack traces are noise.
    """
    if path is None or path == "-":
        raw = sys.stdin.read()
        if not raw.strip():
            raise SystemExit(
                "vstack-diagnose: no trace data on stdin. Pipe a JSON object "
                "or pass --trace <path>."
            )
        try:
            return cast("dict[str, Any]", json.loads(raw))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"vstack-diagnose: stdin is not valid JSON ({exc}).")
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"vstack-diagnose: trace file not found: {path}")
    try:
        return cast("dict[str, Any]", json.loads(p.read_text()))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"vstack-diagnose: {path} is not valid JSON ({exc}).")


def _build_trace_object(payload: dict[str, Any]) -> Any:
    """Convert the JSON payload into a vstack trace dataclass.

    The shape choice is by attribute presence:

      - ``agents`` -> multi-agent (vstack.lencioni.MultiAgentTrace)
      - else -> single-agent (vstack.aar.AgentTrace)

    Org-scale traces don't get a built-in container; the CLI passes
    them through as a SimpleNamespace and lets the diagnose runner
    handle shape inference.
    """
    if "agents" in payload and payload.get("agents"):
        from vstack.lencioni import AgentMessage, MultiAgentTrace

        msgs = [
            AgentMessage(**m) if isinstance(m, dict) else m for m in payload.get("messages", [])
        ]
        return MultiAgentTrace(
            goal=payload.get("goal", ""),
            agents=list(payload.get("agents", [])),
            messages=msgs,
            outcome=payload.get("outcome", ""),
            success=bool(payload.get("success", False)),
        )

    if "org_chart" in payload or "structure_matrix" in payload:
        import types

        return types.SimpleNamespace(**payload)

    # default: single-agent
    from datetime import datetime, timezone

    from vstack.aar import AgentTrace, TraceStep

    def _coerce_step(s: Any, i: int) -> Any:
        if not isinstance(s, dict):
            return s
        # The CLI accepts minimal JSON. We fill in the AAR-schema
        # required fields (timestamp / type / content) from sensible
        # defaults if the caller did not supply them, so a quick smoke
        # test of {"action": "edit"} still produces a usable trace.
        # TraceStep is a pydantic model: it coerces ISO-8601 strings to
        # ``datetime`` and validates ``type`` against its Literal at
        # construction, so the cast below states the contract pydantic
        # actually enforces on these runtime values.
        raw_timestamp = s.get("timestamp")
        timestamp: datetime = (
            cast(datetime, raw_timestamp) if raw_timestamp else datetime.now(timezone.utc)
        )
        step_type: StepType = cast(StepType, s.get("type")) or _guess_step_type(s)
        content = s.get("content") or s.get("note") or s.get("action") or f"step {i + 1}"
        kept: dict[str, Any] = {
            k: v for k, v in s.items() if k in {"metadata", "parent_step_id", "step_id"}
        }
        return TraceStep(
            timestamp=timestamp,
            type=step_type,
            content=str(content),
            **kept,
        )

    steps = [_coerce_step(s, i) for i, s in enumerate(payload.get("steps", []))]
    return AgentTrace(
        goal=payload.get("goal", ""),
        steps=steps,
        outcome=payload.get("outcome", ""),
        success=bool(payload.get("success", False)),
    )


def _guess_step_type(s: dict[str, Any]) -> StepType:
    """Map free-form step dicts to the AAR's TraceStep.type literal.

    The mapping is opinionated but documented so users who care about
    exact typing can pre-populate the field themselves.
    """
    if "action" in s or "tool" in s or "target" in s:
        return "tool_call"
    if "message" in s or "text" in s:
        return "message"
    if "decision" in s or "choice" in s:
        return "decision"
    if "observation" in s or "result" in s:
        return "observation"
    return "thought"


def _resolve_client(
    provider: str | None,
) -> Any | None:
    """Resolve an LLM client by provider name. Returns None when
    ``provider`` is the empty string or "none" (the user explicitly
    declined a client; analyzers that need one will land in
    report.errors)."""
    if provider in (None, "", "none"):
        return None
    if provider == "anthropic":
        from vstack.aar.clients import AnthropicClient

        return AnthropicClient()
    if provider == "openai":
        from vstack.aar.clients import OpenAIClient

        return OpenAIClient()
    if provider == "ollama":
        from vstack.aar.clients import OllamaClient

        return OllamaClient()
    raise SystemExit(
        f"vstack-diagnose: unknown --client {provider!r}. "
        f"Expected one of anthropic / openai / ollama / none."
    )


def _serialise_report(report: Any) -> dict[str, Any]:
    """Convert a DiagnoseReport into a JSON-serialisable dict."""
    return {
        "shape": report.shape,
        "findings": [asdict(f) for f in report.findings],
        "errors": dict(report.errors),
        "per_pattern": [
            {
                "pattern": pr.pattern,
                "elapsed_seconds": pr.elapsed_seconds,
                "finding_count": len(pr.findings),
                "error": pr.error,
            }
            for pr in report.per_pattern
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vstack-diagnose",
        description=(
            "Run a curated bundle of vstack patterns against one agent "
            "or multi-agent trace and print a ranked findings report. "
            "Reads the trace from a JSON file (--trace) or stdin."
        ),
    )
    parser.add_argument(
        "--trace",
        "-t",
        help="Path to a trace JSON file. Omit (or pass '-') to read from stdin.",
        default=None,
    )
    parser.add_argument(
        "--client",
        "-c",
        choices=("anthropic", "openai", "ollama", "none"),
        default="none",
        help=(
            "LLM client to use for analyzers that need one. "
            "Defaults to 'none' so the CLI never starts a paid call without "
            "explicit opt-in. Picking a real provider requires the matching "
            "optional extra to be installed and the env var to be set."
        ),
    )
    parser.add_argument(
        "--shape",
        choices=ALL_SHAPES,
        default=None,
        help="Force trace shape (default: inferred from trace attributes).",
    )
    parser.add_argument(
        "--patterns",
        nargs="*",
        default=None,
        help=(
            "Override the default bundle with this explicit pattern list. "
            "Each value must be a known pattern slug (see --list)."
        ),
    )
    parser.add_argument(
        "--recipe",
        default=None,
        help=(
            "Run a named recipe bundle (see --list-recipes). Recipes are "
            "curated for specific named failure modes; --patterns wins if "
            "both are passed."
        ),
    )
    parser.add_argument(
        "--list-recipes",
        action="store_true",
        help="List every named recipe + its description, then exit.",
    )
    parser.add_argument(
        "--match",
        default=None,
        help=(
            "Free-text description of the failure; the CLI picks the first "
            "matching recipe by keyword. Falls back to default bundle if "
            "no recipe matches."
        ),
    )
    parser.add_argument(
        "--mode",
        default="standard",
        choices=("quick", "standard", "forensic"),
        help="Pipeline mode forwarded to analyzers that accept it.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List every shipped pattern + its applicable shapes, then exit.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a machine-readable JSON report instead of Markdown.",
    )
    parser.add_argument(
        "--sarif",
        action="store_true",
        help=(
            "Emit a SARIF 2.1.0 report (upload with github/codeql-action/"
            "upload-sarif to surface findings in GitHub code scanning)."
        ),
    )
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        help="Number of top findings to surface in the Markdown render (default: 5).",
    )
    parser.add_argument(
        "--fail-on",
        choices=SEVERITY_ORDER,
        default=None,
        help=(
            "Exit non-zero (3) if any finding is at or above this severity. "
            "Use to gate CI directly on the diagnosis. Omit to never fail on findings."
        ),
    )
    args = parser.parse_args(argv)

    if args.list:
        rows = sorted(PATTERNS.values(), key=lambda p: (p.module_id, p.pattern_id))
        for info in rows:
            shapes_str = "/".join(info.shapes)
            print(f"  {info.name:<22}  [{shapes_str:<22}] {info.summary}")
        return 0

    if args.list_recipes:
        from .recipes import list_recipes

        for r in list_recipes():
            print(f"  {r.name:<22}  [{r.shape:<10}] {r.description}")
        return 0

    # Recipe resolution. Order: explicit --recipe > --match > none.
    recipe = args.recipe
    if recipe is None and args.match:
        from .recipes import recipe_for_trigger

        matched = recipe_for_trigger(args.match)
        if matched is not None:
            recipe = matched.name

    payload = _load_trace(args.trace)
    trace_obj = _build_trace_object(payload)
    client = _resolve_client(args.client)

    report = _diagnose(
        trace_obj,
        llm_client=client,
        shape=args.shape,
        patterns=args.patterns,
        recipe=recipe,
        mode=args.mode,
    )

    if args.sarif:
        from .sarif import to_sarif

        trace_uri = args.trace if (args.trace and args.trace != "-") else "trace.json"
        json.dump(to_sarif(report, trace_uri=trace_uri), sys.stdout, indent=2)
        sys.stdout.write("\n")
    elif args.json:
        json.dump(_serialise_report(report), sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        # to_markdown already respects a default of top 5, but if the
        # user picked a different --top we render it directly here.
        if args.top != 5:
            lines = [
                f"# vstack diagnose -- {report.shape} trace",
                "",
                f"Ran {len(report.per_pattern)} patterns; surfaced "
                f"{len(report.findings)} findings, {len(report.errors)} "
                "pattern errors.",
                "",
                f"## Top {args.top} findings",
            ]
            for i, f in enumerate(report.top(args.top), 1):
                lines.append(f"{i}. **[{f.severity}]** `{f.pattern}` -- {f.title}")
                if f.evidence:
                    lines.append(f"   - evidence: {f.evidence}")
                if f.intervention:
                    lines.append(f"   - intervention: {f.intervention}")
            if report.errors:
                lines.append("")
                lines.append("## Pattern errors")
                for name, msg in report.errors.items():
                    lines.append(f"- `{name}`: {msg}")
            print("\n".join(lines))
        else:
            print(report.to_markdown())

    # CI gate: exit non-zero when a finding reaches the --fail-on threshold.
    return _gate_exit_code(report.findings, args.fail_on)


def _gate_exit_code(findings: "list[Any]", fail_on: str | None) -> int:
    """Return 3 if any finding is at/above ``fail_on``, else 0.

    ``fail_on=None`` never gates. Factored out for direct testing.
    """
    if fail_on is None:
        return 0
    threshold = severity_rank(fail_on)
    above = [f for f in findings if severity_rank(f.severity) >= threshold]
    if above:
        worst = max(above, key=lambda f: severity_rank(f.severity))
        print(
            f"vstack-diagnose: gate failed — found {worst.severity} finding (>= {fail_on}).",
            file=sys.stderr,
        )
        return 3
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
