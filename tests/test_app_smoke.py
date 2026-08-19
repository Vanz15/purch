"""Dependency-light smoke checks for the canonical Reflex application."""

import py_compile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_reflex_entrypoint_compiles_without_errors() -> None:
    """Catch syntax errors without starting the Reflex development server."""
    for relative_path in ("rxconfig.py", "purch/purch.py"):
        py_compile.compile(str(ROOT / relative_path), doraise=True)
