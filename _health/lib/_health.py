"""Composite health checks."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Protocol


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class CheckResult:
    """One check's result."""

    name: str
    status: HealthStatus
    duration_ms: int = 0
    detail: str = ""
    error: str | None = None
    critical: bool = True

    @property
    def passed(self) -> bool:
        return self.status == HealthStatus.HEALTHY

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "duration_ms": self.duration_ms,
            "detail": self.detail,
            "error": self.error,
            "critical": self.critical,
        }


class Check(Protocol):
    """A health check."""

    @property
    def name(self) -> str: ...

    @property
    def critical(self) -> bool: ...

    def run(self) -> CheckResult:  # pragma: no cover - protocol stub
        ...


@dataclass
class CallableCheck:
    """Wrap a callable as a Check.

    The callable should return a bool (healthy/unhealthy) or a
    CheckResult for finer-grained reporting.
    """

    name: str
    fn: Callable[[], Any]
    critical_: bool = True
    timeout_ms: int = 0  # 0 = no timeout

    @property
    def critical(self) -> bool:
        return self.critical_

    def run(self) -> CheckResult:
        start = time.time()
        try:
            ret = self.fn()
        except Exception as exc:
            return CheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                duration_ms=int((time.time() - start) * 1000),
                error=str(exc),
                critical=self.critical,
            )

        duration_ms = int((time.time() - start) * 1000)
        if self.timeout_ms and duration_ms > self.timeout_ms:
            return CheckResult(
                name=self.name,
                status=HealthStatus.DEGRADED,
                duration_ms=duration_ms,
                detail=f"exceeded timeout {self.timeout_ms}ms",
                critical=self.critical,
            )

        # Coerce result.
        if isinstance(ret, CheckResult):
            ret.duration_ms = duration_ms
            ret.name = self.name
            return ret
        if isinstance(ret, bool):
            status = HealthStatus.HEALTHY if ret else HealthStatus.UNHEALTHY
            return CheckResult(
                name=self.name,
                status=status,
                duration_ms=duration_ms,
                critical=self.critical,
            )

        # Other returns count as healthy with stringified detail.
        return CheckResult(
            name=self.name,
            status=HealthStatus.HEALTHY,
            duration_ms=duration_ms,
            detail=str(ret) if ret is not None else "",
            critical=self.critical,
        )


@dataclass
class HealthReport:
    """Aggregate report across all checks."""

    results: list[CheckResult] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    @property
    def status(self) -> HealthStatus:
        """Aggregate status:

        - Any critical UNHEALTHY → UNHEALTHY
        - Any non-critical UNHEALTHY → DEGRADED
        - Any DEGRADED → DEGRADED
        - Else → HEALTHY
        """
        has_critical_unhealthy = any(
            r.status == HealthStatus.UNHEALTHY and r.critical for r in self.results
        )
        if has_critical_unhealthy:
            return HealthStatus.UNHEALTHY

        has_degraded = any(r.status == HealthStatus.DEGRADED for r in self.results)
        has_noncritical_unhealthy = any(
            r.status == HealthStatus.UNHEALTHY and not r.critical for r in self.results
        )
        if has_degraded or has_noncritical_unhealthy:
            return HealthStatus.DEGRADED

        return HealthStatus.HEALTHY

    def healthy_count(self) -> int:
        return sum(1 for r in self.results if r.status == HealthStatus.HEALTHY)

    def unhealthy_count(self) -> int:
        return sum(1 for r in self.results if r.status == HealthStatus.UNHEALTHY)

    def failed_checks(self) -> list[CheckResult]:
        return [r for r in self.results if r.status != HealthStatus.HEALTHY]

    def summary(self) -> str:
        return f"{self.status.value}: {self.healthy_count()}/{len(self.results)} healthy"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "timestamp": self.timestamp,
            "summary": self.summary(),
            "healthy": self.healthy_count(),
            "unhealthy": self.unhealthy_count(),
            "total": len(self.results),
            "results": [r.to_dict() for r in self.results],
        }


def run_checks(checks: list[Check]) -> HealthReport:
    """Run all checks; return aggregate report."""
    results = []
    for check in checks:
        try:
            result = check.run()
        except Exception as exc:
            result = CheckResult(
                name=getattr(check, "name", "unknown"),
                status=HealthStatus.UNHEALTHY,
                error=str(exc),
                critical=getattr(check, "critical", True),
            )
        results.append(result)
    return HealthReport(results=results)


@dataclass
class HealthMonitor:
    """Periodic health monitor.

    Does not start its own thread; instead exposes a ``tick()``
    method that you can drive from a scheduler / cron / asyncio
    loop. Stores the latest report.
    """

    checks: list[Check] = field(default_factory=list)
    interval_seconds: float = 30.0
    _last_run_at: float = 0.0
    _last_report: HealthReport | None = None

    def tick(self, now: float | None = None) -> HealthReport | None:
        """Run checks if interval elapsed; return report if ran."""
        current = now if now is not None else time.time()
        if self._last_run_at and (current - self._last_run_at) < self.interval_seconds:
            return None
        report = run_checks(self.checks)
        self._last_run_at = current
        self._last_report = report
        return report

    def force_tick(self) -> HealthReport:
        """Run checks unconditionally."""
        report = run_checks(self.checks)
        self._last_run_at = time.time()
        self._last_report = report
        return report

    @property
    def last_report(self) -> HealthReport | None:
        return self._last_report

    def add_check(self, check: Check) -> HealthMonitor:
        return HealthMonitor(
            checks=[*self.checks, check],
            interval_seconds=self.interval_seconds,
        )
