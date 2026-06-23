"""Tests for the vstack-aggregate CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from vstack.aggregate._cli import main


def _r(findings: list[dict[str, Any]], agent_id: str = "bot-1") -> dict[str, Any]:
    return {"findings": findings, "agent_id": agent_id}


def _f(pattern: str = "lewin", severity: str = "high") -> dict[str, Any]:
    return {"pattern": pattern, "severity": severity, "title": "x"}


def _sample_reports() -> list[dict[str, Any]]:
    return [
        _r([_f("lewin", "high"), _f("aar", "medium")], agent_id="noisy"),
        _r([_f("lewin", "low"), _f("lewin", "high")], agent_id="noisy"),
        _r([_f("aar", "low")], agent_id="quiet"),
    ]


def _write_reports(tmp_path: Path, reports: list[dict[str, Any]]) -> str:
    path = tmp_path / "reports.json"
    path.write_text(json.dumps(reports), encoding="utf-8")
    return str(path)


def test_happy_path_text(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = _write_reports(tmp_path, _sample_reports())
    rc = main(["--reports", path])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Aggregate report summary" in out
    assert "Total findings:  5" in out
    # lewin is the most frequent pattern (3 occurrences).
    assert "lewin" in out
    assert "noisy" in out


def test_happy_path_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = _write_reports(tmp_path, _sample_reports())
    rc = main(["--reports", path, "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["total_reports"] == 3
    assert payload["total_findings"] == 5
    assert payload["unique_patterns"] == 2
    assert payload["top_patterns"][0] == {"pattern": "lewin", "count": 3}
    assert payload["top_agents"][0] == {"agent_id": "noisy", "count": 4}
    assert payload["severity_distribution"] == {"high": 2, "medium": 1, "low": 2}


def test_reports_key_object(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "wrapped.json"
    path.write_text(json.dumps({"reports": _sample_reports()}), encoding="utf-8")
    rc = main(["--reports", str(path), "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["total_reports"] == 3


def test_top_limit_respected(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = _write_reports(tmp_path, _sample_reports())
    rc = main(["--reports", path, "--json", "--top", "1"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload["top_patterns"]) == 1
    assert len(payload["top_agents"]) == 1


def test_stdin_input(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(_sample_reports())))
    rc = main(["--reports", "-", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["total_findings"] == 5


def test_out_file(tmp_path: Path) -> None:
    path = _write_reports(tmp_path, _sample_reports())
    out = tmp_path / "summary.json"
    rc = main(["--reports", path, "--json", "--out", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["total_findings"] == 5


def test_empty_reports(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = _write_reports(tmp_path, [])
    rc = main(["--reports", path, "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["total_reports"] == 0
    assert payload["total_findings"] == 0


def test_missing_file(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["--reports", "/no/such/file/reports.json"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "input file not found" in err


def test_invalid_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{not valid json", encoding="utf-8")
    rc = main(["--reports", str(path)])
    assert rc == 2
    assert "invalid JSON" in capsys.readouterr().err


def test_wrong_top_level_shape(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "shape.json"
    path.write_text(json.dumps({"not_reports": []}), encoding="utf-8")
    rc = main(["--reports", str(path)])
    assert rc == 2
    assert "expected a JSON array" in capsys.readouterr().err


def test_non_positive_top(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = _write_reports(tmp_path, _sample_reports())
    rc = main(["--reports", path, "--top", "0"])
    assert rc == 2
    assert "--top must be a positive integer" in capsys.readouterr().err
