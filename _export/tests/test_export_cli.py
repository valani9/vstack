"""Tests for the vstack-export CLI."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import pytest

from vstack.export._cli import main


def _f(
    pattern: str = "lewin",
    severity: str = "high",
    confidence: float = 0.8,
    title: str | None = None,
    intervention: str | None = None,
) -> dict[str, object]:
    return {
        "pattern": pattern,
        "severity": severity,
        "confidence": confidence,
        "title": title or f"{pattern} finding",
        "intervention": intervention or f"fix {pattern}",
    }


def _report(*findings: dict[str, object]) -> dict[str, object]:
    return {"findings": list(findings)}


def _write_json(tmp_path: Path, name: str, obj: object) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(obj), encoding="utf-8")
    return path


def test_markdown_to_stdout(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    report = _write_json(tmp_path, "r.json", _report(_f("lewin", "high", title="x")))
    rc = main(["--report", str(report), "--format", "markdown"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "# Findings" in out
    assert "lewin" in out
    assert "x" in out


def test_csv_to_stdout(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    report = _write_json(tmp_path, "r.json", _report(_f("lewin"), _f("aar", "medium")))
    rc = main(["--report", str(report), "--format", "csv"])
    out = capsys.readouterr().out
    assert rc == 0
    rows = list(csv.reader(io.StringIO(out)))
    assert rows[0][0] == "pattern"
    assert len(rows) == 3  # header + 2 findings


def test_json_to_stdout(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    report = _write_json(tmp_path, "r.json", _report(_f("lewin", "high")))
    rc = main(["--report", str(report), "--format", "json"])
    out = capsys.readouterr().out
    assert rc == 0
    data = json.loads(out)
    assert data[0]["pattern"] == "lewin"


def test_github_to_stdout(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    report = _write_json(tmp_path, "r.json", _report(_f("lewin", "high", title="my issue")))
    rc = main(["--report", str(report), "--format", "github"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "vstack diagnose" in out
    assert "my issue" in out


def test_jira_to_stdout(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    report = _write_json(tmp_path, "r.json", _report(_f("lewin", "high")))
    rc = main(["--report", str(report), "--format", "jira"])
    out = capsys.readouterr().out
    assert rc == 0
    adf = json.loads(out)
    assert adf["type"] == "doc"
    assert adf["version"] == 1


def test_bare_list_input(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    report = _write_json(tmp_path, "r.json", [_f("lewin")])
    rc = main(["--report", str(report), "--format", "csv"])
    out = capsys.readouterr().out
    assert rc == 0
    rows = list(csv.reader(io.StringIO(out)))
    assert len(rows) == 2  # header + 1 finding


def test_out_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    report = _write_json(tmp_path, "r.json", _report(_f("lewin", "high")))
    out_path = tmp_path / "out.md"
    rc = main(["--report", str(report), "--format", "markdown", "--out", str(out_path)])
    err = capsys.readouterr().err
    assert rc == 0
    assert out_path.is_file()
    assert "lewin" in out_path.read_text(encoding="utf-8")
    assert str(out_path) in err


def test_stdin_input(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(_report(_f("lewin")))))
    rc = main(["--format", "csv"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "lewin" in out


def test_missing_file_is_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["--report", "/nonexistent/path/report.json", "--format", "csv"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "not found" in err


def test_invalid_json_is_usage_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")
    rc = main(["--report", str(bad), "--format", "csv"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "invalid JSON" in err


def test_wrong_json_shape_is_usage_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report = _write_json(tmp_path, "r.json", {"nope": 1})
    rc = main(["--report", str(report), "--format", "csv"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "findings" in err


def test_scalar_json_is_usage_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    report = _write_json(tmp_path, "r.json", 42)
    rc = main(["--report", str(report), "--format", "csv"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "expected a JSON object or array" in err


def test_bad_format_exits_2(tmp_path: Path) -> None:
    report = _write_json(tmp_path, "r.json", _report(_f()))
    with pytest.raises(SystemExit) as excinfo:
        main(["--report", str(report), "--format", "xml"])
    assert excinfo.value.code == 2
