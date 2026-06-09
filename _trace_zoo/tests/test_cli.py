"""Tests for the vstack-trace-zoo CLI."""

from __future__ import annotations

import json

import pytest

from vstack.trace_zoo._cli import main


class TestListCommand:
    def test_list_runs(self, capsys):
        rc = main(["list"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "Name" in captured.out
        assert "stuck_in_loop" in captured.out

    def test_list_json(self, capsys):
        rc = main(["list", "--json"])
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert isinstance(data, list)
        assert len(data) > 0
        for entry in data:
            assert "name" in entry
            assert "shape" in entry
            assert "category" in entry

    def test_list_by_category(self, capsys):
        rc = main(["list", "--category", "reasoning"])
        assert rc == 0
        captured = capsys.readouterr()
        # Should only show reasoning-category traces.
        assert "stuck_in_loop" in captured.out

    def test_list_by_shape(self, capsys):
        rc = main(["list", "--shape", "individual"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "individual" in captured.out


class TestShowCommand:
    def test_show_known(self, capsys):
        rc = main(["show", "stuck_in_loop"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "stuck_in_loop" in captured.out
        assert "reasoning" in captured.out

    def test_show_unknown_returns_1(self, capsys):
        rc = main(["show", "nonexistent_xyz"])
        assert rc == 1

    def test_show_json(self, capsys):
        rc = main(["show", "stuck_in_loop", "--json"])
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["name"] == "stuck_in_loop"


class TestGetCommand:
    def test_get_known_returns_json(self, capsys):
        rc = main(["get", "stuck_in_loop"])
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert "goal" in data
        assert "steps" in data

    def test_get_unknown_returns_1(self, capsys):
        rc = main(["get", "nonexistent_xyz"])
        assert rc == 1


class TestCategoriesCommand:
    def test_categories_runs(self, capsys):
        rc = main(["categories"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "reasoning" in captured.out
        assert "coordination" in captured.out


class TestShapesCommand:
    def test_shapes_runs(self, capsys):
        rc = main(["shapes"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "individual" in captured.out


class TestSubcommandRequired:
    def test_no_args_exits_with_error(self, capsys):
        with pytest.raises(SystemExit):
            main([])
