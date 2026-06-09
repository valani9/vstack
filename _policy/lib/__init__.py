"""vstack.policy — declarative finding-action policies.

A policy is a list of rules that match findings on properties
(pattern / severity / confidence) and route them to actions
(log / alert / page / escalate / ignore / custom).

Quick start
-----------

    from vstack.policy import (
        Policy,
        Rule,
        ActionLog,
        ActionPage,
        ActionAlert,
        evaluate_policy,
    )

    policy = Policy(rules=[
        Rule(
            match={"severity": "high", "pattern": "lewin"},
            action=ActionPage(target="on-call"),
        ),
        Rule(
            match={"severity": "high"},
            action=ActionAlert(channel="#alerts"),
        ),
        Rule(
            match={"severity": "medium"},
            action=ActionLog(level="warning"),
        ),
        Rule(
            match={},
            action=ActionLog(level="info"),
        ),
    ])

    decisions = evaluate_policy(policy, findings)
    for d in decisions:
        print(d.finding["title"], "→", d.action.kind)
"""

from __future__ import annotations

from ._policy import (
    Action,
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

__all__ = [
    "Action",
    "ActionAlert",
    "ActionCustom",
    "ActionEscalate",
    "ActionIgnore",
    "ActionLog",
    "ActionPage",
    "Decision",
    "Policy",
    "Rule",
    "evaluate_policy",
]
