"""Finding export — CSV / Markdown / JSON / Jira / GitHub."""

from __future__ import annotations

import csv
import io
import json
from typing import Any


def _get_findings(report: Any) -> list[Any]:
    if isinstance(report, dict):
        return list(report.get("findings", []))
    if hasattr(report, "findings"):
        return list(report.findings)
    if isinstance(report, list):
        return list(report)
    return []


def _f(finding: Any, field: str, default: Any = "") -> Any:
    if isinstance(finding, dict):
        return finding.get(field, default)
    return getattr(finding, field, default)


def export_csv(report: Any, *, columns: list[str] | None = None) -> str:
    """Export findings as CSV string."""
    findings = _get_findings(report)
    columns = columns or ["pattern", "severity", "confidence", "title", "intervention"]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(columns)
    for finding in findings:
        row = []
        for col in columns:
            val = _f(finding, col, "")
            if isinstance(val, (list, dict)):
                val = json.dumps(val)
            row.append(val)
        writer.writerow(row)
    return output.getvalue()


def export_json(report: Any, *, indent: int = 2) -> str:
    """Export findings as pretty JSON string."""
    findings = _get_findings(report)
    payload = []
    for finding in findings:
        if isinstance(finding, dict):
            payload.append(dict(finding))
        elif hasattr(finding, "model_dump"):
            payload.append(finding.model_dump())
        else:
            # Build dict from canonical finding fields + any instance attrs.
            entry = {
                "pattern": _f(finding, "pattern", ""),
                "severity": _f(finding, "severity", "low"),
                "confidence": _f(finding, "confidence", 0.0),
                "title": _f(finding, "title", ""),
                "intervention": _f(finding, "intervention", ""),
            }
            if hasattr(finding, "__dict__"):
                for k, v in finding.__dict__.items():
                    if not k.startswith("_") and k not in entry:
                        entry[k] = v
            payload.append(entry)
    return json.dumps(payload, indent=indent, default=str)


def export_markdown(
    report: Any,
    *,
    title: str = "Findings",
    include_intervention: bool = True,
) -> str:
    """Export findings as a markdown document."""
    findings = _get_findings(report)
    lines = [f"# {title}", ""]
    lines.append(f"Total findings: **{len(findings)}**")
    lines.append("")

    if not findings:
        lines.append("_No findings._")
        return "\n".join(lines)

    # Group by severity.
    by_severity: dict[str, list[Any]] = {"high": [], "medium": [], "low": [], "info": []}
    for f in findings:
        sev = _f(f, "severity", "info") or "info"
        by_severity.setdefault(sev, []).append(f)

    for sev_name in ("high", "medium", "low"):
        bucket = by_severity.get(sev_name, [])
        if not bucket:
            continue
        lines.append(f"## {sev_name.title()} ({len(bucket)})")
        lines.append("")
        for f in bucket:
            pattern = _f(f, "pattern", "?")
            title_ = _f(f, "title", "")
            lines.append(f"### `{pattern}` — {title_}")
            confidence = _f(f, "confidence", None)
            if confidence is not None:
                lines.append(f"_Confidence: {confidence:.2f}_")
            lines.append("")
            if include_intervention:
                interv = _f(f, "intervention", "")
                if interv:
                    lines.append("**Intervention:**")
                    lines.append("")
                    lines.append(interv)
                    lines.append("")

    return "\n".join(lines)


def export_jira(report: Any) -> dict[str, Any]:
    """Export findings as Jira ADF (Atlassian Document Format).

    Returns a dict suitable for the body of a Jira issue creation
    payload (REST API v3).
    """
    findings = _get_findings(report)
    content: list[dict[str, Any]] = []

    content.append(
        {
            "type": "heading",
            "attrs": {"level": 2},
            "content": [{"type": "text", "text": f"Findings ({len(findings)})"}],
        }
    )

    if not findings:
        content.append({"type": "paragraph", "content": [{"type": "text", "text": "No findings."}]})
    else:
        for f in findings:
            pattern = _f(f, "pattern", "?")
            severity = _f(f, "severity", "low")
            title_ = _f(f, "title", "")
            interv = _f(f, "intervention", "")

            # Heading per finding.
            content.append(
                {
                    "type": "heading",
                    "attrs": {"level": 3},
                    "content": [
                        {
                            "type": "text",
                            "text": f"[{severity.upper()}] {pattern}: {title_}",
                        }
                    ],
                }
            )
            if interv:
                content.append(
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": "Intervention: ",
                                "marks": [{"type": "strong"}],
                            },
                            {"type": "text", "text": interv},
                        ],
                    }
                )

    return {"type": "doc", "version": 1, "content": content}


def export_github_comment(
    report: Any,
    *,
    title: str = "vstack diagnose",
    max_chars: int = 65000,
) -> str:
    """Export a PR-comment-friendly markdown string.

    GitHub PR comments have a 65,536 char limit. The output is
    truncated if needed (lowest-severity findings dropped first).
    """
    findings = _get_findings(report)
    high = sum(1 for f in findings if _f(f, "severity") == "high")
    med = sum(1 for f in findings if _f(f, "severity") == "medium")
    low = sum(1 for f in findings if _f(f, "severity") == "low")

    lines = [f"## 🤖 {title}", ""]
    lines.append(f"**High: {high}**  |  Medium: {med}  |  Low: {low}")
    lines.append("")

    if not findings:
        lines.append("> No findings.")
        return "\n".join(lines)

    # Sort: high, medium, low.
    sev_order = {"high": 0, "medium": 1, "low": 2}
    sorted_findings = sorted(
        findings,
        key=lambda f: sev_order.get(_f(f, "severity", "low"), 3),
    )

    for f in sorted_findings:
        pattern = _f(f, "pattern", "?")
        severity = _f(f, "severity", "low")
        title_ = _f(f, "title", "")
        interv = _f(f, "intervention", "")

        emoji = {"high": "🔴", "medium": "🟡", "low": "🔵"}.get(severity, "⚪")
        lines.append(f"### {emoji} `{pattern}` — {title_}")
        if interv:
            # Truncate intervention if too long.
            if len(interv) > 1000:
                interv = interv[:1000] + "…"
            lines.append("")
            lines.append(f"> {interv}")
        lines.append("")

    output = "\n".join(lines)

    # Truncate if needed.
    if len(output) > max_chars:
        truncated = output[: max_chars - 200]
        truncated += "\n\n_…truncated for length._"
        return truncated

    return output
