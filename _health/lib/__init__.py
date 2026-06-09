"""vstack.health — composite health checks for vstack services.

The health module ships composable health-check primitives suitable
for `/healthz` / `/readyz` HTTP endpoints, CLI doctors, or dashboards:

  - ``Check`` protocol: anything that returns a ``CheckResult``.
  - Built-ins: ``LLMReachableCheck``, ``DatabaseCheck``,
    ``DiskSpaceCheck``, ``CallableCheck``.
  - ``HealthReport`` aggregates checks into HEALTHY / DEGRADED /
    UNHEALTHY with per-check breakdown.
  - ``HealthMonitor`` runs checks at intervals.

Quick start
-----------

    from vstack.health import (
        Check,
        CheckResult,
        HealthReport,
        run_checks,
        CallableCheck,
    )

    def db_ok() -> bool:
        return True

    checks = [
        CallableCheck(name="db", fn=db_ok),
        CallableCheck(name="cache", fn=lambda: True),
    ]
    report = run_checks(checks)
    print(report.status, report.summary())
"""

from __future__ import annotations

from ._health import (
    CallableCheck,
    Check,
    CheckResult,
    HealthMonitor,
    HealthReport,
    HealthStatus,
    run_checks,
)

__all__ = [
    "CallableCheck",
    "Check",
    "CheckResult",
    "HealthMonitor",
    "HealthReport",
    "HealthStatus",
    "run_checks",
]
