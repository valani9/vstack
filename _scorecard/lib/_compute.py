"""Scorecard computation — aggregate multi-pattern findings into
per-dimension scores and an overall grade.

The mapping from pattern to dimension is fixed at module level so
that all scorecards across a fleet are comparable. The mapping
follows the same 5-cluster taxonomy as the recipe catalog.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Any, Literal

from ._grade import Grade, score_to_grade

DimensionName = Literal[
    "reasoning",
    "coordination",
    "trust",
    "workload",
    "culture",
]


# Pattern → dimension mapping. Each pattern's findings contribute
# to its dimension's score. A pattern can map to multiple
# dimensions with different weights.
PATTERN_DIMENSIONS: dict[str, list[tuple[DimensionName, float]]] = {
    # Module 1 — Individual.
    "lewin": [("reasoning", 1.0)],
    "goleman_ei": [("trust", 0.7), ("culture", 0.3)],
    "johari": [("trust", 0.6), ("reasoning", 0.4)],
    "danva_emotion": [("trust", 0.8), ("workload", 0.2)],
    "cognitive_reappraisal": [("workload", 0.7), ("trust", 0.3)],
    "yerkes_dodson": [("workload", 1.0)],
    "hexaco": [("trust", 0.5), ("culture", 0.5)],
    "grant_strengths": [("reasoning", 0.4), ("workload", 0.3), ("trust", 0.3)],
    "motivation_traps": [("reasoning", 0.5), ("workload", 0.5)],
    "sdt_reward": [("workload", 0.6), ("culture", 0.4)],
    "mcgregor": [("coordination", 0.8), ("trust", 0.2)],
    "vroom_expectancy": [("workload", 0.6), ("reasoning", 0.4)],
    # Module 2 — Team.
    "grpi": [("coordination", 1.0)],
    "process_gain_loss": [("coordination", 1.0)],
    "social_loafing": [("coordination", 0.6), ("workload", 0.4)],
    "superflocks": [("coordination", 0.5), ("culture", 0.5)],
    "lencioni": [("trust", 0.5), ("coordination", 0.5)],
    "trust_triangle": [("trust", 1.0)],
    "mcallister_trust": [("trust", 1.0)],
    "psych_safety": [("trust", 0.6), ("culture", 0.4)],
    "glaser_conversation": [("coordination", 0.5), ("workload", 0.5)],
    "feedback_triggers": [("trust", 0.7), ("coordination", 0.3)],
    "plus_delta": [("coordination", 0.7), ("trust", 0.3)],
    "smart_goal": [("coordination", 0.6), ("reasoning", 0.4)],
    "group_decision": [("coordination", 1.0)],
    "debate_pathology": [("reasoning", 0.5), ("coordination", 0.5)],
    "bias_stack": [("reasoning", 1.0)],
    "devils_advocate": [("reasoning", 0.5), ("coordination", 0.5)],
    "thomas_kilmann": [("trust", 0.5), ("coordination", 0.5)],
    "aar": [("reasoning", 0.4), ("coordination", 0.3), ("trust", 0.3)],
    # Module 3 — Organization.
    "schein_culture": [("culture", 1.0)],
    "robbins_culture": [("culture", 1.0)],
    "org_structure": [("coordination", 0.7), ("culture", 0.3)],
    "span_of_control": [("coordination", 1.0)],
}


SEVERITY_PENALTY = {
    "high": 25,
    "medium": 10,
    "low": 3,
}


@dataclass
class PatternContribution:
    """One pattern's contribution to the scorecard.

    A pattern contributes:
      - ``findings_count`` per severity bucket.
      - ``score_delta`` — the score adjustment this pattern caused.
      - ``dimension_share`` — fractional credit per dimension.
    """

    pattern: str
    findings_high: int = 0
    findings_medium: int = 0
    findings_low: int = 0
    score_delta: float = 0.0
    cost_usd: float = 0.0
    duration_ms: int = 0

    def total_findings(self) -> int:
        return self.findings_high + self.findings_medium + self.findings_low


@dataclass
class DimensionScore:
    """A single dimension's score + grade + contributing patterns."""

    name: DimensionName
    score: float  # 0-100
    contributing_patterns: list[str] = field(default_factory=list)
    findings_count: int = 0
    top_finding: str | None = None
    top_intervention: str | None = None

    @property
    def grade(self) -> Grade:
        return score_to_grade(self.score)


@dataclass
class ScoreCardConfig:
    """Configuration for scorecard computation.

    All fields are optional. Defaults are tuned for production use.
    """

    starting_score: float = 100.0
    """The score each dimension starts at. Findings deduct."""

    severity_penalty: dict[str, int] = field(default_factory=lambda: dict(SEVERITY_PENALTY))
    """How many points each finding severity deducts from a dimension."""

    cap_findings_per_dimension: int = 5
    """At most N findings count against any one dimension (avoids
    runaway penalties on noisy patterns)."""

    title: str | None = None
    """Optional title for the scorecard (rendered in HTML/markdown)."""

    agent_id: str | None = None
    """Optional agent ID being scored."""

    fleet_id: str | None = None
    """Optional fleet ID being scored."""


@dataclass
class ScoreCard:
    """A full multi-dimensional scorecard."""

    dimensions: dict[DimensionName, DimensionScore]
    pattern_contributions: list[PatternContribution]
    config: ScoreCardConfig

    metadata: dict[str, Any] = field(default_factory=dict)
    """Misc metadata: timestamps, source traces, etc."""

    @property
    def overall_score(self) -> float:
        """Mean of dimension scores."""
        if not self.dimensions:
            return 0.0
        return statistics.mean(d.score for d in self.dimensions.values())

    @property
    def overall_grade(self) -> Grade:
        return score_to_grade(self.overall_score)

    @property
    def total_cost_usd(self) -> float:
        return sum(p.cost_usd for p in self.pattern_contributions)

    @property
    def total_findings(self) -> int:
        return sum(p.total_findings() for p in self.pattern_contributions)

    def get_dimension(self, name: DimensionName) -> DimensionScore | None:
        return self.dimensions.get(name)

    def top_interventions(self, n: int = 3) -> list[tuple[str, str]]:
        """Return top N (dimension, intervention) pairs ordered by
        dimension severity (worst dimension first).
        """
        sorted_dims = sorted(
            self.dimensions.values(),
            key=lambda d: d.score,
        )
        result: list[tuple[str, str]] = []
        for dim in sorted_dims:
            if dim.top_intervention:
                result.append((dim.name, dim.top_intervention))
            if len(result) >= n:
                break
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_score": self.overall_score,
            "overall_grade": self.overall_grade.letter,
            "dimensions": {
                d.name: {
                    "score": d.score,
                    "grade": d.grade.letter,
                    "findings_count": d.findings_count,
                    "top_finding": d.top_finding,
                    "top_intervention": d.top_intervention,
                    "contributing_patterns": d.contributing_patterns,
                }
                for d in self.dimensions.values()
            },
            "pattern_contributions": [
                {
                    "pattern": p.pattern,
                    "findings_high": p.findings_high,
                    "findings_medium": p.findings_medium,
                    "findings_low": p.findings_low,
                    "score_delta": p.score_delta,
                    "cost_usd": p.cost_usd,
                    "duration_ms": p.duration_ms,
                }
                for p in self.pattern_contributions
            ],
            "total_cost_usd": self.total_cost_usd,
            "total_findings": self.total_findings,
            "metadata": self.metadata,
        }

    def to_markdown(self) -> str:
        from ._render import render_markdown

        return render_markdown(self)

    def to_html(self) -> str:
        from ._render import render_html

        return render_html(self)


def _extract_findings_per_pattern(reports: list[Any]) -> dict[str, list[Any]]:
    """Flatten per-pattern findings from a list of DiagnoseReport-shapes.

    Accepts both real ``DiagnoseReport`` instances and dict-shaped
    JSON deserializations.
    """
    by_pattern: dict[str, list[Any]] = {}
    for report in reports:
        findings = _get_findings(report)
        for f in findings:
            pattern = _get_pattern_name(f)
            if pattern:
                by_pattern.setdefault(pattern, []).append(f)
    return by_pattern


def _get_findings(report: Any) -> list[Any]:
    if hasattr(report, "findings"):
        return list(report.findings)
    if isinstance(report, dict):
        return list(report.get("findings", []))
    return []


def _get_pattern_name(finding: Any) -> str | None:
    value: object
    if hasattr(finding, "pattern"):
        value = finding.pattern
    elif isinstance(finding, dict):
        value = finding.get("pattern")
    else:
        return None
    return value if isinstance(value, str) else None


def _get_severity(finding: Any) -> str:
    value: object
    if hasattr(finding, "severity"):
        value = getattr(finding, "severity", "low")
    elif isinstance(finding, dict):
        value = finding.get("severity", "low")
    else:
        return "low"
    return value if isinstance(value, str) else "low"


def _get_title(finding: Any) -> str:
    value: object
    if hasattr(finding, "title"):
        value = getattr(finding, "title", "")
    elif isinstance(finding, dict):
        value = finding.get("title", "")
    else:
        return ""
    return value if isinstance(value, str) else ""


def _get_intervention(finding: Any) -> str:
    value: object
    if hasattr(finding, "intervention"):
        value = getattr(finding, "intervention", "")
    elif isinstance(finding, dict):
        value = finding.get("intervention", "")
    else:
        return ""
    return value if isinstance(value, str) else ""


def compute_scorecard(
    reports: list[Any] | None = None,
    *,
    traces: list[Any] | None = None,
    llm_client: Any | None = None,
    config: ScoreCardConfig | None = None,
) -> ScoreCard:
    """Compute a scorecard.

    Two ways to call:

    1. **Reports-first** — pass already-computed DiagnoseReport
       instances (or their dict-form JSON):

           reports = [diagnose(trace=t, llm_client=llm) for t in traces]
           scorecard = compute_scorecard(reports=reports)

    2. **Traces-first** — pass traces + an LLM client; the function
       runs ``diagnose()`` on each trace internally:

           scorecard = compute_scorecard(
               traces=traces,
               llm_client=llm,
           )

    The reports-first form is recommended for production because
    it lets you control which patterns ran.
    """
    cfg = config if config is not None else ScoreCardConfig()

    if reports is None:
        if traces is None or llm_client is None:
            raise ValueError("compute_scorecard requires either reports=, or traces= + llm_client=")
        from vstack.diagnose import diagnose

        reports = [diagnose(trace=t, llm_client=llm_client) for t in traces]

    findings_by_pattern = _extract_findings_per_pattern(reports)

    # Compute per-pattern contributions.
    contributions: list[PatternContribution] = []
    for pattern, findings in findings_by_pattern.items():
        high = sum(1 for f in findings if _get_severity(f) == "high")
        medium = sum(1 for f in findings if _get_severity(f) == "medium")
        low = sum(1 for f in findings if _get_severity(f) == "low")

        contributions.append(
            PatternContribution(
                pattern=pattern,
                findings_high=high,
                findings_medium=medium,
                findings_low=low,
                score_delta=-(
                    high * cfg.severity_penalty["high"]
                    + medium * cfg.severity_penalty["medium"]
                    + low * cfg.severity_penalty["low"]
                ),
            )
        )

    # Compute per-dimension scores.
    dimensions: dict[DimensionName, DimensionScore] = {}
    for dim_name in ("reasoning", "coordination", "trust", "workload", "culture"):
        score = cfg.starting_score
        contributing: list[str] = []
        total_findings = 0
        top_severity = ""
        top_finding = None
        top_intervention = None

        for pattern, findings in findings_by_pattern.items():
            mapping = PATTERN_DIMENSIONS.get(pattern, [])
            for dn, weight in mapping:
                if dn != dim_name:
                    continue
                contributing.append(pattern)

                # Cap at N findings per pattern per dimension.
                capped = findings[: cfg.cap_findings_per_dimension]
                total_findings += len(capped)
                for f in capped:
                    sev = _get_severity(f)
                    penalty = cfg.severity_penalty.get(sev, 0) * weight
                    score -= penalty

                    # Track top finding by severity.
                    if _is_higher_severity(sev, top_severity):
                        top_severity = sev
                        top_finding = _get_title(f)
                        top_intervention = _get_intervention(f)

        dimensions[dim_name] = DimensionScore(
            name=dim_name,
            score=max(0.0, min(100.0, score)),
            contributing_patterns=sorted(set(contributing)),
            findings_count=total_findings,
            top_finding=top_finding,
            top_intervention=top_intervention,
        )

    return ScoreCard(
        dimensions=dimensions,
        pattern_contributions=contributions,
        config=cfg,
        metadata={
            "agent_id": cfg.agent_id,
            "fleet_id": cfg.fleet_id,
            "title": cfg.title,
            "n_reports": len(reports),
        },
    )


_SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2, "": -1}


def _is_higher_severity(a: str, b: str) -> bool:
    return _SEVERITY_ORDER.get(a, -1) > _SEVERITY_ORDER.get(b, -1)
