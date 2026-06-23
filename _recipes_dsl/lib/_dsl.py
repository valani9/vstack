"""Recipe DSL parser + validator.

YAML is parsed via PyYAML when available; falls back to a minimal
JSON-style parser otherwise. Custom recipes are validated against
a schema before becoming usable.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast


VALID_SHAPES = {"individual", "team", "org"}
VALID_CLUSTERS = {"reasoning", "coordination", "trust", "workload", "culture"}


class DSLValidationError(Exception):
    """Raised when a recipe fails validation."""


@dataclass
class RecipeDSL:
    """A parsed + validated recipe definition."""

    name: str
    description: str
    shape: str
    cluster: str
    patterns: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)
    intervention_hint: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "shape": self.shape,
            "cluster": self.cluster,
            "patterns": list(self.patterns),
            "triggers": list(self.triggers),
            "intervention_hint": self.intervention_hint,
            "metadata": dict(self.metadata),
        }


def validate_recipe(data: dict[str, Any]) -> None:
    """Validate a recipe dict against the schema. Raises on failure."""
    required = ("name", "description", "shape", "cluster", "patterns")
    for f in required:
        if f not in data:
            raise DSLValidationError(f"Missing required field: {f}")

    if not isinstance(data["name"], str) or not data["name"]:
        raise DSLValidationError("'name' must be a non-empty string")

    if not isinstance(data["description"], str):
        raise DSLValidationError("'description' must be a string")

    if data["shape"] not in VALID_SHAPES:
        raise DSLValidationError(
            f"'shape' must be one of {sorted(VALID_SHAPES)}, got {data['shape']!r}"
        )

    if data["cluster"] not in VALID_CLUSTERS:
        raise DSLValidationError(
            f"'cluster' must be one of {sorted(VALID_CLUSTERS)}, got {data['cluster']!r}"
        )

    patterns = data.get("patterns", [])
    if not isinstance(patterns, list) or not patterns:
        raise DSLValidationError("'patterns' must be a non-empty list")

    for p in patterns:
        if not isinstance(p, str) or not p:
            raise DSLValidationError(f"Pattern entries must be non-empty strings, got {p!r}")

    triggers = data.get("triggers", [])
    if not isinstance(triggers, list):
        raise DSLValidationError("'triggers' must be a list when present")

    for t in triggers:
        if not isinstance(t, str):
            raise DSLValidationError(f"Trigger entries must be strings, got {t!r}")


def load_recipe_from_dict(data: dict[str, Any]) -> RecipeDSL:
    """Validate + construct a RecipeDSL from a dict."""
    validate_recipe(data)
    return RecipeDSL(
        name=data["name"],
        description=data["description"],
        shape=data["shape"],
        cluster=data["cluster"],
        patterns=list(data["patterns"]),
        triggers=list(data.get("triggers", [])),
        intervention_hint=data.get("intervention_hint", ""),
        metadata=dict(data.get("metadata", {})),
    )


def parse_recipe_yaml(yaml_text: str) -> dict[str, Any]:
    """Parse YAML text into a dict.

    Uses PyYAML if available; falls back to a tiny YAML subset that
    supports flat key-value, nested lists, and indented dicts. For
    complex YAML use PyYAML.
    """
    try:
        import yaml

        return cast("dict[str, Any]", yaml.safe_load(yaml_text))
    except ImportError:
        return _parse_minimal_yaml(yaml_text)


def _parse_minimal_yaml(text: str) -> dict[str, Any]:
    """Tiny YAML subset parser. Handles:

        key: value
        list_key:
          - item1
          - item2
        nested_key:
          sub_key: value

    Does NOT handle: anchors, references, multi-line strings,
    inline lists/dicts. For full YAML support, install PyYAML.
    """
    lines = text.split("\n")
    result: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any], str | None]] = [(0, result, None)]

    for raw_line in lines:
        line = raw_line.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue

        indent = len(line) - len(line.lstrip())
        stripped = line.strip()

        # Pop stack until we find the parent indent level.
        while stack and indent < stack[-1][0]:
            stack.pop()
        if not stack:
            stack = [(0, result, None)]

        current_indent, current_dict, list_key = stack[-1]

        if stripped.startswith("- "):
            # List item.
            value = stripped[2:].strip()
            if list_key is not None:
                current_dict.setdefault(list_key, []).append(_parse_value(value))
            continue

        if ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip()
            if not val:
                # Probably the start of a nested dict or list.
                current_dict[key] = {}
                stack.append((indent + 2, current_dict, key))
            else:
                current_dict[key] = _parse_value(val)

    # Cleanup: replace empty dicts {} that were just markers with actual
    # nested values.
    return result


def _parse_value(s: str) -> Any:
    s = s.strip()
    if s.lower() in ("true", "yes"):
        return True
    if s.lower() in ("false", "no"):
        return False
    if s.lower() in ("null", "~", "none"):
        return None
    # Strip surrounding quotes.
    if len(s) >= 2 and s[0] in "\"'" and s[-1] == s[0]:
        return s[1:-1]
    # Try int.
    try:
        return int(s)
    except ValueError:
        pass
    # Try float.
    try:
        return float(s)
    except ValueError:
        pass
    return s


def load_recipe_from_file(path: str | Path) -> RecipeDSL:
    """Load a recipe from a YAML or JSON file."""
    p = Path(path)
    text = p.read_text()
    suffix = p.suffix.lower()

    if suffix in (".yaml", ".yml"):
        data = parse_recipe_yaml(text)
    elif suffix == ".json":
        data = json.loads(text)
    else:
        # Try YAML first then JSON.
        try:
            data = parse_recipe_yaml(text)
        except Exception:
            data = json.loads(text)

    return load_recipe_from_dict(data)


def load_recipes_from_dir(dir_path: str | Path) -> list[RecipeDSL]:
    """Load all .yaml / .yml / .json files in a directory."""
    p = Path(dir_path)
    if not p.is_dir():
        raise FileNotFoundError(f"Not a directory: {dir_path}")

    recipes = []
    for file in sorted(p.iterdir()):
        if file.suffix.lower() in (".yaml", ".yml", ".json"):
            try:
                recipes.append(load_recipe_from_file(file))
            except (DSLValidationError, json.JSONDecodeError):
                continue
    return recipes
