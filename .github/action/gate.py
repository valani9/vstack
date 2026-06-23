#!/usr/bin/env python3
"""Gate script for the vstack GitHub Action.

Runs ``vstack-diagnose`` on an agent trace and fails the build when any
finding is at or above a configured severity threshold. Writes a Markdown
report to the GitHub step summary and sets step outputs.

Configured entirely through environment variables (set by ``action.yml``):

* ``VSTACK_TRACE``   — path to the trace JSON (required)
* ``VSTACK_FAIL_ON`` — min severity that fails the build (default ``high``;
  ``none`` disables failing)
* ``VSTACK_MODE``    — ``quick`` | ``standard`` | ``forensic``
* ``VSTACK_RECIPE``  — optional named recipe bundle
* ``VSTACK_CLIENT``  — ``none`` | ``anthropic`` | ``openai`` | ``ollama``
* ``VSTACK_SHAPE``   — optional forced trace shape
* ``VSTACK_REPORT``  — output path for the JSON report (default
  ``vstack-report.json``)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any

from vstack.diagnose.registry import SEVERITY_ORDER, severity_rank


def build_command(env: dict[str, str]) -> list[str]:
    """Build the ``vstack-diagnose`` argv from the action's env inputs."""
    trace = env.get("VSTACK_TRACE", "").strip()
    if not trace:
        raise ValueError("VSTACK_TRACE (the trace path) is required.")
    cmd = ["vstack-diagnose", "--trace", trace, "--json"]
    client = (env.get("VSTACK_CLIENT") or "none").strip() or "none"
    cmd += ["--client", client]
    mode = (env.get("VSTACK_MODE") or "").strip()
    if mode:
        cmd += ["--mode", mode]
    recipe = (env.get("VSTACK_RECIPE") or "").strip()
    if recipe:
        cmd += ["--recipe", recipe]
    shape = (env.get("VSTACK_SHAPE") or "").strip()
    if shape:
        cmd += ["--shape", shape]
    return cmd


def decide_gate(findings: list[dict[str, Any]], fail_on: str) -> tuple[bool, str, int]:
    """Return ``(failed, max_severity, findings_count)``.

    ``failed`` is True when ``fail_on`` is a real severity and at least one
    finding ranks at or above it. ``fail_on == "none"`` never fails.
    """
    max_rank = -1
    max_sev = "none"
    for finding in findings:
        sev = str(finding.get("severity", "none"))
        rank = severity_rank(sev)
        if rank > max_rank:
            max_rank, max_sev = rank, sev

    fail_on = (fail_on or "high").strip().lower()
    if fail_on == "none" or fail_on not in SEVERITY_ORDER:
        threshold = -1 if fail_on == "none" else severity_rank("high")
    else:
        threshold = severity_rank(fail_on)

    failed = fail_on != "none" and any(
        severity_rank(str(f.get("severity", "none"))) >= threshold for f in findings
    )
    return failed, max_sev, len(findings)


def render_summary(
    report: dict[str, Any],
    findings: list[dict[str, Any]],
    fail_on: str,
    failed: bool,
    max_sev: str,
) -> str:
    """Render a GitHub-flavored Markdown summary of the gate result."""
    verdict = "❌ FAILED" if failed else "✅ PASSED"
    shape = report.get("shape", "?")
    lines = [
        "## vstack agent-quality gate",
        "",
        f"**{verdict}** — shape: `{shape}` · findings: {len(findings)} · "
        f"max severity: `{max_sev}` · fail-on: `{fail_on}`",
        "",
    ]
    if findings:
        lines += ["| Severity | Pattern | Finding |", "|---|---|---|"]
        for f in sorted(
            findings, key=lambda x: severity_rank(str(x.get("severity", "none"))), reverse=True
        ):
            title = str(f.get("title", "")).replace("|", "\\|")
            lines.append(f"| `{f.get('severity', 'none')}` | `{f.get('pattern', '?')}` | {title} |")
    else:
        lines.append("_No findings._")

    errors = report.get("errors") or []
    if errors:
        lines += ["", f"> {len(errors)} pattern(s) errored during diagnosis (see report)."]
    return "\n".join(lines) + "\n"


def sarif_from_report(report: dict[str, Any], trace_uri: str) -> dict[str, Any]:
    """Render a diagnose report dict as SARIF, reusing vstack's own renderer.

    Reconstructs ``Finding`` objects from the JSON report so the Action and the
    ``vstack-diagnose --sarif`` CLI emit identical SARIF.
    """
    from vstack.diagnose import DiagnoseReport, Finding, to_sarif

    findings = [
        Finding(
            pattern=f.get("pattern", "?"),
            severity=f.get("severity", "none"),
            title=f.get("title", ""),
            evidence=f.get("evidence", ""),
            intervention=f.get("intervention", ""),
        )
        for f in (report.get("findings") or [])
    ]
    rep = DiagnoseReport(shape=report.get("shape", "individual"), findings=findings)
    return to_sarif(rep, trace_uri=trace_uri)


def _set_output(key: str, value: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"{key}={value}\n")


def _write_summary(text: str) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(text)


def main(env: dict[str, str] | None = None) -> int:
    env = dict(os.environ if env is None else env)
    try:
        cmd = build_command(env)
    except ValueError as e:
        print(f"vstack-gate: {e}", file=sys.stderr)
        return 2

    proc = subprocess.run(cmd, capture_output=True, text=True)  # noqa: S603
    if proc.returncode != 0:
        print(proc.stderr.strip() or "vstack-diagnose failed.", file=sys.stderr)
        return 2

    try:
        report: dict[str, Any] = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        print(f"vstack-gate: could not parse diagnose output: {e}", file=sys.stderr)
        return 2

    findings = list(report.get("findings") or [])
    fail_on = (env.get("VSTACK_FAIL_ON") or "high").strip().lower()
    failed, max_sev, count = decide_gate(findings, fail_on)

    report_path = (env.get("VSTACK_REPORT") or "vstack-report.json").strip()
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    _set_output("max-severity", max_sev)
    _set_output("findings-count", str(count))
    _set_output("report", report_path)

    sarif_path = (env.get("VSTACK_SARIF") or "").strip()
    if sarif_path:
        sarif = sarif_from_report(report, env.get("VSTACK_TRACE", "trace.json"))
        with open(sarif_path, "w", encoding="utf-8") as fh:
            json.dump(sarif, fh, indent=2)
        _set_output("sarif", sarif_path)

    summary = render_summary(report, findings, fail_on, failed, max_sev)
    _write_summary(summary)
    print(summary)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
