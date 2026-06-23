"""Tests for the vstack-synth CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from vstack.synth._cli import main


def test_list_human_readable(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["list"])

    assert rc == 0
    out = capsys.readouterr().out
    assert "Available templates" in out
    assert "stuck_in_loop" in out
    assert "Retry-loop failure" in out


def test_list_json(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["list", "--json"])

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    names = {entry["name"] for entry in payload}
    assert "stuck_in_loop" in names
    assert "healthy" in names
    stuck = next(e for e in payload if e["name"] == "stuck_in_loop")
    assert stuck["default_params"]["retry_count"] == 3


def test_gen_single_to_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["gen", "--template", "stuck_in_loop", "--seed", "42"])

    assert rc == 0
    trace: dict[str, Any] = json.loads(capsys.readouterr().out)
    assert trace["success"] is False
    assert trace["retry_count"] == 3
    assert isinstance(trace["steps"], list)
    assert trace["steps"]


def test_gen_param_override(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["gen", "--template", "stuck_in_loop", "--param", "retry_count=7", "--seed", "1"])

    assert rc == 0
    trace: dict[str, Any] = json.loads(capsys.readouterr().out)
    assert trace["retry_count"] == 7
    tool_calls = [s for s in trace["steps"] if s["type"] == "tool_call"]
    assert len(tool_calls) == 7


def test_gen_batch_to_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "batch.json"

    rc = main(
        [
            "gen",
            "--template",
            "healthy",
            "--count",
            "5",
            "--seed",
            "3",
            "--out",
            str(out),
        ]
    )

    assert rc == 0
    assert "wrote" in capsys.readouterr().err
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    assert len(payload) == 5
    assert all(t["success"] is True for t in payload)


def test_gen_seed_is_deterministic(capsys: pytest.CaptureFixture[str]) -> None:
    main(["gen", "--template", "stuck_in_loop", "--seed", "99"])
    first = capsys.readouterr().out
    main(["gen", "--template", "stuck_in_loop", "--seed", "99"])
    second = capsys.readouterr().out

    assert first == second


def test_gen_unknown_template_is_usage_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main(["gen", "--template", "does_not_exist"])

    assert rc == 2
    err = capsys.readouterr().err
    assert "vstack-synth: error:" in err
    assert "unknown template" in err


def test_gen_bad_param_is_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["gen", "--template", "stuck_in_loop", "--param", "no_equals_sign"])

    assert rc == 2
    err = capsys.readouterr().err
    assert "vstack-synth: error:" in err
    assert "expected key=value" in err


def test_gen_unexpected_param_is_usage_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main(["gen", "--template", "healthy", "--param", "bogus_kwarg=1"])

    assert rc == 2
    err = capsys.readouterr().err
    assert "vstack-synth: error:" in err


def test_gen_bad_count_is_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["gen", "--template", "healthy", "--count", "0"])

    assert rc == 2
    err = capsys.readouterr().err
    assert "--count must be >= 1" in err
