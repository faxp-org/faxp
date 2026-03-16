#!/usr/bin/env python3
"""Validate developer beta decision snapshot generation and manifest alignment."""

from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = PROJECT_ROOT / "scripts" / "generate_beta_decision_snapshot.py"
CRITERIA_DOC_PATH = PROJECT_ROOT / "docs" / "governance" / "DEVELOPER_BETA_PROMOTION_CRITERIA.md"
SNAPSHOT_PATH = PROJECT_ROOT / "docs" / "releases" / "DEVELOPER_BETA_DECISION_SNAPSHOT.md"
CRITERIA_BEGIN = "<!-- DEVELOPER_BETA_PROMOTION_CRITERIA_BEGIN -->"
CRITERIA_END = "<!-- DEVELOPER_BETA_PROMOTION_CRITERIA_END -->"
SNAPSHOT_BEGIN = "<!-- DEVELOPER_BETA_DECISION_SNAPSHOT_BEGIN -->"
SNAPSHOT_END = "<!-- DEVELOPER_BETA_DECISION_SNAPSHOT_END -->"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _extract_block(document: str, begin: str, end: str) -> str:
    start = document.find(begin)
    stop = document.find(end)
    _assert(start != -1 and stop != -1 and stop > start, f"Missing or invalid block: {begin}")
    return document[start + len(begin) : stop].strip()


def _load_criteria_manifest() -> dict:
    payload = json.loads(
        _extract_block(CRITERIA_DOC_PATH.read_text(encoding="utf-8"), CRITERIA_BEGIN, CRITERIA_END)
    )
    _assert(isinstance(payload, dict), "Criteria manifest must be JSON object.")
    return payload


def _load_snapshot_payload() -> dict:
    _assert(SNAPSHOT_PATH.exists(), f"Missing beta decision snapshot doc: {SNAPSHOT_PATH}")
    snapshot_doc = SNAPSHOT_PATH.read_text(encoding="utf-8")
    payload = json.loads(_extract_block(snapshot_doc, SNAPSHOT_BEGIN, SNAPSHOT_END))
    _assert(isinstance(payload, dict), "Snapshot machine block must be a JSON object.")
    return payload


def main() -> int:
    _assert(GENERATOR_PATH.exists(), "Missing snapshot generator script.")

    subprocess.run([sys.executable, str(GENERATOR_PATH), "--check"], check=True, cwd=str(PROJECT_ROOT))

    criteria = _load_criteria_manifest()
    snapshot = _load_snapshot_payload()

    criteria_list = criteria.get("criteria") or []
    _assert(isinstance(criteria_list, list) and criteria_list, "Criteria list must be non-empty.")

    expected_decision = str(criteria.get("betaDecision") or "").strip().lower()
    _assert(snapshot.get("betaDecision") == expected_decision, "Snapshot betaDecision must match criteria manifest.")

    expected_updated_at = str(criteria.get("updatedAt") or "").strip()
    _assert(
        str(snapshot.get("sourceCriteriaUpdatedAt") or "").strip() == expected_updated_at,
        "Snapshot sourceCriteriaUpdatedAt must match criteria manifest updatedAt.",
    )

    done_count = sum(1 for item in criteria_list if str((item or {}).get("status") or "").strip().lower() == "done")
    _assert(int(snapshot.get("doneCriteria") or -1) == done_count, "Snapshot doneCriteria mismatch.")
    _assert(int(snapshot.get("totalCriteria") or -1) == len(criteria_list), "Snapshot totalCriteria mismatch.")

    expected_remaining_ids = sorted(
        str((item or {}).get("id") or "").strip()
        for item in criteria_list
        if str((item or {}).get("status") or "").strip().lower() != "done"
    )
    actual_remaining_ids = sorted(
        str((item or {}).get("id") or "").strip() for item in (snapshot.get("remainingCriteria") or [])
    )
    _assert(actual_remaining_ids == expected_remaining_ids, "Snapshot remainingCriteria ids mismatch.")

    print("Developer beta decision snapshot checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
