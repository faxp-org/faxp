#!/usr/bin/env python3
"""Validate accessorial commercial-terms profile alignment with runtime and governance scope."""

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
    VALID_ACCESSORIAL_EVIDENCE_TYPES,
    VALID_ACCESSORIAL_PARTIES,
    VALID_ACCESSORIAL_PRICING_MODES,
    VALID_ACCESSORIAL_STATUSES,
)


PROFILE_PATH = PROJECT_ROOT / "conformance" / "accessorial_terms_profile.v1.json"
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
        "requiredPolicyFields",
        "termFields",
        "pricingModes",
        "partyRoles",
        "evidenceTypes",
        "detentionTerms",
        "entryStatuses",
        "normativeConstraints",
        "conformanceRequirements",
    ]:
        _assert(field in profile, f"accessorial profile missing field: {field}")

    _assert(profile["protocol"] == "FAXP", "accessorial profile protocol must be FAXP")
    _assert(
        profile["scope"] == "booking-plane-commercial-terms",
        "accessorial profile scope must be booking-plane-commercial-terms",
    )

    required_policy_fields = {str(item) for item in profile.get("requiredPolicyFields") or []}
    _assert(
        required_policy_fields == {"AllowedTypes", "RequiresApproval", "Currency"},
        "requiredPolicyFields drifted from runtime contract",
    )

    term_fields = profile.get("termFields") or {}
    _assert(
        {str(item) for item in term_fields.get("required") or []} == {"Type", "PricingMode"},
        "termFields.required must be Type and PricingMode",
    )
    _assert(
        "DetentionTerms" in {str(item) for item in term_fields.get("optional") or []},
        "termFields.optional must include DetentionTerms",
    )

    detention_terms = profile.get("detentionTerms") or {}
    _assert(
        {str(item) for item in detention_terms.get("required") or []}
        == {"GracePeriodMinutes", "RateAmount", "RateUnit"},
        "detentionTerms.required must be GracePeriodMinutes, RateAmount, and RateUnit",
    )
    _assert(
        set(detention_terms.get("rateUnits") or []) == set(VALID_DETENTION_RATE_UNITS),
        "detentionTerms.rateUnits must match VALID_DETENTION_RATE_UNITS",
    )
    _assert(
        set(detention_terms.get("locationEvidenceTypes") or [])
        == set(VALID_DETENTION_LOCATION_EVIDENCE_TYPES),
        "detentionTerms.locationEvidenceTypes must match VALID_DETENTION_LOCATION_EVIDENCE_TYPES",
    )

    _assert(
        set(profile.get("pricingModes") or []) == set(VALID_ACCESSORIAL_PRICING_MODES),
        "pricingModes must match VALID_ACCESSORIAL_PRICING_MODES",
    )
    _assert(
        set(profile.get("partyRoles") or []) == set(VALID_ACCESSORIAL_PARTIES),
        "partyRoles must match VALID_ACCESSORIAL_PARTIES",
    )
    _assert(
        set(profile.get("evidenceTypes") or []) == set(VALID_ACCESSORIAL_EVIDENCE_TYPES),
        "evidenceTypes must match VALID_ACCESSORIAL_EVIDENCE_TYPES",
    )
    _assert(
        set(profile.get("entryStatuses") or []) == set(VALID_ACCESSORIAL_STATUSES),
        "entryStatuses must match VALID_ACCESSORIAL_STATUSES",
    )

    constraints = profile.get("normativeConstraints") or {}
    for key in [
        "nonUsdNotSupportedInV011",
        "passThroughRequiresPayerPayee",
        "reimbursableRequiresPayerPayee",
        "tbdRequiresPayerPayee",
        "evidenceTypeRequiredWhenEvidenceRequired",
        "detentionTermsRequiredForDetentionType",
        "detentionTermsOnlyAllowedForDetentionType",
        "locationEvidenceTypeRequiredWhenLocationEvidenceRequired",
        "maxAmountNotRequired",
        "settlementExecutionOutOfScope",
    ]:
        _assert(constraints.get(key) is True, f"normativeConstraints.{key} must be true")

    conformance_requirements = profile.get("conformanceRequirements") or {}
    required_tests = [str(item) for item in conformance_requirements.get("requiredTests") or []]
    required_checks = [str(item) for item in conformance_requirements.get("requiredSuiteChecks") or []]
    _assert(
        "tests/run_accessorial_terms.py" in required_tests,
        "accessorial profile must require tests/run_accessorial_terms.py",
    )
    _assert(
        "tests/run_accessorial_terms_profile.py" in required_tests,
        "accessorial profile must require tests/run_accessorial_terms_profile.py",
    )
    _assert(
        set(required_checks) == {"accessorial_terms", "accessorial_terms_profile"},
        "requiredSuiteChecks must include accessorial_terms and accessorial_terms_profile",
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

    scope_doc = SCOPE_PATH.read_text(encoding="utf-8")
    _assert(
        "Accessorials in protocol core are booking-time commercial terms/addenda only" in scope_doc,
        "scope guardrails must explicitly state booking-plane-only accessorial semantics",
    )
    _assert(
        "settlement/payment execution remain out of scope" in scope_doc,
        "scope guardrails must explicitly keep settlement out of scope",
    )

    print("Accessorial terms profile checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
