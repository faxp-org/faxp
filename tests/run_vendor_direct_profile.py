#!/usr/bin/env python3
"""Validate vendor-direct verifier profile artifact and trusted-registry alignment."""

from __future__ import annotations

from pathlib import Path
import json
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from faxp_mvp_simulation import _normalize_verifier_source  # noqa: E402


PROFILE_PATH = PROJECT_ROOT / "conformance" / "vendor_direct_verifier_profile.v1.json"
REGISTRY_PATH = PROJECT_ROOT / "conformance" / "trusted_verifier_registry.sample.json"
ASSURANCE_ORDER = {"AAL0": 0, "AAL1": 1, "AAL2": 2, "AAL3": 3}


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    _assert(isinstance(payload, dict), f"{path.name} must contain a JSON object.")
    return payload


def _is_active_status(value: str) -> bool:
    return str(value or "").strip().lower() in {"active", "approved"}


def main() -> int:
    profile = _load_json(PROFILE_PATH)
    registry = _load_json(REGISTRY_PATH)

    required_profile_fields = [
        "profileVersion",
        "protocol",
        "profileId",
        "sourceClass",
        "allowedProviderTypes",
        "minimumAssuranceLevel",
        "requiredVerificationResultFields",
        "attestationRequirements",
        "nonLocalPolicy",
        "registryAdmissionRequirements",
    ]
    for field in required_profile_fields:
        _assert(field in profile, f"vendor-direct profile missing field: {field}")

    _assert(profile["protocol"] == "FAXP", "profile protocol must be FAXP")
    _assert(profile["sourceClass"] == "vendor-direct", "sourceClass must be vendor-direct")

    allowed_provider_types = [str(item) for item in profile.get("allowedProviderTypes") or []]
    _assert(allowed_provider_types, "allowedProviderTypes must be non-empty")
    _assert(
        set(allowed_provider_types).issubset({"Compliance", "Identity"}),
        "allowedProviderTypes must be limited to Compliance/Identity for v1.",
    )

    minimum_aal = str(profile.get("minimumAssuranceLevel") or "").strip().upper()
    _assert(minimum_aal in ASSURANCE_ORDER, "minimumAssuranceLevel must be a supported AAL value.")
    _assert(
        ASSURANCE_ORDER[minimum_aal] >= ASSURANCE_ORDER["AAL1"],
        "minimumAssuranceLevel must be at least AAL1.",
    )

    required_result_fields = [
        str(item) for item in profile.get("requiredVerificationResultFields") or []
    ]
    for field in [
        "status",
        "provider",
        "source",
        "provenance",
        "assuranceLevel",
        "score",
        "token",
        "evidenceRef",
        "verifiedAt",
        "attestation",
    ]:
        _assert(field in required_result_fields, f"requiredVerificationResultFields missing: {field}")

    attestation = profile.get("attestationRequirements") or {}
    _assert(
        bool(attestation.get("requireSignedAttestation")),
        "attestationRequirements.requireSignedAttestation must be true",
    )
    required_attestation_fields = [str(item) for item in attestation.get("requiredFields") or []]
    for field in ["alg", "kid", "sig"]:
        _assert(field in required_attestation_fields, f"attestation required field missing: {field}")
    allowed_algorithms = {str(item) for item in attestation.get("allowedAlgorithms") or []}
    _assert(
        {"HMAC_SHA256", "ED25519"}.issubset(allowed_algorithms),
        "allowedAlgorithms must include HMAC_SHA256 and ED25519",
    )

    non_local_policy = profile.get("nonLocalPolicy") or {}
    _assert(
        bool(non_local_policy.get("requireTrustedRegistry")),
        "nonLocalPolicy.requireTrustedRegistry must be true",
    )
    _assert(
        bool(non_local_policy.get("failClosedOnVerifierError")),
        "nonLocalPolicy.failClosedOnVerifierError must be true",
    )

    admission = profile.get("registryAdmissionRequirements") or {}
    required_entry_fields = [str(item) for item in admission.get("requiredEntryFields") or []]
    for field in [
        "providerId",
        "providerType",
        "status",
        "allowedSources",
        "allowedAssuranceLevels",
    ]:
        _assert(field in required_entry_fields, f"requiredEntryFields missing: {field}")
    required_sources = [str(item) for item in admission.get("requiredAllowedSources") or []]
    _assert("vendor-direct" in required_sources, "requiredAllowedSources must include vendor-direct")

    active_statuses = [str(item).lower() for item in admission.get("requiredActiveStatuses") or []]
    _assert("active" in active_statuses, "requiredActiveStatuses must include Active")

    entries = registry.get("entries") or []
    _assert(isinstance(entries, list) and entries, "trusted verifier registry must include entries")
    vendor_direct_entries = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        allowed_sources = [str(item) for item in entry.get("allowedSources") or []]
        normalized_sources = {_normalize_verifier_source(value) for value in allowed_sources}
        if "vendor-direct" in normalized_sources and _is_active_status(entry.get("status")):
            vendor_direct_entries.append(entry)

    _assert(
        vendor_direct_entries,
        "trusted verifier registry must include at least one active provider allowing vendor-direct source.",
    )

    for entry in vendor_direct_entries:
        label = f"providerId={entry.get('providerId')}"
        for field in required_entry_fields:
            _assert(field in entry, f"{label} missing required registry field: {field}")
        provider_type = str(entry.get("providerType") or "")
        _assert(
            provider_type in allowed_provider_types,
            f"{label} providerType must be in profile allowedProviderTypes.",
        )
        assurance_levels = [str(item).upper() for item in entry.get("allowedAssuranceLevels") or []]
        _assert(assurance_levels, f"{label} allowedAssuranceLevels must be non-empty.")
        for level in assurance_levels:
            _assert(level in ASSURANCE_ORDER, f"{label} has invalid assurance level: {level}")
            _assert(
                ASSURANCE_ORDER[level] >= ASSURANCE_ORDER[minimum_aal],
                f"{label} assurance level {level} is below minimum {minimum_aal}.",
            )

    _assert(
        _normalize_verifier_source("vendor-attestation") == "vendor-direct",
        "vendor-attestation alias must normalize to vendor-direct",
    )

    print("Vendor-direct profile checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
