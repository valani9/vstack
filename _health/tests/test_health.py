"""Tests for the health module."""

from __future__ import annotations


from vstack.health import (
    CallableCheck,
    CheckResult,
    HealthMonitor,
    HealthReport,
    HealthStatus,
    run_checks,
)


class TestCheckResult:
    def test_passed_property(self):
        ok = CheckResult(name="a", status=HealthStatus.HEALTHY)
        assert ok.passed
        bad = CheckResult(name="b", status=HealthStatus.UNHEALTHY)
        assert not bad.passed

    def test_to_dict(self):
        r = CheckResult(name="a", status=HealthStatus.HEALTHY, duration_ms=100)
        data = r.to_dict()
        assert data["status"] == "healthy"
        assert data["duration_ms"] == 100


class TestCallableCheck:
    def test_bool_true_healthy(self):
        c = CallableCheck(name="x", fn=lambda: True)
        result = c.run()
        assert result.status == HealthStatus.HEALTHY

    def test_bool_false_unhealthy(self):
        c = CallableCheck(name="x", fn=lambda: False)
        result = c.run()
        assert result.status == HealthStatus.UNHEALTHY

    def test_exception_unhealthy(self):
        def boom():
            raise ValueError("oops")

        c = CallableCheck(name="x", fn=boom)
        result = c.run()
        assert result.status == HealthStatus.UNHEALTHY
        assert "oops" in result.error

    def test_returning_check_result(self):
        ret = CheckResult(name="x", status=HealthStatus.DEGRADED, detail="slow")
        c = CallableCheck(name="x", fn=lambda: ret)
        result = c.run()
        assert result.status == HealthStatus.DEGRADED
        assert result.detail == "slow"

    def test_critical_propagated(self):
        c = CallableCheck(name="x", fn=lambda: True, critical_=False)
        result = c.run()
        assert result.critical is False

    def test_duration_recorded(self):
        c = CallableCheck(name="x", fn=lambda: True)
        result = c.run()
        assert result.duration_ms >= 0


class TestHealthReport:
    def test_all_healthy(self):
        results = [
            CheckResult(name="a", status=HealthStatus.HEALTHY),
            CheckResult(name="b", status=HealthStatus.HEALTHY),
        ]
        report = HealthReport(results=results)
        assert report.status == HealthStatus.HEALTHY
        assert report.healthy_count() == 2

    def test_critical_unhealthy_makes_unhealthy(self):
        results = [
            CheckResult(name="a", status=HealthStatus.HEALTHY),
            CheckResult(name="b", status=HealthStatus.UNHEALTHY, critical=True),
        ]
        report = HealthReport(results=results)
        assert report.status == HealthStatus.UNHEALTHY

    def test_noncritical_unhealthy_makes_degraded(self):
        results = [
            CheckResult(name="a", status=HealthStatus.HEALTHY),
            CheckResult(name="b", status=HealthStatus.UNHEALTHY, critical=False),
        ]
        report = HealthReport(results=results)
        assert report.status == HealthStatus.DEGRADED

    def test_degraded_makes_degraded(self):
        results = [
            CheckResult(name="a", status=HealthStatus.HEALTHY),
            CheckResult(name="b", status=HealthStatus.DEGRADED),
        ]
        report = HealthReport(results=results)
        assert report.status == HealthStatus.DEGRADED

    def test_failed_checks_filter(self):
        results = [
            CheckResult(name="a", status=HealthStatus.HEALTHY),
            CheckResult(name="b", status=HealthStatus.UNHEALTHY),
            CheckResult(name="c", status=HealthStatus.DEGRADED),
        ]
        report = HealthReport(results=results)
        failed = report.failed_checks()
        assert len(failed) == 2

    def test_summary_string(self):
        results = [
            CheckResult(name="a", status=HealthStatus.HEALTHY),
            CheckResult(name="b", status=HealthStatus.UNHEALTHY),
        ]
        report = HealthReport(results=results)
        summary = report.summary()
        assert "unhealthy" in summary
        assert "1/2 healthy" in summary

    def test_to_dict(self):
        report = HealthReport(results=[CheckResult(name="a", status=HealthStatus.HEALTHY)])
        data = report.to_dict()
        assert data["status"] == "healthy"
        assert data["total"] == 1


class TestRunChecks:
    def test_runs_each_check(self):
        checks = [
            CallableCheck(name="a", fn=lambda: True),
            CallableCheck(name="b", fn=lambda: True),
        ]
        report = run_checks(checks)
        assert len(report.results) == 2

    def test_mixed_status(self):
        checks = [
            CallableCheck(name="a", fn=lambda: True),
            CallableCheck(name="b", fn=lambda: False),
        ]
        report = run_checks(checks)
        assert report.status == HealthStatus.UNHEALTHY


class TestHealthMonitor:
    def test_first_tick_runs(self):
        monitor = HealthMonitor(checks=[CallableCheck(name="a", fn=lambda: True)])
        report = monitor.tick(now=100.0)
        assert report is not None
        assert monitor.last_report is report

    def test_second_tick_within_interval_skipped(self):
        monitor = HealthMonitor(
            checks=[CallableCheck(name="a", fn=lambda: True)],
            interval_seconds=30.0,
        )
        monitor.tick(now=100.0)
        # 10 seconds later — should NOT re-run.
        report2 = monitor.tick(now=110.0)
        assert report2 is None

    def test_tick_after_interval(self):
        monitor = HealthMonitor(
            checks=[CallableCheck(name="a", fn=lambda: True)],
            interval_seconds=30.0,
        )
        monitor.tick(now=100.0)
        report2 = monitor.tick(now=200.0)
        assert report2 is not None

    def test_force_tick_always_runs(self):
        monitor = HealthMonitor(
            checks=[CallableCheck(name="a", fn=lambda: True)],
            interval_seconds=999999.0,
        )
        monitor.tick(now=100.0)
        report2 = monitor.force_tick()
        assert report2 is not None

    def test_add_check_immutable(self):
        m1 = HealthMonitor()
        m2 = m1.add_check(CallableCheck(name="a", fn=lambda: True))
        assert len(m1.checks) == 0
        assert len(m2.checks) == 1


class TestTimeoutHandling:
    def test_within_timeout_healthy(self):
        c = CallableCheck(
            name="fast",
            fn=lambda: True,
            timeout_ms=1000,
        )
        result = c.run()
        assert result.status == HealthStatus.HEALTHY

    def test_no_timeout_means_no_check(self):
        # timeout_ms=0 → no timeout enforcement.
        c = CallableCheck(name="x", fn=lambda: True, timeout_ms=0)
        result = c.run()
        assert result.status == HealthStatus.HEALTHY
