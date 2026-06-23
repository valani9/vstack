"""Render a :class:`~vstack.diagnose.DiagnoseReport` as SARIF 2.1.0.

SARIF (Static Analysis Results Interchange Format) is the standard GitHub
consumes for code-scanning: upload it with ``github/codeql-action/upload-sarif``
and vstack findings show up in the repository's Security tab and as PR
annotations. Each vstack pattern becomes a SARIF *rule*; each finding becomes
a *result* whose ``level`` is mapped from the finding's severity.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .runner import DiagnoseReport

SARIF_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
SARIF_VERSION = "2.1.0"
_INFO_URI = "https://github.com/valani9/vstack"

# vstack's seven-point severity → SARIF's three levels (+ none).
_LEVEL_FOR_SEVERITY: dict[str, str] = {
    "critical": "error",
    "high": "error",
    "medium": "warning",
    "moderate": "warning",
    "low": "note",
    "trace": "note",
    "none": "none",
}


def _vstack_version() -> str:
    try:
        from importlib.metadata import PackageNotFoundError, version

        try:
            return version("valanistack")
        except PackageNotFoundError:
            return "0.0.0"
    except Exception:
        return "0.0.0"


def to_sarif(
    report: DiagnoseReport,
    *,
    trace_uri: str = "trace.json",
    version: str | None = None,
) -> dict[str, Any]:
    """Return a SARIF 2.1.0 log (as a dict) for one diagnose report.

    Parameters
    ----------
    report:
        The :class:`DiagnoseReport` to render.
    trace_uri:
        The artifact location recorded on each result, so GitHub attributes
        findings to the diagnosed trace file.
    version:
        Tool version to record; defaults to the installed valanistack version.
    """
    rules: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []

    for finding in report.findings:
        rule_id = f"vstack/{finding.pattern}"
        if rule_id not in rules:
            rules[rule_id] = {
                "id": rule_id,
                "name": finding.pattern,
                "shortDescription": {"text": f"vstack pattern: {finding.pattern}"},
                "helpUri": f"{_INFO_URI}/blob/main/PATTERNS.md",
            }

        message = finding.title
        if finding.evidence:
            message += f"\n\nEvidence: {finding.evidence}"
        if finding.intervention:
            message += f"\n\nIntervention: {finding.intervention}"

        results.append(
            {
                "ruleId": rule_id,
                "level": _LEVEL_FOR_SEVERITY.get(finding.severity, "warning"),
                "message": {"text": message},
                "locations": [{"physicalLocation": {"artifactLocation": {"uri": trace_uri}}}],
                "properties": {
                    "severity": finding.severity,
                    "intervention": finding.intervention,
                },
            }
        )

    return {
        "$schema": SARIF_SCHEMA,
        "version": SARIF_VERSION,
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "vstack",
                        "informationUri": _INFO_URI,
                        "version": version or _vstack_version(),
                        "rules": list(rules.values()),
                    }
                },
                "results": results,
            }
        ],
    }
