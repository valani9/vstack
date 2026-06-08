"""Tests for the ``vstack-diagnose`` CLI.

These tests drive the CLI's ``main()`` entry point with synthetic args
+ stdin and assert on captured stdout. They don't spawn subprocesses
and they don't require an LLM client.
"""

from __future__ import annotations

import json
from io import StringIO

import pytest

from vstack.diagnose.cli import main as cli_main


def _run(argv: list[str], stdin: str = "", monkeypatch=None) -> tuple[int, str, str]:
    """Invoke ``main()`` with controlled stdin/stdout and return
    ``(exit_code, stdout, stderr)``."""
    import sys

    out = StringIO()
    err = StringIO()
    in_ = StringIO(stdin)

    real_stdin = sys.stdin
    real_stdout = sys.stdout
    real_stderr = sys.stderr
    sys.stdin = in_
    sys.stdout = out
    sys.stderr = err
    try:
        code = cli_main(argv)
    finally:
        sys.stdin = real_stdin
        sys.stdout = real_stdout
        sys.stderr = real_stderr
    return code, out.getvalue(), err.getvalue()


def test_list_lists_patterns() -> None:
    code, out, _ = _run(["--list"])
    assert code == 0
    assert "lewin" in out
    assert "lencioni" in out
    assert "psych_safety" in out


def test_missing_trace_stdin_exits_with_message() -> None:
    with pytest.raises(SystemExit) as excinfo:
        _run([])  # no stdin, no --trace
    assert "vstack-diagnose" in str(excinfo.value)


def test_invalid_json_stdin_exits_with_message() -> None:
    with pytest.raises(SystemExit) as excinfo:
        _run([], stdin="{not json")
    assert "not valid JSON" in str(excinfo.value)


def test_argparse_rejects_unknown_client_choice() -> None:
    """argparse's `choices=` enforces the allowed list. An unknown
    provider name causes argparse to print usage and SystemExit(2)
    before any of our code runs."""
    with pytest.raises(SystemExit) as excinfo:
        _run(
            ["--client", "totally-not-a-thing", "--patterns", "lewin"],
            stdin=json.dumps(
                {
                    "goal": "x",
                    "steps": [],
                    "outcome": "y",
                    "success": False,
                }
            ),
        )
    assert excinfo.value.code == 2


def test_runs_diagnose_with_none_client_json_output() -> None:
    payload = {
        "goal": "test",
        "steps": [{"action": "edit", "target": "x.py"}],
        "outcome": "broken",
        "success": False,
    }
    code, out, _ = _run(
        [
            "--client",
            "none",
            "--shape",
            "individual",
            "--patterns",
            "lewin",
            "--json",
        ],
        stdin=json.dumps(payload),
    )
    assert code == 0
    data = json.loads(out)
    assert data["shape"] == "individual"
    # The real Lewin analyzer requires a client; it should land in errors.
    assert "lewin" in data["errors"]
    assert any(p["pattern"] == "lewin" for p in data["per_pattern"])


def test_runs_diagnose_with_none_client_markdown_output() -> None:
    payload = {
        "goal": "test",
        "steps": [{"action": "edit", "target": "x.py"}],
        "outcome": "broken",
        "success": False,
    }
    code, out, _ = _run(
        [
            "--client",
            "none",
            "--shape",
            "individual",
            "--patterns",
            "lewin",
        ],
        stdin=json.dumps(payload),
    )
    assert code == 0
    assert "vstack diagnose" in out
    # No findings because the only pattern errored out, but the report
    # should still include the Pattern errors section.
    assert "lewin" in out
