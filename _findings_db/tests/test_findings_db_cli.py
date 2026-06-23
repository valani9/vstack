"""Tests for the vstack-findings-db CLI."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from vstack.findings_db._cli import main


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


def test_add_then_list_roundtrip(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    db = tmp_path / "findings.db"
    report = _write_json(tmp_path, "r.json", _report(_f("lewin", "high"), _f("aar", "medium")))

    rc = main(["add", "--db", str(db), "--report", str(report), "--run-id", "run-1"])
    err = capsys.readouterr().err
    assert rc == 0
    assert "Stored 2 finding(s)" in err
    assert db.is_file()

    rc = main(["list", "--db", str(db)])
    out = capsys.readouterr().out
    assert rc == 0
    records = json.loads(out)
    assert len(records) == 2
    assert {r["pattern"] for r in records} == {"lewin", "aar"}
    assert all(r["run_id"] == "run-1" for r in records)


def test_add_creates_parent_directory(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    db = tmp_path / "nested" / "dir" / "findings.db"
    report = _write_json(tmp_path, "r.json", _report(_f()))
    rc = main(["add", "--db", str(db), "--report", str(report)])
    assert capsys.readouterr()  # drain
    assert rc == 0
    assert db.is_file()


def test_add_from_stdin(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db = tmp_path / "findings.db"
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(_report(_f("lewin")))))
    rc = main(["add", "--db", str(db)])
    err = capsys.readouterr().err
    assert rc == 0
    assert "Stored 1 finding(s)" in err


def test_add_bare_list_input(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    db = tmp_path / "findings.db"
    report = _write_json(tmp_path, "r.json", [_f("lewin"), _f("aar")])
    rc = main(["add", "--db", str(db), "--report", str(report)])
    err = capsys.readouterr().err
    assert rc == 0
    assert "Stored 2 finding(s)" in err


def test_list_filter_by_pattern(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    db = tmp_path / "findings.db"
    report = _write_json(tmp_path, "r.json", _report(_f("lewin"), _f("aar"), _f("grpi")))
    main(["add", "--db", str(db), "--report", str(report)])
    capsys.readouterr()

    rc = main(["list", "--db", str(db), "--pattern", "lewin", "--pattern", "aar"])
    out = capsys.readouterr().out
    assert rc == 0
    records = json.loads(out)
    assert {r["pattern"] for r in records} == {"lewin", "aar"}


def test_list_filter_by_severity_and_limit(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db = tmp_path / "findings.db"
    report = _write_json(
        tmp_path,
        "r.json",
        _report(_f("a", "high"), _f("b", "high"), _f("c", "low")),
    )
    main(["add", "--db", str(db), "--report", str(report)])
    capsys.readouterr()

    rc = main(["list", "--db", str(db), "--severity", "high", "--limit", "1"])
    out = capsys.readouterr().out
    assert rc == 0
    records = json.loads(out)
    assert len(records) == 1
    assert records[0]["severity"] == "high"


def test_stats_group_by_severity(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    db = tmp_path / "findings.db"
    report = _write_json(
        tmp_path,
        "r.json",
        _report(_f("a", "high"), _f("b", "high"), _f("c", "low")),
    )
    main(["add", "--db", str(db), "--report", str(report)])
    capsys.readouterr()

    rc = main(["stats", "--db", str(db), "--group-by", "severity"])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["group_by"] == "severity"
    assert payload["total"] == 3
    assert payload["counts"]["high"] == 2
    assert payload["counts"]["low"] == 1


def test_add_missing_file_is_usage_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db = tmp_path / "findings.db"
    rc = main(["add", "--db", str(db), "--report", "/nonexistent/report.json"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "not found" in err


def test_add_invalid_json_is_usage_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db = tmp_path / "findings.db"
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")
    rc = main(["add", "--db", str(db), "--report", str(bad)])
    err = capsys.readouterr().err
    assert rc == 2
    assert "invalid JSON" in err


def test_add_wrong_json_shape_is_usage_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db = tmp_path / "findings.db"
    report = _write_json(tmp_path, "r.json", {"nope": 1})
    rc = main(["add", "--db", str(db), "--report", str(report)])
    err = capsys.readouterr().err
    assert rc == 2
    assert "findings" in err


def test_list_missing_db_is_usage_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    db = tmp_path / "does_not_exist.db"
    rc = main(["list", "--db", str(db)])
    err = capsys.readouterr().err
    assert rc == 2
    assert "db file not found" in err


def test_no_subcommand_exits_2(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main([])
    assert excinfo.value.code == 2


def test_bad_group_by_exits_2(tmp_path: Path) -> None:
    db = tmp_path / "findings.db"
    with pytest.raises(SystemExit) as excinfo:
        main(["stats", "--db", str(db), "--group-by", "bogus"])
    assert excinfo.value.code == 2
