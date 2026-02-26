#!/usr/bin/env python3
"""Validate equipment taxonomy profile alignment with runtime and governance scope."""

from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from faxp_mvp_simulation import (  # noqa: E402
    VALID_EQUIPMENT_CLASSES,
    VALID_EQUIPMENT_SUBCLASSES,
    VALID_EQUIPMENT_TAGS,
)


PROFILE_PATH = PROJECT_ROOT / "conformance" / "equipment_profile.v1.json"
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
        "equipmentFields",
        "searchFilterFields",
        "bidAcceptanceField",
        "bidAcceptance",
        "executionReportField",
        "normativeConstraints",
        "conformanceRequirements",
    ]:
        _assert(field in profile, f"equipment profile missing field: {field}")

    _assert(profile["protocol"] == "FAXP", "equipment profile protocol must be FAXP")
    _assert(
        profile["scope"] == "booking-plane-commercial-terms",
        "equipment profile scope must be booking-plane-commercial-terms",
    )

    equipment_fields = profile.get("equipmentFields") or {}
    _assert(
        set(equipment_fields.get("required") or []) == {"EquipmentType"},
        "equipmentFields.required must equal {EquipmentType}",
    )
    _assert(
        set(equipment_fields.get("optional") or [])
        == {
            "EquipmentClass",
            "EquipmentSubClass",
            "EquipmentTags",
            "TrailerCount",
            "EquipmentSpecialDescription",
        },
        "equipmentFields.optional drifted from runtime contract",
    )
    _assert(
        set(profile.get("searchFilterFields") or [])
        == {
            "EquipmentClass",
            "EquipmentSubClass",
            "RequiredEquipmentTags",
            "TrailerLengthMin",
            "TrailerLengthMax",
        },
        "searchFilterFields drifted from runtime contract",
    )
    _assert(
        profile.get("bidAcceptanceField") == "EquipmentAcceptance",
        "bidAcceptanceField must be EquipmentAcceptance",
    )
    bid_acceptance = profile.get("bidAcceptance") or {}
    _assert(
        set(bid_acceptance.get("requiredFields") or []) == {"Accepted"},
        "bidAcceptance.requiredFields must equal {Accepted}",
    )
    _assert(
        set(bid_acceptance.get("optionalFields") or [])
        == {
            "EquipmentClass",
            "EquipmentSubClass",
            "EquipmentTags",
            "TrailerLength",
            "TrailerLengthMin",
            "TrailerLengthMax",
            "TrailerCount",
            "Notes",
        },
        "bidAcceptance.optionalFields drifted from runtime contract",
    )
    _assert(
        profile.get("executionReportField") == "EquipmentTerms",
        "executionReportField must be EquipmentTerms",
    )

    constraints = profile.get("normativeConstraints") or {}
    for key in [
        "primaryClassSupported",
        "secondarySubclassSupported",
        "tagBasedCapabilitySupported",
        "typeAliasNormalizationSupported",
        "tagInferenceFromSubclassSupported",
        "specialClassRequiresDescription",
        "equipmentMismatchMayCounter",
        "dispatchAssetAssignmentOutOfScope",
    ]:
        _assert(constraints.get(key) is True, f"normativeConstraints.{key} must be true")
    _assert(
        constraints.get("counterReasonCode") == "EquipmentCompatibilityDispute",
        "counterReasonCode must be EquipmentCompatibilityDispute",
    )

    conformance_requirements = profile.get("conformanceRequirements") or {}
    required_tests = [str(item) for item in conformance_requirements.get("requiredTests") or []]
    required_checks = [str(item) for item in conformance_requirements.get("requiredSuiteChecks") or []]
    _assert(
        set(required_tests) == {"tests/run_equipment_terms.py", "tests/run_equipment_profile.py"},
        "requiredTests must include equipment runtime + profile checks",
    )
    _assert(
        set(required_checks) == {"equipment_terms", "equipment_profile"},
        "requiredSuiteChecks must include equipment_terms and equipment_profile",
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

    _assert(VALID_EQUIPMENT_CLASSES, "VALID_EQUIPMENT_CLASSES must be non-empty")
    _assert(VALID_EQUIPMENT_SUBCLASSES, "VALID_EQUIPMENT_SUBCLASSES must be non-empty")
    _assert(VALID_EQUIPMENT_TAGS, "VALID_EQUIPMENT_TAGS must be non-empty")

    commercial_doc = COMMERCIAL_TERMS_DOC_PATH.read_text(encoding="utf-8")
    _assert(
        "EquipmentClass" in commercial_doc,
        "booking-plane commercial terms doc must include EquipmentClass guidance",
    )
    scope_doc = SCOPE_PATH.read_text(encoding="utf-8")
    _assert(
        "driver assignment" in scope_doc,
        "scope guardrails must keep dispatch asset assignment out of scope",
    )

    print("Equipment taxonomy profile checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
