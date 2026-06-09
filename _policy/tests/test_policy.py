"""Tests for the policy module."""

from __future__ import annotations


from vstack.policy import (
    ActionAlert,
    ActionCustom,
    ActionEscalate,
    ActionIgnore,
    ActionLog,
    ActionPage,
    Decision,
    Policy,
    Rule,
    evaluate_policy,
)


def _f(pattern="lewin", severity="high", confidence=0.8, **extra):
    return {
        "pattern": pattern,
        "severity": severity,
        "confidence": confidence,
        "title": f"{pattern} finding",
        **extra,
    }


class TestActions:
    def test_action_log_default(self):
        a = ActionLog()
        assert a.kind == "log"
        assert a.level == "info"

    def test_action_alert(self):
        a = ActionAlert(channel="#alerts")
        assert a.kind == "alert"
        assert a.channel == "#alerts"

    def test_action_page(self):
        a = ActionPage(target="on-call")
        assert a.kind == "page"

    def test_action_escalate(self):
        a = ActionEscalate(tier="tier-2")
        assert a.kind == "escalate"

    def test_action_ignore(self):
        a = ActionIgnore()
        assert a.kind == "ignore"

    def test_action_custom_with_payload(self):
        a = ActionCustom(target="webhook", url="https://example.com")
        assert a.kind == "custom"
        assert a.payload["target"] == "webhook"

    def test_action_to_dict(self):
        a = ActionLog(level="warning")
        data = a.to_dict()
        assert data["kind"] == "log"
        assert data["level"] == "warning"


class TestRule:
    def test_empty_match_is_wildcard(self):
        rule = Rule()
        assert rule.matches(_f())

    def test_exact_severity_match(self):
        rule = Rule(match={"severity": "high"})
        assert rule.matches(_f(severity="high"))
        assert not rule.matches(_f(severity="low"))

    def test_pattern_match(self):
        rule = Rule(match={"pattern": "lewin"})
        assert rule.matches(_f(pattern="lewin"))
        assert not rule.matches(_f(pattern="aar"))

    def test_multiple_fields_all_required(self):
        rule = Rule(match={"severity": "high", "pattern": "lewin"})
        assert rule.matches(_f(severity="high", pattern="lewin"))
        assert not rule.matches(_f(severity="high", pattern="aar"))
        assert not rule.matches(_f(severity="low", pattern="lewin"))

    def test_list_match_any(self):
        rule = Rule(match={"severity": ["high", "medium"]})
        assert rule.matches(_f(severity="high"))
        assert rule.matches(_f(severity="medium"))
        assert not rule.matches(_f(severity="low"))

    def test_range_match_min(self):
        rule = Rule(match={"confidence": {"min": 0.7}})
        assert rule.matches(_f(confidence=0.9))
        assert not rule.matches(_f(confidence=0.5))

    def test_range_match_max(self):
        rule = Rule(match={"confidence": {"max": 0.5}})
        assert rule.matches(_f(confidence=0.3))
        assert not rule.matches(_f(confidence=0.7))

    def test_range_match_both(self):
        rule = Rule(match={"confidence": {"min": 0.5, "max": 0.8}})
        assert rule.matches(_f(confidence=0.6))
        assert not rule.matches(_f(confidence=0.4))
        assert not rule.matches(_f(confidence=0.9))

    def test_rule_to_dict(self):
        rule = Rule(
            name="critical",
            match={"severity": "high"},
            action=ActionPage(target="on-call"),
        )
        data = rule.to_dict()
        assert data["name"] == "critical"
        assert data["action"]["kind"] == "page"


class TestPolicy:
    def test_empty_policy_falls_back_to_default(self):
        policy = Policy()
        decisions = evaluate_policy(policy, [_f()])
        assert decisions[0].action.kind == "log"  # default
        assert decisions[0].rule_name == "default"

    def test_first_match_wins(self):
        policy = Policy(
            rules=[
                Rule(match={"severity": "high"}, action=ActionPage()),
                Rule(match={"severity": "high"}, action=ActionAlert()),
            ]
        )
        decisions = evaluate_policy(policy, [_f(severity="high")])
        # First rule wins.
        assert decisions[0].action.kind == "page"

    def test_no_match_uses_default(self):
        policy = Policy(
            rules=[Rule(match={"severity": "high"}, action=ActionPage())],
            default_action=ActionIgnore(),
        )
        decisions = evaluate_policy(policy, [_f(severity="low")])
        assert decisions[0].action.kind == "ignore"

    def test_complex_routing(self):
        policy = Policy(
            rules=[
                Rule(
                    name="page-critical-lewin",
                    match={"severity": "high", "pattern": "lewin"},
                    action=ActionPage(target="on-call"),
                ),
                Rule(
                    name="alert-high",
                    match={"severity": "high"},
                    action=ActionAlert(channel="#alerts"),
                ),
                Rule(
                    name="log-medium",
                    match={"severity": "medium"},
                    action=ActionLog(level="warning"),
                ),
            ],
            default_action=ActionLog(level="info"),
        )
        findings = [
            _f(pattern="lewin", severity="high"),  # → page
            _f(pattern="aar", severity="high"),  # → alert
            _f(pattern="grpi", severity="medium"),  # → warning log
            _f(pattern="trust_triangle", severity="low"),  # → default
        ]
        decisions = evaluate_policy(policy, findings)
        assert decisions[0].action.kind == "page"
        assert decisions[1].action.kind == "alert"
        assert decisions[2].action.kind == "log"
        assert decisions[2].action.level == "warning"
        assert decisions[3].action.kind == "log"
        assert decisions[3].rule_name == "default"

    def test_add_rule_immutable(self):
        p1 = Policy()
        p2 = p1.add_rule(Rule())
        assert len(p1.rules) == 0
        assert len(p2.rules) == 1


class TestDecisionFromAttributeAccess:
    def test_handles_object_finding(self):
        class FakeFinding:
            pattern = "lewin"
            severity = "high"
            confidence = 0.9
            title = "test"
            intervention = "fix"

        policy = Policy(rules=[Rule(match={"severity": "high"}, action=ActionAlert())])
        decisions = evaluate_policy(policy, [FakeFinding()])
        assert decisions[0].action.kind == "alert"


class TestSerialization:
    def test_policy_to_dict(self):
        policy = Policy(
            name="prod",
            rules=[
                Rule(name="r1", match={"severity": "high"}, action=ActionPage()),
            ],
        )
        data = policy.to_dict()
        assert data["name"] == "prod"
        assert len(data["rules"]) == 1
        assert data["rules"][0]["action"]["kind"] == "page"

    def test_decision_to_dict(self):
        decision = Decision(
            finding={"pattern": "lewin", "severity": "high"},
            action=ActionPage(target="on-call"),
            rule_name="critical",
            rule_index=0,
        )
        data = decision.to_dict()
        assert data["action"]["kind"] == "page"
        assert data["rule_name"] == "critical"
