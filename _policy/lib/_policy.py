"""Policy primitives + evaluation engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Action:
    """Base class for actions. Subclass for specific kinds."""

    kind: str

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, **{k: v for k, v in self.__dict__.items() if k != "kind"}}


@dataclass
class ActionLog(Action):
    """Log the finding."""

    level: str = "info"

    def __init__(self, level: str = "info"):
        super().__init__(kind="log")
        self.level = level


@dataclass
class ActionAlert(Action):
    """Alert via a channel (e.g., Slack)."""

    channel: str = ""

    def __init__(self, channel: str = ""):
        super().__init__(kind="alert")
        self.channel = channel


@dataclass
class ActionPage(Action):
    """Page on-call."""

    target: str = ""

    def __init__(self, target: str = ""):
        super().__init__(kind="page")
        self.target = target


@dataclass
class ActionEscalate(Action):
    """Escalate to a higher tier."""

    tier: str = ""

    def __init__(self, tier: str = ""):
        super().__init__(kind="escalate")
        self.tier = tier


@dataclass
class ActionIgnore(Action):
    """Explicitly ignore the finding."""

    def __init__(self):
        super().__init__(kind="ignore")


@dataclass
class ActionCustom(Action):
    """Custom action with arbitrary payload."""

    payload: dict[str, Any] = field(default_factory=dict)

    def __init__(self, **payload):
        super().__init__(kind="custom")
        self.payload = payload


@dataclass
class Rule:
    """A policy rule: match + action."""

    match: dict[str, Any] = field(default_factory=dict)
    """Match criteria. Matches finding fields via equality. Empty
    match = wildcard."""

    action: Action = field(default_factory=lambda: ActionLog())

    name: str = ""

    def matches(self, finding: dict[str, Any]) -> bool:
        """True if the finding satisfies all match criteria."""
        for key, expected in self.match.items():
            actual = finding.get(key)
            if isinstance(expected, list):
                if actual not in expected:
                    return False
            elif isinstance(expected, dict):
                # Range-style match: {"min": 0.7, "max": 1.0}.
                if "min" in expected and (actual is None or actual < expected["min"]):
                    return False
                if "max" in expected and (actual is None or actual > expected["max"]):
                    return False
            else:
                if actual != expected:
                    return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "match": dict(self.match),
            "action": self.action.to_dict(),
        }


@dataclass
class Policy:
    """A list of rules evaluated in order; first match wins."""

    rules: list[Rule] = field(default_factory=list)
    name: str = ""
    default_action: Action = field(default_factory=lambda: ActionLog())

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "rules": [r.to_dict() for r in self.rules],
            "default_action": self.default_action.to_dict(),
        }

    def add_rule(self, rule: Rule) -> Policy:
        return Policy(
            rules=[*self.rules, rule],
            name=self.name,
            default_action=self.default_action,
        )


@dataclass
class Decision:
    """The result of evaluating a finding against a policy."""

    finding: dict[str, Any]
    action: Action
    rule_name: str = ""
    rule_index: int = -1

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding": dict(self.finding),
            "action": self.action.to_dict(),
            "rule_name": self.rule_name,
            "rule_index": self.rule_index,
        }


def evaluate_policy(policy: Policy, findings: list[Any]) -> list[Decision]:
    """Evaluate each finding against the policy; return ordered Decisions.

    Each finding is matched against rules in order; the first
    matching rule's action wins. If no rule matches, the default
    action applies.
    """
    decisions = []
    for finding in findings:
        finding_dict = _as_dict(finding)
        matched = False
        for i, rule in enumerate(policy.rules):
            if rule.matches(finding_dict):
                decisions.append(
                    Decision(
                        finding=finding_dict,
                        action=rule.action,
                        rule_name=rule.name or f"rule-{i}",
                        rule_index=i,
                    )
                )
                matched = True
                break
        if not matched:
            decisions.append(
                Decision(
                    finding=finding_dict,
                    action=policy.default_action,
                    rule_name="default",
                    rule_index=-1,
                )
            )
    return decisions


def _as_dict(finding: Any) -> dict[str, Any]:
    if isinstance(finding, dict):
        return dict(finding)
    # Try attribute access.
    return {
        "pattern": getattr(finding, "pattern", None),
        "severity": getattr(finding, "severity", None),
        "confidence": getattr(finding, "confidence", None),
        "title": getattr(finding, "title", None),
        "intervention": getattr(finding, "intervention", None),
    }
