"""vstack.scorecard — per-agent multi-pattern scorecard with letter grades.

The scorecard module aggregates findings from many vstack patterns
into a single per-agent (or per-fleet) scorecard with:

  - Per-dimension scores (Reasoning / Coordination / Trust /
    Workload / Culture).
  - Letter grade (A+ to F) per dimension.
  - Trend indicator (improving / stable / regressing) vs a baseline.
  - Top 3 highest-impact interventions.
  - Cost summary across the patterns evaluated.

Use cases
---------

* **Production triage.** Run on a representative sample of last
  week's traces; surface the dimension grade.
* **Pre-deploy gate.** Run on regression traces; block deploy if
  any dimension regresses to a worse grade.
* **Quarterly review.** Run on a fleet sample; produce a
  dashboard-ready scorecard PNG / HTML.

Quick start
-----------

    from vstack.scorecard import (
        ScoreCard,
        ScoreCardConfig,
        compute_scorecard,
    )
    from vstack.aar.clients import StubClient

    traces = [...]  # list of AgentTrace
    scorecard = compute_scorecard(
        traces=traces,
        llm_client=StubClient(),
        config=ScoreCardConfig(),
    )

    print(scorecard.to_markdown())
    print(scorecard.overall_grade)  # "A-" / "B+" / etc.

CLI
---

    vstack-scorecard compute --traces traces.json --out scorecard.json
    vstack-scorecard render scorecard.json --format html > scorecard.html
    vstack-scorecard compare baseline.json current.json
"""

from __future__ import annotations

from ._cli import main as _cli_main
from ._compare import (
    ScoreCardComparison,
    compare_scorecards,
)
from ._compute import (
    DimensionScore,
    PatternContribution,
    ScoreCard,
    ScoreCardConfig,
    compute_scorecard,
)
from ._grade import (
    GRADE_SCALE,
    Grade,
    score_to_grade,
)
from ._render import (
    render_html,
    render_markdown,
    render_text,
)

__all__ = [
    "DimensionScore",
    "GRADE_SCALE",
    "Grade",
    "PatternContribution",
    "ScoreCard",
    "ScoreCardComparison",
    "ScoreCardConfig",
    "_cli_main",
    "compare_scorecards",
    "compute_scorecard",
    "render_html",
    "render_markdown",
    "render_text",
    "score_to_grade",
]
