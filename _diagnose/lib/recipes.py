"""Curated pattern bundles for specific named failure modes.

Each recipe is a small, opinionated list of patterns that together
diagnose one recognizable kind of agent or crew failure. Recipes are
narrower than the shape-default bundles in :data:`vstack.diagnose.
registry.DEFAULT_BUNDLES`: where the default bundle covers ``team``
generally, a recipe like :data:`STUCK_IN_LOOP` covers exactly the case
where one agent retries the same failing fix.

The recipes catalog lets users say "I think my agent is stuck in a
loop, give me the bundle for that" without picking patterns by hand.
They're also the building block for the upcoming ``vstack.recipes`` CLI
command which takes a free-text failure description and picks a recipe
via keyword match.

A recipe is just a tuple of pattern slugs from the :data:`PATTERNS`
registry. Adding a new recipe is one line below; nothing else needs
to change.
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
        the upcoming auto-match path. None of these are matched
        exactly; the trigger list is a hint set, not a parser.
    """

    name: str
    description: str
    patterns: tuple[str, ...]
    shape: TraceShape
    triggers: tuple[str, ...] = ()


# --- catalog ---------------------------------------------------------

# Adding a new recipe: append an entry to this list. The construction
# below validates that every named pattern slug exists in PATTERNS at
# import time, so a typo in a slug raises immediately instead of
# silently mis-routing.

_CATALOG: tuple[Recipe, ...] = (
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
