"""Tests for the vstack-timeline CLI."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from vstack.timeline._cli import main


def _ts(year: int = 2026, month: int = 1, day: int = 1, hour: int = 0) -> float:
    return datetime(year, month, day, hour, tzinfo=timezone.utc).timestamp()


def _finding(severity: str, timestamp: float) -> dict[str, object]:
    return {"pattern": "test", "severity": severity, "timestamp": timestamp}


def _write_reports(path: Path, findings: list[dict[str, object]]) -> Path:
    path.write_text(json.dumps({"findings": findings}), encoding="utf-8")
    return path


class TestHappyPath:
    def test_markdown_to_stdout(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        reports = _write_reports(
            tmp_path / "reports.json",
            [
                _finding("high", _ts(2026, 1, 1, 14)),
                _finding("medium", _ts(2026, 1, 1, 15)),
            ],
        )

        code = main(["--reports", str(reports), "--format", "markdown"])

        assert code == 0
        out = capsys.readouterr().out
        assert "# Timeline (hour)" in out
        assert "Sparkline" in out
        assert "Period" in out

    def test_sparkline_to_stdout(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        reports = _write_reports(
            tmp_path / "reports.json",
            [_finding("high", _ts(2026, 1, 1, 14))],
        )

        code = main(["--reports", str(reports), "--format", "sparkline"])

        assert code == 0
        out = capsys.readouterr().out.strip()
        assert out != ""
        assert out != "(empty)"

    def test_bare_list_input(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        path = tmp_path / "findings.json"
        path.write_text(
            json.dumps([_finding("high", _ts(2026, 1, 1, 14))]),
            encoding="utf-8",
        )

        code = main(["--reports", str(path)])

        assert code == 0
        assert "# Timeline" in capsys.readouterr().out

    def test_bucket_day_and_out_file(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        reports = _write_reports(
            tmp_path / "reports.json",
            [
                _finding("high", _ts(2026, 1, 1, 9)),
                _finding("low", _ts(2026, 1, 1, 18)),
            ],
        )
        out_file = tmp_path / "timeline.md"

        code = main(
            [
                "--reports",
                str(reports),
                "--bucket",
                "day",
                "--out",
                str(out_file),
            ]
        )

        assert code == 0
        written = out_file.read_text(encoding="utf-8")
        assert "# Timeline (day)" in written
        # Output went to the file, not stdout.
        assert capsys.readouterr().out == ""


class TestErrorPaths:
    def test_missing_file_returns_2(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        missing = tmp_path / "does-not-exist.json"

        code = main(["--reports", str(missing)])

        assert code == 2
        err = capsys.readouterr().err
        assert "vstack-timeline: error:" in err
        assert "not found" in err

    def test_invalid_json_returns_2(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = tmp_path / "bad.json"
        path.write_text("{not valid json", encoding="utf-8")

        code = main(["--reports", str(path)])

        assert code == 2
        assert "invalid JSON" in capsys.readouterr().err

    def test_object_without_findings_key_returns_2(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = tmp_path / "obj.json"
        path.write_text(json.dumps({"unexpected": []}), encoding="utf-8")

        code = main(["--reports", str(path)])

        assert code == 2
        assert "no 'findings' or 'reports' key" in capsys.readouterr().err
