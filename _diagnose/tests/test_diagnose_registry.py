"""Tests for the vstack.diagnose registry: structural invariants that
must hold for every shipped pattern entry. These tests do not call any
LLM and do not require any pattern's optional dependencies; they only
read the static :data:`PATTERNS` dict.
"""

from __future__ import annotations

import pytest

from vstack.diagnose.registry import (
    ALL_SHAPES,
    DEFAULT_BUNDLES,
    PATTERNS,
    PatternInfo,
    SEVERITY_ORDER,
    iter_bundle,
    severity_rank,
)


def test_patterns_dict_is_non_empty() -> None:
    assert len(PATTERNS) >= 30, f"only {len(PATTERNS)} patterns registered; expected >= 30"


def test_pattern_names_are_unique_slugs() -> None:
    # The dict key is the slug; we additionally check each entry's
    # ``name`` field matches its key so iteration on values stays sane.
    for slug, info in PATTERNS.items():
        assert info.name == slug, f"key/value mismatch: key={slug!r} info.name={info.name!r}"


@pytest.mark.parametrize("slug,info", list(PATTERNS.items()))
def test_pattern_entry_has_required_metadata(slug: str, info: PatternInfo) -> None:
    assert info.module.startswith("vstack."), info.module
    # analyzer name may be None for a small number of patterns that
    # only ship an async analyzer; we tolerate that but require at
    # least one of the two.
    assert info.analyzer or info.analyzer_async, (
        f"pattern {slug!r} ships neither sync nor async analyzer"
    )
    assert info.shapes, f"pattern {slug!r} has no applicable shapes"
    for shape in info.shapes:
        assert shape in ALL_SHAPES, f"pattern {slug!r} declares unknown shape {shape!r}"
    assert 1 <= info.module_id <= 3
    assert 1 <= info.pattern_id <= 99
    assert info.summary, f"pattern {slug!r} has no summary"


def test_pattern_ids_unique() -> None:
    seen: dict[int, str] = {}
    for slug, info in PATTERNS.items():
        prior = seen.get(info.pattern_id)
        assert prior is None, f"pattern_id {info.pattern_id} reused by {prior!r} and {slug!r}"
        seen[info.pattern_id] = slug


def test_default_bundles_reference_real_patterns() -> None:
    for shape, slugs in DEFAULT_BUNDLES.items():
        assert shape in ALL_SHAPES
        assert slugs, f"empty default bundle for shape {shape!r}"
        for slug in slugs:
            assert slug in PATTERNS, f"bundle for shape {shape!r} references unknown {slug!r}"


@pytest.mark.parametrize("shape", ALL_SHAPES)
def test_iter_bundle_returns_pattern_infos(shape: str) -> None:
    bundle = iter_bundle(shape)  # type: ignore[arg-type]
    assert bundle, f"empty bundle for shape {shape!r}"
    assert all(isinstance(p, PatternInfo) for p in bundle)


def test_iter_bundle_default_is_team() -> None:
    assert iter_bundle(None) == iter_bundle("team")


def test_iter_bundle_rejects_unknown_shape() -> None:
    with pytest.raises(ValueError):
        iter_bundle("does-not-exist")  # type: ignore[arg-type]


def test_severity_order_is_monotonic() -> None:
    for i, label in enumerate(SEVERITY_ORDER):
        assert severity_rank(label) == i, label
    # Case + whitespace tolerance.
    assert severity_rank("  CRITICAL ") == severity_rank("critical")
    # Unknown labels rank as -1 (below everything).
    assert severity_rank("garbage") == -1
    assert severity_rank("") == -1
