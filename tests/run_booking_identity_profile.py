#!/usr/bin/env python3
"""Validate booking identity profile alignment with runtime and roadmap intent."""

from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = PROJECT_ROOT / "conformance" / "booking_identity_profile.v1.json"
ROADMAP_PATH = PROJECT_ROOT / "docs" / "roadmap" / "PHASE_2_IMPLEMENTATION_ROADMAP.md"
RFC_PATH = PROJECT_ROOT / "docs" / "rfc" / "RFC-v0.3-operational-handoff-metadata.md"
CONFORMANCE_SUITE_PATH = PROJECT_ROOT / "conformance" / "run_all_checks.py"
SCHEMA_PATHS = [
    PROJECT_ROOT / "faxp.schema.json",
    PROJECT_ROOT / "faxp.v0.2.schema.json",
]


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
        "envelopeIdentity",
        "bookingIdentifiers",
        "normativeConstraints",
        "conformanceRequirements",
    ]:
        _assert(field in profile, f"booking identity profile missing field: {field}")

    _assert(profile["protocol"] == "FAXP", "booking identity profile protocol must be FAXP")
    _assert(profile["scope"] == "booking-plane-identity", "booking identity profile scope mismatch")

    envelope_identity = profile.get("envelopeIdentity") or {}
    _assert(
        set(envelope_identity.get("partyFields") or []) == {"From", "To"},
        "partyFields must equal {From, To}",
    )
    _assert(
        set(envelope_identity.get("agentIdFields") or []) == {"FromAgentID", "ToAgentID"},
        "agentIdFields must equal {FromAgentID, ToAgentID}",
    )
    _assert(
        envelope_identity.get("nonLocalModeRequiresAgentIds") is True,
        "nonLocalModeRequiresAgentIds must be true",
    )
    _assert(
        envelope_identity.get("agentIdsMustBindToPartyNames") is True,
        "agentIdsMustBindToPartyNames must be true",
    )

    booking_identifiers = profile.get("bookingIdentifiers") or {}
    _assert(
        set(booking_identifiers.get("executionReportRequiredFields") or []) == {"ContractID", "LoadID|TruckID"},
        "executionReportRequiredFields drifted from runtime contract",
    )
    _assert(
        booking_identifiers.get("optionalCorrelationField") == "LoadReferenceNumbers",
        "optionalCorrelationField must be LoadReferenceNumbers",
    )
    _assert(
        booking_identifiers.get("contractIdIsCanonicalBookingIdentifier") is True,
        "contractIdIsCanonicalBookingIdentifier must be true",
    )

    constraints = profile.get("normativeConstraints") or {}
    for key in [
        "existingEnvelopeFieldsRemainPrimaryIdentitySurface",
        "executionReportMustRemainOperationallyAttributable",
        "loadReferenceNumbersRemainOptionalCorrelationMetadata",
        "noGlobalParticipantRegistry",
        "noUniversalTrustScore",
    ]:
        _assert(constraints.get(key) is True, f"normativeConstraints.{key} must be true")

    conformance = profile.get("conformanceRequirements") or {}
    required_tests = {str(item) for item in conformance.get("requiredTests") or []}
    required_checks = {str(item) for item in conformance.get("requiredSuiteChecks") or []}
    _assert(
        required_tests == {"tests/run_booking_identity_terms.py", "tests/run_booking_identity_profile.py"},
        "requiredTests must include runtime + profile booking identity checks",
    )
    _assert(
        required_checks == {"booking_identity_terms", "booking_identity_profile"},
        "requiredSuiteChecks must include booking identity terms/profile checks",
    )

    for rel_path in required_tests:
        _assert((PROJECT_ROOT / rel_path).exists(), f"required test not found: {rel_path}")

    for schema_path in SCHEMA_PATHS:
        schema = _load_json(schema_path)
        properties = schema.get("properties") or {}
        _assert("FromAgentID" in properties, f"{schema_path.name} missing FromAgentID property")
        _assert("ToAgentID" in properties, f"{schema_path.name} missing ToAgentID property")

    roadmap_text = ROADMAP_PATH.read_text(encoding="utf-8")
    _assert(
        "clearer guidance for `AgentID`, counterparty identity, and booking references" in roadmap_text,
        "Phase 2 roadmap must continue to call out AgentID and booking references",
    )
    rfc_text = RFC_PATH.read_text(encoding="utf-8")
    _assert(
        "booking identity/reference data remains required" in rfc_text,
        "operational handoff RFC must preserve booking identity requirement",
    )

    listed_checks_run = subprocess.run(
        [sys.executable, str(CONFORMANCE_SUITE_PATH), "--list-checks"],
        check=True,
        capture_output=True,
        text=True,
    )
    listed_checks = {line.strip() for line in listed_checks_run.stdout.splitlines() if line.strip()}
    for check_name in required_checks:
        _assert(check_name in listed_checks, f"missing suite check from run_all_checks.py: {check_name}")

    print("Booking identity profile checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
