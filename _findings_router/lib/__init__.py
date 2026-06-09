"""vstack.findings_router — smart routing of findings to teams / owners.

The findings_router module maps findings onto an owner team based on
configurable routing rules. Useful for:

  - **Triage workflows** — auto-assign findings to the team that owns
    the relevant subsystem.
  - **Issue tracker integration** — route to the right Jira project /
    GitHub label / PagerDuty service.
  - **On-call dispatch** — route high-severity findings to on-call
    rotation based on pattern domain.

Quick start
-----------

    from vstack.findings_router import (
        FindingsRouter,
        OwnerRoute,
        route_findings,
    )

    router = FindingsRouter(routes=[
        OwnerRoute(
            owner="platform-team",
            match={"pattern": ["lewin", "yerkes_dodson", "motivation_traps"]},
            jira_project="PLAT",
            severity_floor="medium",
        ),
        OwnerRoute(
            owner="trust-team",
            match={"pattern": ["trust_triangle", "mcallister_trust"]},
            github_label="trust-regression",
        ),
        # Default catch-all:
        OwnerRoute(owner="triage", match={}),
    ])

    assignments = router.route(findings)
    for a in assignments:
        print(a.owner, "←", a.finding["title"])
"""

from __future__ import annotations

from ._router import (
    Assignment,
    FindingsRouter,
    OwnerRoute,
    route_findings,
)

__all__ = [
    "Assignment",
    "FindingsRouter",
    "OwnerRoute",
    "route_findings",
]
