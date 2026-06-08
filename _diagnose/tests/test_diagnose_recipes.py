"""Tests for the named-recipe layer.

The recipes catalog is loaded + validated at import time, so most of
what we check here is that the catalog is non-empty, every pattern slug
referenced exists, the trigger-keyword matcher behaves sensibly, and
the ``diagnose(recipe=...)`` integration uses the recipe's pattern list.
"""

from __future__ import annotations

import pytest

from vstack.diagnose import (
    PATTERNS,
    RECIPES,
    diagnose,
    list_recipes,
    patterns_for_recipe,
    recipe_for_trigger,
)


def test_catalog_non_empty() -> None:
    assert len(RECIPES) >= 5


def test_every_recipe_pattern_exists() -> None:
    for r in RECIPES.values():
        for slug in r.patterns:
            assert slug in PATTERNS, (
                f"recipe {r.name!r} references unknown pattern {slug!r}"
            )


def test_every_recipe_has_a_description_and_shape() -> None:
    for r in RECIPES.values():
        assert r.description, f"recipe {r.name!r} missing description"
        assert r.shape in ("individual", "team", "org")


def test_recipe_lookup_by_name_returns_patterns_tuple() -> None:
    pats = patterns_for_recipe("stuck_in_loop")
    assert isinstance(pats, tuple)
    assert pats == RECIPES["stuck_in_loop"].patterns


def test_recipe_lookup_unknown_raises_keyerror() -> None:
    with pytest.raises(KeyError):
        patterns_for_recipe("does_not_exist")


def test_list_recipes_returns_all() -> None:
    seq = list_recipes()
    assert len(seq) == len(RECIPES)
    names = {r.name for r in seq}
    assert names == set(RECIPES)


def test_trigger_matcher_picks_stuck_in_loop_from_phrase() -> None:
    match = recipe_for_trigger("My agent keeps making the same mistake on auth")
    assert match is not None
    assert match.name == "stuck_in_loop"


def test_trigger_matcher_picks_agents_arguing() -> None:
    match = recipe_for_trigger("The crew is consensus failure all day")
    assert match is not None
    assert match.name == "agents_arguing"


def test_trigger_matcher_returns_none_when_nothing_matches() -> None:
    assert recipe_for_trigger("a totally unrelated string") is None
    assert recipe_for_trigger("") is None


def test_diagnose_recipe_uses_recipe_pattern_list() -> None:
    """When recipe= is set and patterns= is omitted, the diagnose runner
    must use the recipe's pattern list. We pick a recipe with patterns
    we know will error out (no llm_client), then check that those
    pattern names appear in the per_pattern report."""
    import types

    trace = types.SimpleNamespace(goal="x", steps=())
    report = diagnose(
        trace,
        llm_client=None,
        recipe="stuck_in_loop",
        shape="individual",
    )
    expected = RECIPES["stuck_in_loop"].patterns
    seen = {pr.pattern for pr in report.per_pattern}
    assert seen == set(expected)


def test_diagnose_explicit_patterns_beats_recipe() -> None:
    """patterns= explicitly overrides recipe=."""
    import types

    trace = types.SimpleNamespace(goal="x", steps=())
    report = diagnose(
        trace,
        llm_client=None,
        recipe="stuck_in_loop",
        patterns=["lewin"],
        shape="individual",
    )
    seen = {pr.pattern for pr in report.per_pattern}
    assert seen == {"lewin"}


def test_diagnose_unknown_recipe_raises() -> None:
    import types
    with pytest.raises(ValueError):
        diagnose(
            types.SimpleNamespace(goal="x", steps=()),
            recipe="nope-not-a-recipe",
        )
