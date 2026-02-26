#!/usr/bin/env python3
"""Validate driver-configuration profile alignment with runtime and governance scope."""

from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from faxp_mvp_simulation import VALID_DRIVER_CONFIGURATIONS  # noqa: E402


PROFILE_PATH = PROJECT_ROOT / "conformance" / "driver_configuration_profile.v1.json"
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
        "newTruckField",
        "searchFilterField",
        "bidRequestAcceptanceField",
        "bidRequestAcceptance",
        "executionReportField",
        "normativeConstraints",
        "conformanceRequirements",
    ]:
        _assert(field in profile, f"driver configuration profile missing field: {field}")

    _assert(profile["protocol"] == "FAXP", "driver configuration profile protocol must be FAXP")
    _assert(
        profile["scope"] == "booking-plane-commercial-terms",
        "driver configuration profile scope must be booking-plane-commercial-terms",
    )
    _assert(profile.get("newLoadField") == "DriverConfiguration", "newLoadField must be DriverConfiguration")
    _assert(profile.get("newTruckField") == "DriverConfiguration", "newTruckField must be DriverConfiguration")
    _assert(
        profile.get("searchFilterField") == "RequiredDriverConfiguration",
        "searchFilterField must be RequiredDriverConfiguration",
    )
    _assert(
        profile.get("bidRequestAcceptanceField") == "DriverConfigurationAcceptance",
        "bidRequestAcceptanceField must be DriverConfigurationAcceptance",
    )
    acceptance = profile.get("bidRequestAcceptance") or {}
    _assert(
        set(acceptance.get("requiredFields") or []) == {"Accepted"},
        "bidRequestAcceptance.requiredFields must equal {Accepted}",
    )
    _assert(
        set(acceptance.get("optionalFields") or []) == {"DriverConfiguration", "Notes"},
        "bidRequestAcceptance.optionalFields must equal {DriverConfiguration, Notes}",
    )
    _assert(profile.get("executionReportField") == "DriverTerms", "executionReportField must be DriverTerms")

    constraints = profile.get("normativeConstraints") or {}
    for key in [
        "driverConfigurationEnumLocked",
        "explicitAcceptanceRequiredWhenPresent",
        "configurationMismatchMayCounter",
        "driverAssignmentExecutionOutOfScope",
    ]:
        _assert(constraints.get(key) is True, f"normativeConstraints.{key} must be true")
    _assert(
        constraints.get("counterReasonCode") == "DriverConfigurationDispute",
        "counterReasonCode must be DriverConfigurationDispute",
    )

    conformance_requirements = profile.get("conformanceRequirements") or {}
    required_tests = [str(item) for item in conformance_requirements.get("requiredTests") or []]
    required_checks = [str(item) for item in conformance_requirements.get("requiredSuiteChecks") or []]
    _assert(
        set(required_tests) == {
            "tests/run_driver_configuration_terms.py",
            "tests/run_driver_configuration_profile.py",
        },
        "requiredTests must include driver configuration runtime + profile checks",
    )
    _assert(
        set(required_checks) == {
            "driver_configuration_terms",
            "driver_configuration_profile",
        },
        "requiredSuiteChecks must include driver configuration checks",
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
        "DriverConfiguration" in commercial_doc,
        "booking-plane commercial terms doc must include DriverConfiguration guidance",
    )
    scope_doc = SCOPE_PATH.read_text(encoding="utf-8")
    _assert(
        "driver assignment" in scope_doc,
        "scope guardrails must keep driver assignment out of core scope",
    )

    _assert(VALID_DRIVER_CONFIGURATIONS == {"Single", "Team"}, "driver configuration enum drifted")

    print("Driver configuration profile checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
