#!/usr/bin/env python3
"""Validate operational handoff profile alignment with runtime and scope guardrails."""

from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = PROJECT_ROOT / "conformance" / "operational_handoff_profile.v1.json"
RFC_PATH = PROJECT_ROOT / "docs" / "rfc" / "RFC-v0.3-operational-handoff-metadata.md"
SCOPE_PATH = PROJECT_ROOT / "docs" / "governance" / "SCOPE_GUARDRAILS.md"
HANDOFF_DOC_PATH = PROJECT_ROOT / "docs" / "governance" / "VERIFICATION_RESPONSIBILITY_MODEL.md"
CONFORMANCE_SUITE_PATH = PROJECT_ROOT / "conformance" / "run_all_checks.py"


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
        "executionReportField",
        "bookingIdentityAssumptions",
        "operationalHandoff",
        "normativeConstraints",
        "conformanceRequirements",
    ]:
        _assert(field in profile, f"operational handoff profile missing field: {field}")

    _assert(profile["protocol"] == "FAXP", "operational handoff profile protocol must be FAXP")
    _assert(
        profile["scope"] == "booking-plane-operational-handoff",
        "operational handoff profile scope must be booking-plane-operational-handoff",
    )
    _assert(
        profile.get("executionReportField") == "OperationalHandoff",
        "executionReportField must be OperationalHandoff",
    )

    identity = profile.get("bookingIdentityAssumptions") or {}
    _assert(
        set(identity.get("envelopeFields") or []) == {"From", "To"},
        "bookingIdentityAssumptions.envelopeFields must equal {From, To}",
    )
    _assert(
        set(identity.get("executionReportFields") or []) == {"LoadID|TruckID", "ContractID"},
        "bookingIdentityAssumptions.executionReportFields drifted from runtime contract",
    )
    _assert(
        identity.get("optionalCorrelationField") == "LoadReferenceNumbers",
        "optionalCorrelationField must be LoadReferenceNumbers",
    )

    handoff = profile.get("operationalHandoff") or {}
    _assert(
        set(handoff.get("requiredFields") or [])
        == {"OperationalReference", "SystemOfRecordType", "SystemOfRecordRef", "SetupStatus"},
        "requiredFields drifted from runtime contract",
    )
    _assert(
        set(handoff.get("optionalFields") or [])
        == {"HandoffEndpointType", "HandoffEndpointRef", "SupportedHandoffActions"},
        "optionalFields drifted from runtime contract",
    )

    constraints = profile.get("normativeConstraints") or {}
    for key in [
        "routingIntentOnly",
        "bookingIdentityMustRemainExplicit",
        "manualFallbackRemainsConformant",
        "dispatchPacketContentOutOfScope",
        "operationalExecutionStateOutOfScope",
        "setupStatusMayDriveAutomationPolicy",
    ]:
        _assert(constraints.get(key) is True, f"normativeConstraints.{key} must be true")

    conformance = profile.get("conformanceRequirements") or {}
    required_tests = {str(item) for item in conformance.get("requiredTests") or []}
    required_checks = {str(item) for item in conformance.get("requiredSuiteChecks") or []}
    _assert(
        required_tests
        == {"tests/run_operational_handoff_terms.py", "tests/run_operational_handoff_profile.py"},
        "requiredTests must include runtime + profile handoff checks",
    )
    _assert(
        required_checks == {"operational_handoff_terms", "operational_handoff_profile"},
        "requiredSuiteChecks must include operational_handoff terms/profile checks",
    )

    for rel_path in required_tests:
        _assert((PROJECT_ROOT / rel_path).exists(), f"required test not found: {rel_path}")

    listed_checks_run = subprocess.run(
        [sys.executable, str(CONFORMANCE_SUITE_PATH), "--list-checks"],
        check=True,
        capture_output=True,
        text=True,
    )
    listed_checks = {line.strip() for line in listed_checks_run.stdout.splitlines() if line.strip()}
    for check_name in required_checks:
        _assert(check_name in listed_checks, f"missing suite check from run_all_checks.py: {check_name}")

    rfc_text = RFC_PATH.read_text(encoding="utf-8")
    _assert(
        "required booking identity/reference layer" in rfc_text,
        "RFC must preserve required booking identity/reference language",
    )
    _assert(
        "optional operational routing layer" in rfc_text,
        "RFC must preserve optional operational routing language",
    )

    scope_text = SCOPE_PATH.read_text(encoding="utf-8")
    _assert(
        "Optional post-booking operational handoff metadata may describe neutral routing intent only" in scope_text,
        "scope guardrails must keep operational handoff routing-only",
    )
    handoff_doc = HANDOFF_DOC_PATH.read_text(encoding="utf-8")
    _assert(
        "Existing onboarding/payment/dispatch process executes in TMS/portals." in handoff_doc,
        "verification responsibility doc must preserve external ops handoff flow",
    )

    print("Operational handoff profile checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
