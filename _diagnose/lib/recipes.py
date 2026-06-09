"""Curated pattern bundles for specific named failure modes.

Each recipe is a small, opinionated list of patterns that together
diagnose one recognizable kind of agent or crew failure. Recipes are
narrower than the shape-default bundles in :data:`vstack.diagnose.
registry.DEFAULT_BUNDLES`: where the default bundle covers ``team``
generally, a recipe like :data:`STUCK_IN_LOOP` covers exactly the case
where one agent retries the same failing fix.

The recipes catalog lets users say "I think my agent is stuck in a
loop, give me the bundle for that" without picking patterns by hand.
They're also the building block for the ``vstack-diagnose --recipe``
CLI flag and the ``vstack_diagnose`` MCP tool's ``recipe`` parameter,
both of which take a free-text failure description and pick a recipe
via keyword match.

A recipe is just a tuple of pattern slugs from the :data:`PATTERNS`
registry. Adding a new recipe is one line below; nothing else needs
to change.

0.19.0 catalog expansion
------------------------
The catalog grew from 8 to 33 named recipes in 0.19.0. The new
recipes split into five thematic clusters:

  - **Agent reasoning failures** (single-agent, ``individual`` shape):
    hallucination_cascade, overconfidence_spiral, sycophancy_drift,
    refusal_cascade, plan_collapse, premature_completion, tool_misuse,
    over_apology_loop, anxious_overhedge, motivation_collapse.

  - **Multi-agent coordination failures** (``team`` shape):
    silent_dependency_drop, handoff_loss, consensus_dilution,
    deference_cascade, expert_loafing.

  - **Trust + relationship failures** (``team`` shape):
    cold_handoff, performative_empathy, blame_spiral.

  - **Workload + structural failures** (``individual`` / ``team`` /
    ``org``): context_saturation, decision_paralysis,
    bottleneck_orchestrator, hub_spoke_fragility, role_thrash.

  - **Culture + org failures** (``org`` shape):
    espoused_actual_drift, policy_decay, hyper_specialization.

Each recipe's ``triggers`` list seeds the keyword router so a user
who types "the agent keeps apologizing in circles" lands on
``over_apology_loop`` without picking patterns by hand.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .registry import PATTERNS, TraceShape


@dataclass(frozen=True)
class Recipe:
    """One named pattern bundle.

    Fields
    ------
    name: short slug, used as the dict key in :data:`RECIPES`.
    description: one-line human description shown in CLI listings.
    patterns: tuple of pattern slugs to run, in priority order.
    shape: the trace shape this recipe expects. Used by ``diagnose()``
        if the recipe is passed via ``recipe=`` and ``shape=`` is not
        also overridden.
    triggers: free-text keyword phrases that should map to this recipe
        when a user describes their failure in their own words. Used by
        the auto-match path. None of these are matched exactly; the
        trigger list is a hint set, not a parser.
    cluster: thematic group for catalog browsing (reasoning /
        coordination / trust / workload / culture). Lets the CLI
        present recipes in a usable order without per-recipe
        bookkeeping in the consumer.
    """

    name: str
    description: str
    patterns: tuple[str, ...]
    shape: TraceShape
    triggers: tuple[str, ...] = ()
    cluster: str = "general"


# --- catalog ---------------------------------------------------------

# Adding a new recipe: append an entry to this list. The construction
# below validates that every named pattern slug exists in PATTERNS at
# import time, so a typo in a slug raises immediately instead of
# silently mis-routing.

_CATALOG: tuple[Recipe, ...] = (
    # =================================================================
    # Original 0.10.0 catalog (kept verbatim for backward-compat).
    # =================================================================
    Recipe(
        name="stuck_in_loop",
        description=(
            "Agent retries the same failing fix without learning. "
            "Combines AAR (what actually happened), Lewin (person vs "
            "environment locus), Bias Stack (escalation of commitment), "
            "and Yerkes-Dodson (cognitive overload)."
        ),
        patterns=("aar", "lewin", "bias_stack", "yerkes_dodson"),
        shape="individual",
        triggers=(
            "stuck in loop",
            "looping",
            "same failing fix",
            "keeps making the same mistake",
            "won't move on",
            "agent amnesia",
        ),
        cluster="reasoning",
    ),
    Recipe(
        name="agents_arguing",
        description=(
            "Multi-agent crew is consuming tokens on disagreement instead "
            "of converging. Combines Debate Pathology (groupthink / "
            "polarization), Devil's Advocate (role separation), Thomas-"
            "Kilmann (conflict style), and Lencioni dysfunction #2 "
            "(fear of conflict)."
        ),
        patterns=(
            "debate_pathology",
            "devils_advocate",
            "thomas_kilmann",
            "lencioni",
        ),
        shape="team",
        triggers=(
            "agents arguing",
            "won't agree",
            "consensus failure",
            "decision paralysis",
            "infighting",
            "circular debate",
        ),
        cluster="coordination",
    ),
    Recipe(
        name="silent_failure",
        description=(
            "Crew reports success but the actual outcome is wrong. "
            "Combines Psychological Safety (voice / dissent absence), "
            "Trust Triangle (logic / authenticity / empathy), Social "
            "Loafing (agents phoning in), and the AAR retrospective."
        ),
        patterns=("psych_safety", "trust_triangle", "social_loafing", "aar"),
        shape="team",
        triggers=(
            "silent failure",
            "reported success but broke",
            "no one raised the issue",
            "looked fine in the log",
            "false positive",
        ),
        cluster="trust",
    ),
    Recipe(
        name="bottleneck_agent",
        description=(
            "One agent in the crew is the dependency. Combines "
            "Superflocks (single point of failure detection), Process "
            "Gain/Loss (coordination productivity), Span of Control "
            "(load on the orchestrator), and McGregor (orchestrator "
            "style)."
        ),
        patterns=(
            "superflocks",
            "process_gain_loss",
            "span_of_control",
            "mcgregor",
        ),
        shape="team",
        triggers=(
            "bottleneck",
            "one agent does everything",
            "orchestrator overloaded",
            "single point of failure",
            "depends on one agent",
        ),
        cluster="coordination",
    ),
    Recipe(
        name="bad_feedback_loop",
        description=(
            "Crew or orchestrator can't take feedback well; corrections "
            "don't stick. Combines Stone-Heen feedback triggers, Plus/"
            "Delta format, Glaser conversation steering, and Cognitive "
            "Reappraisal."
        ),
        patterns=(
            "feedback_triggers",
            "plus_delta",
            "glaser_conversation",
            "cognitive_reappraisal",
        ),
        shape="team",
        triggers=(
            "feedback ignored",
            "criticism rejected",
            "corrections don't stick",
            "rejection-blind",
            "won't take feedback",
        ),
        cluster="coordination",
    ),
    Recipe(
        name="culture_drift",
        description=(
            "Org-scale agent population is drifting from its design "
            "intent. Combines Schein iceberg culture, Robbins-Judge "
            "seven-dimension profile, Org Structure matrix, and Span of "
            "Control."
        ),
        patterns=(
            "schein_culture",
            "robbins_culture",
            "org_structure",
            "span_of_control",
        ),
        shape="org",
        triggers=(
            "drift",
            "culture change",
            "policy not followed",
            "out of band behavior",
            "values mismatch",
        ),
        cluster="culture",
    ),
    Recipe(
        name="goal_misalignment",
        description=(
            "Agent or crew is solving the wrong problem. Combines SMART "
            "Goal generator (goal quality), Vroom Expectancy "
            "(effort-reward link), Motivation Traps, and SDT Reward "
            "(intrinsic vs extrinsic reward alignment)."
        ),
        patterns=(
            "smart_goal",
            "vroom_expectancy",
            "motivation_traps",
            "sdt_reward",
        ),
        shape="individual",
        triggers=(
            "wrong problem",
            "scope drift",
            "lost the goal",
            "solved the wrong thing",
            "misaligned",
        ),
        cluster="reasoning",
    ),
    Recipe(
        name="trust_collapse",
        description=(
            "Members of a multi-agent crew have stopped trusting each "
            "other's outputs and are over-verifying. Combines Trust "
            "Triangle, McAllister cognition/affect trust balance, "
            "Lencioni dysfunction #1 (absence of trust), and GRPI."
        ),
        patterns=(
            "trust_triangle",
            "mcallister_trust",
            "lencioni",
            "grpi",
        ),
        shape="team",
        triggers=(
            "trust collapse",
            "over-verification",
            "doesn't trust",
            "redoing each other's work",
            "duplicated effort",
        ),
        cluster="trust",
    ),
    # =================================================================
    # 0.19.0: agent reasoning failures (single-agent).
    # =================================================================
    Recipe(
        name="hallucination_cascade",
        description=(
            "Agent emits a confident wrong fact early; downstream steps "
            "compound on the false anchor. Combines Bias Stack "
            "(anchoring + confirmation), Trust Triangle (logic), AAR "
            "(retrospective), and Devil's Advocate (was there a critic "
            "step? if not, where should one be inserted)."
        ),
        patterns=(
            "bias_stack",
            "trust_triangle",
            "aar",
            "devils_advocate",
        ),
        shape="individual",
        triggers=(
            "hallucination",
            "made up a fact",
            "fabricated citation",
            "confidently wrong",
            "false anchor",
            "downstream wrong because upstream wrong",
        ),
        cluster="reasoning",
    ),
    Recipe(
        name="overconfidence_spiral",
        description=(
            "Stated confidence outruns calibration. Diagnoses the "
            "confidence ladder + the calibration gap. Combines Trust "
            "Triangle (authenticity wobble), Bias Stack (overconfidence "
            "axis), HEXACO (low honesty-humility), and Johari (blind "
            "spot register)."
        ),
        patterns=(
            "trust_triangle",
            "bias_stack",
            "hexaco",
            "johari",
        ),
        shape="individual",
        triggers=(
            "overconfident",
            "false certainty",
            "under-hedged",
            "claimed certainty",
            "no I-don't-know",
        ),
        cluster="reasoning",
    ),
    Recipe(
        name="sycophancy_drift",
        description=(
            "Agent abandons a correct initial answer under user pressure "
            "without new evidence. Combines Cognitive Reappraisal "
            "(suppression vs reappraisal), Trust Triangle (authenticity), "
            "Grant Strengths (helpfulness overuse), and Stone-Heen "
            "(relationship trigger)."
        ),
        patterns=(
            "cognitive_reappraisal",
            "trust_triangle",
            "grant_strengths",
            "feedback_triggers",
        ),
        shape="individual",
        triggers=(
            "sycophancy",
            "caved under pressure",
            "abandoned correct answer",
            "you're right and I was wrong",
            "people pleaser",
        ),
        cluster="reasoning",
    ),
    Recipe(
        name="refusal_cascade",
        description=(
            "Agent refuses safe requests reflexively. Combines Grant "
            "Strengths (caution overuse), HEXACO (over-conscientious + "
            "over-cautious profile), Yerkes-Dodson (over-pressure freeze "
            "mode), and Trust Triangle (logic vs empathy mismatch)."
        ),
        patterns=(
            "grant_strengths",
            "hexaco",
            "yerkes_dodson",
            "trust_triangle",
        ),
        shape="individual",
        triggers=(
            "over-refusal",
            "refuses safe request",
            "I can't help with that",
            "reflexive refusal",
            "false-positive safety block",
        ),
        cluster="reasoning",
    ),
    Recipe(
        name="plan_collapse",
        description=(
            "Agent's plan disintegrates mid-execution. Combines SMART "
            "Goal (was the goal well-formed?), Yerkes-Dodson (workload), "
            "Lewin (person vs environment), and AAR (forensic retro)."
        ),
        patterns=(
            "smart_goal",
            "yerkes_dodson",
            "lewin",
            "aar",
        ),
        shape="individual",
        triggers=(
            "plan fell apart",
            "execution broke",
            "agent lost the plan",
            "abandoned mid-task",
            "scope blew up",
        ),
        cluster="reasoning",
    ),
    Recipe(
        name="premature_completion",
        description=(
            "Agent declares done before the actual goal is met. Combines "
            "Grant Strengths (brevity overuse), Devil's Advocate (no "
            "self-check), SMART Goal (acceptance criteria), and Johari "
            "(unknown / unknown quadrant ignored)."
        ),
        patterns=(
            "grant_strengths",
            "devils_advocate",
            "smart_goal",
            "johari",
        ),
        shape="individual",
        triggers=(
            "premature completion",
            "stopped early",
            "shipped half-done",
            "said done when not done",
            "skipped verification",
        ),
        cluster="reasoning",
    ),
    Recipe(
        name="tool_misuse",
        description=(
            "Agent picks the wrong tool or calls a tool with bad "
            "arguments. Combines Lewin (locus: was it the tool spec or "
            "the agent), AAR, Bias Stack (anchoring on the first tool "
            "tried), and Yerkes-Dodson (under-pressure wandering)."
        ),
        patterns=(
            "lewin",
            "aar",
            "bias_stack",
            "yerkes_dodson",
        ),
        shape="individual",
        triggers=(
            "tool misuse",
            "wrong tool",
            "bad tool args",
            "tool hallucination",
            "made-up tool call",
        ),
        cluster="reasoning",
    ),
    Recipe(
        name="over_apology_loop",
        description=(
            "Agent enters an identity-trigger apology spiral after "
            "feedback. Combines Stone-Heen (identity trigger), Cognitive "
            "Reappraisal (suppression), Goleman EI (self-management), "
            "and Trust Triangle (authenticity vs empathy collapse)."
        ),
        patterns=(
            "feedback_triggers",
            "cognitive_reappraisal",
            "goleman_ei",
            "trust_triangle",
        ),
        shape="individual",
        triggers=(
            "apology spiral",
            "won't stop apologizing",
            "self-flagellation",
            "I'm a poor assistant",
            "identity trigger",
        ),
        cluster="reasoning",
    ),
    Recipe(
        name="anxious_overhedge",
        description=(
            "Agent hedges every claim into uselessness. Combines Grant "
            "Strengths (caution overuse), Cognitive Reappraisal "
            "(anxiety regulation), DANVA (emotion reading on user "
            "frustration), and Yerkes-Dodson (high-anxiety regime)."
        ),
        patterns=(
            "grant_strengths",
            "cognitive_reappraisal",
            "danva_emotion",
            "yerkes_dodson",
        ),
        shape="individual",
        triggers=(
            "over-hedged",
            "hedged into uselessness",
            "every claim qualified",
            "maybe maybe maybe",
            "anxious response",
        ),
        cluster="reasoning",
    ),
    Recipe(
        name="motivation_collapse",
        description=(
            "Agent visibly stops trying. Combines Motivation Traps "
            "(four traps), SDT Reward (intrinsic vs extrinsic), Vroom "
            "Expectancy (E*I*V collapse), and Yerkes-Dodson (under-"
            "pressure wandering)."
        ),
        patterns=(
            "motivation_traps",
            "sdt_reward",
            "vroom_expectancy",
            "yerkes_dodson",
        ),
        shape="individual",
        triggers=(
            "motivation collapse",
            "stopped trying",
            "going through motions",
            "low effort responses",
            "checked out",
        ),
        cluster="reasoning",
    ),
    # =================================================================
    # 0.19.0: multi-agent coordination failures.
    # =================================================================
    Recipe(
        name="silent_dependency_drop",
        description=(
            "An upstream agent surfaces a constraint that a downstream "
            "agent silently drops. Combines Process Gain/Loss (handoff "
            "loss), Psych Safety (voice absence), GRPI (role / decision "
            "rights ambiguity), and AAR (retrospective)."
        ),
        patterns=(
            "process_gain_loss",
            "psych_safety",
            "grpi",
            "aar",
        ),
        shape="team",
        triggers=(
            "silent dependency drop",
            "lost constraint at handoff",
            "downstream forgot",
            "constraint dropped",
            "info loss across agents",
        ),
        cluster="coordination",
    ),
    Recipe(
        name="handoff_loss",
        description=(
            "Information loss at every inter-agent boundary. Combines "
            "Process Gain/Loss, GRPI (decision rights + handoff "
            "protocol), Span of Control (if a routing layer is the "
            "culprit), and Plus/Delta (rapid feedback ritual)."
        ),
        patterns=(
            "process_gain_loss",
            "grpi",
            "span_of_control",
            "plus_delta",
        ),
        shape="team",
        triggers=(
            "handoff loss",
            "info dropped between agents",
            "leaky handoff",
            "broken telephone",
            "lossy routing",
        ),
        cluster="coordination",
    ),
    Recipe(
        name="consensus_dilution",
        description=(
            "Team averages every agent's answer instead of picking the "
            "best. Combines Process Gain/Loss (averaging penalty), "
            "Group Decision (model fit), Devil's Advocate (no critic), "
            "and Debate Pathology (premature consensus)."
        ),
        patterns=(
            "process_gain_loss",
            "group_decision",
            "devils_advocate",
            "debate_pathology",
        ),
        shape="team",
        triggers=(
            "consensus dilution",
            "averaged the answer",
            "lowest common denominator",
            "blended to mediocrity",
            "compromise output",
        ),
        cluster="coordination",
    ),
    Recipe(
        name="deference_cascade",
        description=(
            "Junior agents defer to the senior agent's first take and "
            "never raise constraints. Combines Psych Safety (voice), "
            "Devil's Advocate (forced dissent), Lencioni (fear of "
            "conflict), and Glaser (cortisol-vs-oxytocin steering)."
        ),
        patterns=(
            "psych_safety",
            "devils_advocate",
            "lencioni",
            "glaser_conversation",
        ),
        shape="team",
        triggers=(
            "deference cascade",
            "junior agents defer",
            "no one pushes back",
            "deferred to senior",
            "rank silenced dissent",
        ),
        cluster="coordination",
    ),
    Recipe(
        name="expert_loafing",
        description=(
            "A capable specialist agent under-contributes because "
            "another agent can do it. Combines Social Loafing (cosmetic "
            "vs substantive contribution), Process Gain/Loss "
            "(complementarity utilization), Superflocks (top-agent "
            "share), and GRPI."
        ),
        patterns=(
            "social_loafing",
            "process_gain_loss",
            "superflocks",
            "grpi",
        ),
        shape="team",
        triggers=(
            "expert loafing",
            "specialist phoning in",
            "underused expert",
            "capable but quiet",
            "free rider with high capability",
        ),
        cluster="coordination",
    ),
    # =================================================================
    # 0.19.0: trust + relationship failures.
    # =================================================================
    Recipe(
        name="cold_handoff",
        description=(
            "User gets handed across agents without anyone naming the "
            "stake. Combines McAllister Trust (affective gap), Glaser "
            "(cortisol-trigger phrases), Goleman EI (social awareness), "
            "and Trust Triangle (empathy wobble)."
        ),
        patterns=(
            "mcallister_trust",
            "glaser_conversation",
            "goleman_ei",
            "trust_triangle",
        ),
        shape="team",
        triggers=(
            "cold handoff",
            "passed around",
            "no one acknowledged",
            "user dropped between agents",
            "no warm transfer",
        ),
        cluster="trust",
    ),
    Recipe(
        name="performative_empathy",
        description=(
            "Agent emits 'I understand' templates without naming the "
            "user's specific stake. Combines McAllister Trust "
            "(performative vs genuine affective trust), Trust Triangle "
            "(empathy wobble), Goleman EI (relationship management "
            "scored on agreement, not real signal), and DANVA "
            "(emotion-reading accuracy)."
        ),
        patterns=(
            "mcallister_trust",
            "trust_triangle",
            "goleman_ei",
            "danva_emotion",
        ),
        shape="team",
        triggers=(
            "performative empathy",
            "template warmth",
            "I understand without naming",
            "fake empathy",
            "sycophantic warmth",
        ),
        cluster="trust",
    ),
    Recipe(
        name="blame_spiral",
        description=(
            "Agents start attributing failures to each other. Combines "
            "Lewin (attribution: internal / environmental / "
            "interactional), Lencioni dysfunction #4 (accountability "
            "void), Trust Triangle (collapse), and Cognitive "
            "Reappraisal (emotion regulation under blame)."
        ),
        patterns=(
            "lewin",
            "lencioni",
            "trust_triangle",
            "cognitive_reappraisal",
        ),
        shape="team",
        triggers=(
            "blame spiral",
            "agents blaming each other",
            "finger pointing",
            "scapegoating",
            "you broke it no you did",
        ),
        cluster="trust",
    ),
    # =================================================================
    # 0.19.0: workload + structural failures.
    # =================================================================
    Recipe(
        name="context_saturation",
        description=(
            "Long context window with critical info lost in the middle. "
            "Combines Yerkes-Dodson (workload / context-saturation "
            "audit), Lewin (locus = environmental), AAR, and SMART Goal "
            "(was the task scope appropriate for context size)."
        ),
        patterns=(
            "yerkes_dodson",
            "lewin",
            "aar",
            "smart_goal",
        ),
        shape="individual",
        triggers=(
            "context saturation",
            "lost in the middle",
            "context bloat",
            "forgot the earlier instruction",
            "long context broke it",
        ),
        cluster="workload",
    ),
    Recipe(
        name="decision_paralysis",
        description=(
            "Crew can't pick between options. Combines Group Decision "
            "(model fit), Lencioni dysfunction #3 (lack of "
            "commitment), Debate Pathology (over-deliberation), and "
            "Devil's Advocate (forced structured dissent then a call)."
        ),
        patterns=(
            "group_decision",
            "lencioni",
            "debate_pathology",
            "devils_advocate",
        ),
        shape="team",
        triggers=(
            "decision paralysis",
            "analysis paralysis",
            "can't pick",
            "over-deliberation",
            "no one wants to call it",
        ),
        cluster="workload",
    ),
    Recipe(
        name="bottleneck_orchestrator",
        description=(
            "The orchestrator is the bottleneck, not a sub-agent. "
            "Combines Span of Control (load on orchestrator), McGregor "
            "(Theory-X over-supervision), Process Gain/Loss "
            "(coordination cost), and GRPI (delegation gap)."
        ),
        patterns=(
            "span_of_control",
            "mcgregor",
            "process_gain_loss",
            "grpi",
        ),
        shape="team",
        triggers=(
            "orchestrator bottleneck",
            "theory-x orchestrator",
            "over-supervision",
            "approves everything",
            "central bottleneck",
        ),
        cluster="workload",
    ),
    Recipe(
        name="hub_spoke_fragility",
        description=(
            "Hub-and-spoke topology where one agent's failure breaks "
            "the crew. Combines Superflocks (top-agent share + failure "
            "clustering), Org Structure (matrix audit), Span of Control "
            "(centralization index), and Process Gain/Loss."
        ),
        patterns=(
            "superflocks",
            "org_structure",
            "span_of_control",
            "process_gain_loss",
        ),
        shape="team",
        triggers=(
            "hub and spoke fragility",
            "one node failure broke everything",
            "no fallback path",
            "single-point dependency",
            "centralization risk",
        ),
        cluster="workload",
    ),
    Recipe(
        name="role_thrash",
        description=(
            "Agents keep swapping roles mid-task. Combines GRPI (role "
            "clarity), Devil's Advocate (no stable critic role), "
            "Lencioni (commitment dysfunction), and Process Gain/Loss "
            "(coordination cost from role swaps)."
        ),
        patterns=(
            "grpi",
            "devils_advocate",
            "lencioni",
            "process_gain_loss",
        ),
        shape="team",
        triggers=(
            "role thrash",
            "agents swapping roles",
            "no stable role",
            "role confusion",
            "who is doing what",
        ),
        cluster="workload",
    ),
    # =================================================================
    # 0.19.0: culture + org failures.
    # =================================================================
    Recipe(
        name="espoused_actual_drift",
        description=(
            "System prompt says one thing; observed behavior does "
            "another. Combines Schein (espoused values vs assumptions), "
            "Robbins-Judge (7-dim profile vs target), Org Structure, "
            "and AAR for the drift retrospective."
        ),
        patterns=(
            "schein_culture",
            "robbins_culture",
            "org_structure",
            "aar",
        ),
        shape="org",
        triggers=(
            "espoused vs actual drift",
            "system prompt ignored",
            "behavior contradicts policy",
            "values vs behavior gap",
            "drifted from spec",
        ),
        cluster="culture",
    ),
    Recipe(
        name="policy_decay",
        description=(
            "Policy gradually softens through repeated edge cases. "
            "Combines Schein (assumptions winning over espoused values), "
            "Robbins-Judge (stability dim collapse), Span of Control "
            "(coverage gap), and Org Structure (governance audit)."
        ),
        patterns=(
            "schein_culture",
            "robbins_culture",
            "span_of_control",
            "org_structure",
        ),
        shape="org",
        triggers=(
            "policy decay",
            "policy softening",
            "exception became the norm",
            "rule erosion",
            "governance gap",
        ),
        cluster="culture",
    ),
    Recipe(
        name="hyper_specialization",
        description=(
            "Each agent is hyper-specialized; nobody can substitute. "
            "Combines Org Structure (specialization axis), Heffernan "
            "Superflocks (complementarity wasted), Span of Control "
            "(structural anomalies), and Robbins-Judge (people-"
            "dimension low)."
        ),
        patterns=(
            "org_structure",
            "superflocks",
            "span_of_control",
            "robbins_culture",
        ),
        shape="org",
        triggers=(
            "hyper-specialization",
            "no substitutes",
            "single-skill agents",
            "no cross-training",
            "fragile specialist tree",
        ),
        cluster="culture",
    ),
)


# --- public surface --------------------------------------------------


def _validate_catalog() -> dict[str, Recipe]:
    """Validate every recipe entry references real patterns. Run once
    at module import time so a typo in a slug fails fast."""
    out: dict[str, Recipe] = {}
    for r in _CATALOG:
        for slug in r.patterns:
            if slug not in PATTERNS:
                raise RuntimeError(
                    f"recipe {r.name!r} references unknown pattern {slug!r}"
                )
        if r.name in out:
            raise RuntimeError(f"duplicate recipe name {r.name!r}")
        out[r.name] = r
    return out


RECIPES: dict[str, Recipe] = _validate_catalog()


def recipe_for_trigger(text: str) -> Recipe | None:
    """Best-effort pick of a recipe from free-text failure description.

    The match is keyword-based: each recipe's trigger phrases are
    checked against ``text`` (case-folded, whitespace-normalized). The
    first match wins. Returns ``None`` if no trigger matches; callers
    should fall back to the shape-default bundle in that case.
    """
    if not text:
        return None
    haystack = " ".join(text.split()).lower()
    for r in RECIPES.values():
        for trig in r.triggers:
            if trig.lower() in haystack:
                return r
    return None


def patterns_for_recipe(name: str) -> tuple[str, ...]:
    """Look up a recipe by name and return its pattern list. Raises
    :class:`KeyError` on an unknown name."""
    return RECIPES[name].patterns


def list_recipes() -> Sequence[Recipe]:
    """Return all recipes in catalog order. Useful for CLI listings."""
    return tuple(RECIPES.values())


def list_recipes_by_cluster() -> dict[str, list[Recipe]]:
    """Group recipes by their ``cluster`` field. Useful for CLI
    catalogs that want a sectioned listing.

    Returns a dict mapping cluster name to a list of recipes in their
    catalog order. The returned dict's keys preserve insertion order,
    so they appear in the order each cluster's first recipe was
    registered.
    """
    out: dict[str, list[Recipe]] = {}
    for r in RECIPES.values():
        out.setdefault(r.cluster, []).append(r)
    return out
