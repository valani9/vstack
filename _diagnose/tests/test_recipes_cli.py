"""Tests for the ``vstack-recipes`` CLI."""

from __future__ import annotations

import json


from vstack.diagnose.recipes_cli import main


def test_no_args_lists_all_clusters(capsys) -> None:
    rc = main([])
    out = capsys.readouterr().out
    assert rc == 0
    # All 5 clusters appear in the output.
    for cluster in ("REASONING", "COORDINATION", "TRUST", "WORKLOAD", "CULTURE"):
        assert cluster in out
    # Several canonical recipes appear.
    assert "stuck_in_loop" in out
    assert "agents_arguing" in out
    assert "silent_failure" in out


def test_compact_emits_one_slug_per_line(capsys) -> None:
    rc = main(["--compact"])
    out = capsys.readouterr().out
    assert rc == 0
    lines = [ln for ln in out.splitlines() if ln.strip()]
    # We have at least the original 8 + many more.
    assert len(lines) >= 30
    # Each line should be a valid recipe slug (no whitespace beyond the line).
    for ln in lines:
        assert " " not in ln.strip()


def test_filter_by_cluster_reasoning(capsys) -> None:
    rc = main(["--cluster", "reasoning"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "REASONING" in out
    # culture cluster should not appear when filtered
    assert "CULTURE" not in out
    assert "stuck_in_loop" in out


def test_filter_by_shape_individual(capsys) -> None:
    rc = main(["--shape", "individual"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "stuck_in_loop" in out
    # Team-only recipes should not appear when filtered to individual shape
    assert "agents_arguing" not in out


def test_match_routes_text_to_recipe(capsys) -> None:
    # Uses one of the registered trigger phrases for over_apology_loop
    rc = main(["--match", "won't stop apologizing"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "over_apology_loop" in out


def test_match_returns_nonzero_on_no_hit(capsys) -> None:
    rc = main(["--match", "nothing-could-possibly-match-this-string-xyz"])
    captured = capsys.readouterr()
    assert rc == 1
    assert "no recipe matched" in captured.err


def test_q_search_substring(capsys) -> None:
    rc = main(["--q", "blame"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "blame_spiral" in out


def test_q_no_hits_returns_nonzero(capsys) -> None:
    rc = main(["--q", "xyz_no_match_zzz"])
    assert rc == 1


def test_show_prints_detail(capsys) -> None:
    rc = main(["--show", "stuck_in_loop"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "stuck_in_loop" in out
    assert "individual" in out  # the shape
    # Pattern list
    assert "aar" in out
    assert "lewin" in out


def test_show_unknown_recipe_returns_nonzero(capsys) -> None:
    rc = main(["--show", "no_such_recipe"])
    captured = capsys.readouterr()
    assert rc == 1
    assert "unknown recipe" in captured.err


def test_show_json_emits_valid_json(capsys) -> None:
    rc = main(["--show", "stuck_in_loop", "--json"])
    out = capsys.readouterr().out
    assert rc == 0
    parsed = json.loads(out)
    assert parsed["name"] == "stuck_in_loop"
    assert "patterns" in parsed
    assert isinstance(parsed["patterns"], list)


def test_show_md_emits_markdown(capsys) -> None:
    rc = main(["--show", "stuck_in_loop", "--md"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "# Recipe: `stuck_in_loop`" in out
    assert "## Patterns" in out
    assert "```bash" in out
    assert "vstack-diagnose --trace your-trace.json --recipe stuck_in_loop" in out


def test_json_list_format(capsys) -> None:
    rc = main(["--json", "--cluster", "trust"])
    out = capsys.readouterr().out
    assert rc == 0
    parsed = json.loads(out)
    assert isinstance(parsed, list)
    assert all("name" in r for r in parsed)
    # All entries are trust cluster
    assert all(r["cluster"] == "trust" for r in parsed)
