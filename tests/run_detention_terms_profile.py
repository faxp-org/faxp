#!/usr/bin/env python3
"""Validate detention commercial-terms profile alignment with runtime and scope boundaries."""

from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from faxp_mvp_simulation import (  # noqa: E402
    VALID_DETENTION_LOCATION_EVIDENCE_TYPES,
    VALID_DETENTION_RATE_UNITS,
)


PROFILE_PATH = PROJECT_ROOT / "conformance" / "detention_terms_profile.v1.json"
COMMERCIAL_TERMS_DOC_PATH = PROJECT_ROOT / "docs" / "governance" / "BOOKING_PLANE_COMMERCIAL_TERMS.md"
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
        "detentionTermFields",
        "rateUnits",
        "locationEvidenceTypes",
        "normativeConstraints",
        "conformanceRequirements",
    ]:
        _assert(field in profile, f"detention profile missing field: {field}")

    _assert(profile["protocol"] == "FAXP", "detention profile protocol must be FAXP")
    _assert(
        profile["scope"] == "booking-plane-commercial-terms",
        "detention profile scope must be booking-plane-commercial-terms",
    )

    detention_term_fields = profile.get("detentionTermFields") or {}
    _assert(
        {str(item) for item in detention_term_fields.get("required") or []}
        == {"GracePeriodMinutes", "RateAmount", "RateUnit"},
        "detentionTermFields.required must be GracePeriodMinutes, RateAmount, and RateUnit",
    )
    optional_fields = {str(item) for item in detention_term_fields.get("optional") or []}
    for field in [
        "BillingIncrementMinutes",
        "RequiresDelayNotice",
        "RequiresLocationEvidence",
        "LocationEvidenceType",
        "Notes",
    ]:
        _assert(field in optional_fields, f"detentionTermFields.optional missing: {field}")

    _assert(
        set(profile.get("rateUnits") or []) == set(VALID_DETENTION_RATE_UNITS),
        "rateUnits must match VALID_DETENTION_RATE_UNITS",
    )
    _assert(
        set(profile.get("locationEvidenceTypes") or []) == set(VALID_DETENTION_LOCATION_EVIDENCE_TYPES),
        "locationEvidenceTypes must match VALID_DETENTION_LOCATION_EVIDENCE_TYPES",
    )

    constraints = profile.get("normativeConstraints") or {}
    for key in [
        "detentionTermsRequiredForDetentionType",
        "detentionTermsOnlyAllowedForDetentionType",
        "locationEvidenceTypeRequiredWhenLocationEvidenceRequired",
        "bookingPlaneOnly",
        "settlementExecutionOutOfScope",
    ]:
        _assert(constraints.get(key) is True, f"normativeConstraints.{key} must be true")

    conformance_requirements = profile.get("conformanceRequirements") or {}
    required_tests = [str(item) for item in conformance_requirements.get("requiredTests") or []]
    required_checks = [str(item) for item in conformance_requirements.get("requiredSuiteChecks") or []]
    _assert(
        required_tests == ["tests/run_detention_terms_profile.py"],
        "detention profile requiredTests must include only tests/run_detention_terms_profile.py",
    )
    _assert(
        required_checks == ["detention_terms_profile"],
        "detention profile requiredSuiteChecks must include only detention_terms_profile",
    )

    listed_checks_run = subprocess.run(
        [sys.executable, str(CONFORMANCE_SUITE_PATH), "--list-checks"],
        check=True,
        capture_output=True,
        text=True,
    )
    listed_checks = set(line.strip() for line in listed_checks_run.stdout.splitlines() if line.strip())
    for check_name in required_checks:
        _assert(check_name in listed_checks, f"missing suite check from run_all_checks.py: {check_name}")

    commercial_terms_doc = COMMERCIAL_TERMS_DOC_PATH.read_text(encoding="utf-8")
    _assert(
        "Detention commercial policy terms as booking metadata" in commercial_terms_doc,
        "booking-plane commercial terms doc must include detention booking metadata text",
    )
    _assert(
        "proof adjudication remains external" in commercial_terms_doc,
        "booking-plane commercial terms doc must keep adjudication out of core scope",
    )

    print("Detention terms profile checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
