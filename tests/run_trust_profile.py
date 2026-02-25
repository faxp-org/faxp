#!/usr/bin/env python3
"""Validate trust profile artifact and cross-check alignment with runtime and registry policy."""

from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from faxp_mvp_simulation import _normalize_verifier_source  # noqa: E402


TRUST_PROFILE_PATH = PROJECT_ROOT / "conformance" / "trust_profile.v1.json"
VENDOR_PROFILE_PATH = PROJECT_ROOT / "conformance" / "vendor_direct_verifier_profile.v1.json"
REGISTRY_PATH = PROJECT_ROOT / "conformance" / "trusted_verifier_registry.sample.json"
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
    profile = _load_json(TRUST_PROFILE_PATH)
    vendor_profile = _load_json(VENDOR_PROFILE_PATH)
    registry = _load_json(REGISTRY_PATH)

    required_profile_fields = [
        "profileVersion",
        "profileId",
        "protocol",
        "transportSecurity",
        "messageAuthenticity",
        "verifierAttestation",
        "sourceClasses",
        "operationalBoundary",
        "conformanceRequirements",
    ]
    for field in required_profile_fields:
        _assert(field in profile, f"trust profile missing field: {field}")

    _assert(profile["protocol"] == "FAXP", "trust profile protocol must be FAXP")

    transport = profile.get("transportSecurity") or {}
    _assert(
        bool(transport.get("requiredInNonLocal")),
        "transportSecurity.requiredInNonLocal must be true",
    )
    _assert(
        float(str(transport.get("minimumTlsVersion") or "0")) >= 1.2,
        "transportSecurity.minimumTlsVersion must be >= 1.2",
    )

    authenticity = profile.get("messageAuthenticity") or {}
    _assert(
        bool(authenticity.get("requireSignedEnvelope")),
        "messageAuthenticity.requireSignedEnvelope must be true",
    )
    envelope_algorithms = {str(item) for item in authenticity.get("allowedSignatureAlgorithms") or []}
    _assert(
        {"HMAC_SHA256", "ED25519"}.issubset(envelope_algorithms),
        "messageAuthenticity.allowedSignatureAlgorithms must include HMAC_SHA256 and ED25519",
    )
    _assert(
        bool(authenticity.get("requireReplayProtection")),
        "messageAuthenticity.requireReplayProtection must be true",
    )
    _assert(
        bool(authenticity.get("requireTtlValidation")),
        "messageAuthenticity.requireTtlValidation must be true",
    )

    attestation = profile.get("verifierAttestation") or {}
    _assert(
        bool(attestation.get("requireSignedAttestation")),
        "verifierAttestation.requireSignedAttestation must be true",
    )
    attestation_algorithms = {str(item) for item in attestation.get("allowedAlgorithms") or []}
    _assert(
        {"HMAC_SHA256", "ED25519"}.issubset(attestation_algorithms),
        "verifierAttestation.allowedAlgorithms must include HMAC_SHA256 and ED25519",
    )
    required_attestation_fields = {str(item) for item in attestation.get("requiredFields") or []}
    _assert(
        {"alg", "kid", "sig"}.issubset(required_attestation_fields),
        "verifierAttestation.requiredFields must include alg/kid/sig",
    )
    _assert(
        bool(attestation.get("trustedRegistryRequiredInNonLocal")),
        "verifierAttestation.trustedRegistryRequiredInNonLocal must be true",
    )
    _assert(
        bool(attestation.get("failClosedOnVerifierError")),
        "verifierAttestation.failClosedOnVerifierError must be true",
    )

    source_classes = profile.get("sourceClasses") or {}
    canonical = {str(item) for item in source_classes.get("canonical") or []}
    expected_canonical = {
        "vendor-direct",
        "implementer-adapter",
        "authority-only",
        "self-attested",
    }
    _assert(canonical == expected_canonical, "sourceClasses.canonical set mismatch")

    aliases = source_classes.get("aliases") or {}
    _assert(isinstance(aliases, dict) and aliases, "sourceClasses.aliases must be a non-empty object")
    for alias, canonical_value in aliases.items():
        normalized_alias = _normalize_verifier_source(alias)
        normalized_value = _normalize_verifier_source(canonical_value)
        _assert(
            normalized_alias == normalized_value,
            f"source alias mapping mismatch: {alias} -> {canonical_value}",
        )

    non_local_allowed = {str(item) for item in source_classes.get("nonLocalAllowed") or []}
    _assert(
        non_local_allowed == {"vendor-direct", "implementer-adapter"},
        "sourceClasses.nonLocalAllowed must be vendor-direct and implementer-adapter",
    )

    policy_restricted = {str(item) for item in source_classes.get("policyRestricted") or []}
    _assert(
        {"authority-only", "self-attested"}.issubset(policy_restricted),
        "sourceClasses.policyRestricted must include authority-only and self-attested",
    )
    _assert(
        not non_local_allowed.intersection(policy_restricted),
        "sourceClasses.nonLocalAllowed must not overlap policyRestricted",
    )

    boundary = profile.get("operationalBoundary") or {}
    for field in [
        "faxpHostsVerifierInfrastructure",
        "faxpStoresVerifierCredentials",
        "faxpMaintainsGlobalParticipantRegistry",
    ]:
        _assert(field in boundary, f"operationalBoundary missing field: {field}")
        _assert(boundary[field] is False, f"operationalBoundary.{field} must be false")

    conformance_requirements = profile.get("conformanceRequirements") or {}
    required_tests = [str(item) for item in conformance_requirements.get("requiredTests") or []]
    required_checks = [str(item) for item in conformance_requirements.get("requiredSuiteChecks") or []]
    _assert("tests/run_trust_profile.py" in required_tests, "trust profile must self-reference run_trust_profile test")
    _assert("trust_profile" in required_checks, "trust profile must require trust_profile suite check")

    for rel_path in required_tests:
        _assert((PROJECT_ROOT / rel_path).exists(), f"conformanceRequirements test not found: {rel_path}")

    listed_checks_run = subprocess.run(
        [sys.executable, str(CONFORMANCE_SUITE_PATH), "--list-checks"],
        check=True,
        capture_output=True,
        text=True,
    )
    listed_checks = set(line.strip() for line in listed_checks_run.stdout.splitlines() if line.strip())
    for check_name in required_checks:
        _assert(check_name in listed_checks, f"missing suite check from run_all_checks.py: {check_name}")

    registry_entries = registry.get("entries") or []
    _assert(isinstance(registry_entries, list) and registry_entries, "trusted verifier registry entries must exist")

    active_source_classes = set()
    for entry in registry_entries:
        if not isinstance(entry, dict):
            continue
        status = str(entry.get("status") or "").strip().lower()
        if status not in {"active", "approved"}:
            continue
        for source in entry.get("allowedSources") or []:
            active_source_classes.add(_normalize_verifier_source(source))

    for source_class in non_local_allowed:
        _assert(
            source_class in active_source_classes,
            f"trusted verifier registry must include active {source_class} source support",
        )

    _assert(
        vendor_profile.get("sourceClass") in non_local_allowed,
        "vendor_direct_verifier_profile sourceClass must be allowed in non-local trust policy",
    )

    print("Trust profile checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
