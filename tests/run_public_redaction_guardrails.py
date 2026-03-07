#!/usr/bin/env python3
"""Fail CI when public-facing files contain partner-specific names or local machine paths."""

from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

# Public-facing surfaces only.
PUBLIC_ROOTS = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "docs",
    REPO_ROOT / "website",
    REPO_ROOT / ".github" / "ISSUE_TEMPLATE",
    REPO_ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md",
    REPO_ROOT / ".github" / "CODEOWNERS",
]

SKIP_DIR_NAMES = {".git", ".venv", "__pycache__", "node_modules", "public"}
TEXT_SUFFIXES = {".md", ".txt", ".json", ".yml", ".yaml", ".toml", ".html", ".htm"}
EXPLICIT_TEXT_FILES = {REPO_ROOT / ".github" / "CODEOWNERS"}

FORBIDDEN_PATTERNS = [
    ("Partner name leak: Diesel TMS", re.compile(r"\bdiesel\s*tms\b", re.IGNORECASE)),
    ("Partner name leak: dieseltms", re.compile(r"\bdieseltms\b", re.IGNORECASE)),
    ("Partner name leak: Jamie", re.compile(r"\bjamie\b", re.IGNORECASE)),
    ("Partner name leak: BrokerPro", re.compile(r"\bbrokerpro\b", re.IGNORECASE)),
    (
        "Partner name leak: DR Dispatch",
        re.compile(r"\bdr\s*dispatch\b|\bdrdispatch\b", re.IGNORECASE),
    ),
    (
        "Partner name leak: Rick/Richard Holland",
        re.compile(r"\brick\s+holland\b|\brichard\s+holland\b", re.IGNORECASE),
    ),
    ("Local absolute path leak: macOS home path", re.compile(r"/Users/[A-Za-z0-9._-]+/")),
    ("Local absolute path leak: Windows user path", re.compile(r"[A-Za-z]:\\\\Users\\\\")),
]


def _is_text_candidate(path: Path) -> bool:
    return path in EXPLICIT_TEXT_FILES or path.suffix.lower() in TEXT_SUFFIXES


def _iter_public_files() -> list[Path]:
    files: list[Path] = []
    for root in PUBLIC_ROOTS:
        if not root.exists():
            continue
        if root.is_file():
            if _is_text_candidate(root):
                files.append(root)
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in SKIP_DIR_NAMES for part in path.parts):
                continue
            if _is_text_candidate(path):
                files.append(path)
    return sorted(set(files))


def main() -> int:
    violations: list[str] = []
    for path in _iter_public_files():
        rel = path.relative_to(REPO_ROOT)
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for line_no, line in enumerate(lines, start=1):
            for reason, pattern in FORBIDDEN_PATTERNS:
                if pattern.search(line):
                    violations.append(f"{rel}:{line_no}: {reason}")

    if violations:
        print("Public redaction guardrails violation(s) detected:")
        for violation in violations:
            print(f"- {violation}")
        return 1

    print("Public redaction guardrails check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
