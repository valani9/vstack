"""Findings router."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


_SEVERITY_RANK = {"none": 0, "low": 1, "medium": 2, "high": 3}


@dataclass
class OwnerRoute:
    """One routing rule for an owner / team."""

    owner: str
    match: dict[str, Any] = field(default_factory=dict)
    """Match criteria (same shape as vstack.policy.Rule.match).
    Empty dict = wildcard."""

    severity_floor: str = "low"
    """Minimum severity to route here. Findings below floor skip this route."""

    jira_project: str | None = None
    github_label: str | None = None
    pagerduty_service: str | None = None
    slack_channel: str | None = None

    name: str = ""

    def matches(self, finding: dict[str, Any]) -> bool:
        # Severity floor check.
        sev = finding.get("severity", "low")
        if _SEVERITY_RANK.get(sev, 0) < _SEVERITY_RANK.get(self.severity_floor, 0):
            return False

        # Field-based match (delegate to policy-style matcher).
        for key, expected in self.match.items():
            actual = finding.get(key)
            if isinstance(expected, list):
                if actual not in expected:
                    return False
            elif isinstance(expected, dict):
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
            "owner": self.owner,
            "match": dict(self.match),
            "severity_floor": self.severity_floor,
            "jira_project": self.jira_project,
            "github_label": self.github_label,
            "pagerduty_service": self.pagerduty_service,
            "slack_channel": self.slack_channel,
            "name": self.name,
        }


@dataclass
class Assignment:
    """A routed finding → owner with channel metadata."""

    finding: dict[str, Any]
    owner: str
    rule_name: str = ""
    route: OwnerRoute | None = None

    @property
    def jira_project(self) -> str | None:
        return self.route.jira_project if self.route else None

    @property
    def github_label(self) -> str | None:
        return self.route.github_label if self.route else None

    @property
    def pagerduty_service(self) -> str | None:
        return self.route.pagerduty_service if self.route else None

    @property
    def slack_channel(self) -> str | None:
        return self.route.slack_channel if self.route else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "owner": self.owner,
            "rule_name": self.rule_name,
            "finding": dict(self.finding),
            "channels": {
                "jira": self.jira_project,
                "github": self.github_label,
                "pagerduty": self.pagerduty_service,
                "slack": self.slack_channel,
            },
        }


@dataclass
class FindingsRouter:
    """Route findings to owners based on ordered routes."""

    routes: list[OwnerRoute] = field(default_factory=list)
    default_owner: str = "unrouted"

    def route(self, findings: list[Any]) -> list[Assignment]:
        assignments = []
        for finding in findings:
            finding_dict = _as_dict(finding)
            matched_route = None
            for r in self.routes:
                if r.matches(finding_dict):
                    matched_route = r
                    break
            if matched_route:
                assignments.append(
                    Assignment(
                        finding=finding_dict,
                        owner=matched_route.owner,
                        rule_name=matched_route.name or matched_route.owner,
                        route=matched_route,
                    )
                )
            else:
                assignments.append(
                    Assignment(
                        finding=finding_dict,
                        owner=self.default_owner,
                        rule_name="default",
                        route=None,
                    )
                )
        return assignments

    def group_by_owner(self, findings: list[Any]) -> dict[str, list[Assignment]]:
        grouped: dict[str, list[Assignment]] = {}
        for a in self.route(findings):
            grouped.setdefault(a.owner, []).append(a)
        return grouped

    def add_route(self, route: OwnerRoute) -> FindingsRouter:
        return FindingsRouter(
            routes=[*self.routes, route],
            default_owner=self.default_owner,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "default_owner": self.default_owner,
            "routes": [r.to_dict() for r in self.routes],
        }


def route_findings(
    findings: list[Any],
    routes: list[OwnerRoute],
    *,
    default_owner: str = "unrouted",
) -> list[Assignment]:
    """Convenience: build a router + route in one call."""
    router = FindingsRouter(routes=routes, default_owner=default_owner)
    return router.route(findings)


def _as_dict(finding: Any) -> dict[str, Any]:
    if isinstance(finding, dict):
        return dict(finding)
    return {
        "pattern": getattr(finding, "pattern", None),
        "severity": getattr(finding, "severity", None),
        "confidence": getattr(finding, "confidence", None),
        "title": getattr(finding, "title", None),
        "intervention": getattr(finding, "intervention", None),
    }
