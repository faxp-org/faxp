#!/usr/bin/env python3
"""Run FMCSA parser regression tests from JSON fixtures."""

from __future__ import annotations

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from adapter.fmcsa_live import normalize_fmcsa_live_payload


FIXTURE_DIR = Path(__file__).resolve().parent / "fmcsa_fixtures"


def _load_fixture(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _assert_expected(actual: dict, expected: dict, fixture_name: str) -> None:
    for key, expected_value in expected.items():
        if key not in actual:
            raise AssertionError(f"{fixture_name}: missing key in result: {key}")
        actual_value = actual[key]
        if actual_value != expected_value:
            raise AssertionError(
                f"{fixture_name}: expected {key}={expected_value!r}, got {actual_value!r}"
            )


def main() -> int:
    fixture_paths = sorted(FIXTURE_DIR.glob("*.json"))
    if not fixture_paths:
        print("No FMCSA parser fixtures found.", file=sys.stderr)
        return 1

    for path in fixture_paths:
        fixture = _load_fixture(path)
        fixture_name = fixture.get("name", path.name)
        requested_mc = fixture["requested_mc"]
        payload = fixture["payload"]
        expected = fixture["expected"]

        actual = normalize_fmcsa_live_payload(payload, requested_mc)
        _assert_expected(actual, expected, fixture_name)
        print(f"[PASS] {fixture_name}")

    print(f"FMCSA parser fixture tests passed: {len(fixture_paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
