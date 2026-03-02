#!/usr/bin/env python3
"""Validate builder integration profile consistency and discoverability."""

from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = PROJECT_ROOT / "conformance" / "builder_integration_profile.v1.json"
DOC_PATH = PROJECT_ROOT / "docs" / "adapters" / "BUILDER_INTEGRATION_PROFILE.md"
PLAYBOOK_PATH = PROJECT_ROOT / "docs" / "governance" / "CERTIFICATION_PLAYBOOK.md"
HANDOFF_PATH = PROJECT_ROOT / "docs" / "adapters" / "ADAPTER_IMPLEMENTER_HANDOFF.md"
DOC_INDEX_PATH = PROJECT_ROOT / "docs" / "INDEX.md"
CONFORMANCE_README_PATH = PROJECT_ROOT / "conformance" / "README.md"
SUITE_PATH = PROJECT_ROOT / "conformance" / "run_all_checks.py"

KNOWN_PROFILE_FILES = {
    "booking-identity-profile.v1": "conformance/booking_identity_profile.v1.json",
    "operational-handoff-metadata.v1": "conformance/operational_handoff_profile.v1.json",
    "shipper-orchestration-minimal.v1": "conformance/shipper_orchestration_profile.v1.json",
    "accessorial_terms_profile.v1": "conformance/accessorial_terms_profile.v1.json",
    "detention_terms_profile.v1": "conformance/detention_terms_profile.v1.json",
    "multi_stop_terms_profile.v1": "conformance/multi_stop_terms_profile.v1.json",
    "special_instructions_profile.v1": "conformance/special_instructions_profile.v1.json",
    "schedule_terms_profile.v1": "conformance/schedule_terms_profile.v1.json",
    "driver_configuration_profile.v1": "conformance/driver_configuration_profile.v1.json",
    "load_reference_numbers_profile.v1": "conformance/load_reference_numbers_profile.v1.json",
    "equipment_profile.v1": "conformance/equipment_profile.v1.json",
    "rate_model_profile.v1": "conformance/rate_model_profile.v1.json",
}


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    _assert(isinstance(payload, dict), f"{path.name} must contain a JSON object.")
    return payload


def main() -> int:
    profile = _load_json(PROFILE_PATH)

    for field in [
        "profileVersion",
        "profileId",
        "protocol",
        "scope",
        "claimSurface",
        "minimumClaimRequirements",
        "claimMatrix",
        "normativeConstraints",
        "conformanceRequirements",
    ]:
        _assert(field in profile, f"builder integration profile missing field: {field}")

    _assert(profile["protocol"] == "FAXP", "builder integration profile protocol must be FAXP")
    _assert(
        profile["scope"] == "booking-plane-builder-integration",
        "builder integration profile scope mismatch",
    )

    claim_surface = profile.get("claimSurface") or {}
    _assert(
        set(claim_surface.get("supportedRoles") or []) == {"Broker", "Carrier", "Shipper"},
        "supportedRoles must equal {Broker, Carrier, Shipper}",
    )
    _assert(
        set(claim_surface.get("supportedFlows") or []) == {"LoadCentric", "TruckCapacity", "ShipperOrigin"},
        "supportedFlows must equal {LoadCentric, TruckCapacity, ShipperOrigin}",
    )
    _assert(
        set(claim_surface.get("verificationIntegrationPatterns") or [])
        == {"vendor-direct", "implementer-adapter", "authority-only", "self-attested"},
        "verificationIntegrationPatterns drifted from governance model",
    )
    _assert(
        set(claim_surface.get("optionalInteropTracks") or []) == {"A2A", "MCP"},
        "optionalInteropTracks must equal {A2A, MCP}",
    )

    supported_profile_ids = set(claim_surface.get("supportedProfileIds") or [])
    _assert(supported_profile_ids == set(KNOWN_PROFILE_FILES.keys()), "supportedProfileIds drifted from expected booking-plane profiles")
    for rel_path in KNOWN_PROFILE_FILES.values():
        _assert((PROJECT_ROOT / rel_path).exists(), f"referenced profile artifact missing: {rel_path}")

    minimums = profile.get("minimumClaimRequirements") or {}
    for key in [
        "mustDeclareAtLeastOneRole",
        "mustDeclareAtLeastOneFlow",
        "mustDeclareAtLeastOneVerificationPattern",
        "mustReferenceConformanceEvidence",
        "allClaimedProfileIdsMustBeKnown",
    ]:
        _assert(minimums.get(key) is True, f"minimumClaimRequirements.{key} must be true")

    claim_matrix = profile.get("claimMatrix") or {}
    for key in ["BrokerBookingPlane", "CarrierBookingPlane", "ShipperOriginOptional"]:
        _assert(key in claim_matrix, f"claimMatrix missing section: {key}")

    constraints = profile.get("normativeConstraints") or {}
    for key in [
        "faxpCoreRemainsBookingPlaneOnly",
        "noFaxpHostedOperationsRequired",
        "verificationProviderNeutralityRequired",
        "claimedCapabilitiesMustMapToPassingChecks",
        "undeclaredCapabilitiesMustNotBeImplied",
    ]:
        _assert(constraints.get(key) is True, f"normativeConstraints.{key} must be true")

    conformance = profile.get("conformanceRequirements") or {}
    required_docs = {str(item) for item in conformance.get("requiredDocs") or []}
    required_tests = {str(item) for item in conformance.get("requiredTests") or []}
    required_checks = {str(item) for item in conformance.get("requiredSuiteChecks") or []}
    _assert(
        required_docs
        == {
            "docs/adapters/BUILDER_INTEGRATION_PROFILE.md",
            "docs/adapters/ADAPTER_IMPLEMENTER_HANDOFF.md",
            "docs/governance/CERTIFICATION_PLAYBOOK.md",
        },
        "requiredDocs must include explainer, handoff, and playbook",
    )
    _assert(required_tests == {"tests/run_builder_integration_profile.py"}, "requiredTests must include profile test")
    _assert(required_checks == {"builder_integration_profile"}, "requiredSuiteChecks must include builder_integration_profile")

    for rel_path in required_docs | required_tests:
        _assert((PROJECT_ROOT / rel_path).exists(), f"required path not found: {rel_path}")

    doc_text = DOC_PATH.read_text(encoding="utf-8")
    _assert("standard capability sheet for builders" in doc_text, "builder explainer must preserve plain-English framing")
    playbook_text = PLAYBOOK_PATH.read_text(encoding="utf-8")
    _assert("builder integration profile" in playbook_text.lower(), "playbook must reference builder integration profile")
    handoff_text = HANDOFF_PATH.read_text(encoding="utf-8")
    _assert("builder integration profile" in handoff_text.lower(), "adapter handoff doc must reference builder integration profile")
    index_text = DOC_INDEX_PATH.read_text(encoding="utf-8")
    _assert("docs/adapters/BUILDER_INTEGRATION_PROFILE.md" in index_text, "docs index must include builder explainer")
    conformance_readme = CONFORMANCE_README_PATH.read_text(encoding="utf-8")
    _assert("builder_integration_profile.v1.json" in conformance_readme, "conformance README must list builder profile")

    listed_checks_run = subprocess.run(
        [sys.executable, str(SUITE_PATH), "--list-checks"],
        check=True,
        capture_output=True,
        text=True,
    )
    listed_checks = {line.strip() for line in listed_checks_run.stdout.splitlines() if line.strip()}
    for check_name in required_checks:
        _assert(check_name in listed_checks, f"missing suite check from run_all_checks.py: {check_name}")

    print("Builder integration profile checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
