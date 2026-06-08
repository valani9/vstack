"""Registry of every vstack pattern, with the metadata needed to route
trace shapes to relevant bundles.

This module is the single source of truth for "what patterns ship in
this release and what shapes do they apply to." Adding a new pattern
to vstack means adding one entry here.

The registry is intentionally declarative. It only stores import paths
+ class names + tags. The :func:`resolve_pattern` helper does the lazy
import at runtime, so a missing optional dependency for one pattern
does not break loading the registry for the rest.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Any, Literal


# Trace-shape vocabulary. Patterns advertise which shapes they accept.
TraceShape = Literal["individual", "team", "org"]
ALL_SHAPES: tuple[TraceShape, ...] = ("individual", "team", "org")


# Severity vocabulary. Mirrors the AAR pattern's 7-point scale so that
# findings from different patterns compare cleanly. Patterns that emit
# coarser scores (low/medium/high) are mapped into this scale.
Severity = Literal[
    "none", "trace", "low", "moderate", "medium", "high", "critical"
]
SEVERITY_ORDER: tuple[Severity, ...] = (
    "none",
    "trace",
    "low",
    "moderate",
    "medium",
    "high",
    "critical",
)


def severity_rank(s: str) -> int:
    """Map a severity label to its rank (0 = least, 6 = most). Unknown
    labels rank as -1 so they sort to the bottom of any reverse-sorted
    list. Case-insensitive; tolerates surrounding whitespace."""
    if not s:
        return -1
    key = s.strip().lower()
    try:
        return SEVERITY_ORDER.index(key)  # type: ignore[arg-type]
    except ValueError:
        return -1


@dataclass(frozen=True)
class PatternInfo:
    """Static metadata about one shipped pattern.

    Fields
    ------
    name: short slug used as the key in :data:`PATTERNS`. Stable across
        releases.
    module: dotted import path of the pattern's sub-package, e.g.
        ``vstack.aar``.
    analyzer: the main (sync) analyzer class name exposed by the
        sub-package's top-level ``__init__.py``.
    analyzer_async: the async-variant class name, if the pattern
        exposes one. ``None`` if no async variant is shipped.
    shapes: trace shapes this pattern applies to (any subset of
        :data:`ALL_SHAPES`).
    module_id: numeric module id from the original course curriculum.
        Useful for grouping in reports.
    pattern_id: numeric pattern id within its module (the ``NN-`` prefix
        from the source folder name).
    summary: one-line human description for tooling. NOT a docstring;
        keep it short.
    """

    name: str
    module: str
    analyzer: str | None
    analyzer_async: str | None
    shapes: tuple[TraceShape, ...]
    module_id: int
    pattern_id: int
    summary: str
    tags: tuple[str, ...] = field(default_factory=tuple)


# --- registry ---------------------------------------------------------

# Listed in pattern_id order. Each entry is a single, declarative row.
# Add a new pattern by appending another entry. Do not import here.

PATTERNS: dict[str, PatternInfo] = {
    info.name: info
    for info in [
        # --- module 1: individual --------------------------------------
        PatternInfo(
            name="lewin",
            module="vstack.lewin",
            analyzer="LewinAttributionDetector",
            analyzer_async="LewinAttributionDetectorAsync",
            shapes=("individual",),
            module_id=1,
            pattern_id=1,
            summary="Person-vs-environment failure attribution (Lewin B=f(P,E)).",
            tags=("attribution", "diagnosis"),
        ),
        PatternInfo(
            name="goleman_ei",
            module="vstack.goleman_ei",
            analyzer="EIAuditDetector",
            analyzer_async="EIAuditDetectorAsync",
            shapes=("individual",),
            module_id=1,
            pattern_id=2,
            summary="Emotional-intelligence audit for agent self-awareness.",
            tags=("emotion", "self-awareness"),
        ),
        PatternInfo(
            name="johari",
            module="vstack.johari",
            analyzer="JohariSelfAuditor",
            analyzer_async="JohariSelfAuditorAsync",
            shapes=("individual",),
            module_id=1,
            pattern_id=3,
            summary="Self vs other-attributed disclosure quadrants.",
            tags=("self-disclosure", "feedback"),
        ),
        PatternInfo(
            name="danva_emotion",
            module="vstack.danva_emotion",
            analyzer="EmotionRecognitionAnalyzer",
            analyzer_async="EmotionRecognitionAnalyzerAsync",
            shapes=("individual",),
            module_id=1,
            pattern_id=4,
            summary="Emotion-recognition accuracy probe (Nowicki-Duke DANVA).",
            tags=("emotion", "perception"),
        ),
        PatternInfo(
            name="cognitive_reappraisal",
            module="vstack.cognitive_reappraisal",
            analyzer="ReappraisalAnalyzer",
            analyzer_async="ReappraisalAnalyzerAsync",
            shapes=("individual",),
            module_id=1,
            pattern_id=5,
            summary="Reframe-based emotion regulation under failure.",
            tags=("emotion", "regulation"),
        ),
        PatternInfo(
            name="yerkes_dodson",
            module="vstack.yerkes_dodson",
            analyzer="WorkloadDetector",
            analyzer_async="YerkesDodsonAnalyzerAsync",
            shapes=("individual",),
            module_id=1,
            pattern_id=6,
            summary="Workload vs performance curve (Yerkes-Dodson).",
            tags=("workload", "performance"),
        ),
        PatternInfo(
            name="hexaco",
            module="vstack.hexaco",
            analyzer="HEXACOPersonalityAnalyzer",
            analyzer_async="HEXACOPersonalityAnalyzerAsync",
            shapes=("individual",),
            module_id=1,
            pattern_id=7,
            summary="HEXACO personality profile of the agent under load.",
            tags=("personality",),
        ),
        PatternInfo(
            name="grant_strengths",
            module="vstack.grant_strengths",
            analyzer="GrantStrengthsAnalyzer",
            analyzer_async="GrantStrengthsAnalyzerAsync",
            shapes=("individual",),
            module_id=1,
            pattern_id=8,
            summary="Strengths-as-weaknesses inversion (Grant 2014).",
            tags=("strengths", "self-regulation"),
        ),
        PatternInfo(
            name="motivation_traps",
            module="vstack.motivation_traps",
            analyzer="MotivationTrapsAnalyzer",
            analyzer_async="MotivationTrapsAnalyzerAsync",
            shapes=("individual",),
            module_id=1,
            pattern_id=9,
            summary="Common motivation traps in single-agent loops.",
            tags=("motivation",),
        ),
        PatternInfo(
            name="sdt_reward",
            module="vstack.sdt_reward",
            analyzer="SDTRewardAnalyzer",
            analyzer_async="SDTRewardAnalyzerAsync",
            shapes=("individual",),
            module_id=1,
            pattern_id=10,
            summary="Self-determination theory: intrinsic-reward alignment.",
            tags=("motivation", "reward"),
        ),
        PatternInfo(
            name="mcgregor",
            module="vstack.mcgregor",
            analyzer="McGregorOrchestratorAnalyzer",
            analyzer_async="McGregorOrchestratorAnalyzerAsync",
            shapes=("individual", "team"),
            module_id=1,
            pattern_id=11,
            summary="Theory-X vs Theory-Y orchestrator style.",
            tags=("orchestration", "management"),
        ),
        PatternInfo(
            name="vroom_expectancy",
            module="vstack.vroom_expectancy",
            analyzer="VroomExpectancyAnalyzer",
            analyzer_async="VroomExpectancyAnalyzerAsync",
            shapes=("individual",),
            module_id=1,
            pattern_id=12,
            summary="Vroom expectancy: effort -> performance -> reward.",
            tags=("motivation",),
        ),
        # --- module 2: team --------------------------------------------
        PatternInfo(
            name="grpi",
            module="vstack.grpi",
            analyzer="GRPIWorkingAgreementAnalyzer",
            analyzer_async="GRPIWorkingAgreementAnalyzerAsync",
            shapes=("team",),
            module_id=2,
            pattern_id=13,
            summary="GRPI working agreement: goals, roles, processes, interactions.",
            tags=("team-charter", "roles"),
        ),
        PatternInfo(
            name="process_gain_loss",
            module="vstack.process_gain_loss",
            analyzer="ProcessGainLossAnalyzer",
            analyzer_async="ProcessGainLossAnalyzerAsync",
            shapes=("team",),
            module_id=2,
            pattern_id=14,
            summary="Coordination productivity in multi-agent crews.",
            tags=("coordination",),
        ),
        PatternInfo(
            name="social_loafing",
            module="vstack.social_loafing",
            analyzer="SocialLoafingAnalyzer",
            analyzer_async="SocialLoafingAnalyzerAsync",
            shapes=("team",),
            module_id=2,
            pattern_id=15,
            summary="Detects coast / hide / phone-in patterns per agent.",
            tags=("accountability",),
        ),
        PatternInfo(
            name="superflocks",
            module="vstack.superflocks",
            analyzer="SuperflocksAnalyzer",
            analyzer_async="SuperflocksAnalyzerAsync",
            shapes=("team",),
            module_id=2,
            pattern_id=16,
            summary="Heffernan superflocks: dependency on one or two agents.",
            tags=("dependency", "robustness"),
        ),
        PatternInfo(
            name="lencioni",
            module="vstack.lencioni",
            analyzer="LencioniAnalyzer",
            analyzer_async="LencioniAnalyzerAsync",
            shapes=("team",),
            module_id=2,
            pattern_id=17,
            summary="Lencioni five-dysfunctions pyramid for crews.",
            tags=("trust", "conflict", "commitment", "accountability", "results"),
        ),
        PatternInfo(
            name="trust_triangle",
            module="vstack.trust_triangle",
            analyzer="TrustTriangleAnalyzer",
            analyzer_async="TrustTriangleAnalyzerAsync",
            shapes=("team",),
            module_id=2,
            pattern_id=18,
            summary="Logic, authenticity, empathy: trust triangle audit.",
            tags=("trust",),
        ),
        PatternInfo(
            name="mcallister_trust",
            module="vstack.mcallister_trust",
            analyzer="TrustBalanceAnalyzer",
            analyzer_async="TrustBalanceAnalyzerAsync",
            shapes=("team",),
            module_id=2,
            pattern_id=19,
            summary="Cognition- vs affect-based trust balance.",
            tags=("trust",),
        ),
        PatternInfo(
            name="psych_safety",
            module="vstack.psych_safety",
            analyzer="PsychologicalSafetyAnalyzer",
            analyzer_async="PsychologicalSafetyAnalyzerAsync",
            shapes=("team",),
            module_id=2,
            pattern_id=20,
            summary="Edmondson psychological safety for crews.",
            tags=("psychological-safety", "voice"),
        ),
        PatternInfo(
            name="glaser_conversation",
            module="vstack.glaser_conversation",
            analyzer="ConversationSteeringAnalyzer",
            analyzer_async="ConversationSteeringAnalyzerAsync",
            shapes=("team",),
            module_id=2,
            pattern_id=21,
            summary="Conversational intelligence steering (Glaser).",
            tags=("conversation",),
        ),
        PatternInfo(
            name="feedback_triggers",
            module="vstack.feedback_triggers",
            analyzer="FeedbackTriggerAnalyzer",
            analyzer_async="FeedbackTriggerAnalyzerAsync",
            shapes=("team",),
            module_id=2,
            pattern_id=22,
            summary="Stone-Heen truth/relationship/identity triggers in feedback.",
            tags=("feedback",),
        ),
        PatternInfo(
            name="plus_delta",
            module="vstack.plus_delta",
            analyzer="PlusDeltaFeedbackAnalyzer",
            analyzer_async="PlusDeltaFeedbackAnalyzerAsync",
            shapes=("team",),
            module_id=2,
            pattern_id=23,
            summary="Plus/delta feedback format on crew exchanges.",
            tags=("feedback",),
        ),
        PatternInfo(
            name="smart_goal",
            module="vstack.smart_goal",
            analyzer="SMARTGoalAnalyzer",
            analyzer_async="SMARTGoalAnalyzerAsync",
            shapes=("individual", "team"),
            module_id=2,
            pattern_id=24,
            summary="SMART goal generator + crew goal-quality scoring.",
            tags=("goals",),
        ),
        PatternInfo(
            name="group_decision",
            module="vstack.group_decision",
            analyzer="DecisionProtocolAnalyzer",
            analyzer_async="DecisionProtocolAnalyzerAsync",
            shapes=("team",),
            module_id=2,
            pattern_id=25,
            summary="Group decision protocol fit (consent/consensus/...).",
            tags=("decision-making",),
        ),
        PatternInfo(
            name="debate_pathology",
            module="vstack.debate_pathology",
            analyzer="DebatePathologyAnalyzer",
            analyzer_async="DebatePathologyAnalyzerAsync",
            shapes=("team",),
            module_id=2,
            pattern_id=26,
            summary="Groupthink, polarization, contagion in crew debate.",
            tags=("groupthink", "polarization"),
        ),
        PatternInfo(
            name="bias_stack",
            module="vstack.bias_stack",
            analyzer="BiasStackAnalyzer",
            analyzer_async="BiasStackAnalyzerAsync",
            shapes=("individual", "team"),
            module_id=2,
            pattern_id=27,
            summary="Cognitive-bias stack on agent reasoning.",
            tags=("bias", "reasoning"),
        ),
        PatternInfo(
            name="devils_advocate",
            module="vstack.devils_advocate",
            analyzer="RoleSeparationAnalyzer",
            analyzer_async="RoleSeparationAnalyzerAsync",
            shapes=("team",),
            module_id=2,
            pattern_id=28,
            summary="Devil's-advocate role-separation in crew debate.",
            tags=("debate", "robustness"),
        ),
        PatternInfo(
            name="thomas_kilmann",
            module="vstack.thomas_kilmann",
            analyzer="ConflictStyleAnalyzer",
            analyzer_async="ConflictStyleAnalyzerAsync",
            shapes=("team",),
            module_id=2,
            pattern_id=29,
            summary="Thomas-Kilmann conflict-style selection in crew clashes.",
            tags=("conflict",),
        ),
        PatternInfo(
            name="aar",
            module="vstack.aar",
            analyzer="AARAnalyzer",
            analyzer_async="AARAnalyzerAsync",
            shapes=("individual", "team"),
            module_id=2,
            pattern_id=30,
            summary="Wharton four-step After-Action Review generator.",
            tags=("post-mortem", "retro"),
        ),
        # --- module 3: organization ------------------------------------
        PatternInfo(
            name="schein_culture",
            module="vstack.schein_culture",
            analyzer="CultureAuditAnalyzer",
            analyzer_async="CultureAuditAnalyzerAsync",
            shapes=("org",),
            module_id=3,
            pattern_id=31,
            summary="Schein three-level culture audit (artifacts/values/assumptions).",
            tags=("culture",),
        ),
        PatternInfo(
            name="robbins_culture",
            module="vstack.robbins_culture",
            analyzer="CultureProfileAnalyzer",
            analyzer_async="CultureProfileAnalyzerAsync",
            shapes=("org",),
            module_id=3,
            pattern_id=32,
            summary="Robbins-Judge 7-dimension culture profile.",
            tags=("culture",),
        ),
        PatternInfo(
            name="org_structure",
            module="vstack.org_structure",
            analyzer="StructureMatrixAnalyzer",
            analyzer_async="StructureMatrixAnalyzerAsync",
            shapes=("org",),
            module_id=3,
            pattern_id=33,
            summary="Galbraith/Mintzberg structure matrix for agent orgs.",
            tags=("structure",),
        ),
        PatternInfo(
            name="span_of_control",
            module="vstack.span_of_control",
            analyzer="SpanLoadCalculator",
            analyzer_async="SpanLoadCalculatorAsync",
            shapes=("org",),
            module_id=3,
            pattern_id=34,
            summary="Span-of-control + centralization for orchestrator agents.",
            tags=("structure",),
        ),
    ]
}


# --- default bundles --------------------------------------------------

# These bundles are the ``diagnose()`` defaults for each shape. Each
# bundle is curated rather than "everything that applies to the shape"
# because running all team patterns on every crew trace would burn
# tokens for marginal value. A user who wants the full sweep can pass
# ``patterns=list(PATTERNS)`` explicitly.

DEFAULT_BUNDLES: dict[TraceShape, tuple[str, ...]] = {
    "individual": (
        "lewin",
        "yerkes_dodson",
        "bias_stack",
        "aar",
    ),
    "team": (
        "lencioni",
        "psych_safety",
        "trust_triangle",
        "process_gain_loss",
        "bias_stack",
        "debate_pathology",
        "aar",
    ),
    "org": (
        "schein_culture",
        "robbins_culture",
        "org_structure",
        "span_of_control",
    ),
}


# --- public helpers ---------------------------------------------------


def iter_bundle(shape: TraceShape | None) -> tuple[PatternInfo, ...]:
    """Return the default :data:`PATTERNS` entries for one trace shape.

    Raises :class:`ValueError` if ``shape`` is not one of
    :data:`ALL_SHAPES`. ``None`` returns the team bundle (the most
    common case in practice for multi-agent debugging).
    """
    if shape is None:
        shape = "team"
    if shape not in ALL_SHAPES:
        raise ValueError(
            f"unknown trace shape {shape!r}; expected one of {ALL_SHAPES}"
        )
    return tuple(PATTERNS[name] for name in DEFAULT_BUNDLES[shape])


def resolve_pattern(info: PatternInfo) -> dict[str, Any]:
    """Lazy-import a pattern's analyzer classes.

    Returns a dict with keys ``analyzer`` and ``analyzer_async``, each
    holding the resolved class object (or ``None`` if the pattern
    doesn't expose one). Raises :class:`ImportError` if the pattern's
    sub-package can't be loaded.

    The import is cached at the module-import level (Python's standard
    sys.modules cache), so calling this repeatedly during one
    ``diagnose()`` run is cheap.
    """
    module = importlib.import_module(info.module)
    out: dict[str, Any] = {"analyzer": None, "analyzer_async": None}
    if info.analyzer:
        out["analyzer"] = getattr(module, info.analyzer, None)
    if info.analyzer_async:
        out["analyzer_async"] = getattr(module, info.analyzer_async, None)
    return out
