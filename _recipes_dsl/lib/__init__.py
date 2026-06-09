"""vstack.recipes_dsl — declarative DSL for custom recipes.

Define recipes in YAML or JSON instead of Python code. Useful for:

  - Non-engineering teams owning recipe definitions.
  - Recipe sharing across projects.
  - Recipe versioning + git diffing.

Example YAML
------------

    # my_recipe.yaml
    name: incident_triage
    description: Triage agent failures during an incident.
    shape: individual
    cluster: reasoning
    patterns:
      - lewin
      - yerkes_dodson
      - bias_stack
      - aar
    triggers:
      - "agent is stuck retrying"
      - "agent loop"
      - "production incident"
    intervention_hint: "Apply Lewin locus + Yerkes-Dodson load checks."

Loading
-------

    from vstack.recipes_dsl import load_recipe_from_file

    recipe = load_recipe_from_file("my_recipe.yaml")
    print(recipe.name, recipe.patterns)

Bulk loading
------------

    from vstack.recipes_dsl import load_recipes_from_dir

    recipes = load_recipes_from_dir("recipes/")
    for r in recipes:
        print(r.name)
"""

from __future__ import annotations

from ._dsl import (
    DSLValidationError,
    RecipeDSL,
    load_recipe_from_dict,
    load_recipe_from_file,
    load_recipes_from_dir,
    parse_recipe_yaml,
    validate_recipe,
)

__all__ = [
    "DSLValidationError",
    "RecipeDSL",
    "load_recipe_from_dict",
    "load_recipe_from_file",
    "load_recipes_from_dir",
    "parse_recipe_yaml",
    "validate_recipe",
]
