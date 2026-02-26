#!/usr/bin/env python3
"""Validate schedule commitment profile alignment with runtime and governance scope."""

from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


PROFILE_PATH = PROJECT_ROOT / "conformance" / "schedule_terms_profile.v1.json"
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
        "newLoadFields",
        "bidRequestAcceptanceField",
        "scheduleAcceptance",
        "executionReportField",
        "normativeConstraints",
        "conformanceRequirements",
    ]:
        _assert(field in profile, f"schedule profile missing field: {field}")

    _assert(profile["protocol"] == "FAXP", "schedule profile protocol must be FAXP")
    _assert(
        profile["scope"] == "booking-plane-commercial-terms",
        "schedule profile scope must be booking-plane-commercial-terms",
    )

    new_load_fields = profile.get("newLoadFields") or {}
    _assert(
        set(new_load_fields.get("required") or []) == {"PickupEarliest", "PickupLatest"},
        "newLoadFields.required must include pickup range fields",
    )
    _assert(
        set(new_load_fields.get("optional") or [])
        == {"DeliveryEarliest", "DeliveryLatest", "PickupTimeWindow", "DeliveryTimeWindow"},
        "newLoadFields.optional drifted from runtime contract",
    )

    _assert(
        profile.get("bidRequestAcceptanceField") == "ScheduleAcceptance",
        "bidRequestAcceptanceField must be ScheduleAcceptance",
    )
    acceptance = profile.get("scheduleAcceptance") or {}
    _assert(
        set(acceptance.get("requiredFields") or []) == {"Accepted"},
        "scheduleAcceptance.requiredFields must equal {Accepted}",
    )
    _assert(
        set(acceptance.get("optionalFields") or [])
        == {"Exceptions", "PickupTimeWindow", "DeliveryTimeWindow", "Notes"},
        "scheduleAcceptance.optionalFields drifted from runtime contract",
    )
    _assert(
        profile.get("executionReportField") == "ScheduleTerms",
        "executionReportField must be ScheduleTerms",
    )

    constraints = profile.get("normativeConstraints") or {}
    for key in [
        "pickupRangeRequired",
        "deliveryRangePairRequiredWhenPresent",
        "timeWindowSupportsAppointmentOrRange",
        "scheduleDisputeMayCounter",
        "dispatchSchedulingExecutionOutOfScope",
    ]:
        _assert(constraints.get(key) is True, f"normativeConstraints.{key} must be true")
    _assert(
        constraints.get("counterReasonCode") == "ScheduleWindowDispute",
        "counterReasonCode must be ScheduleWindowDispute",
    )

    conformance_requirements = profile.get("conformanceRequirements") or {}
    required_tests = [str(item) for item in conformance_requirements.get("requiredTests") or []]
    required_checks = [str(item) for item in conformance_requirements.get("requiredSuiteChecks") or []]
    _assert(
        set(required_tests) == {"tests/run_schedule_terms.py", "tests/run_schedule_terms_profile.py"},
        "requiredTests must include schedule runtime + profile checks",
    )
    _assert(
        set(required_checks) == {"schedule_terms", "schedule_terms_profile"},
        "requiredSuiteChecks must include schedule_terms and schedule_terms_profile",
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
        "ScheduleAcceptance" in commercial_doc,
        "booking-plane commercial terms doc must include ScheduleAcceptance guidance",
    )
    scope_doc = SCOPE_PATH.read_text(encoding="utf-8")
    _assert(
        "stop-level dispatch updates" in scope_doc,
        "scope guardrails must keep dispatch execution out of core scope",
    )

    print("Schedule commitment profile checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
