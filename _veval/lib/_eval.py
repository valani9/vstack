"""Pattern eval harness — ground truth comparison."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class EvalCase:
    """A single labeled eval case."""

    trace: Any
    expected_severity: str  # "high" | "medium" | "low" | "none"
    expected_pattern: str | None = None
    case_id: str = ""
    description: str = ""

    def is_positive(self) -> bool:
        """True if this case expects a finding (severity != none)."""
        return self.expected_severity != "none"


@dataclass
class EvalRun:
    """Result of running a single eval case."""

    case_id: str
    expected_severity: str
    predicted_severity: str
    expected_positive: bool
    predicted_positive: bool

    @property
    def is_correct(self) -> bool:
        return self.expected_severity == self.predicted_severity

    @property
    def is_tp(self) -> bool:
        """True positive: expected pos AND predicted pos."""
        return self.expected_positive and self.predicted_positive

    @property
    def is_fp(self) -> bool:
        """False positive: expected neg AND predicted pos."""
        return not self.expected_positive and self.predicted_positive

    @property
    def is_fn(self) -> bool:
        """False negative: expected pos AND predicted neg."""
        return self.expected_positive and not self.predicted_positive

    @property
    def is_tn(self) -> bool:
        """True negative: expected neg AND predicted neg."""
        return not self.expected_positive and not self.predicted_positive

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "expected_severity": self.expected_severity,
            "predicted_severity": self.predicted_severity,
            "expected_positive": self.expected_positive,
            "predicted_positive": self.predicted_positive,
            "is_correct": self.is_correct,
        }


@dataclass
class ConfusionMatrix:
    """2x2 confusion matrix (positive vs negative)."""

    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0

    @property
    def total(self) -> int:
        return self.tp + self.fp + self.fn + self.tn

    def to_dict(self) -> dict[str, int]:
        return {"tp": self.tp, "fp": self.fp, "fn": self.fn, "tn": self.tn}


@dataclass
class EvalMetrics:
    """Standard classification metrics."""

    precision: float
    recall: float
    f1: float
    accuracy: float
    confusion: ConfusionMatrix
    n_cases: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "accuracy": self.accuracy,
            "confusion": self.confusion.to_dict(),
            "n_cases": self.n_cases,
        }


@dataclass
class EvalResult:
    """Aggregated result from an EvalHarness run."""

    runs: list[EvalRun] = field(default_factory=list)
    pattern: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def metrics(self) -> EvalMetrics:
        return compute_metrics(self)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern": self.pattern,
            "runs": [r.to_dict() for r in self.runs],
            "n_runs": len(self.runs),
            "metadata": self.metadata,
        }

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: str | Path) -> EvalResult:
        data = json.loads(Path(path).read_text())
        runs = [
            EvalRun(
                case_id=r["case_id"],
                expected_severity=r["expected_severity"],
                predicted_severity=r["predicted_severity"],
                expected_positive=r["expected_positive"],
                predicted_positive=r["predicted_positive"],
            )
            for r in data.get("runs", [])
        ]
        return cls(
            runs=runs,
            pattern=data.get("pattern", ""),
            metadata=data.get("metadata", {}),
        )


def compute_metrics(result: EvalResult) -> EvalMetrics:
    """Compute precision/recall/F1/accuracy + confusion matrix."""
    cm = ConfusionMatrix()
    for r in result.runs:
        if r.is_tp:
            cm.tp += 1
        elif r.is_fp:
            cm.fp += 1
        elif r.is_fn:
            cm.fn += 1
        elif r.is_tn:
            cm.tn += 1

    n = len(result.runs)
    if n == 0:
        return EvalMetrics(
            precision=0.0,
            recall=0.0,
            f1=0.0,
            accuracy=0.0,
            confusion=cm,
            n_cases=0,
        )

    correct = sum(1 for r in result.runs if r.is_correct)
    accuracy = correct / n

    if cm.tp + cm.fp == 0:
        precision = 0.0
    else:
        precision = cm.tp / (cm.tp + cm.fp)

    if cm.tp + cm.fn == 0:
        recall = 0.0
    else:
        recall = cm.tp / (cm.tp + cm.fn)

    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)

    return EvalMetrics(
        precision=precision,
        recall=recall,
        f1=f1,
        accuracy=accuracy,
        confusion=cm,
        n_cases=n,
    )


class EvalHarness:
    """Run eval cases through a pattern; collect ground-truth comparison."""

    def __init__(self, *, cases: list[EvalCase], pattern: str):
        self.cases = cases
        self.pattern = pattern

    def run(
        self,
        *,
        llm_client: Any,
        mode: str = "standard",
    ) -> EvalResult:
        runs = []
        for i, case in enumerate(self.cases):
            run = self._run_one(case=case, case_idx=i, llm_client=llm_client, mode=mode)
            runs.append(run)
        return EvalResult(
            runs=runs,
            pattern=self.pattern,
            metadata={"mode": mode, "n_cases": len(self.cases)},
        )

    def _run_one(
        self,
        *,
        case: EvalCase,
        case_idx: int,
        llm_client: Any,
        mode: str,
    ) -> EvalRun:
        from vstack.diagnose import diagnose

        case_id = case.case_id or f"case-{case_idx}"

        try:
            report = diagnose(
                trace=case.trace,
                llm_client=llm_client,
                patterns=[self.pattern],
                mode=mode,
            )
        except Exception:
            return EvalRun(
                case_id=case_id,
                expected_severity=case.expected_severity,
                predicted_severity="error",
                expected_positive=case.is_positive(),
                predicted_positive=False,
            )

        findings = _get_findings(report)
        predicted_severity = _max_severity(findings)
        predicted_positive = predicted_severity != "none"

        return EvalRun(
            case_id=case_id,
            expected_severity=case.expected_severity,
            predicted_severity=predicted_severity,
            expected_positive=case.is_positive(),
            predicted_positive=predicted_positive,
        )


def _get_findings(report: Any) -> list[Any]:
    if isinstance(report, dict):
        return list(report.get("findings", []))
    if hasattr(report, "findings"):
        return list(report.findings)
    return []


_SEVERITY_RANK = {"none": 0, "low": 1, "medium": 2, "high": 3}


def _max_severity(findings: list[Any]) -> str:
    if not findings:
        return "none"
    severities: list[str] = []
    for f in findings:
        if isinstance(f, dict):
            severities.append(str(f.get("severity", "low")))
        else:
            severities.append(str(getattr(f, "severity", "low")))
    return max(severities, key=lambda s: _SEVERITY_RANK.get(s, 0))
