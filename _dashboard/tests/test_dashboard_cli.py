"""Tests for the ``vstack-dashboard`` CLI."""

from __future__ import annotations

import io
import json
from pathlib import Path


from vstack.dashboard.cli import main


def _sample_payload() -> dict:
    return {
        "shape": "individual",
        "findings": [
            {
                "pattern": "lewin",
                "severity": "high",
                "title": "env locus",
                "evidence": "stale rag",
                "intervention": "refresh",
            }
        ],
        "per_pattern": [
            {
                "pattern": "lewin",
                "n_findings": 1,
                "elapsed_seconds": 1.0,
                "error": None,
            }
        ],
        "errors": {},
        "cost": {
            "llm_calls": 1,
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
            "elapsed_ms": 1000,
            "by_pattern": {},
            "by_model": {},
        },
    }


def test_render_from_file(tmp_path: Path) -> None:
    src = tmp_path / "report.json"
    src.write_text(json.dumps(_sample_payload()))
    out = tmp_path / "dashboard.html"
    rc = main(["render", "--in", str(src), "--out", str(out)])
    assert rc == 0
    body = out.read_text()
    assert body.startswith("<!doctype html>")
    assert "env locus" in body


def test_render_from_stdin(capsys, monkeypatch) -> None:
    payload = json.dumps(_sample_payload())
    monkeypatch.setattr("sys.stdin", io.StringIO(payload))
    rc = main(["render"])
    assert rc == 0
    captured = capsys.readouterr()
    assert captured.out.startswith("<!doctype html>")
    assert "env locus" in captured.out


def test_render_rejects_empty_input(capsys, monkeypatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    rc = main(["render"])
    assert rc == 2


def test_render_rejects_invalid_json(capsys, monkeypatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("{not json"))
    rc = main(["render"])
    assert rc == 2


def test_render_accepts_custom_title(tmp_path: Path) -> None:
    src = tmp_path / "r.json"
    src.write_text(json.dumps(_sample_payload()))
    out = tmp_path / "dash.html"
    rc = main(["render", "--in", str(src), "--out", str(out), "--title", "Acme Diagnostics"])
    assert rc == 0
    body = out.read_text()
    assert "Acme Diagnostics" in body
