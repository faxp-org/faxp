#!/usr/bin/env python3
"""Fail CI when public-facing files contain partner-specific names or local machine paths."""

from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import urlparse


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
    ("Local absolute path leak: macOS home path", re.compile(r"/Users/[A-Za-z0-9._-]+/")),
    ("Local absolute path leak: Windows user path", re.compile(r"[A-Za-z]:\\\\Users\\\\")),
    (
        "Credential leak: Authorization Bearer token literal",
        re.compile(r"(?i)authorization\s*[:=]\s*bearer\s+[A-Za-z0-9._-]{20,}"),
    ),
    (
        "Credential leak: JWT-like token literal",
        re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
    ),
    (
        "Credential leak: PEM key block marker",
        re.compile(r"-----BEGIN [A-Z ]*PRIVAT\x45 K\x45Y-----"),
    ),
]

URL_PATTERN = re.compile(r"https?://[^\s)\]>\"]+")
APPROVED_PUBLIC_DOMAINS = {
    "example.com",
    "faxp.org",
    "github.com",
    "json-schema.org",
}
PRIVATE_TERMS_ENV = "FAXP_PRIVATE_REDACTION_TERMS"


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


def _normalize_domain(url: str) -> str:
    parsed = urlparse(url.strip())
    return parsed.netloc.lower().strip("`.,;:)]}>\"'")


def _is_domain_approved(domain: str) -> bool:
    if not domain:
        return False
    if domain in APPROVED_PUBLIC_DOMAINS:
        return True
    # Allow common safe subdomain usage under approved roots.
    return any(domain.endswith(f".{root}") for root in APPROVED_PUBLIC_DOMAINS)


def _private_term_patterns() -> list[tuple[str, re.Pattern[str]]]:
    raw = str(os.getenv(PRIVATE_TERMS_ENV, "") or "").strip()
    if not raw:
        return []
    terms = [term.strip() for term in raw.split(",") if term.strip()]
    patterns: list[tuple[str, re.Pattern[str]]] = []
    for term in terms:
        patterns.append(
            (
                f"Private redaction term leak (from {PRIVATE_TERMS_ENV}): {term}",
                re.compile(re.escape(term), re.IGNORECASE),
            )
        )
    return patterns


def main() -> int:
    violations: list[str] = []
    private_patterns = _private_term_patterns()
    for path in _iter_public_files():
        rel = path.relative_to(REPO_ROOT)
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for line_no, line in enumerate(lines, start=1):
            for reason, pattern in FORBIDDEN_PATTERNS:
                if pattern.search(line):
                    violations.append(f"{rel}:{line_no}: {reason}")
            for reason, pattern in private_patterns:
                if pattern.search(line):
                    violations.append(f"{rel}:{line_no}: {reason}")
            for url in URL_PATTERN.findall(line):
                domain = _normalize_domain(url)
                if not _is_domain_approved(domain):
                    violations.append(
                        f"{rel}:{line_no}: Unapproved external domain in public-facing file: {domain}"
                    )

    if violations:
        print("Public redaction guardrails violation(s) detected:")
        for violation in violations:
            print(f"- {violation}")
        return 1

    print("Public redaction guardrails check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
