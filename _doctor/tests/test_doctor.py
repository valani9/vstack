"""Tests for ``vstack.doctor``."""

from __future__ import annotations

import json

import pytest

import vstack.doctor as doctor
from vstack.doctor._doctor import (
    _CORE_CLIS_FALLBACK,
    HealthStatus,
    _check_api_security_posture,
    _check_cli_on_path,
    _check_home_dir,
    _check_pattern_registry,
    _check_python_version,
    _check_vstack_version,
    _discover_clis,
    run_all_checks,
)
from vstack.doctor.cli import main as cli_main


def test_python_version_ok() -> None:
    result = _check_python_version()
    assert result.status == HealthStatus.OK
    assert "Python" in result.summary


def test_vstack_version_ok() -> None:
    result = _check_vstack_version()
    assert result.status == HealthStatus.OK
    assert "valanistack" in result.summary


def test_pattern_registry_ok() -> None:
    result = _check_pattern_registry()
    assert result.status == HealthStatus.OK
    assert "34" in result.summary


def test_home_dir_writable(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("VSTACK_HOME", str(tmp_path))
    result = _check_home_dir()
    assert result.status == HealthStatus.OK


def test_cli_on_path_missing() -> None:
    result = _check_cli_on_path("definitely-not-a-real-cli-zzz")
    assert result.status == HealthStatus.ERROR


def test_discover_clis_enumerates_installed_scripts() -> None:
    # When valanistack is installed, discovery returns the real console
    # scripts — far more than the core fallback, and including modern CLIs
    # that the old hardcoded list missed.
    clis = _discover_clis()
    assert "vstack" in clis
    assert "vstack-doctor" in clis  # doctor itself was missing from the old list
    # workflow + module CLIs that the stale hardcoded list never checked
    for name in ("vstack-diagnose", "vstack-scorecard", "vstack-redaction", "vstack-lewin"):
        assert name in clis, f"{name} should be discovered"
    # the installed surface is much larger than the 10-entry fallback
    assert len(clis) > len(_CORE_CLIS_FALLBACK)


def test_discover_clis_falls_back_when_metadata_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # If distribution metadata can't be read, fall back to the core list
    # rather than checking nothing.
    import importlib.metadata as md

    def _boom(_name: str) -> object:
        raise md.PackageNotFoundError("valanistack")

    monkeypatch.setattr(md, "distribution", _boom)
    assert _discover_clis() == _CORE_CLIS_FALLBACK


def test_run_all_checks_validates_every_installed_cli() -> None:
    # The doctor must check every discovered CLI, not a stale subset.
    report = run_all_checks(skip_network=True)
    cli_checks = {c.name for c in report.checks if c.name.startswith("cli/")}
    expected = {f"cli/{name}" for name in _discover_clis()}
    assert cli_checks == expected


def test_api_security_warns_on_require_without_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VSTACK_API_REQUIRE_AUTH", "true")
    monkeypatch.delenv("VSTACK_API_KEYS", raising=False)
    monkeypatch.delenv("VSTACK_API_KEYS_FILE", raising=False)
    result = _check_api_security_posture()
    assert result.status == HealthStatus.ERROR


def test_api_security_ok_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VSTACK_API_REQUIRE_AUTH", raising=False)
    monkeypatch.delenv("VSTACK_API_KEYS", raising=False)
    monkeypatch.delenv("VSTACK_API_KEYS_FILE", raising=False)
    result = _check_api_security_posture()
    assert result.status == HealthStatus.OK


def test_run_all_checks_returns_report() -> None:
    report = run_all_checks(skip_network=True)
    assert report.checks
    # Every check has a name + status + summary.
    for c in report.checks:
        assert c.name
        assert isinstance(c.status, HealthStatus)
        assert c.summary


def test_run_all_checks_skip_network_excludes_pypi() -> None:
    report = run_all_checks(skip_network=True)
    names = {c.name for c in report.checks}
    assert "pypi_upgrade" not in names


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------


def test_cli_default_text_output(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    rc = cli_main(["--skip-network"])
    # rc is 0 when no ERROR-level findings; rc is 1 when there are.
    # Either is fine for this test; we just check the format.
    assert rc in (0, 1)
    out = capsys.readouterr().out
    assert "vstack_version" in out


def test_cli_json_output(capsys: pytest.CaptureFixture[str]) -> None:
    rc = cli_main(["--skip-network", "--json"])
    assert rc in (0, 1)
    body = json.loads(capsys.readouterr().out)
    assert "checks" in body
    assert "has_errors" in body
    assert "has_warnings" in body
    assert any(c["name"] == "vstack_version" for c in body["checks"])


def test_cli_only_errors(capsys: pytest.CaptureFixture[str]) -> None:
    rc = cli_main(["--skip-network", "--only-errors"])
    assert rc in (0, 1)
    # No assertion on stdout content -- some environments will have
    # zero errors and others (e.g. missing optional extras as the
    # default state) won't actually error -- just verify it doesn't
    # crash.


def test_module_exports() -> None:
    for name in ("CheckResult", "DoctorReport", "HealthStatus", "run_all_checks"):
        assert name in doctor.__all__
    assert doctor.__version__
