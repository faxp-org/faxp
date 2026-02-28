#!/usr/bin/env python3
"""Validate adapter certification profile v2 artifact and transition semantics."""

from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = PROJECT_ROOT / "conformance" / "adapter_certification_profile.v2.json"
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
        "supportedLegacyProfileVersions",
        "deprecationPolicy",
        "evidenceClasses",
        "tierRequirements",
        "registryRequirements",
        "governanceRules",
        "conformanceRequirements",
    ]:
        _assert(field in profile, f"adapter certification profile v2 missing field: {field}")

    _assert(profile["protocol"] == "FAXP", "protocol must be FAXP")
    _assert(profile["profileVersion"] == "2.0.0", "profileVersion must be 2.0.0")

    legacy_versions = [str(item) for item in profile.get("supportedLegacyProfileVersions") or []]
    _assert("1.x" in legacy_versions, "supportedLegacyProfileVersions must include 1.x")

    deprecation = profile.get("deprecationPolicy") or {}
    _assert(
        deprecation.get("v1AcceptedDuringTransition") is True,
        "deprecationPolicy.v1AcceptedDuringTransition must be true",
    )
    _assert(
        deprecation.get("v1RetirementRequiresFutureGovernanceApproval") is True,
        "deprecationPolicy.v1RetirementRequiresFutureGovernanceApproval must be true",
    )

    evidence_classes = profile.get("evidenceClasses") or {}
    expected_classes = {
        "SchemaEvidence",
        "SecurityEvidence",
        "OperationalEvidence",
        "InteropEvidence",
    }
    _assert(set(evidence_classes.keys()) == expected_classes, "evidenceClasses set mismatch")
    for class_name in expected_classes:
        class_payload = evidence_classes.get(class_name) or {}
        refs = [str(item) for item in class_payload.get("requiredRefs") or []]
        _assert(refs, f"{class_name} requiredRefs must be non-empty")

    tiers = profile.get("tierRequirements") or {}
    _assert(
        set(tiers.keys()) == {"SelfAttested", "Conformant", "TrustedProduction"},
        "tierRequirements must define SelfAttested/Conformant/TrustedProduction",
    )
    _assert(
        tiers["SelfAttested"].get("requiredEvidenceClasses") == ["SchemaEvidence"],
        "SelfAttested must require SchemaEvidence only",
    )
    _assert(
        tiers["Conformant"].get("requiredEvidenceClasses") == ["SchemaEvidence", "SecurityEvidence"],
        "Conformant requiredEvidenceClasses mismatch",
    )
    trusted_required = tiers["TrustedProduction"].get("requiredEvidenceClasses") or []
    _assert(
        trusted_required == ["SchemaEvidence", "SecurityEvidence", "OperationalEvidence"],
        "TrustedProduction requiredEvidenceClasses mismatch",
    )
    _assert(
        (tiers["TrustedProduction"].get("optionalEvidenceClasses") or []) == ["InteropEvidence"],
        "TrustedProduction optionalEvidenceClasses must be [InteropEvidence]",
    )
    for tier_name, tier_payload in tiers.items():
        max_age = int(tier_payload.get("maximumEvidenceAgeDays") or 0)
        _assert(max_age == 30, f"{tier_name} maximumEvidenceAgeDays must be 30")

    registry = profile.get("registryRequirements") or {}
    required_metadata = [str(item) for item in registry.get("requiredMetadataFields") or []]
    for field in [
        "adapterProfileVersion",
        "evidenceFreshnessCheckedAt",
        "keyLifecyclePolicyRef",
        "decisionRecordRef",
    ]:
        _assert(field in required_metadata, f"registryRequirements missing metadata field: {field}")

    decision_statuses = {str(item) for item in registry.get("decisionRecordRequiredForStatuses") or []}
    _assert(
        decision_statuses == {"Active", "Suspended", "Revoked"},
        "decisionRecordRequiredForStatuses must be Active/Suspended/Revoked",
    )

    rules = profile.get("governanceRules") or {}
    for field in [
        "builderHostedArchitectureRequired",
        "mandatorySuiteLinkageRequired",
        "missingMandatoryEvidenceFailsClosed",
    ]:
        _assert(rules.get(field) is True, f"governanceRules.{field} must be true")

    conformance = profile.get("conformanceRequirements") or {}
    required_tests = {str(item) for item in conformance.get("requiredTests") or []}
    required_checks = {str(item) for item in conformance.get("requiredSuiteChecks") or []}
    _assert(
        required_tests == {"tests/run_adapter_certification_profile_v2.py"},
        "conformanceRequirements.requiredTests must self-reference the v2 test",
    )
    _assert(
        required_checks == {"adapter_certification_profile_v2"},
        "conformanceRequirements.requiredSuiteChecks must contain adapter_certification_profile_v2",
    )

    listed_checks_run = subprocess.run(
        [sys.executable, str(CONFORMANCE_SUITE_PATH), "--list-checks"],
        check=True,
        capture_output=True,
        text=True,
    )
    listed_checks = {line.strip() for line in listed_checks_run.stdout.splitlines() if line.strip()}
    _assert(
        "adapter_certification_profile_v2" in listed_checks,
        "run_all_checks.py missing adapter_certification_profile_v2",
    )

    print("Adapter certification profile v2 checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
