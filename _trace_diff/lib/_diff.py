"""Trace diff — structural comparison."""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Literal


StepDiffKind = Literal["unchanged", "added", "removed", "changed"]


@dataclass
class StepDiff:
    """One step's change between before and after."""

    kind: StepDiffKind
    before_index: int | None = None
    after_index: int | None = None
    before_type: str = ""
    after_type: str = ""
    before_content: str = ""
    after_content: str = ""

    @property
    def type_changed(self) -> bool:
        return self.kind == "changed" and self.before_type != self.after_type

    @property
    def content_changed(self) -> bool:
        return self.kind == "changed" and self.before_content != self.after_content

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "before_index": self.before_index,
            "after_index": self.after_index,
            "before_type": self.before_type,
            "after_type": self.after_type,
            "type_changed": self.type_changed,
            "content_changed": self.content_changed,
        }


@dataclass
class TraceDelta:
    """Full delta between two traces."""

    goal_before: str = ""
    goal_after: str = ""
    outcome_before: str = ""
    outcome_after: str = ""
    success_before: bool = False
    success_after: bool = False
    step_count_before: int = 0
    step_count_after: int = 0
    step_diffs: list[StepDiff] = field(default_factory=list)

    @property
    def goal_changed(self) -> bool:
        return self.goal_before != self.goal_after

    @property
    def outcome_changed(self) -> bool:
        return self.outcome_before != self.outcome_after

    @property
    def success_flipped(self) -> bool:
        return self.success_before != self.success_after

    @property
    def step_count_delta(self) -> int:
        return self.step_count_after - self.step_count_before

    @property
    def added_steps(self) -> list[StepDiff]:
        return [d for d in self.step_diffs if d.kind == "added"]

    @property
    def removed_steps(self) -> list[StepDiff]:
        return [d for d in self.step_diffs if d.kind == "removed"]

    @property
    def changed_steps(self) -> list[StepDiff]:
        return [d for d in self.step_diffs if d.kind == "changed"]

    @property
    def unchanged_steps(self) -> list[StepDiff]:
        return [d for d in self.step_diffs if d.kind == "unchanged"]

    def is_regression(self) -> bool:
        """True if before succeeded but after failed."""
        return self.success_before and not self.success_after

    def is_recovery(self) -> bool:
        """True if before failed but after succeeded."""
        return not self.success_before and self.success_after

    def summary(self) -> str:
        regression = "REGRESSION" if self.is_regression() else ""
        recovery = "RECOVERY" if self.is_recovery() else ""
        marker = regression or recovery or ""
        return (
            f"{marker} steps: {self.step_count_before} → {self.step_count_after}, "
            f"added: {len(self.added_steps)}, removed: {len(self.removed_steps)}, "
            f"changed: {len(self.changed_steps)}, unchanged: {len(self.unchanged_steps)}, "
            f"success: {self.success_before} → {self.success_after}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal_before": self.goal_before,
            "goal_after": self.goal_after,
            "goal_changed": self.goal_changed,
            "outcome_before": self.outcome_before,
            "outcome_after": self.outcome_after,
            "outcome_changed": self.outcome_changed,
            "success_before": self.success_before,
            "success_after": self.success_after,
            "success_flipped": self.success_flipped,
            "is_regression": self.is_regression(),
            "is_recovery": self.is_recovery(),
            "step_count_before": self.step_count_before,
            "step_count_after": self.step_count_after,
            "step_count_delta": self.step_count_delta,
            "added": len(self.added_steps),
            "removed": len(self.removed_steps),
            "changed": len(self.changed_steps),
            "unchanged": len(self.unchanged_steps),
            "step_diffs": [d.to_dict() for d in self.step_diffs],
        }

    def to_markdown(self) -> str:
        lines = ["# Trace Delta", ""]
        lines.append(f"**Summary**: {self.summary()}")
        lines.append("")

        if self.goal_changed:
            lines.append("## Goal Changed")
            lines.append(f"- Before: `{self.goal_before}`")
            lines.append(f"- After: `{self.goal_after}`")
            lines.append("")

        if self.success_flipped:
            verdict = "REGRESSION" if self.is_regression() else "RECOVERY"
            lines.append(f"## {verdict}")
            lines.append(f"- Success: {self.success_before} → {self.success_after}")
            lines.append("")

        if self.outcome_changed:
            lines.append("## Outcome Changed")
            lines.append(f"- Before: {self.outcome_before}")
            lines.append(f"- After: {self.outcome_after}")
            lines.append("")

        if self.added_steps:
            lines.append(f"## ➕ Added Steps ({len(self.added_steps)})")
            for d in self.added_steps:
                lines.append(f"- @{d.after_index}: [{d.after_type}] {d.after_content[:80]}")
            lines.append("")

        if self.removed_steps:
            lines.append(f"## ➖ Removed Steps ({len(self.removed_steps)})")
            for d in self.removed_steps:
                lines.append(f"- @{d.before_index}: [{d.before_type}] {d.before_content[:80]}")
            lines.append("")

        if self.changed_steps:
            lines.append(f"## ✏️ Changed Steps ({len(self.changed_steps)})")
            for d in self.changed_steps:
                if d.type_changed:
                    lines.append(
                        f"- @{d.before_index}/{d.after_index}: "
                        f"type {d.before_type} → {d.after_type}"
                    )
                else:
                    lines.append(
                        f"- @{d.before_index}/{d.after_index}: [{d.before_type}] content changed"
                    )
            lines.append("")

        return "\n".join(lines)


def _get_steps(trace: Any) -> list[Any]:
    if isinstance(trace, dict):
        return list(trace.get("steps", []))
    if hasattr(trace, "steps"):
        return list(trace.steps)
    return []


def _step_field(step: Any, field: str, default: str = "") -> str:
    if isinstance(step, dict):
        return str(step.get(field, default))
    return str(getattr(step, field, default))


def _step_fingerprint(step: Any) -> str:
    """Compact string representation for SequenceMatcher."""
    type_ = _step_field(step, "type")
    content = _step_field(step, "content")
    return f"{type_}|{content[:200]}"


def diff_traces(before: Any, after: Any) -> TraceDelta:
    """Compute a structural delta between two traces."""
    before_steps = _get_steps(before)
    after_steps = _get_steps(after)

    before_fingerprints = [_step_fingerprint(s) for s in before_steps]
    after_fingerprints = [_step_fingerprint(s) for s in after_steps]

    # Use SequenceMatcher for alignment (Myers-style diff).
    matcher = SequenceMatcher(None, before_fingerprints, after_fingerprints)

    step_diffs: list[StepDiff] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                step_diffs.append(
                    StepDiff(
                        kind="unchanged",
                        before_index=i1 + k,
                        after_index=j1 + k,
                        before_type=_step_field(before_steps[i1 + k], "type"),
                        after_type=_step_field(after_steps[j1 + k], "type"),
                        before_content=_step_field(before_steps[i1 + k], "content"),
                        after_content=_step_field(after_steps[j1 + k], "content"),
                    )
                )
        elif tag == "replace":
            # Treat 1:1 replacement as "changed", others as add+remove.
            length_before = i2 - i1
            length_after = j2 - j1
            common = min(length_before, length_after)
            for k in range(common):
                step_diffs.append(
                    StepDiff(
                        kind="changed",
                        before_index=i1 + k,
                        after_index=j1 + k,
                        before_type=_step_field(before_steps[i1 + k], "type"),
                        after_type=_step_field(after_steps[j1 + k], "type"),
                        before_content=_step_field(before_steps[i1 + k], "content"),
                        after_content=_step_field(after_steps[j1 + k], "content"),
                    )
                )
            for k in range(common, length_before):
                step_diffs.append(
                    StepDiff(
                        kind="removed",
                        before_index=i1 + k,
                        before_type=_step_field(before_steps[i1 + k], "type"),
                        before_content=_step_field(before_steps[i1 + k], "content"),
                    )
                )
            for k in range(common, length_after):
                step_diffs.append(
                    StepDiff(
                        kind="added",
                        after_index=j1 + k,
                        after_type=_step_field(after_steps[j1 + k], "type"),
                        after_content=_step_field(after_steps[j1 + k], "content"),
                    )
                )
        elif tag == "delete":
            for k in range(i2 - i1):
                step_diffs.append(
                    StepDiff(
                        kind="removed",
                        before_index=i1 + k,
                        before_type=_step_field(before_steps[i1 + k], "type"),
                        before_content=_step_field(before_steps[i1 + k], "content"),
                    )
                )
        elif tag == "insert":
            for k in range(j2 - j1):
                step_diffs.append(
                    StepDiff(
                        kind="added",
                        after_index=j1 + k,
                        after_type=_step_field(after_steps[j1 + k], "type"),
                        after_content=_step_field(after_steps[j1 + k], "content"),
                    )
                )

    return TraceDelta(
        goal_before=_field(before, "goal"),
        goal_after=_field(after, "goal"),
        outcome_before=_field(before, "outcome"),
        outcome_after=_field(after, "outcome"),
        success_before=_field_bool(before, "success"),
        success_after=_field_bool(after, "success"),
        step_count_before=len(before_steps),
        step_count_after=len(after_steps),
        step_diffs=step_diffs,
    )


def _field(trace: Any, field: str) -> str:
    if isinstance(trace, dict):
        return str(trace.get(field, ""))
    return str(getattr(trace, field, ""))


def _field_bool(trace: Any, field: str) -> bool:
    if isinstance(trace, dict):
        return bool(trace.get(field, False))
    return bool(getattr(trace, field, False))
