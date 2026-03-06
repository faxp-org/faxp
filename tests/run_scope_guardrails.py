#!/usr/bin/env python3
"""Fail CI when protocol-core files drift into out-of-scope lifecycle domains."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]

# Protocol-core artifacts guarded for scope drift.
# NOTE:
# - `faxp_mvp_simulation.py` is intentionally excluded. It is a reference
#   implementer/runtime artifact (builder-side behavior), not normative
#   protocol-core schema/governance source.
CORE_FILES = [
    REPO_ROOT / "faxp.schema.json",
    REPO_ROOT / "faxp.v0.2.schema.json",
]

# Keep these focused on domains that are explicitly out-of-scope for protocol core.
# NOTE: DispatchAuthorization (booking-time risk gate) is intentionally permitted.
FORBIDDEN_PATTERNS = [
    ("Driver assignment workflow", re.compile(r"\bdriver[\s_-]*assignment\b", re.IGNORECASE)),
    ("Route optimization workflow", re.compile(r"\broute[\s_-]*optimization\b", re.IGNORECASE)),
    ("Telematics workflow", re.compile(r"\btelematics\b", re.IGNORECASE)),
    ("Proof-of-delivery workflow", re.compile(r"\bproof[\s_-]*of[\s_-]*delivery\b|\bpod\b", re.IGNORECASE)),
    ("Bill-of-lading workflow", re.compile(r"\bbill[\s_-]*of[\s_-]*lading\b|\bbol\b", re.IGNORECASE)),
    ("Invoicing workflow", re.compile(r"\binvoice(?:s|d|ing)?\b", re.IGNORECASE)),
    ("Payment workflow", re.compile(r"\bpayment(?:s|status|request|instruction|terms)?\b", re.IGNORECASE)),
    ("Settlement workflow", re.compile(r"\bsettlement\b|\bremittance\b|\bfactoring\b", re.IGNORECASE)),
    ("Dispatch message lifecycle", re.compile(r"\bdispatch(?:update|instruction|event)s?\b", re.IGNORECASE)),
]


def _iter_lines(path: Path) -> Iterable[tuple[int, str]]:
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        yield line_no, line


def main() -> int:
    violations: list[str] = []

    for core_file in CORE_FILES:
        if not core_file.exists():
            violations.append(f"[MISSING] {core_file}")
            continue
        for line_no, line in _iter_lines(core_file):
            for reason, pattern in FORBIDDEN_PATTERNS:
                if pattern.search(line):
                    violations.append(
                        f"{core_file}:{line_no}: {reason} (matched: {pattern.pattern})"
                    )

    if violations:
        print("Scope guardrails violation(s) detected:")
        for violation in violations:
            print(f"- {violation}")
        return 1

    print("Scope guardrails check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
