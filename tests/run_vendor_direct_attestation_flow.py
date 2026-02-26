#!/usr/bin/env python3
"""Validate vendor-direct attestation sample and decision-record linkage."""

from __future__ import annotations

from pathlib import Path
import hashlib
import hmac
import json
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from faxp_mvp_simulation import _normalize_verifier_source  # noqa: E402


PROFILE_PATH = PROJECT_ROOT / "conformance" / "vendor_direct_verifier_profile.v1.json"
ATTESTATION_PATH = PROJECT_ROOT / "conformance" / "vendor_direct_attestation.sample.json"
DECISION_RECORD_PATH = PROJECT_ROOT / "conformance" / "certification_decision_record.sample.json"
TRUSTED_REGISTRY_PATH = PROJECT_ROOT / "conformance" / "trusted_verifier_registry.sample.json"
ATTESTATION_KEYRING_PATH = PROJECT_ROOT / "conformance" / "attestation_keys.sample.json"
ASSURANCE_ORDER = {"AAL0": 0, "AAL1": 1, "AAL2": 2, "AAL3": 3}


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    _assert(isinstance(payload, dict), f"{path.name} must contain a JSON object.")
    return payload


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _active_status(value: str) -> bool:
    return str(value or "").strip().lower() in {"active", "approved"}


def main() -> int:
    profile = _load_json(PROFILE_PATH)
    result = _load_json(ATTESTATION_PATH)
    decision = _load_json(DECISION_RECORD_PATH)
    registry = _load_json(TRUSTED_REGISTRY_PATH)
    keyring = _load_json(ATTESTATION_KEYRING_PATH)

    _assert(
        profile.get("sourceClass") == "vendor-direct",
        "vendor-direct verifier profile sourceClass must be vendor-direct.",
    )
    required_result_fields = [str(field) for field in profile.get("requiredVerificationResultFields") or []]
    for field in required_result_fields:
        _assert(field in result, f"vendor-direct attestation result missing required field: {field}")

    source = str(result.get("source") or "")
    source_normalized = _normalize_verifier_source(source)
    _assert(source_normalized == "vendor-direct", "attestation source must normalize to vendor-direct.")
    _assert(
        str(result.get("provenance") or "") == source_normalized,
        "attestation provenance must match normalized source.",
    )

    provider_id = str(result.get("provider") or "")
    _assert(provider_id, "attestation provider is required.")
    registry_entries = registry.get("entries") or []
    _assert(isinstance(registry_entries, list) and registry_entries, "trusted verifier registry must have entries.")
    provider_entry = None
    for entry in registry_entries:
        if isinstance(entry, dict) and str(entry.get("providerId") or "") == provider_id:
            provider_entry = entry
            break
    _assert(provider_entry is not None, "attestation provider must exist in trusted verifier registry.")
    _assert(_active_status(provider_entry.get("status")), "attestation provider must be active/approved.")

    allowed_sources = [
        _normalize_verifier_source(item) for item in provider_entry.get("allowedSources") or []
    ]
    _assert(
        "vendor-direct" in allowed_sources,
        "provider registry entry must allow vendor-direct source.",
    )

    attestation = result.get("attestation") or {}
    _assert(isinstance(attestation, dict), "attestation object is required.")
    attestation_requirements = profile.get("attestationRequirements") or {}
    required_attestation_fields = [
        str(field) for field in attestation_requirements.get("requiredFields") or []
    ]
    for field in required_attestation_fields:
        _assert(field in attestation, f"attestation missing required field: {field}")

    alg = str(attestation.get("alg") or "").upper()
    _assert(
        alg in {str(item).upper() for item in attestation_requirements.get("allowedAlgorithms") or []},
        "attestation algorithm must be allowed by vendor-direct profile.",
    )
    _assert(alg == "HMAC_SHA256", "sample vendor-direct attestation must use HMAC_SHA256.")

    kid = str(attestation.get("kid") or "")
    signature = str(attestation.get("sig") or "")
    keys = keyring.get("keys") or {}
    key_value = str(keys.get(kid) or "")
    _assert(key_value, "attestation kid must resolve in attestation keyring.")
    signed_payload = {key: value for key, value in result.items() if key != "attestation"}
    expected_sig = hmac.new(
        key_value.encode("utf-8"),
        _canonical_json(signed_payload).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    _assert(
        hmac.compare_digest(expected_sig, signature),
        "vendor-direct attestation signature verification failed.",
    )

    assurance_level = str(result.get("assuranceLevel") or "").upper()
    minimum_aal = str(profile.get("minimumAssuranceLevel") or "").upper()
    _assert(
        assurance_level in ASSURANCE_ORDER,
        "attestation assuranceLevel must be a supported AAL value.",
    )
    _assert(minimum_aal in ASSURANCE_ORDER, "profile minimumAssuranceLevel must be valid.")
    _assert(
        ASSURANCE_ORDER[assurance_level] >= ASSURANCE_ORDER[minimum_aal],
        "attestation assuranceLevel must satisfy profile minimumAssuranceLevel.",
    )
    allowed_assurance = [str(item).upper() for item in provider_entry.get("allowedAssuranceLevels") or []]
    _assert(
        assurance_level in allowed_assurance,
        "attestation assuranceLevel must be allowed by trusted registry entry.",
    )

    token = str(result.get("token") or "")
    expected_evidence_ref = f"sha256:{hashlib.sha256(token.encode('utf-8')).hexdigest()[:24]}"
    _assert(
        str(result.get("evidenceRef") or "") == expected_evidence_ref,
        "attestation evidenceRef must match token-derived reference format.",
    )

    evidence_links = decision.get("evidenceLinks") or []
    _assert(isinstance(evidence_links, list) and evidence_links, "decision record evidenceLinks must be non-empty.")
    vendor_refs = [
        item
        for item in evidence_links
        if isinstance(item, dict) and str(item.get("type") or "") == "VendorDirectAttestation"
    ]
    _assert(vendor_refs, "decision record must include VendorDirectAttestation evidence link.")
    vendor_ref = str(vendor_refs[0].get("ref") or "")
    _assert(
        vendor_ref == "conformance/vendor_direct_attestation.sample.json",
        "VendorDirectAttestation evidence ref must point to canonical sample attestation artifact.",
    )
    _assert((PROJECT_ROOT / vendor_ref).resolve().exists(), "VendorDirectAttestation evidence file must exist.")
    _assert(
        "VENDOR_DIRECT_ATTESTATION_PASS" in {str(code) for code in decision.get("decisionReasonCodes") or []},
        "decisionReasonCodes must include VENDOR_DIRECT_ATTESTATION_PASS.",
    )

    print("Vendor-direct attestation flow checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
