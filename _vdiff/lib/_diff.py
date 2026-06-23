"""Diff two DiagnoseReports — surface added/removed/changed findings."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


_SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2}


def _get_findings(report: Any) -> list[dict[str, Any]]:
    if isinstance(report, dict):
        return list(report.get("findings", []))
    if hasattr(report, "findings"):
        return list(report.findings)
    return []


def _get_per_pattern(report: Any) -> dict[str, Any]:
    if isinstance(report, dict):
        return dict(report.get("per_pattern", {}))
    if hasattr(report, "per_pattern"):
        return dict(report.per_pattern)
    return {}


def _finding_key(finding: Any) -> tuple[str, str]:
    if isinstance(finding, dict):
        pattern = finding.get("pattern", "")
        title = finding.get("title", "")
    else:
        pattern = getattr(finding, "pattern", "")
        title = getattr(finding, "title", "")
    return (str(pattern), str(title))


def _get_severity(finding: Any) -> str:
    if isinstance(finding, dict):
        return str(finding.get("severity", "low"))
    return str(getattr(finding, "severity", "low"))


def _get_intervention(finding: Any) -> str:
    if isinstance(finding, dict):
        return str(finding.get("intervention", ""))
    return str(getattr(finding, "intervention", ""))


@dataclass
class FindingDiff:
    """A single finding's change between before and after."""

    pattern: str
    title: str
    kind: str  # "added" | "removed" | "severity_changed" | "intervention_changed" | "unchanged"
    severity_before: str | None = None
    severity_after: str | None = None
    intervention_before: str | None = None
    intervention_after: str | None = None

    @property
    def severity_increased(self) -> bool:
        if not self.severity_before or not self.severity_after:
            return False
        return _SEVERITY_ORDER.get(self.severity_after, -1) > _SEVERITY_ORDER.get(
            self.severity_before, -1
        )

    @property
    def severity_decreased(self) -> bool:
        if not self.severity_before or not self.severity_after:
            return False
        return _SEVERITY_ORDER.get(self.severity_after, -1) < _SEVERITY_ORDER.get(
            self.severity_before, -1
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern": self.pattern,
            "title": self.title,
            "kind": self.kind,
            "severity_before": self.severity_before,
            "severity_after": self.severity_after,
            "intervention_before": self.intervention_before,
            "intervention_after": self.intervention_after,
        }


@dataclass
class ReportDelta:
    """Full delta between two reports."""

    finding_diffs: list[FindingDiff] = field(default_factory=list)
    patterns_added: list[str] = field(default_factory=list)
    patterns_removed: list[str] = field(default_factory=list)
    before_count: int = 0
    after_count: int = 0

    @property
    def added(self) -> list[FindingDiff]:
        return [d for d in self.finding_diffs if d.kind == "added"]

    @property
    def removed(self) -> list[FindingDiff]:
        return [d for d in self.finding_diffs if d.kind == "removed"]

    @property
    def severity_changed(self) -> list[FindingDiff]:
        return [d for d in self.finding_diffs if d.kind == "severity_changed"]

    @property
    def intervention_changed(self) -> list[FindingDiff]:
        return [d for d in self.finding_diffs if d.kind == "intervention_changed"]

    @property
    def unchanged(self) -> list[FindingDiff]:
        return [d for d in self.finding_diffs if d.kind == "unchanged"]

    @property
    def severity_increased(self) -> list[FindingDiff]:
        return [d for d in self.finding_diffs if d.severity_increased]

    @property
    def severity_decreased(self) -> list[FindingDiff]:
        return [d for d in self.finding_diffs if d.severity_decreased]

    def is_regression(self, *, threshold: float = 0.1) -> bool:
        """Returns True if the diff represents a regression.

        Regression definition:
          - Any new high-severity finding, OR
          - Severity increase on any existing finding, OR
          - More than `threshold` fraction of findings new.
        """
        new_high = any(d.severity_after == "high" for d in self.added)
        if new_high:
            return True

        if self.severity_increased:
            return True

        if self.after_count > 0:
            new_fraction = len(self.added) / max(1, self.after_count)
            if new_fraction > threshold:
                return True

        return False

    def is_improvement(self, *, threshold: float = 0.1) -> bool:
        """Returns True if the diff represents an improvement."""
        removed_high = any(d.severity_before == "high" for d in self.removed)
        if removed_high:
            return True

        if self.severity_decreased:
            return True

        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "before_count": self.before_count,
            "after_count": self.after_count,
            "added": [d.to_dict() for d in self.added],
            "removed": [d.to_dict() for d in self.removed],
            "severity_changed": [d.to_dict() for d in self.severity_changed],
            "intervention_changed": [d.to_dict() for d in self.intervention_changed],
            "unchanged_count": len(self.unchanged),
            "patterns_added": self.patterns_added,
            "patterns_removed": self.patterns_removed,
            "is_regression": self.is_regression(),
            "is_improvement": self.is_improvement(),
        }

    def to_markdown(self) -> str:
        lines = ["# Report Delta", ""]
        lines.append(
            f"**Findings**: {self.before_count} → {self.after_count}  "
            f"(Δ {self.after_count - self.before_count:+d})"
        )
        lines.append("")

        if self.added:
            lines.append(f"## ➕ Added ({len(self.added)})")
            for d in self.added:
                lines.append(f"- **[{d.severity_after}]** {d.pattern}: {d.title}")
            lines.append("")

        if self.removed:
            lines.append(f"## ➖ Removed ({len(self.removed)})")
            for d in self.removed:
                lines.append(f"- **[{d.severity_before}]** {d.pattern}: {d.title}")
            lines.append("")

        if self.severity_changed:
            lines.append(f"## ⚠️ Severity Changed ({len(self.severity_changed)})")
            for d in self.severity_changed:
                arrow = "↗" if d.severity_increased else "↘"
                lines.append(
                    f"- {arrow} **{d.pattern}**: {d.severity_before} → {d.severity_after} "
                    f"— {d.title}"
                )
            lines.append("")

        if self.intervention_changed:
            lines.append(f"## 💡 Intervention Changed ({len(self.intervention_changed)})")
            for d in self.intervention_changed:
                lines.append(f"- **{d.pattern}**: {d.title}")
            lines.append("")

        if self.unchanged:
            lines.append(f"## ✓ Unchanged ({len(self.unchanged)})")
            lines.append("")

        if self.patterns_added:
            lines.append(f"**Patterns added**: {', '.join(self.patterns_added)}")
        if self.patterns_removed:
            lines.append(f"**Patterns removed**: {', '.join(self.patterns_removed)}")

        return "\n".join(lines)


def diff_reports(before: Any, after: Any) -> ReportDelta:
    """Compute a structured delta between two reports."""
    before_findings = _get_findings(before)
    after_findings = _get_findings(after)

    before_by_key = {_finding_key(f): f for f in before_findings}
    after_by_key = {_finding_key(f): f for f in after_findings}

    all_keys = set(before_by_key) | set(after_by_key)

    finding_diffs: list[FindingDiff] = []
    for key in all_keys:
        pattern, title = key
        b = before_by_key.get(key)
        a = after_by_key.get(key)

        if b is None and a is not None:
            finding_diffs.append(
                FindingDiff(
                    pattern=pattern,
                    title=title,
                    kind="added",
                    severity_after=_get_severity(a),
                    intervention_after=_get_intervention(a),
                )
            )
        elif b is not None and a is None:
            finding_diffs.append(
                FindingDiff(
                    pattern=pattern,
                    title=title,
                    kind="removed",
                    severity_before=_get_severity(b),
                    intervention_before=_get_intervention(b),
                )
            )
        elif b is not None and a is not None:
            b_sev = _get_severity(b)
            a_sev = _get_severity(a)
            b_int = _get_intervention(b)
            a_int = _get_intervention(a)

            if b_sev != a_sev:
                finding_diffs.append(
                    FindingDiff(
                        pattern=pattern,
                        title=title,
                        kind="severity_changed",
                        severity_before=b_sev,
                        severity_after=a_sev,
                        intervention_before=b_int,
                        intervention_after=a_int,
                    )
                )
            elif b_int != a_int:
                finding_diffs.append(
                    FindingDiff(
                        pattern=pattern,
                        title=title,
                        kind="intervention_changed",
                        severity_before=b_sev,
                        severity_after=a_sev,
                        intervention_before=b_int,
                        intervention_after=a_int,
                    )
                )
            else:
                finding_diffs.append(
                    FindingDiff(
                        pattern=pattern,
                        title=title,
                        kind="unchanged",
                        severity_before=b_sev,
                        severity_after=a_sev,
                    )
                )

    before_patterns = set(_get_per_pattern(before).keys())
    after_patterns = set(_get_per_pattern(after).keys())

    return ReportDelta(
        finding_diffs=finding_diffs,
        patterns_added=sorted(after_patterns - before_patterns),
        patterns_removed=sorted(before_patterns - after_patterns),
        before_count=len(before_findings),
        after_count=len(after_findings),
    )
