"""Tests for the findings_router module."""

from __future__ import annotations


from vstack.findings_router import (
    Assignment,
    FindingsRouter,
    OwnerRoute,
    route_findings,
)


def _f(pattern="lewin", severity="high", confidence=0.8, title=None):
    return {
        "pattern": pattern,
        "severity": severity,
        "confidence": confidence,
        "title": title or f"{pattern} finding",
        "intervention": f"fix {pattern}",
    }


class TestOwnerRoute:
    def test_default_route_matches_all(self):
        route = OwnerRoute(owner="team")
        assert route.matches(_f())

    def test_pattern_match(self):
        route = OwnerRoute(owner="team", match={"pattern": "lewin"})
        assert route.matches(_f(pattern="lewin"))
        assert not route.matches(_f(pattern="aar"))

    def test_pattern_list_match(self):
        route = OwnerRoute(
            owner="team",
            match={"pattern": ["lewin", "aar"]},
        )
        assert route.matches(_f(pattern="lewin"))
        assert route.matches(_f(pattern="aar"))
        assert not route.matches(_f(pattern="grpi"))

    def test_severity_floor(self):
        route = OwnerRoute(owner="team", severity_floor="high")
        assert route.matches(_f(severity="high"))
        assert not route.matches(_f(severity="medium"))
        assert not route.matches(_f(severity="low"))

    def test_confidence_range_match(self):
        route = OwnerRoute(
            owner="team",
            match={"confidence": {"min": 0.8}},
        )
        assert route.matches(_f(confidence=0.9))
        assert not route.matches(_f(confidence=0.5))

    def test_combined_match(self):
        route = OwnerRoute(
            owner="team",
            match={"pattern": "lewin"},
            severity_floor="high",
        )
        assert route.matches(_f(pattern="lewin", severity="high"))
        assert not route.matches(_f(pattern="lewin", severity="low"))
        assert not route.matches(_f(pattern="aar", severity="high"))

    def test_to_dict(self):
        route = OwnerRoute(
            owner="team",
            match={"pattern": "lewin"},
            jira_project="PLAT",
            github_label="bug",
        )
        data = route.to_dict()
        assert data["owner"] == "team"
        assert data["jira_project"] == "PLAT"


class TestFindingsRouter:
    def test_default_router_routes_to_default(self):
        router = FindingsRouter(default_owner="catch-all")
        assignments = router.route([_f()])
        assert assignments[0].owner == "catch-all"
        assert assignments[0].rule_name == "default"

    def test_first_match_wins(self):
        router = FindingsRouter(
            routes=[
                OwnerRoute(owner="a", match={"pattern": "lewin"}),
                OwnerRoute(owner="b", match={"pattern": "lewin"}),
            ]
        )
        assignments = router.route([_f(pattern="lewin")])
        assert assignments[0].owner == "a"

    def test_routes_each_finding(self):
        router = FindingsRouter(
            routes=[
                OwnerRoute(owner="lewin-team", match={"pattern": "lewin"}),
                OwnerRoute(owner="aar-team", match={"pattern": "aar"}),
            ]
        )
        assignments = router.route(
            [
                _f(pattern="lewin"),
                _f(pattern="aar"),
                _f(pattern="other"),
            ]
        )
        assert assignments[0].owner == "lewin-team"
        assert assignments[1].owner == "aar-team"
        assert assignments[2].owner == "unrouted"

    def test_severity_floor_skips_low(self):
        router = FindingsRouter(
            routes=[
                OwnerRoute(
                    owner="critical-team",
                    match={"pattern": "lewin"},
                    severity_floor="high",
                ),
                OwnerRoute(
                    owner="any-team",
                    match={"pattern": "lewin"},
                ),
            ]
        )
        # Low severity finding skips critical-team and falls to any-team.
        a1 = router.route([_f(pattern="lewin", severity="low")])
        assert a1[0].owner == "any-team"

        # High severity finding matches critical-team.
        a2 = router.route([_f(pattern="lewin", severity="high")])
        assert a2[0].owner == "critical-team"

    def test_channels_propagated(self):
        router = FindingsRouter(
            routes=[
                OwnerRoute(
                    owner="team",
                    match={"pattern": "lewin"},
                    jira_project="PLAT",
                    github_label="bug",
                    slack_channel="#alerts",
                ),
            ]
        )
        assignments = router.route([_f(pattern="lewin")])
        assert assignments[0].jira_project == "PLAT"
        assert assignments[0].github_label == "bug"
        assert assignments[0].slack_channel == "#alerts"

    def test_group_by_owner(self):
        router = FindingsRouter(
            routes=[
                OwnerRoute(owner="lewin-team", match={"pattern": "lewin"}),
                OwnerRoute(owner="aar-team", match={"pattern": "aar"}),
            ]
        )
        grouped = router.group_by_owner(
            [
                _f(pattern="lewin"),
                _f(pattern="lewin"),
                _f(pattern="aar"),
                _f(pattern="other"),
            ]
        )
        assert len(grouped["lewin-team"]) == 2
        assert len(grouped["aar-team"]) == 1
        assert len(grouped["unrouted"]) == 1

    def test_add_route_immutable(self):
        r1 = FindingsRouter()
        r2 = r1.add_route(OwnerRoute(owner="team"))
        assert len(r1.routes) == 0
        assert len(r2.routes) == 1

    def test_to_dict(self):
        router = FindingsRouter(routes=[OwnerRoute(owner="team", match={"pattern": "lewin"})])
        data = router.to_dict()
        assert data["default_owner"] == "unrouted"
        assert len(data["routes"]) == 1


class TestRouteFindings:
    def test_convenience_function(self):
        assignments = route_findings(
            [_f(pattern="lewin")],
            [OwnerRoute(owner="team", match={"pattern": "lewin"})],
        )
        assert assignments[0].owner == "team"


class TestObjectFindings:
    def test_handles_attribute_finding(self):
        class FakeFinding:
            pattern = "lewin"
            severity = "high"
            confidence = 0.9
            title = "test"
            intervention = "fix"

        router = FindingsRouter(routes=[OwnerRoute(owner="team", match={"pattern": "lewin"})])
        assignments = router.route([FakeFinding()])
        assert assignments[0].owner == "team"


class TestAssignmentSerialization:
    def test_to_dict(self):
        route = OwnerRoute(owner="team", jira_project="PLAT")
        finding = _f()
        a = Assignment(finding=finding, owner="team", rule_name="r1", route=route)
        data = a.to_dict()
        assert data["owner"] == "team"
        assert data["channels"]["jira"] == "PLAT"
