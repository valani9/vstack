"""Tests for the vstack-redaction CLI."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from vstack.redaction._cli import main


class TestTextMode:
    def test_scrub_text_arg(self, capsys: pytest.CaptureFixture[str]) -> None:
        rc = main(["--text", "Contact alice@example.com now"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "alice@example.com" not in captured.out
        assert "[EMAIL]" in captured.out
        # Counts go to stderr, not stdout.
        assert "email" in captured.err
        assert "total" in captured.err

    def test_scrub_text_stdin(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("sys.stdin", io.StringIO("ssn 123-45-6789 here"))
        rc = main(["--text", "-"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "123-45-6789" not in captured.out
        assert "[SSN]" in captured.out

    def test_default_mode_reads_stdin(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # No flags at all -> default to text mode reading stdin.
        monkeypatch.setattr("sys.stdin", io.StringIO("ip 192.168.1.1"))
        rc = main([])
        assert rc == 0
        captured = capsys.readouterr()
        assert "192.168.1.1" not in captured.out
        assert "[IPV4]" in captured.out

    def test_text_no_matches_reports_clean(self, capsys: pytest.CaptureFixture[str]) -> None:
        rc = main(["--text", "nothing sensitive here"])
        assert rc == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "nothing sensitive here"
        assert "no matches" in captured.err

    def test_text_out_file(self, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
        out = tmp_path / "scrubbed.txt"
        rc = main(["--text", "mail bob@x.com", "--out", str(out)])
        assert rc == 0
        written = out.read_text(encoding="utf-8")
        assert "[EMAIL]" in written
        assert "bob@x.com" not in written


class TestTraceMode:
    def _write_trace(self, tmp_path: Path) -> Path:
        # Same shape used by the library's own trace tests.
        trace = {
            "goal": "Find alice@example.com",
            "outcome": "Returned secret sk-abcdef123456789012345",
            "steps": [
                {"type": "message", "content": "Contact alice@example.com"},
                {"type": "tool_call", "content": "echo 'safe'"},
            ],
            "success": False,
        }
        path = tmp_path / "trace.json"
        path.write_text(json.dumps(trace), encoding="utf-8")
        return path

    def test_trace_to_stdout(self, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
        path = self._write_trace(tmp_path)
        rc = main(["--trace", str(path)])
        assert rc == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "alice@example.com" not in data["goal"]
        assert data["goal"] == "Find [EMAIL]"
        assert "sk-abcdef" not in data["outcome"]
        assert "alice@example.com" not in data["steps"][0]["content"]
        # Non-sensitive step content preserved.
        assert "safe" in data["steps"][1]["content"]
        # Counts reported to stderr.
        assert "email" in captured.err

    def test_trace_to_out_file(self, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
        path = self._write_trace(tmp_path)
        out = tmp_path / "scrubbed.json"
        rc = main(["--trace", str(path), "--out", str(out)])
        assert rc == 0
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "alice@example.com" not in data["goal"]
        assert data["success"] is False  # untouched fields survive
        captured = capsys.readouterr()
        assert str(out) in captured.err  # "Wrote scrubbed trace to ..."

    def test_trace_original_file_untouched(self, tmp_path: Path) -> None:
        path = self._write_trace(tmp_path)
        before = path.read_text(encoding="utf-8")
        out = tmp_path / "scrubbed.json"
        main(["--trace", str(path), "--out", str(out)])
        assert path.read_text(encoding="utf-8") == before


class TestListPatterns:
    def test_list_plain(self, capsys: pytest.CaptureFixture[str]) -> None:
        rc = main(["--list-patterns"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "email" in captured.out
        assert "[EMAIL]" in captured.out
        assert "pattern(s)" in captured.out

    def test_list_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        rc = main(["--list-patterns", "--json"])
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert isinstance(data, list)
        assert len(data) > 0
        for entry in data:
            assert "name" in entry
            assert "pattern" in entry
            assert "replacement" in entry


class TestErrorPaths:
    def test_missing_trace_file_exits_2(
        self, capsys: pytest.CaptureFixture[str], tmp_path: Path
    ) -> None:
        missing = tmp_path / "does_not_exist.json"
        rc = main(["--trace", str(missing)])
        assert rc == 2
        captured = capsys.readouterr()
        assert "error:" in captured.err
        assert "not found" in captured.err

    def test_invalid_json_exits_2(self, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("{not valid json", encoding="utf-8")
        rc = main(["--trace", str(bad)])
        assert rc == 2
        assert "invalid JSON" in capsys.readouterr().err

    def test_non_object_trace_exits_2(
        self, capsys: pytest.CaptureFixture[str], tmp_path: Path
    ) -> None:
        arr = tmp_path / "arr.json"
        arr.write_text("[1, 2, 3]", encoding="utf-8")
        rc = main(["--trace", str(arr)])
        assert rc == 2
        assert "JSON object" in capsys.readouterr().err

    def test_unwritable_out_dir_exits_2(
        self, capsys: pytest.CaptureFixture[str], tmp_path: Path
    ) -> None:
        # Parent path is a file, so writing under it must fail loudly.
        blocker = tmp_path / "afile"
        blocker.write_text("x", encoding="utf-8")
        out = blocker / "nested.txt"
        rc = main(["--text", "a@b.com", "--out", str(out)])
        assert rc == 2
        assert "error:" in capsys.readouterr().err

    def test_mutually_exclusive_flags(self, tmp_path: Path) -> None:
        path = tmp_path / "t.json"
        path.write_text("{}", encoding="utf-8")
        # argparse mutually-exclusive group -> SystemExit(2).
        with pytest.raises(SystemExit) as exc:
            main(["--trace", str(path), "--text", "x"])
        assert exc.value.code == 2
