#!/usr/bin/env python3
"""Validate A2A watch governance artifacts and tracking config."""

from __future__ import annotations

from pathlib import Path
import json
import re


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHANGE_MANAGEMENT_PATH = PROJECT_ROOT / "docs" / "interop" / "A2A_CHANGE_MANAGEMENT.md"
TRACKING_PATH = PROJECT_ROOT / "docs" / "interop" / "A2A_UPSTREAM_TRACKING.json"
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "check_a2a_upstream.py"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    _assert(CHANGE_MANAGEMENT_PATH.exists(), "A2A change management doc is missing.")
    _assert(TRACKING_PATH.exists(), "A2A upstream tracking config is missing.")
    _assert(SCRIPT_PATH.exists(), "A2A upstream watch script is missing.")

    tracking = _load_json(TRACKING_PATH)
    required_fields = [
        "trackingVersion",
        "upstreamRepo",
        "trackedRef",
        "trackedRefType",
        "reviewCadence",
        "lastReviewedAt",
        "owner",
    ]
    for field in required_fields:
        _assert(field in tracking, f"Tracking config missing required field: {field}")

    upstream_repo = str(tracking["upstreamRepo"]).strip()
    _assert(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", upstream_repo) is not None, "upstreamRepo must match '<owner>/<repo>'.")

    tracked_ref = str(tracking["trackedRef"]).strip()
    _assert(tracked_ref != "", "trackedRef must be non-empty.")

    tracked_type = str(tracking["trackedRefType"]).strip()
    _assert(tracked_type in {"release", "tag", "branch", "unknown"}, "trackedRefType must be release/tag/branch/unknown.")

    change_doc = CHANGE_MANAGEMENT_PATH.read_text(encoding="utf-8")
    for marker in [
        "A2A_COMPATIBILITY_PROFILE.md",
        "a2a_translator_contract.json",
        "A2A_UPSTREAM_TRACKING.json",
        "check_a2a_upstream.py",
    ]:
        _assert(marker in change_doc, f"A2A change management doc missing reference: {marker}")

    print("A2A watch artifact checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
