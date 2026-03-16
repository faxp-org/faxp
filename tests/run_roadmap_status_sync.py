#!/usr/bin/env python3
"""Ensure roadmap workstream status remains synchronized across roadmap docs."""

from __future__ import annotations

from pathlib import Path
import re


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VNEXT_PATH = PROJECT_ROOT / "docs" / "roadmap" / "VNEXT_EXECUTION_CHECKLIST_2026-03-07.md"
PHASE2_PATH = PROJECT_ROOT / "docs" / "roadmap" / "PHASE_2_IMPLEMENTATION_ROADMAP.md"

VNEXT_ROW_RE = re.compile(
    r"^\|\s*([A-F])\.\s*[^|]+\|\s*(Done|In Progress|Ongoing|Blocked|Not Started)\s*\|",
    re.MULTILINE,
)
PHASE2_ROW_RE = re.compile(
    r"^- Workstream ([A-F]) \([^)]*\):\s*(Done|In Progress|Ongoing|Blocked|Not Started)\s*$",
    re.MULTILINE,
)
REMAINING_RE = re.compile(r"^3\.\s*Remaining active execution:\s*([A-F,\sand]+)\.\s*$", re.MULTILINE)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _normalize_status(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def _parse_vnext_statuses(text: str) -> dict[str, str]:
    statuses = {code: _normalize_status(status) for code, status in VNEXT_ROW_RE.findall(text)}
    _assert(set(statuses.keys()) == set("ABCDEF"), "VNEXT roadmap must contain status rows for workstreams A-F.")
    return statuses


def _parse_phase2_statuses(text: str) -> dict[str, str]:
    statuses = {code: _normalize_status(status) for code, status in PHASE2_ROW_RE.findall(text)}
    _assert(set(statuses.keys()) == set("ABCDEF"), "Phase 2 roadmap must contain status rows for workstreams A-F.")
    return statuses


def _parse_remaining_active(text: str) -> set[str]:
    match = REMAINING_RE.search(text)
    _assert(match is not None, "Phase 2 roadmap must include 'Remaining active execution' line item.")
    raw = match.group(1)
    return set(re.findall(r"[A-F]", raw))


def main() -> int:
    _assert(VNEXT_PATH.exists(), f"Missing vNext roadmap: {VNEXT_PATH}")
    _assert(PHASE2_PATH.exists(), f"Missing Phase 2 roadmap: {PHASE2_PATH}")

    vnext_text = VNEXT_PATH.read_text(encoding="utf-8")
    phase2_text = PHASE2_PATH.read_text(encoding="utf-8")

    vnext = _parse_vnext_statuses(vnext_text)
    phase2 = _parse_phase2_statuses(phase2_text)

    _assert(
        vnext == phase2,
        f"Roadmap status mismatch between vNext and Phase 2 docs: vNext={vnext}, phase2={phase2}",
    )

    expected_remaining = {code for code, status in phase2.items() if status != "done"}
    listed_remaining = _parse_remaining_active(phase2_text)
    _assert(
        listed_remaining == expected_remaining,
        (
            "Phase 2 'Remaining active execution' list must match non-done workstreams. "
            f"expected={sorted(expected_remaining)} actual={sorted(listed_remaining)}"
        ),
    )

    print("Roadmap status sync checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
