"""Tests for the recipes_dsl module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vstack.recipes_dsl import (
    DSLValidationError,
    RecipeDSL,
    load_recipe_from_dict,
    load_recipe_from_file,
    load_recipes_from_dir,
    parse_recipe_yaml,
    validate_recipe,
)


def _valid_recipe_dict():
    return {
        "name": "test_recipe",
        "description": "A test recipe.",
        "shape": "individual",
        "cluster": "reasoning",
        "patterns": ["lewin", "aar"],
        "triggers": ["test trigger"],
        "intervention_hint": "Apply Lewin first.",
    }


class TestValidateRecipe:
    def test_valid_recipe_passes(self):
        validate_recipe(_valid_recipe_dict())

    def test_missing_name_fails(self):
        data = _valid_recipe_dict()
        del data["name"]
        with pytest.raises(DSLValidationError, match="name"):
            validate_recipe(data)

    def test_empty_name_fails(self):
        data = _valid_recipe_dict()
        data["name"] = ""
        with pytest.raises(DSLValidationError):
            validate_recipe(data)

    def test_invalid_shape_fails(self):
        data = _valid_recipe_dict()
        data["shape"] = "alien"
        with pytest.raises(DSLValidationError, match="shape"):
            validate_recipe(data)

    def test_invalid_cluster_fails(self):
        data = _valid_recipe_dict()
        data["cluster"] = "alien"
        with pytest.raises(DSLValidationError, match="cluster"):
            validate_recipe(data)

    def test_empty_patterns_fails(self):
        data = _valid_recipe_dict()
        data["patterns"] = []
        with pytest.raises(DSLValidationError, match="patterns"):
            validate_recipe(data)

    def test_non_string_pattern_fails(self):
        data = _valid_recipe_dict()
        data["patterns"] = [42]
        with pytest.raises(DSLValidationError):
            validate_recipe(data)

    def test_non_list_triggers_fails(self):
        data = _valid_recipe_dict()
        data["triggers"] = "not a list"
        with pytest.raises(DSLValidationError):
            validate_recipe(data)


class TestLoadRecipeFromDict:
    def test_constructs_recipe(self):
        recipe = load_recipe_from_dict(_valid_recipe_dict())
        assert isinstance(recipe, RecipeDSL)
        assert recipe.name == "test_recipe"
        assert recipe.patterns == ["lewin", "aar"]

    def test_invalid_dict_raises(self):
        with pytest.raises(DSLValidationError):
            load_recipe_from_dict({})

    def test_optional_fields_default(self):
        data = {
            "name": "t",
            "description": "d",
            "shape": "individual",
            "cluster": "reasoning",
            "patterns": ["lewin"],
        }
        recipe = load_recipe_from_dict(data)
        assert recipe.triggers == []
        assert recipe.intervention_hint == ""

    def test_metadata_passes_through(self):
        data = _valid_recipe_dict()
        data["metadata"] = {"custom": "value"}
        recipe = load_recipe_from_dict(data)
        assert recipe.metadata["custom"] == "value"


class TestLoadFromFile:
    def test_load_json(self, tmp_path: Path):
        path = tmp_path / "recipe.json"
        path.write_text(json.dumps(_valid_recipe_dict()))
        recipe = load_recipe_from_file(path)
        assert recipe.name == "test_recipe"

    def test_load_yaml(self, tmp_path: Path):
        path = tmp_path / "recipe.yaml"
        yaml_text = """\
name: test_recipe
description: A test recipe.
shape: individual
cluster: reasoning
patterns:
  - lewin
  - aar
triggers:
  - test trigger
intervention_hint: Apply Lewin first.
"""
        path.write_text(yaml_text)
        recipe = load_recipe_from_file(path)
        assert recipe.name == "test_recipe"
        assert "lewin" in recipe.patterns

    def test_load_unknown_extension_attempts_yaml(self, tmp_path: Path):
        path = tmp_path / "recipe.txt"
        # Write JSON; parser will try YAML first, then JSON.
        path.write_text(json.dumps(_valid_recipe_dict()))
        recipe = load_recipe_from_file(path)
        assert recipe.name == "test_recipe"

    def test_invalid_yaml_raises(self, tmp_path: Path):
        path = tmp_path / "recipe.yaml"
        path.write_text("not: valid: yaml: at all:")
        with pytest.raises((DSLValidationError, json.JSONDecodeError, Exception)):
            load_recipe_from_file(path)


class TestLoadFromDir:
    def test_loads_multiple_files(self, tmp_path: Path):
        for i in range(3):
            data = _valid_recipe_dict()
            data["name"] = f"recipe_{i}"
            (tmp_path / f"r{i}.json").write_text(json.dumps(data))

        recipes = load_recipes_from_dir(tmp_path)
        assert len(recipes) == 3
        names = sorted(r.name for r in recipes)
        assert names == ["recipe_0", "recipe_1", "recipe_2"]

    def test_skips_invalid_files(self, tmp_path: Path):
        # One valid, one invalid.
        (tmp_path / "good.json").write_text(json.dumps(_valid_recipe_dict()))
        (tmp_path / "bad.json").write_text("not even json")

        recipes = load_recipes_from_dir(tmp_path)
        assert len(recipes) == 1

    def test_nonexistent_dir_raises(self):
        with pytest.raises(FileNotFoundError):
            load_recipes_from_dir("/nonexistent/path/xyz")


class TestParseRecipeYAML:
    def test_simple_yaml(self):
        text = """\
name: test
shape: individual
"""
        result = parse_recipe_yaml(text)
        assert result["name"] == "test"
        assert result["shape"] == "individual"

    def test_list_yaml(self):
        text = """\
name: test
patterns:
  - lewin
  - aar
"""
        result = parse_recipe_yaml(text)
        assert "lewin" in result["patterns"]
        assert "aar" in result["patterns"]


class TestRecipeDSLToDict:
    def test_roundtrip(self):
        data = _valid_recipe_dict()
        recipe = load_recipe_from_dict(data)
        out = recipe.to_dict()
        assert out["name"] == data["name"]
        assert out["patterns"] == data["patterns"]
        assert out["triggers"] == data["triggers"]
