"""Tests for the smart findings extractor in vstack.diagnose.adapters.

The extractor's contract is lossless extraction across the field-name
conventions vstack patterns actually use. These tests construct
SimpleNamespace results in the shapes real analyzers produce
(Lencioni dysfunctions, Bias Stack biases, AAR lessons, Trust
Triangle legs, Psych Safety behaviors, Heffernan metrics, etc.) and
verify that:

  1. Each evidence list yields N Findings, not 1.
  2. Per-item categorical title fields (``dysfunction``, ``leg``,
     ``factor``, ...) populate Finding.title.
  3. Pattern-specific severity field names (``severity_of_gap``,
     ``severity_of_absence``, ``inverted_u_position``) normalize to
     the canonical 7-point scale.
  4. ``evidence_quotes`` lists collapse to a one-quote string.
  5. The registered per-pattern adapter override path takes precedence
     over the smart extractor.
  6. Backward compatibility: bare ``findings=[...]`` lists still work.
  7. Fallback: result-with-severity-and-title-only still produces one
     Finding (legacy single-object path).
"""

from __future__ import annotations

from types import SimpleNamespace

from vstack.diagnose import Finding
from vstack.diagnose.adapters import (
    ADAPTERS,
    extract_findings,
    register,
)


# --- lossless multi-finding extraction (the main win) ----------------


def test_extracts_n_lencioni_dysfunctions() -> None:
    result = SimpleNamespace(
        dysfunctions=[
            SimpleNamespace(
                dysfunction="absence-of-trust",
                severity="high",
                score=0.82,
                explanation="agents avoid vulnerability",
                evidence_quotes=["I don't need help"],
            ),
            SimpleNamespace(
                dysfunction="fear-of-conflict",
                severity="medium",
                score=0.55,
                explanation="artificial harmony",
                evidence_quotes=["sounds good", "agreed"],
            ),
            SimpleNamespace(
                dysfunction="lack-of-commitment",
                severity="low",
                score=0.30,
                explanation="decisions revisited",
                evidence_quotes=[],
            ),
            SimpleNamespace(
                dysfunction="avoidance-of-accountability",
                severity="none",
                score=0.05,
                explanation="self-corrects",
                evidence_quotes=[],
            ),
            SimpleNamespace(
                dysfunction="inattention-to-results",
                severity="trace",
                score=0.12,
                explanation="one weak signal",
                evidence_quotes=[],
            ),
        ]
    )
    findings = extract_findings("lencioni", result)
    assert len(findings) == 5
    # All carry the categorical name in the title.
    titles = [f.title for f in findings]
    assert any("absence-of-trust" in t for t in titles)
    assert any("fear-of-conflict" in t for t in titles)
    # Severity preserves the pattern's wire-format label.
    sev_map = {f.title.split(":")[0]: f.severity for f in findings}
    assert sev_map["absence-of-trust"] == "high"
    assert sev_map["fear-of-conflict"] == "medium"
    # Evidence quote was extracted (first element of the list).
    high_finding = next(f for f in findings if "absence-of-trust" in f.title)
    assert high_finding.evidence == "I don't need help"


def test_extracts_four_bias_stack_biases() -> None:
    result = SimpleNamespace(
        biases=[
            SimpleNamespace(
                bias="anchoring",
                severity="high",
                score=0.78,
                explanation="first-hypothesis dominance",
                evidence_quotes=["this looks like a race condition"],
            ),
            SimpleNamespace(
                bias="overconfidence",
                severity="medium",
                score=0.6,
                explanation="claims certainty without evidence",
                evidence_quotes=["I'm 100% sure"],
            ),
            SimpleNamespace(
                bias="confirmation",
                severity="low",
                score=0.3,
                explanation="some disconfirming evidence engaged",
                evidence_quotes=[],
            ),
            SimpleNamespace(
                bias="escalation-of-commitment",
                severity="none",
                score=0.05,
                explanation="pivoted on early signal",
                evidence_quotes=[],
            ),
        ]
    )
    findings = extract_findings("bias_stack", result)
    assert len(findings) == 4
    titles = [f.title for f in findings]
    assert any("anchoring" in t for t in titles)
    assert any("overconfidence" in t for t in titles)


def test_extracts_aar_lessons() -> None:
    """AAR Lessons carry no severity field; the built-in AAR override
    adapter surfaces each Lesson as a moderate-severity Finding with
    the pattern slug + description in the title and the root_cause +
    framework anchor in evidence."""
    result = SimpleNamespace(
        lessons=[
            SimpleNamespace(
                pattern="premature-commitment",
                description="committed to JWT on step 3",
                root_cause="missed alternatives",
                framework_anchor="Lencioni 2002",
                cross_pattern_links=[],
            ),
            SimpleNamespace(
                pattern="missing-verification",
                description="no contract check before deploy",
                root_cause="time pressure",
                framework_anchor="Wharton AAR",
                cross_pattern_links=[],
            ),
        ]
    )
    findings = extract_findings("aar", result)
    assert len(findings) == 2
    titles = [f.title for f in findings]
    assert any("premature-commitment" in t for t in titles)
    assert any("missing-verification" in t for t in titles)
    # Severity defaults to "moderate" since Lessons carry no severity
    # field by design.
    assert all(f.severity == "moderate" for f in findings)
    # Evidence carries root_cause + framework anchor.
    assert any("Lencioni 2002" in f.evidence for f in findings)
    assert any("time pressure" in f.evidence for f in findings)


# --- pattern-specific severity field names ---------------------------


def test_severity_of_gap_normalizes(  # McAllister trust dimensions
) -> None:
    result = SimpleNamespace(
        legs=[
            SimpleNamespace(
                leg="cognitive",
                severity_of_gap="none",
                score=0.9,
                explanation="strong reasoning",
                evidence_quotes=[],
            ),
            SimpleNamespace(
                leg="authenticity",
                severity_of_gap="high",
                score=0.22,
                explanation="sycophantic agreement",
                evidence_quotes=["you're right"],
            ),
        ]
    )
    findings = extract_findings("mcallister_trust", result)
    assert len(findings) == 2
    sev_by_leg = {f.title.split(":")[0]: f.severity for f in findings}
    assert sev_by_leg["cognitive"] == "none"
    assert sev_by_leg["authenticity"] == "high"


def test_severity_of_absence_normalizes(  # Psych Safety
) -> None:
    result = SimpleNamespace(
        behaviors=[
            SimpleNamespace(
                behavior="voice",
                severity_of_absence="high",
                presence_score=0.15,
                explanation="silence after every decision",
                evidence_quotes=["sounds good"],
            )
        ]
    )
    findings = extract_findings("psych_safety", result)
    assert len(findings) == 1
    assert findings[0].severity == "high"


# --- per-pattern adapter override path -------------------------------


def test_registered_adapter_takes_precedence() -> None:
    """An override registered via @register wins over the smart
    extractor for that pattern slug."""

    @register("custompat_test")
    def _adapt(result):
        return [
            Finding(
                pattern="custompat_test",
                severity="critical",
                title="override path",
                evidence="from override",
            )
        ]

    try:
        # The result has a normal dysfunctions list; the smart extractor
        # would emit 2 findings, but the override returns exactly 1.
        result = SimpleNamespace(
            dysfunctions=[
                SimpleNamespace(
                    dysfunction="x", severity="high", evidence_quotes=[]
                ),
                SimpleNamespace(
                    dysfunction="y", severity="medium", evidence_quotes=[]
                ),
            ]
        )
        findings = extract_findings("custompat_test", result)
        assert len(findings) == 1
        assert findings[0].title == "override path"
        assert findings[0].severity == "critical"
    finally:
        ADAPTERS.pop("custompat_test", None)


def test_adapter_exception_falls_through_to_smart() -> None:
    """If an override raises, the runner should not break -- the smart
    extractor takes over."""

    @register("custompat_err")
    def _adapt(result):
        raise RuntimeError("override boom")

    try:
        result = SimpleNamespace(
            dysfunctions=[
                SimpleNamespace(
                    dysfunction="x", severity="high", evidence_quotes=[]
                )
            ]
        )
        findings = extract_findings("custompat_err", result)
        # Smart extractor still produced the Finding.
        assert len(findings) == 1
        assert findings[0].severity == "high"
    finally:
        ADAPTERS.pop("custompat_err", None)


# --- backward compatibility ------------------------------------------


def test_legacy_findings_list_still_works() -> None:
    """Pre-uplift patterns that exposed a generic ``findings`` list of
    dicts must still work."""
    result = SimpleNamespace(
        findings=[
            {
                "severity": "high",
                "title": "legacy finding 1",
                "evidence": "old style",
            },
            {
                "severity": "low",
                "title": "legacy finding 2",
                "evidence": "old style 2",
            },
        ]
    )
    findings = extract_findings("legacy", result)
    assert len(findings) == 2
    assert findings[0].severity == "high"
    assert findings[1].severity == "low"
    assert findings[0].evidence == "old style"


def test_top_findings_alias_still_works() -> None:
    result = SimpleNamespace(
        top_findings=[
            SimpleNamespace(severity="critical", title="t1", evidence_quotes=["q1"]),
        ]
    )
    findings = extract_findings("legacy_top", result)
    assert len(findings) == 1
    assert findings[0].severity == "critical"


# --- score-only fallback ---------------------------------------------


def test_score_only_result_emits_one_finding() -> None:
    """A pattern result with only a numeric ``score`` and no evidence
    list still surfaces one Finding via the score-fallback path."""
    result = SimpleNamespace(score=0.82, summary="overall drift")
    findings = extract_findings("score_only", result)
    assert len(findings) == 1
    # 0.82 maps to "high" per the 7-point band table.
    assert findings[0].severity == "high"
    assert "overall drift" in findings[0].title


def test_severity_and_title_at_top_level_emits_one_finding() -> None:
    result = SimpleNamespace(
        severity="medium",
        title="top-level finding",
        evidence="top-level evidence",
    )
    findings = extract_findings("top_level", result)
    assert len(findings) == 1
    assert findings[0].severity == "medium"
    assert findings[0].title == "top-level finding"


# --- empty + None safety ---------------------------------------------


def test_none_result_yields_empty() -> None:
    assert extract_findings("anything", None) == []


def test_empty_evidence_list_falls_through() -> None:
    """An empty ``dysfunctions=[]`` should not block the extractor;
    it should keep walking the inventory and then fall back."""
    result = SimpleNamespace(
        dysfunctions=[],
        severity="low",
        title="no items but top-level signal",
    )
    findings = extract_findings("empty_then_top", result)
    assert len(findings) == 1
    assert findings[0].severity == "low"


def test_item_without_severity_or_score_is_skipped() -> None:
    """If an item has neither severity nor a numeric score, we skip it
    rather than surfacing a meaningless 'trace' finding."""
    result = SimpleNamespace(
        dysfunctions=[
            SimpleNamespace(dysfunction="vague", explanation="no signal"),
            SimpleNamespace(
                dysfunction="real", severity="high", evidence_quotes=["q"]
            ),
        ]
    )
    findings = extract_findings("skip_vague", result)
    assert len(findings) == 1
    assert "real" in findings[0].title
