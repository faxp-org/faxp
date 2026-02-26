#!/usr/bin/env python3
"""Validate load-reference-number profile alignment with runtime and governance scope."""

from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


PROFILE_PATH = PROJECT_ROOT / "conformance" / "load_reference_numbers_profile.v1.json"
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
        "executionReportField",
        "loadReferenceNumbers",
        "normativeConstraints",
        "conformanceRequirements",
    ]:
        _assert(field in profile, f"load reference profile missing field: {field}")

    _assert(profile["protocol"] == "FAXP", "load reference profile protocol must be FAXP")
    _assert(
        profile["scope"] == "booking-plane-commercial-terms",
        "load reference profile scope must be booking-plane-commercial-terms",
    )
    _assert(
        profile.get("newLoadField") == "LoadReferenceNumbers",
        "newLoadField must be LoadReferenceNumbers",
    )
    _assert(
        profile.get("executionReportField") == "LoadReferenceNumbers",
        "executionReportField must be LoadReferenceNumbers",
    )

    terms = profile.get("loadReferenceNumbers") or {}
    _assert(
        set(terms.get("optionalFields") or [])
        == {"PrimaryReferenceNumber", "SecondaryReferenceNumber", "Additional"},
        "loadReferenceNumbers.optionalFields drifted from runtime contract",
    )
    _assert(
        set(terms.get("additionalReferenceFields") or [])
        == {"ReferenceType", "ReferenceValue", "IssuerParty"},
        "additionalReferenceFields drifted from runtime contract",
    )

    constraints = profile.get("normativeConstraints") or {}
    for key in [
        "loadIdRemainsCanonicalProtocolIdentifier",
        "referenceNumbersAreExternalCorrelationMetadata",
        "atLeastOneReferenceRequiredWhenObjectPresent",
        "documentSettlementWorkflowsOutOfScope",
    ]:
        _assert(constraints.get(key) is True, f"normativeConstraints.{key} must be true")

    conformance_requirements = profile.get("conformanceRequirements") or {}
    required_tests = [str(item) for item in conformance_requirements.get("requiredTests") or []]
    required_checks = [str(item) for item in conformance_requirements.get("requiredSuiteChecks") or []]
    _assert(
        set(required_tests) == {
            "tests/run_load_reference_numbers_terms.py",
            "tests/run_load_reference_numbers_profile.py",
        },
        "requiredTests must include load reference runtime + profile checks",
    )
    _assert(
        set(required_checks) == {
            "load_reference_numbers_terms",
            "load_reference_numbers_profile",
        },
        "requiredSuiteChecks must include load reference checks",
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
        "LoadReferenceNumbers" in commercial_doc,
        "booking-plane commercial terms doc must include LoadReferenceNumbers guidance",
    )
    scope_doc = SCOPE_PATH.read_text(encoding="utf-8")
    _assert(
        "payment rails" in scope_doc,
        "scope guardrails must keep settlement/document workflows out of core scope",
    )

    print("Load reference number profile checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
