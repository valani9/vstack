"""Tests for the vstack-heatmap CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vstack.heatmap._cli import main


def _reports() -> list[dict[str, object]]:
    return [
        {"findings": [{"pattern": "lewin", "severity": "high", "title": "t"}]},
        {
            "findings": [
                {"pattern": "grpi", "severity": "medium", "title": "t"},
                {"pattern": "trust_triangle", "severity": "low", "title": "t"},
            ]
        },
    ]


def _write_reports(tmp_path: Path, payload: object) -> Path:
    path = tmp_path / "reports.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_ascii_dimension_to_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    reports_path = _write_reports(tmp_path, _reports())
    out_path = tmp_path / "grid.txt"

    code = main(
        [
            "--reports",
            str(reports_path),
            "--by",
            "dimension",
            "--format",
            "ascii",
            "--out",
            str(out_path),
        ]
    )

    assert code == 0
    rendered = out_path.read_text(encoding="utf-8")
    assert "Pattern × Dimension Heatmap" in rendered
    assert "lewin" in rendered
    assert "grpi" in rendered
    # Stderr reports the write; stdout stays empty.
    captured = capsys.readouterr()
    assert f"Wrote {out_path}" in captured.err
    assert captured.out == ""


def test_html_trace_to_stdout(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    reports_path = _write_reports(tmp_path, {"reports": _reports()})

    code = main(
        [
            "--reports",
            str(reports_path),
            "--by",
            "trace",
            "--format",
            "html",
            "--trace-names",
            "alpha,beta",
        ]
    )

    assert code == 0
    out = capsys.readouterr().out
    assert "<table" in out
    assert "alpha" in out
    assert "beta" in out
    assert "hsl(" in out


def test_missing_file_is_usage_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    missing = tmp_path / "nope.json"

    code = main(["--reports", str(missing)])

    assert code == 2
    err = capsys.readouterr().err
    assert "vstack-heatmap: error:" in err
    assert "not found" in err


def test_invalid_json_is_usage_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")

    code = main(["--reports", str(bad)])

    assert code == 2
    err = capsys.readouterr().err
    assert "invalid JSON" in err
