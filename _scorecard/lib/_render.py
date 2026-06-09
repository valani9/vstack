"""Scorecard rendering — markdown, text, HTML.

Text rendering is for terminal output (no colors by default).
Markdown rendering is for documentation embed.
HTML rendering is for the dashboard.
"""

from __future__ import annotations

from ._compute import ScoreCard
from ._grade import grade_to_color, grade_to_emoji


def render_text(scorecard: ScoreCard) -> str:
    """Plain-text rendering suitable for terminal output."""
    lines: list[str] = []
    title = scorecard.config.title or "Scorecard"
    lines.append(f"=== {title} ===")
    lines.append("")

    overall_grade = scorecard.overall_grade
    lines.append(f"OVERALL: {overall_grade.letter} ({scorecard.overall_score:.1f}/100)")
    lines.append("")

    lines.append(f"{'Dimension':15s}  {'Score':>6s}  {'Grade':>5s}  Findings")
    lines.append(f"{'-' * 15}  {'-' * 6}  {'-' * 5}  --------")
    for name in ("reasoning", "coordination", "trust", "workload", "culture"):
        d = scorecard.get_dimension(name)
        if d is None:
            continue
        lines.append(f"{d.name:15s}  {d.score:6.1f}  {d.grade.letter:>5s}  {d.findings_count}")

    lines.append("")
    lines.append("Top interventions:")
    for i, (dim, intervention) in enumerate(scorecard.top_interventions(), 1):
        lines.append(f"  {i}. [{dim}] {intervention[:80]}")

    lines.append("")
    lines.append(
        f"Total cost: ${scorecard.total_cost_usd:.4f} | Total findings: {scorecard.total_findings}"
    )

    return "\n".join(lines)


def render_markdown(scorecard: ScoreCard) -> str:
    """Markdown rendering suitable for embedding in docs."""
    lines: list[str] = []
    title = scorecard.config.title or "Scorecard"
    lines.append(f"# {title}")
    lines.append("")

    overall_grade = scorecard.overall_grade
    emoji = grade_to_emoji(overall_grade)
    lines.append(
        f"**Overall**: {emoji} **{overall_grade.letter}** ({scorecard.overall_score:.1f}/100)"
    )
    lines.append("")

    if scorecard.config.agent_id:
        lines.append(f"**Agent**: `{scorecard.config.agent_id}`")
    if scorecard.config.fleet_id:
        lines.append(f"**Fleet**: `{scorecard.config.fleet_id}`")
    if scorecard.config.agent_id or scorecard.config.fleet_id:
        lines.append("")

    lines.append("## Dimensions")
    lines.append("")
    lines.append("| Dimension     | Score   | Grade | Findings |")
    lines.append("|---------------|---------|-------|----------|")
    for name in ("reasoning", "coordination", "trust", "workload", "culture"):
        d = scorecard.get_dimension(name)
        if d is None:
            continue
        lines.append(
            f"| {d.name:13s} | {d.score:6.1f}  | "
            f"{grade_to_emoji(d.grade)} **{d.grade.letter}** | "
            f"{d.findings_count:8d} |"
        )

    lines.append("")
    lines.append("## Top Interventions")
    lines.append("")
    for i, (dim, intervention) in enumerate(scorecard.top_interventions(), 1):
        lines.append(f"{i}. **[{dim}]** {intervention}")

    lines.append("")
    lines.append("## Per-Pattern Contributions")
    lines.append("")
    lines.append("| Pattern              | High | Med | Low | Δ Score |")
    lines.append("|----------------------|------|-----|-----|---------|")
    for p in sorted(
        scorecard.pattern_contributions,
        key=lambda p: p.score_delta,
    ):
        lines.append(
            f"| {p.pattern:20s} | {p.findings_high:4d} | "
            f"{p.findings_medium:3d} | {p.findings_low:3d} | "
            f"{p.score_delta:+7.1f} |"
        )

    lines.append("")
    lines.append(
        f"**Total cost**: ${scorecard.total_cost_usd:.4f}  |  "
        f"**Total findings**: {scorecard.total_findings}"
    )

    return "\n".join(lines)


HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
body {{ background: #0a0a0a; color: #e5e5e5; font-family: -apple-system, system-ui, sans-serif; padding: 2rem; max-width: 1200px; margin: 0 auto; }}
h1 {{ color: {overall_color}; border-bottom: 2px solid {overall_color}; padding-bottom: 0.5rem; }}
.overall {{ font-size: 4rem; font-weight: bold; color: {overall_color}; text-align: center; padding: 2rem; margin: 1rem 0; background: #1a1a1a; border-radius: 1rem; }}
.dimension {{ display: flex; justify-content: space-between; align-items: center; padding: 1rem; background: #1a1a1a; margin: 0.5rem 0; border-radius: 0.5rem; border-left: 5px solid #444; }}
.dimension-name {{ font-size: 1.2rem; font-weight: 500; text-transform: capitalize; }}
.dimension-grade {{ font-size: 2rem; font-weight: bold; min-width: 80px; text-align: center; padding: 0.5rem 1rem; border-radius: 0.5rem; }}
.dimension-score {{ font-family: ui-monospace, Menlo, monospace; color: #999; min-width: 80px; text-align: right; }}
.dimension-findings {{ color: #aaa; min-width: 100px; }}
.section {{ margin: 2rem 0; }}
.section h2 {{ color: #aaa; font-size: 1.2rem; text-transform: uppercase; letter-spacing: 0.1em; }}
.intervention {{ background: #1a1a1a; padding: 1rem; margin: 0.5rem 0; border-radius: 0.5rem; border-left: 3px solid #3b82f6; }}
.intervention-dim {{ font-size: 0.85rem; color: #3b82f6; text-transform: uppercase; letter-spacing: 0.05em; }}
.footer {{ text-align: center; color: #666; margin-top: 3rem; font-size: 0.9rem; }}
table {{ width: 100%; border-collapse: collapse; }}
th, td {{ padding: 0.5rem; text-align: left; border-bottom: 1px solid #333; }}
th {{ color: #aaa; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; }}
</style>
</head>
<body>
<h1>{title}</h1>
<div class="overall">{overall_emoji} {overall_grade} ({overall_score:.1f}/100)</div>

<div class="section">
<h2>Dimensions</h2>
{dimensions_html}
</div>

<div class="section">
<h2>Top Interventions</h2>
{interventions_html}
</div>

<div class="section">
<h2>Per-Pattern Contributions</h2>
<table>
<tr><th>Pattern</th><th>High</th><th>Medium</th><th>Low</th><th>Δ Score</th></tr>
{patterns_html}
</table>
</div>

<div class="footer">
Total cost: ${total_cost:.4f} | Total findings: {total_findings}
</div>
</body>
</html>
"""


DIMENSION_TEMPLATE = """\
<div class="dimension" style="border-left-color: {color};">
  <div class="dimension-name">{name}</div>
  <div class="dimension-grade" style="background: {color}; color: white;">{grade}</div>
  <div class="dimension-score">{score:.1f} / 100</div>
  <div class="dimension-findings">{findings} findings</div>
</div>
"""


INTERVENTION_TEMPLATE = """\
<div class="intervention">
  <div class="intervention-dim">{dim}</div>
  <div>{intervention}</div>
</div>
"""


PATTERN_ROW_TEMPLATE = """\
<tr><td>{pattern}</td><td>{high}</td><td>{med}</td><td>{low}</td><td>{delta:+.1f}</td></tr>
"""


def render_html(scorecard: ScoreCard) -> str:
    """HTML rendering suitable for dashboard embed."""
    title = scorecard.config.title or "Scorecard"
    overall_grade = scorecard.overall_grade

    dimensions_html = "".join(
        DIMENSION_TEMPLATE.format(
            name=d.name,
            grade=d.grade.letter,
            score=d.score,
            color=grade_to_color(d.grade),
            findings=d.findings_count,
        )
        for d in [
            scorecard.get_dimension(n)
            for n in ("reasoning", "coordination", "trust", "workload", "culture")
        ]
        if d is not None
    )

    interventions_html = "".join(
        INTERVENTION_TEMPLATE.format(dim=dim, intervention=intervention)
        for dim, intervention in scorecard.top_interventions()
    )

    patterns_html = "".join(
        PATTERN_ROW_TEMPLATE.format(
            pattern=p.pattern,
            high=p.findings_high,
            med=p.findings_medium,
            low=p.findings_low,
            delta=p.score_delta,
        )
        for p in sorted(
            scorecard.pattern_contributions,
            key=lambda p: p.score_delta,
        )
    )

    return HTML_TEMPLATE.format(
        title=title,
        overall_grade=overall_grade.letter,
        overall_emoji=grade_to_emoji(overall_grade),
        overall_score=scorecard.overall_score,
        overall_color=grade_to_color(overall_grade),
        dimensions_html=dimensions_html,
        interventions_html=interventions_html or "<p>No interventions surfaced.</p>",
        patterns_html=patterns_html or "<tr><td colspan='5'>No patterns ran.</td></tr>",
        total_cost=scorecard.total_cost_usd,
        total_findings=scorecard.total_findings,
    )
