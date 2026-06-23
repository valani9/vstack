"""Per-pattern findings adapters for vstack.diagnose.

The runner used to call a single ``_coerce_findings`` reflective
helper that knew only about the generic ``findings`` and
``top_findings`` attribute names. Almost no real vstack pattern
exposes either of those; the runner therefore fell back to the
single-object case in ``_coerce_findings`` and surfaced exactly ONE
finding per pattern run.

That was lossy. A real Lencioni run has FIVE dysfunction-evidence
entries; a Bias Stack run has FOUR bias scores; an AAR run has
1-5 lessons. Those should each surface as their own Finding in the
ranked report.

This module replaces the lossy fallback with a smart extractor that
knows the field-name conventions vstack patterns actually use. It
walks any of the known evidence-list field names, then for each item
in that list it extracts a Finding using a second set of field-name
conventions (title from any of ``dysfunction`` / ``leg`` / ``factor``
/ ... ; severity from any of ``severity`` / ``severity_of_gap`` /
``severity_of_absence``; evidence from ``evidence_quotes``; etc.).

For patterns whose conventions differ from the smart extractor's
inventories, the per-pattern ``ADAPTERS`` dispatch table lets us
register a bespoke extractor under the pattern slug. None are
needed today (the smart extractor covers all 34 shipped patterns)
but the hook is there for future patterns.

The runner imports ``extract_findings(pattern, result)`` from this
module and uses it in place of the old ``_coerce_findings``.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Callable, TypeGuard

from .registry import SEVERITY_ORDER, severity_rank

# Avoid importing Finding from runner at module load (circular).
# Re-define the same lightweight dataclass here and the runner imports
# its Finding from us instead.
from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    """A single ranked finding extracted from one pattern's output.

    Severity is one of the seven-point labels from
    :data:`vstack.diagnose.registry.SEVERITY_ORDER`. ``evidence`` is a
    short free-text quote or summary; ``intervention`` is the
    recommended next-step phrasing. Both are optional because
    different patterns emit different richness.
    """

    pattern: str
    severity: str
    title: str
    evidence: str = ""
    intervention: str = ""

    def severity_rank(self) -> int:
        return severity_rank(self.severity)


# --- field-name inventories ------------------------------------------

# Evidence-list field names: every name under which a vstack pattern's
# main return object may carry the per-item evidence list. Walked in
# the order listed; the first one that yields a non-empty iterable
# wins. The "_evidence" suffix variants are listed after the bare
# names because some patterns expose BOTH (e.g., one as the canonical
# field and one as a computed accessor) and we prefer the canonical.
_EVIDENCE_LIST_FIELDS: tuple[str, ...] = (
    # canonical (already supported by the legacy path)
    "findings",
    "top_findings",
    # categorical-axis names (per-pattern)
    "dysfunctions",  # Lencioni
    "legs",  # Trust Triangle (when v0.2 result exposes it)
    "domains",  # Goleman EI (v0.2 result)
    "factors",  # generic
    "triggers",  # Stone-Heen
    "strengths",  # Grant
    "pathologies",  # Debate Pathology
    "quadrants",  # Johari
    "behaviors",  # Psych Safety
    "loci",  # Lewin (when v0.2 result exposes it)
    "terms",  # Vroom (when v0.2 result exposes it)
    "traps",  # Motivation Traps (when v0.2 result exposes it)
    "needs",  # SDT (when v0.2 result exposes it)
    "biases",  # Bias Stack (when v0.2 result exposes it)
    "characteristics",  # Robbins-Judge
    "dimensions",  # Org Structure / McAllister
    "phases",  # Devil's Advocate (when v0.2 result exposes it)
    "zones",  # Yerkes-Dodson (when v0.2 result exposes it)
    "styles",  # Thomas-Kilmann (when v0.2 result exposes it)
    "metrics",  # Heffernan / Span-of-Control
    "lessons",  # AAR
    "branches",  # Mayer-Salovey overlay
    # _evidence-suffix names (often the canonical schema field)
    "dysfunction_evidence",
    "leg_evidence",
    "domain_evidence",
    "factor_evidence",
    "trigger_evidence",
    "strength_evidence",
    "pathology_evidence",
    "behavior_evidence",
    "locus_evidence",
    "trap_evidence",
    "need_evidence",
    "term_evidence",
    "bias_evidence",
    "phase_evidence",
    "style_evidence",
    "strategy_evidence",
    "zone_evidence",
    "dimension_evidence",
    # collection accessor names
    "agent_contributions",  # Social Loafing
    "contributing_factors",  # Process Gain/Loss (forensic-mode result)
    "evidence",  # generic last-chance
)


# Categorical title field names: when an item is a per-item record
# (one of N dysfunctions, legs, factors, ...), the categorical name
# of the axis appears under one of these keys. Walked in priority
# order so a bare "title" wins when it is also present.
_TITLE_FIELDS: tuple[str, ...] = (
    # generic-first
    "title",
    "name",
    "label",
    # categorical-axis names
    "dysfunction",
    "leg",
    "domain",
    "factor",
    "trigger",
    "strength",
    "pathology",
    "quadrant",
    "behavior",
    "locus",
    "term",
    "trap",
    "need",
    "bias",
    "characteristic",
    "dimension",
    "phase",
    "zone",
    "style",
    "branch",
    "state",  # Cognitive Reappraisal (strategy state) / Glaser (neurochemical)
    "strategy",  # Cognitive Reappraisal
    "pattern",  # AAR Lesson.pattern (failure-pattern slug)
    "agent_name",  # Social Loafing
    "metric",  # Heffernan / Span (the metric name)
)


# Evidence-quote field names. ``evidence_quotes`` is a list across
# essentially every pattern; we take the first element so the Finding
# carries a one-quote snapshot. ``evidence`` / ``quote`` / ``quotes``
# are fallback variants.
_EVIDENCE_QUOTE_FIELDS: tuple[str, ...] = (
    "evidence_quotes",
    "evidence_quote",
    "quotes",
    "quote",
    "evidence",
)


# Explanation / description field names. Used to fill the title when
# the categorical-axis name was not enough OR to enrich the evidence
# string when no verbatim quote was present.
_EXPLANATION_FIELDS: tuple[str, ...] = (
    "explanation",
    "description",
    "summary",
    "notes",
    "rationale",
)


# Severity field names. The schema column varies across patterns; we
# walk these in order and pick the first present.
_SEVERITY_FIELDS: tuple[str, ...] = (
    "severity",
    "severity_of_gap",  # McAllister
    "severity_of_absence",  # Psych Safety
    "severity_of_overuse",  # Grant (if exposed)
    "mismatch_severity",  # Cognitive Reappraisal forensic
    "risk",  # HEXACO factor / Robbins-Judge characteristic
)


# Score field names used when severity is absent and we need to
# derive one from a numeric axis.
_SCORE_FIELDS: tuple[str, ...] = (
    "score",
    "weight",  # Johari
    "presence_score",  # Psych Safety
    "wobble_score",  # Trust Triangle
    "overuse_score",  # Grant
    "observed_score",  # Robbins-Judge / Org Structure
    "fit_score",  # Robbins-Judge / Org Structure
    "substantive_score",  # Devil's Advocate
    "value",  # Heffernan metric
    "coherence_score",  # Schein
)


# Per-pattern override dispatch table. Keys are pattern slugs from
# :data:`vstack.diagnose.registry.PATTERNS`. Values are callables
# ``(result) -> list[Finding]`` that bypass the smart extractor for
# patterns whose conventions do not fit. Empty by default; the smart
# extractor covers every shipped pattern.
ADAPTERS: dict[str, Callable[[Any], list["Finding"]]] = {}


def register(
    pattern_name: str,
) -> Callable[[Callable[[Any], list["Finding"]]], Callable[[Any], list["Finding"]]]:
    """Decorator used to register a per-pattern adapter override.

    Example::

        @register("lencioni")
        def _adapt(result):
            return [Finding(...) for ev in result.dysfunctions]
    """

    def deco(
        fn: Callable[[Any], list["Finding"]],
    ) -> Callable[[Any], list["Finding"]]:
        ADAPTERS[pattern_name] = fn
        return fn

    return deco


# --- public extractor ------------------------------------------------


def extract_findings(pattern: str, result: Any) -> list["Finding"]:
    """Best-effort lossless extraction of Findings from one pattern's
    result object.

    Order of attempts:

    1. Per-pattern adapter registered via :func:`register`. None are
       registered by default; the smart extractor below handles every
       shipped pattern.
    2. Smart extractor: walks the known evidence-list field-name
       inventory, then for each item walks the per-item field-name
       inventories to build a Finding.
    3. Fallback: result-itself-has-severity-and-title (legacy behavior).
    4. Fallback: numeric score on the result, mapped to severity.
    5. No actionable signal -> empty list.
    """
    if result is None:
        return []

    # Step 1: explicit per-pattern adapter wins.
    fn = ADAPTERS.get(pattern)
    if fn is not None:
        try:
            return list(fn(result))
        except Exception:
            # An adapter raising should not nuke the report. Fall
            # through to the smart extractor.
            pass

    # Step 2: smart extractor over the evidence-list inventory.
    smart = _extract_smart(pattern, result)
    if smart:
        return smart

    # Step 3: result has severity + title at the top level.
    sev = _first_attr(result, _SEVERITY_FIELDS)
    if sev is not None:
        title = _first_attr(result, _TITLE_FIELDS) or _first_attr(result, _EXPLANATION_FIELDS)
        if title:
            return [
                Finding(
                    pattern=pattern,
                    severity=_normalize_severity(sev),
                    title=str(title)[:200],
                    evidence=_first_evidence_string(result),
                    intervention=_first_intervention_string(result),
                )
            ]

    # Step 4: numeric score at top level.
    for sf in _SCORE_FIELDS:
        s = getattr(result, sf, None)
        if s is not None:
            title = (
                _first_attr(result, _TITLE_FIELDS)
                or _first_attr(result, _EXPLANATION_FIELDS)
                or f"{sf}={s}"
            )
            return [
                Finding(
                    pattern=pattern,
                    severity=_score_to_severity(s),
                    title=str(title)[:200],
                    evidence=_first_evidence_string(result),
                    intervention=_first_intervention_string(result),
                )
            ]

    # Step 5: nothing actionable; not an error, just a clean run.
    return []


# --- smart extractor internals ---------------------------------------


def _extract_smart(pattern: str, result: Any) -> list["Finding"]:
    for field in _EVIDENCE_LIST_FIELDS:
        items = getattr(result, field, None)
        if not _is_iterable_of_records(items):
            continue
        out: list[Finding] = []
        for item in items:
            f = _item_to_finding(pattern, item)
            if f is not None:
                out.append(f)
        if out:
            return out
    return []


def _item_to_finding(pattern: str, item: Any) -> Finding | None:
    """Convert one evidence-list item to a Finding.

    The item can be a dict, a pydantic model, a frozen dataclass, or
    a SimpleNamespace; we treat them all uniformly via _get().
    """
    # If the item is already a Finding we trust it (but rebind pattern
    # for safety).
    if isinstance(item, Finding):
        return Finding(
            pattern=pattern,
            severity=item.severity,
            title=item.title,
            evidence=item.evidence,
            intervention=item.intervention,
        )

    sev = _get_first(item, _SEVERITY_FIELDS)
    if sev is None:
        # Try to derive severity from a numeric score field on the item.
        for sf in _SCORE_FIELDS:
            s = _get(item, sf)
            if s is not None:
                sev = _score_to_severity(s)
                break
    if sev is None:
        # No severity signal at all -> skip this item rather than
        # surfacing a meaningless "trace" Finding.
        return None

    title_raw = _get_first(item, _TITLE_FIELDS)
    explanation = _get_first(item, _EXPLANATION_FIELDS)
    if title_raw and explanation:
        title = f"{title_raw}: {str(explanation)[:120]}"
    else:
        title = str(title_raw or explanation or "")
    if not title:
        return None

    evidence = _first_evidence_string(item)
    intervention = _first_intervention_string(item)
    return Finding(
        pattern=pattern,
        severity=_normalize_severity(sev),
        title=title[:200],
        evidence=evidence,
        intervention=intervention,
    )


# --- field-access helpers --------------------------------------------


def _get(item: Any, name: str) -> Any:
    """Read an attribute or dict key uniformly."""
    if isinstance(item, dict):
        return item.get(name)
    return getattr(item, name, None)


def _get_first(item: Any, names: Iterable[str]) -> Any:
    for n in names:
        v = _get(item, n)
        if v is not None and v != "":
            return v
    return None


def _first_attr(obj: Any, names: Iterable[str]) -> Any:
    """Same as _get_first but works on attribute-only objects."""
    for n in names:
        v = getattr(obj, n, None)
        if v is not None and v != "":
            return v
    return None


def _first_evidence_string(item: Any) -> str:
    for n in _EVIDENCE_QUOTE_FIELDS:
        v = _get(item, n)
        if v is None:
            continue
        if isinstance(v, (list, tuple)) and v:
            return str(v[0])[:200]
        if isinstance(v, str) and v:
            return v[:200]
    return ""


def _first_intervention_string(item: Any) -> str:
    """Patterns sometimes carry the next-step phrasing alongside the
    evidence item. We do not have a strong cross-pattern convention
    here; we try the small set of known names.
    """
    for n in ("intervention", "next_step", "suggested_implementation"):
        v = _get(item, n)
        if v:
            return str(v)[:200]
    return ""


# --- iterable detection ----------------------------------------------


def _is_iterable_of_records(value: Any) -> TypeGuard[Iterable[Any]]:
    """Return True iff ``value`` is a non-empty iterable of record-like
    items (dicts, dataclasses, pydantic models, SimpleNamespaces, or
    Finding instances). Strings and bytes do not count.
    """
    if value is None:
        return False
    if isinstance(value, (str, bytes)):
        return False
    if isinstance(value, dict):
        return False
    try:
        iter(value)
    except TypeError:
        return False
    # Materialize a peek so generators don't get exhausted mid-walk.
    # We expect every vstack analyzer to return list/tuple, not a
    # generator, so this is cheap.
    try:
        items = list(value)
    except TypeError:
        return False
    if not items:
        return False
    head = items[0]
    if isinstance(head, (str, bytes, int, float, bool)):
        return False
    return True


# --- severity helpers ------------------------------------------------


def _normalize_severity(value: Any) -> str:
    """Map any plausible severity expression to a 7-point label.

    Accepts: already-canonical labels ("none" / "trace" / ... /
    "critical"), pattern-specific short forms ("low" / "medium" /
    "high" without the in-between bands), categorical strings
    ("overused" / "borderline" / etc.), and numeric values.

    Anything we cannot map falls back to "trace" so the Finding still
    enters the report at the lowest severity rank rather than getting
    dropped.
    """
    if isinstance(value, str):
        v = value.strip().lower()
        if v in SEVERITY_ORDER:
            return v
        # Four-label wire format used by several patterns.
        if v in ("nit",):
            return "low"
        # Categorical labels from specific patterns.
        if v in ("overused", "severe", "abandoning", "incoherent"):
            return "high"
        if v in ("borderline", "drifting", "mild", "at-risk", "developing"):
            return "moderate"
        if v in ("healthy", "well-fit", "intrinsic", "aligned", "motivated"):
            return "none"
        if v in ("under_used", "partial-fit", "mixed", "weak"):
            return "low"
        # If it's a known synonym that maps to "none", honor it.
        if v in ("ok", "clean", "fine"):
            return "none"
        # Last resort: keep the literal if it's anywhere in SEVERITY_ORDER
        # (case-insensitive), otherwise trace.
        return v if v in SEVERITY_ORDER else "trace"

    # Numeric severity: map via _score_to_severity.
    try:
        return _score_to_severity(value)
    except Exception:
        return "trace"


def _score_to_severity(score: Any) -> str:
    """Map a numeric pattern score to a 7-point severity label.

    Convention: higher numeric score = higher severity (more
    dysfunction / risk / etc.). The mapper handles 0-1, 0-10, and
    0-100 ranges by normalizing. Out-of-range or non-numeric values
    return "trace" as a safe default.
    """
    try:
        s = float(score)
    except (TypeError, ValueError):
        return "trace"
    if 0.0 <= s <= 1.0:
        norm = s
    elif s <= 10.0:
        norm = s / 10.0
    else:
        norm = max(0.0, min(1.0, s / 100.0))
    if norm < 0.10:
        return "none"
    if norm < 0.25:
        return "trace"
    if norm < 0.40:
        return "low"
    if norm < 0.55:
        return "moderate"
    if norm < 0.70:
        return "medium"
    if norm < 0.85:
        return "high"
    return "critical"


# ---------------------------------------------------------------------
# Built-in per-pattern overrides
# ---------------------------------------------------------------------
#
# These are registered as part of ADAPTERS at import time so the smart
# extractor's "skip items without severity or score" rule does not
# silently drop patterns whose schema is narrative-shaped rather than
# scored-evidence-shaped.


@register("aar")
def _adapt_aar(result: Any) -> list["Finding"]:
    """AAR Lessons carry no severity field by design -- they are
    narrative findings, not scored evidence. We default to "moderate"
    so each Lesson surfaces in the ranked report; the framework anchor
    + root_cause go into evidence + intervention slots.
    """
    lessons = getattr(result, "lessons", None)
    if not lessons:
        return []
    out: list[Finding] = []
    for ln in lessons:
        pattern_slug = _get(ln, "pattern") or _get(ln, "name") or ""
        description = _get(ln, "description") or _get(ln, "summary") or ""
        root_cause = _get(ln, "root_cause") or ""
        framework_anchor = _get(ln, "framework_anchor") or ""
        title = f"{pattern_slug}: {description}" if pattern_slug else description
        evidence = (
            f"{root_cause} (anchor: {framework_anchor})"
            if root_cause and framework_anchor
            else root_cause or framework_anchor
        )
        out.append(
            Finding(
                pattern="aar",
                severity="moderate",
                title=str(title)[:200],
                evidence=str(evidence)[:200],
                intervention="",
            )
        )
    return out


__all__ = [
    "ADAPTERS",
    "Finding",
    "extract_findings",
    "register",
]
