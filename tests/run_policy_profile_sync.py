#!/usr/bin/env python3
"""Ensure policy profile docs and regression tests remain synchronized."""

from __future__ import annotations

from pathlib import Path
import json
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from policy_profile_matrix import load_policy_test_matrix  # noqa: E402


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    matrix_cases = load_policy_test_matrix(PROJECT_ROOT)
    _assert(matrix_cases, "Policy test matrix is empty.")

    run_policy_decisions_source = (
        PROJECT_ROOT / "tests" / "run_policy_decisions.py"
    ).read_text(encoding="utf-8")
    _assert(
        "load_policy_test_matrix(PROJECT_ROOT)" in run_policy_decisions_source,
        "run_policy_decisions.py must load normative cases from POLICY_PROFILES.md.",
    )

    degraded_modes_covered: set[str] = set()
    for case in matrix_cases:
        case_id = str(case["id"])
        profile_id = str(case["profileId"])
        profile_path = PROJECT_ROOT / "profiles" / "verification" / f"{profile_id}.json"
        _assert(profile_path.exists(), f"{case_id}: profile not found at {profile_path}")
        profile = _load_json(profile_path)
        degraded_mode = str((profile.get("policyDefaults") or {}).get("degradedMode") or "")
        _assert(
            degraded_mode in {"HardBlock", "SoftHold", "GraceCache"},
            f"{case_id}: invalid degraded mode {degraded_mode!r} in {profile_id}",
        )
        degraded_modes_covered.add(degraded_mode)

    _assert(
        degraded_modes_covered == {"HardBlock", "SoftHold", "GraceCache"},
        (
            "Normative policy matrix must cover HardBlock, SoftHold, and GraceCache. "
            f"Observed: {sorted(degraded_modes_covered)}"
        ),
    )

    print(
        "Policy profile doc/test sync checks passed "
        f"({len(matrix_cases)} normative cases, modes={sorted(degraded_modes_covered)})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
