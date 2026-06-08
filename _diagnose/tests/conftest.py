"""Pytest configuration for the vstack.diagnose test suite.

Tests import from the installed ``vstack`` package, which means the
``_diagnose/lib/`` source folder is shipped under ``vstack/diagnose/``
via the hatchling ``force-include`` mapping in ``pyproject.toml``.
Install with ``pip install -e .`` from the repo root before running
tests. If you edit the diagnose source you may need to re-run
``pip install -e .`` to refresh the force-included copy under
``site-packages``.
"""
