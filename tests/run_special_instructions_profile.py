#!/usr/bin/env python3
"""Validate special-instructions commercial-term profile alignment with runtime and governance scope."""

from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


PROFILE_PATH = PROJECT_ROOT / "conformance" / "special_instructions_profile.v1.json"
COMMERCIAL_TERMS_DOC_PATH = PROJECT_ROOT / "docs" / "governance" / "BOOKING_PLANE_COMMERCIAL_TERMS.md"
SCOPE_PATH = PROJECT_ROOT / "docs" / "governance" / "SCOPE_GUARDRAILS.md"
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
        "newLoadField",
        "bidRequestAcceptanceField",
        "bidRequestAcceptance",
        "executionReportField",
        "normativeConstraints",
        "conformanceRequirements",
    ]:
        _assert(field in profile, f"special instructions profile missing field: {field}")

    _assert(profile["protocol"] == "FAXP", "special instructions profile protocol must be FAXP")
    _assert(
        profile["scope"] == "booking-plane-commercial-terms",
        "special instructions profile scope must be booking-plane-commercial-terms",
    )
    _assert(
        profile.get("newLoadField") == "SpecialInstructions",
        "newLoadField must be SpecialInstructions",
    )
    _assert(
        profile.get("bidRequestAcceptanceField") == "SpecialInstructionsAcceptance",
        "bidRequestAcceptanceField must be SpecialInstructionsAcceptance",
    )
    acceptance = profile.get("bidRequestAcceptance") or {}
    _assert(
        set(acceptance.get("requiredFields") or []) == {"Accepted"},
        "bidRequestAcceptance.requiredFields must equal {Accepted}",
    )
    _assert(
        set(acceptance.get("optionalFields") or []) == {"Exceptions", "Notes"},
        "bidRequestAcceptance.optionalFields must equal {Exceptions, Notes}",
    )
    _assert(
        profile.get("executionReportField") == "SpecialInstructions",
        "executionReportField must be SpecialInstructions",
    )

    constraints = profile.get("normativeConstraints") or {}
    for key in [
        "instructionsAreBookingTerms",
        "explicitAcceptanceRequiredWhenPresent",
        "exceptionsMayCounter",
        "dispatchTrackingOutOfScope",
    ]:
        _assert(constraints.get(key) is True, f"normativeConstraints.{key} must be true")
    _assert(
        constraints.get("counterReasonCode") == "SpecialInstructionsDispute",
        "counterReasonCode must be SpecialInstructionsDispute",
    )

    conformance_requirements = profile.get("conformanceRequirements") or {}
    required_tests = [str(item) for item in conformance_requirements.get("requiredTests") or []]
    required_checks = [str(item) for item in conformance_requirements.get("requiredSuiteChecks") or []]
    _assert(
        set(required_tests) == {
            "tests/run_special_instructions_terms.py",
            "tests/run_special_instructions_profile.py",
        },
        "requiredTests must include special-instructions runtime + profile checks",
    )
    _assert(
        set(required_checks) == {
            "special_instructions_terms",
            "special_instructions_profile",
        },
        "requiredSuiteChecks must include special_instructions_terms and special_instructions_profile",
    )

    for rel_path in required_tests:
        _assert((PROJECT_ROOT / rel_path).exists(), f"required test not found: {rel_path}")

    listed_checks_run = subprocess.run(
        [sys.executable, str(CONFORMANCE_SUITE_PATH), "--list-checks"],
        check=True,
        capture_output=True,
        text=True,
    )
    listed_checks = set(line.strip() for line in listed_checks_run.stdout.splitlines() if line.strip())
    for check_name in required_checks:
        _assert(check_name in listed_checks, f"missing suite check from run_all_checks.py: {check_name}")

    commercial_doc = COMMERCIAL_TERMS_DOC_PATH.read_text(encoding="utf-8")
    _assert(
        "SpecialInstructions" in commercial_doc,
        "booking-plane commercial terms doc must include SpecialInstructions guidance",
    )
    scope_doc = SCOPE_PATH.read_text(encoding="utf-8")
    _assert(
        "stop-level dispatch updates" in scope_doc,
        "scope guardrails must keep dispatch stop-state operations out of core scope",
    )

    print("Special-instructions profile checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
