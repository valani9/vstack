"""Tests for the vstack-vdiff CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from vstack.vdiff._cli import main


def _f(
    pattern: str,
    severity: str,
    title: str = "",
    intervention: str = "",
) -> dict[str, Any]:
    return {
        "pattern": pattern,
        "severity": severity,
        "title": title or f"{pattern}-{severity}-title",
        "intervention": intervention or f"fix {pattern}",
    }


def _report(
    findings: list[dict[str, Any]] | None = None,
    per_pattern: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "findings": findings if findings is not None else [],
        "per_pattern": per_pattern if per_pattern is not None else {},
    }


def _write(path: Path, report: dict[str, Any]) -> str:
    path.write_text(json.dumps(report), encoding="utf-8")
    return str(path)


def test_happy_path_markdown(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    before = _write(tmp_path / "before.json", _report([_f("lewin", "medium", title="loop")]))
    after = _write(tmp_path / "after.json", _report([_f("lewin", "high", title="loop")]))

    rc = main(["--before", before, "--after", after])

    assert rc == 0
    out = capsys.readouterr().out
    assert "# Report Delta" in out
    assert "Severity Changed" in out
    assert "medium → high" in out


def test_happy_path_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    before = _write(tmp_path / "before.json", _report([_f("lewin", "high")]))
    after = _write(tmp_path / "after.json", _report([_f("aar", "medium")]))

    rc = main(["--before", before, "--after", after, "--json"])

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["before_count"] == 1
    assert payload["after_count"] == 1
    assert len(payload["added"]) == 1
    assert payload["added"][0]["pattern"] == "aar"
    assert len(payload["removed"]) == 1
    assert payload["removed"][0]["pattern"] == "lewin"


def test_stdin_after(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    before = _write(tmp_path / "before.json", _report([]))
    monkeypatch.setattr(
        "sys.stdin",
        _StringIO(json.dumps(_report([_f("lewin", "low")]))),
    )

    rc = main(["--before", before, "--after", "-", "--json"])

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload["added"]) == 1


def test_both_stdin_is_usage_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["--before", "-", "--after", "-"])

    assert rc == 2
    err = capsys.readouterr().err
    assert "only one of --before/--after may read from stdin" in err


def test_missing_file_is_usage_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    before = _write(tmp_path / "before.json", _report([]))
    missing = str(tmp_path / "does_not_exist.json")

    rc = main(["--before", before, "--after", missing])

    assert rc == 2
    err = capsys.readouterr().err
    assert "vstack-vdiff: error:" in err
    assert "not found" in err


def test_invalid_json_is_usage_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")
    after = _write(tmp_path / "after.json", _report([]))

    rc = main(["--before", str(bad), "--after", after])

    assert rc == 2
    err = capsys.readouterr().err
    assert "invalid JSON" in err


def test_non_object_report_is_usage_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    arr = tmp_path / "arr.json"
    arr.write_text("[1, 2, 3]", encoding="utf-8")
    after = _write(tmp_path / "after.json", _report([]))

    rc = main(["--before", str(arr), "--after", after])

    assert rc == 2
    err = capsys.readouterr().err
    assert "expected a JSON object" in err


class _StringIO:
    """Minimal stdin stand-in exposing only ``read()``."""

    def __init__(self, data: str) -> None:
        self._data = data

    def read(self) -> str:
        return self._data
