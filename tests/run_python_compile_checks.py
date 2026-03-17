#!/usr/bin/env python3
"""Compile all Python source files in-repo to catch syntax errors early."""

from __future__ import annotations

import py_compile
import sys
from pathlib import Path


EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    "node_modules",
    "build",
    "dist",
}


def _iter_python_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*.py"):
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    files = _iter_python_files(root)
    if not files:
        print("No Python files found.")
        return 0

    errors: list[tuple[Path, Exception]] = []
    for path in files:
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:  # pragma: no cover - exercised in CI on failure
            errors.append((path, exc))

    print(f"Compiled {len(files)} Python files.")
    if not errors:
        print("Python compile checks passed.")
        return 0

    print(f"Python compile checks failed for {len(errors)} file(s):")
    for path, exc in errors:
        rel = path.relative_to(root)
        print(f" - {rel}: {exc}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
