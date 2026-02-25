#!/usr/bin/env python3
"""Validate verification policy profile artifacts and normative decision matrix lock."""

from __future__ import annotations

from pathlib import Path
import json
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from policy_profile_matrix import load_policy_test_matrix  # noqa: E402


PROFILE_PATH = PROJECT_ROOT / "conformance" / "verification_policy_profile.v1.json"
ALLOWED_MODES = {"HardBlock", "SoftHold", "GraceCache"}


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    _assert(isinstance(payload, dict), f"{path.name} must contain a JSON object.")
    return payload


def _load_profile(path: Path) -> dict:
    payload = _load_json(path)
    for field in [
        "profileId",
        "policyDefaults",
        "riskTiers",
    ]:
        _assert(field in payload, f"{path.name} missing required field: {field}")
    return payload


def main() -> int:
    artifact = _load_json(PROFILE_PATH)
    for field in [
        "profileVersion",
        "profileId",
        "protocol",
        "canonicalProfiles",
        "matrixLock",
        "conformanceRequirements",
    ]:
        _assert(field in artifact, f"verification policy profile missing field: {field}")

    _assert(artifact.get("protocol") == "FAXP", "protocol must be FAXP")

    canonical_profiles = artifact.get("canonicalProfiles") or []
    _assert(
        isinstance(canonical_profiles, list) and canonical_profiles,
        "canonicalProfiles must be a non-empty array",
    )

    canonical_ids: set[str] = set()
    observed_modes: set[str] = set()
    for item in canonical_profiles:
        _assert(isinstance(item, dict), "canonicalProfiles entries must be objects")
        profile_id = str(item.get("profileId") or "").strip()
        rel_path = str(item.get("path") or "").strip()
        expected_mode = str(item.get("expectedDegradedMode") or "").strip()
        _assert(profile_id, "canonical profile entry missing profileId")
        _assert(rel_path, f"{profile_id}: canonical profile entry missing path")
        _assert(expected_mode in ALLOWED_MODES, f"{profile_id}: invalid expectedDegradedMode {expected_mode!r}")
        _assert(profile_id not in canonical_ids, f"duplicate canonical profileId: {profile_id}")
        canonical_ids.add(profile_id)

        profile_path = (PROJECT_ROOT / rel_path).resolve()
        _assert(profile_path.exists(), f"canonical profile file not found: {rel_path}")
        profile = _load_profile(profile_path)
        _assert(
            str(profile.get("profileId") or "").strip() == profile_id,
            f"{profile_id}: profileId mismatch in {rel_path}",
        )

        defaults = profile.get("policyDefaults") or {}
        mode = str(defaults.get("degradedMode") or "").strip()
        _assert(mode == expected_mode, f"{profile_id}: degradedMode expected {expected_mode}, got {mode}")
        observed_modes.add(mode)

        tier_threshold = int(defaults.get("requireManualEscalationForTier", 3))
        _assert(0 <= tier_threshold <= 3, f"{profile_id}: requireManualEscalationForTier must be 0..3")

        tiers = profile.get("riskTiers") or []
        tier_ids = [int(tier.get("tier", -1)) for tier in tiers]
        _assert(sorted(tier_ids) == [0, 1, 2, 3], f"{profile_id}: riskTiers must contain exactly tiers 0..3")
        for tier in tiers:
            tier_id = int(tier.get("tier", -1))
            requires_human = bool(tier.get("requiresHumanApproval", False))
            if tier_id >= tier_threshold:
                _assert(
                    requires_human,
                    (
                        f"{profile_id}: tier {tier_id} must require human approval "
                        f"for threshold {tier_threshold}"
                    ),
                )

    matrix_lock = artifact.get("matrixLock") or {}
    required_case_ids = [str(item) for item in matrix_lock.get("requiredCaseIds") or []]
    required_modes = {str(item) for item in matrix_lock.get("requiredDegradedModesCovered") or []}
    _assert(required_case_ids, "matrixLock.requiredCaseIds must be non-empty")
    _assert(required_modes == ALLOWED_MODES, "matrixLock.requiredDegradedModesCovered must match canonical modes")

    cases = load_policy_test_matrix(PROJECT_ROOT)
    observed_case_ids = [str(case.get("id") or "").strip() for case in cases]
    _assert(
        set(observed_case_ids) == set(required_case_ids),
        "normative policy matrix case IDs differ from matrixLock.requiredCaseIds",
    )
    _assert(
        len(observed_case_ids) == len(required_case_ids),
        "normative policy matrix contains duplicate case IDs",
    )

    covered_profiles = {str(case.get("profileId") or "").strip() for case in cases}
    _assert(
        covered_profiles == canonical_ids,
        "normative policy matrix must cover exactly canonical profile IDs",
    )

    covered_modes = set()
    for profile_id in covered_profiles:
        profile_path = PROJECT_ROOT / "profiles" / "verification" / f"{profile_id}.json"
        profile = _load_profile(profile_path)
        covered_modes.add(str((profile.get("policyDefaults") or {}).get("degradedMode") or ""))
    _assert(
        covered_modes == required_modes,
        "normative policy matrix profile coverage does not satisfy required degraded mode coverage",
    )

    requirements = artifact.get("conformanceRequirements") or {}
    required_tests = [str(item) for item in requirements.get("requiredTests") or []]
    required_checks = [str(item) for item in requirements.get("requiredSuiteChecks") or []]
    _assert(
        required_tests
        == [
            "tests/run_verification_policy_profile.py",
            "tests/run_policy_decisions.py",
            "tests/run_policy_profile_sync.py",
        ],
        "conformanceRequirements.requiredTests mismatch",
    )
    _assert(
        required_checks
        == [
            "verification_policy_profile",
            "policy_decisions",
            "policy_profile_sync",
        ],
        "conformanceRequirements.requiredSuiteChecks mismatch",
    )

    print("Verification policy profile checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
