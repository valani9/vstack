"""Tests for the vstack-trace-diff CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from vstack.trace_diff._cli import main


def _step(type_: str = "thought", content: str = "x") -> dict[str, Any]:
    return {"type": type_, "content": content}


def _trace(
    steps: list[dict[str, Any]] | None = None,
    goal: str = "goal",
    outcome: str = "outcome",
    success: bool = True,
) -> dict[str, Any]:
    return {
        "goal": goal,
        "steps": steps if steps is not None else [],
        "outcome": outcome,
        "success": success,
    }


def _write(path: Path, trace: dict[str, Any]) -> str:
    path.write_text(json.dumps(trace), encoding="utf-8")
    return str(path)


def test_happy_path_markdown(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    before = _write(
        tmp_path / "before.json",
        _trace(steps=[_step("thought", "a")], success=True),
    )
    after = _write(
        tmp_path / "after.json",
        _trace(steps=[_step("observation", "a")], success=False),
    )

    rc = main(["--before", before, "--after", after])

    assert rc == 0
    out = capsys.readouterr().out
    assert "# Trace Delta" in out
    assert "REGRESSION" in out


def test_happy_path_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    before = _write(tmp_path / "before.json", _trace(steps=[_step()]))
    after = _write(tmp_path / "after.json", _trace(steps=[_step(), _step()]))

    rc = main(["--before", before, "--after", after, "--json"])

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["step_count_before"] == 1
    assert payload["step_count_after"] == 2
    assert payload["added"] == 1


def test_missing_file_is_usage_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    before = _write(tmp_path / "before.json", _trace())
    missing = str(tmp_path / "does_not_exist.json")

    rc = main(["--before", before, "--after", missing])

    assert rc == 2
    err = capsys.readouterr().err
    assert "vstack-trace-diff: error:" in err
    assert "not found" in err


def test_invalid_json_is_usage_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")
    after = _write(tmp_path / "after.json", _trace())

    rc = main(["--before", str(bad), "--after", after])

    assert rc == 2
    err = capsys.readouterr().err
    assert "invalid JSON" in err


def test_non_object_trace_is_usage_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    arr = tmp_path / "arr.json"
    arr.write_text("[1, 2, 3]", encoding="utf-8")
    after = _write(tmp_path / "after.json", _trace())

    rc = main(["--before", str(arr), "--after", after])

    assert rc == 2
    err = capsys.readouterr().err
    assert "expected a JSON object" in err
