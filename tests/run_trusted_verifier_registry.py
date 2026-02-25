#!/usr/bin/env python3
"""Regression checks for trusted verifier registry enforcement."""

from __future__ import annotations

from pathlib import Path
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import faxp_mvp_simulation as sim  # noqa: E402


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _expect_failure(result: dict, expected_substring: str) -> None:
    try:
        sim._validate_verification_result(result, "VerificationResult")  # noqa: SLF001
    except ValueError as exc:
        _assert(
            expected_substring in str(exc),
            f"expected failure containing {expected_substring!r}, got {exc!r}",
        )
        return
    raise AssertionError("expected validation to fail but it passed")


def main() -> int:
    registry_path = PROJECT_ROOT / "conformance" / "trusted_verifier_registry.sample.json"
    _assert(registry_path.exists(), "trusted verifier registry sample is missing")
    registry_payload = json.loads(registry_path.read_text(encoding="utf-8"))
    _assert(isinstance(registry_payload, dict), "trusted verifier registry sample must be an object")
    _assert(
        isinstance(registry_payload.get("entries"), list) and registry_payload["entries"],
        "trusted verifier registry sample must include non-empty entries",
    )
    provider_ids = {
        str(item.get("providerId") or "").strip()
        for item in registry_payload.get("entries", [])
        if isinstance(item, dict)
    }
    _assert(
        "compliance.authority-record.adapter" in provider_ids,
        "trusted verifier registry sample must include compliance.authority-record.adapter",
    )

    original = {
        "NON_LOCAL_MODE": sim.NON_LOCAL_MODE,
        "ENFORCE_TRUSTED_VERIFIER_REGISTRY": sim.ENFORCE_TRUSTED_VERIFIER_REGISTRY,
        "TRUSTED_VERIFIER_REGISTRY": sim.TRUSTED_VERIFIER_REGISTRY,
        "REQUIRE_SIGNED_VERIFIER": sim.REQUIRE_SIGNED_VERIFIER,
    }
    try:
        sim.NON_LOCAL_MODE = True
        sim.ENFORCE_TRUSTED_VERIFIER_REGISTRY = True
        sim.REQUIRE_SIGNED_VERIFIER = False
        sim.TRUSTED_VERIFIER_REGISTRY = {
            "compliance.authority-record.adapter": {
                "providerId": "compliance.authority-record.adapter",
                "providerType": "Compliance",
                "status": "Active",
                "allowedSources": ["hosted-adapter"],
                "allowedAssuranceLevels": ["AAL1"],
                "allowedAttestationKids": [],
            },
            "identity.liveness-document.mock": {
                "providerId": "identity.liveness-document.mock",
                "providerType": "Identity",
                "status": "Inactive",
                "allowedSources": ["mock-biometric"],
                "allowedAssuranceLevels": ["AAL2"],
                "allowedAttestationKids": [],
            },
        }

        valid_result = {
            "status": "Success",
            "provider": "compliance.authority-record.adapter",
            "category": "Compliance",
            "method": "AuthorityRecordCheck",
            "assuranceLevel": "AAL1",
            "score": 95,
            "source": "hosted-adapter",
            "token": "test-token",
            "evidenceRef": "sha256:test",
            "verifiedAt": "2026-02-25T00:00:00Z",
        }
        sim._validate_verification_result(valid_result, "VerificationResult")  # noqa: SLF001

        unknown_provider = dict(valid_result)
        unknown_provider["provider"] = "unknown.provider"
        _expect_failure(unknown_provider, "not in trusted verifier registry")

        inactive_provider = dict(valid_result)
        inactive_provider["provider"] = "identity.liveness-document.mock"
        _expect_failure(inactive_provider, "not active in trusted verifier registry")

        bad_source = dict(valid_result)
        bad_source["source"] = "authority-mock"
        _expect_failure(bad_source, "source 'authority-mock' is not allowed")

        fm_fail_result, fm_fail_badge = sim.run_verification(
            provider="FMCSA",
            status="Success",
            mc_number="498282",
            fmcsa_source="authority-mock",
        )
        _assert(fm_fail_result["status"] == "Fail", "non-local FMCSA authority-mock should fail")
        _assert(fm_fail_badge == "None", "non-local FMCSA authority-mock should not grant badge")
        _assert(
            "requires hosted-adapter" in str(fm_fail_result.get("error", "")),
            "non-local FMCSA failure reason mismatch",
        )

        id_fail_result, id_fail_badge = sim.run_verification(
            provider="MockBiometricProvider",
            status="Success",
        )
        _assert(
            id_fail_result["status"] == "Fail",
            "non-local mock identity provider should fail",
        )
        _assert(id_fail_badge == "None", "non-local mock identity provider should not grant badge")
        _assert(
            "requires trusted external identity verifier" in str(id_fail_result.get("error", "")).lower(),
            "non-local identity failure reason mismatch",
        )

        print("Trusted verifier registry regression checks passed.")
        return 0
    finally:
        sim.NON_LOCAL_MODE = original["NON_LOCAL_MODE"]
        sim.ENFORCE_TRUSTED_VERIFIER_REGISTRY = original[
            "ENFORCE_TRUSTED_VERIFIER_REGISTRY"
        ]
        sim.TRUSTED_VERIFIER_REGISTRY = original["TRUSTED_VERIFIER_REGISTRY"]
        sim.REQUIRE_SIGNED_VERIFIER = original["REQUIRE_SIGNED_VERIFIER"]


if __name__ == "__main__":
    raise SystemExit(main())
