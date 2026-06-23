"""Gate primitives + composition."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol, cast


def _get_findings(report: Any) -> list[Any]:
    if isinstance(report, dict):
        return list(report.get("findings", []))
    if hasattr(report, "findings"):
        return list(report.findings)
    return []


def _get_severity(finding: Any) -> str:
    if isinstance(finding, dict):
        return cast(str, finding.get("severity", "low"))
    return cast(str, getattr(finding, "severity", "low"))


def _get_attr(obj: Any, field: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(field, default)
    return getattr(obj, field, default)


@dataclass
class GateFailure:
    """A single failing gate."""

    gate_name: str
    reason: str
    observed: Any = None
    threshold: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate_name": self.gate_name,
            "reason": self.reason,
            "observed": self.observed,
            "threshold": self.threshold,
        }


@dataclass
class GateResult:
    """Outcome of evaluating a GateSet."""

    passed: bool
    failures: list[GateFailure] = field(default_factory=list)
    gates_checked: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "failures": [f.to_dict() for f in self.failures],
            "gates_checked": self.gates_checked,
        }

    def exit_code(self) -> int:
        return 0 if self.passed else 1


class Gate(Protocol):
    """A single gate. Implementors return ``None`` on pass or a
    ``GateFailure`` on fail."""

    @property
    def name(self) -> str: ...

    def check(
        self, *, report: Any = None, baseline: Any = None, eval_metrics: Any = None
    ) -> GateFailure | None:  # pragma: no cover
        ...


@dataclass
class SeverityCountGate:
    """Fail if the number of findings at a severity exceeds a max."""

    severity: str = "high"
    max_count: int = 0
    _name: str = ""

    @property
    def name(self) -> str:
        return self._name or f"severity_count[{self.severity}]<={self.max_count}"

    def check(self, *, report: Any = None, **_kwargs: Any) -> GateFailure | None:
        if report is None:
            return None
        findings = _get_findings(report)
        count = sum(1 for f in findings if _get_severity(f) == self.severity)
        if count > self.max_count:
            return GateFailure(
                gate_name=self.name,
                reason=f"{count} {self.severity} findings, max allowed = {self.max_count}",
                observed=count,
                threshold=self.max_count,
            )
        return None


@dataclass
class F1Gate:
    """Fail if eval F1 is below threshold."""

    min_f1: float = 0.7
    _name: str = ""

    @property
    def name(self) -> str:
        return self._name or f"f1>={self.min_f1}"

    def check(self, *, eval_metrics: Any = None, **_kwargs: Any) -> GateFailure | None:
        if eval_metrics is None:
            return None
        f1 = _get_attr(eval_metrics, "f1", 0.0)
        if f1 < self.min_f1:
            return GateFailure(
                gate_name=self.name,
                reason=f"F1={f1:.3f} below threshold {self.min_f1:.3f}",
                observed=f1,
                threshold=self.min_f1,
            )
        return None


@dataclass
class PrecisionGate:
    min_precision: float = 0.7
    _name: str = ""

    @property
    def name(self) -> str:
        return self._name or f"precision>={self.min_precision}"

    def check(self, *, eval_metrics: Any = None, **_kwargs: Any) -> GateFailure | None:
        if eval_metrics is None:
            return None
        precision = _get_attr(eval_metrics, "precision", 0.0)
        if precision < self.min_precision:
            return GateFailure(
                gate_name=self.name,
                reason=f"Precision={precision:.3f} below threshold {self.min_precision:.3f}",
                observed=precision,
                threshold=self.min_precision,
            )
        return None


@dataclass
class RecallGate:
    min_recall: float = 0.7
    _name: str = ""

    @property
    def name(self) -> str:
        return self._name or f"recall>={self.min_recall}"

    def check(self, *, eval_metrics: Any = None, **_kwargs: Any) -> GateFailure | None:
        if eval_metrics is None:
            return None
        recall = _get_attr(eval_metrics, "recall", 0.0)
        if recall < self.min_recall:
            return GateFailure(
                gate_name=self.name,
                reason=f"Recall={recall:.3f} below threshold {self.min_recall:.3f}",
                observed=recall,
                threshold=self.min_recall,
            )
        return None


@dataclass
class BaselineComparisonGate:
    """Fail if the current report shows more findings (or higher
    severity) than the baseline beyond a tolerance."""

    max_score_drop: float = 10.0
    """Maximum allowed drop in 'overall_score' between baseline and current."""

    max_new_high: int = 0
    """Maximum new high-severity findings vs baseline."""

    _name: str = ""

    @property
    def name(self) -> str:
        return self._name or "baseline_comparison"

    def check(
        self,
        *,
        report: Any = None,
        baseline: Any = None,
        **_kwargs: Any,
    ) -> GateFailure | None:
        if report is None or baseline is None:
            return None

        # Count high-severity findings in each.
        report_findings = _get_findings(report)
        baseline_findings = _get_findings(baseline)
        report_high = sum(1 for f in report_findings if _get_severity(f) == "high")
        baseline_high = sum(1 for f in baseline_findings if _get_severity(f) == "high")
        new_high = max(0, report_high - baseline_high)

        if new_high > self.max_new_high:
            return GateFailure(
                gate_name=self.name,
                reason=f"{new_high} new high-severity findings vs baseline; max allowed = {self.max_new_high}",
                observed=new_high,
                threshold=self.max_new_high,
            )

        # Optional: compare 'overall_score' if both have it.
        report_score = _get_attr(report, "overall_score", None)
        baseline_score = _get_attr(baseline, "overall_score", None)
        if report_score is not None and baseline_score is not None:
            drop = baseline_score - report_score
            if drop > self.max_score_drop:
                return GateFailure(
                    gate_name=self.name,
                    reason=f"Overall score dropped {drop:.1f} pts; max allowed = {self.max_score_drop}",
                    observed=drop,
                    threshold=self.max_score_drop,
                )

        return None


@dataclass
class CustomGate:
    """Gate driven by a user-supplied predicate."""

    name_: str
    predicate: Callable[..., GateFailure | None]

    @property
    def name(self) -> str:
        return self.name_

    def check(self, **kwargs: Any) -> GateFailure | None:
        return self.predicate(**kwargs)


@dataclass
class GateSet:
    """A composable set of gates, evaluated in order."""

    gates: list[Gate] = field(default_factory=list)

    def check(
        self,
        *,
        report: Any = None,
        baseline: Any = None,
        eval_metrics: Any = None,
    ) -> GateResult:
        failures = []
        for gate in self.gates:
            try:
                failure = gate.check(
                    report=report,
                    baseline=baseline,
                    eval_metrics=eval_metrics,
                )
            except Exception as exc:
                failure = GateFailure(
                    gate_name=getattr(gate, "name", "unknown"),
                    reason=f"gate raised: {exc}",
                )
            if failure is not None:
                failures.append(failure)

        return GateResult(
            passed=len(failures) == 0,
            failures=failures,
            gates_checked=len(self.gates),
        )

    def add(self, gate: Gate) -> GateSet:
        return GateSet(gates=[*self.gates, gate])

    def to_dict(self) -> dict[str, Any]:
        return {"gates": [getattr(g, "name", "unknown") for g in self.gates]}
