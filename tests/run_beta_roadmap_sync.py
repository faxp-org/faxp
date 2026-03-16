#!/usr/bin/env python3
"""Ensure beta-promotion criterion status stays aligned with Workstream F roadmap status."""

from __future__ import annotations

from pathlib import Path
import json
import re


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VNEXT_PATH = PROJECT_ROOT / "docs" / "roadmap" / "VNEXT_EXECUTION_CHECKLIST_2026-03-07.md"
CRITERIA_PATH = PROJECT_ROOT / "docs" / "governance" / "DEVELOPER_BETA_PROMOTION_CRITERIA.md"
SNAPSHOT_PATH = PROJECT_ROOT / "docs" / "releases" / "DEVELOPER_BETA_DECISION_SNAPSHOT.md"

CRITERIA_BEGIN = "<!-- DEVELOPER_BETA_PROMOTION_CRITERIA_BEGIN -->"
CRITERIA_END = "<!-- DEVELOPER_BETA_PROMOTION_CRITERIA_END -->"
SNAPSHOT_BEGIN = "<!-- DEVELOPER_BETA_DECISION_SNAPSHOT_BEGIN -->"
SNAPSHOT_END = "<!-- DEVELOPER_BETA_DECISION_SNAPSHOT_END -->"

WORKSTREAM_F_RE = re.compile(
    r"^\|\s*F\.\s*Second Independent Implementer Demo\s*\|\s*(Done|In Progress|Ongoing|Blocked|Not Started)\s*\|",
    re.MULTILINE,
)
CRITERION_ID = "second_independent_implementer_demo"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _extract_block(document: str, begin: str, end: str) -> str:
    start = document.find(begin)
    stop = document.find(end)
    _assert(start != -1 and stop != -1 and stop > start, f"Missing or invalid block: {begin}")
    return document[start + len(begin) : stop].strip()


def _normalize_status(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def _read_workstream_f_status() -> str:
    text = VNEXT_PATH.read_text(encoding="utf-8")
    match = WORKSTREAM_F_RE.search(text)
    _assert(match is not None, "Missing Workstream F status row in vNext roadmap.")
    return _normalize_status(match.group(1))


def _load_criteria_manifest() -> dict:
    text = CRITERIA_PATH.read_text(encoding="utf-8")
    return json.loads(_extract_block(text, CRITERIA_BEGIN, CRITERIA_END))


def _load_snapshot_manifest() -> dict:
    text = SNAPSHOT_PATH.read_text(encoding="utf-8")
    return json.loads(_extract_block(text, SNAPSHOT_BEGIN, SNAPSHOT_END))


def main() -> int:
    for path in [VNEXT_PATH, CRITERIA_PATH, SNAPSHOT_PATH]:
        _assert(path.exists(), f"Missing required document: {path}")

    workstream_f_status = _read_workstream_f_status()
    criteria = _load_criteria_manifest()
    snapshot = _load_snapshot_manifest()

    criteria_items = criteria.get("criteria") or []
    _assert(isinstance(criteria_items, list) and criteria_items, "Criteria manifest must include non-empty criteria.")

    target = None
    for item in criteria_items:
        if str((item or {}).get("id") or "").strip() == CRITERION_ID:
            target = item
            break
    _assert(target is not None, f"Missing criterion in manifest: {CRITERION_ID}")

    criterion_status = _normalize_status(str((target or {}).get("status") or ""))
    _assert(
        criterion_status in {"done", "in_progress", "blocked", "not_started"},
        f"Unexpected status for {CRITERION_ID}: {criterion_status}",
    )

    if criterion_status == "done":
        _assert(
            workstream_f_status == "done",
            "Workstream F must be Done when second implementer criterion is done.",
        )
    else:
        _assert(
            workstream_f_status != "done",
            "Workstream F must not be Done while second implementer criterion is still non-done.",
        )
        _assert(
            str(criteria.get("betaDecision") or "").strip().lower() == "not_ready",
            "betaDecision must remain not_ready until second implementer criterion is done.",
        )

    remaining = snapshot.get("remainingCriteria") or []
    remaining_ids = {str((item or {}).get("id") or "").strip() for item in remaining}
    if criterion_status == "done":
        _assert(
            CRITERION_ID not in remaining_ids,
            "Decision snapshot must not list second implementer criterion in remainingCriteria once done.",
        )
    else:
        _assert(
            CRITERION_ID in remaining_ids,
            "Decision snapshot must list second implementer criterion in remainingCriteria while non-done.",
        )

    print("Beta roadmap sync checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
