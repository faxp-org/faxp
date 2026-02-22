#!/usr/bin/env python3
"""Validate verification profile and certification registry artifacts."""

from __future__ import annotations

from datetime import datetime
import hashlib
import hmac
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILE_SCHEMA_PATH = PROJECT_ROOT / "profiles" / "verification" / "profile.schema.json"
STRICT_PROFILE_PATH = PROJECT_ROOT / "profiles" / "verification" / "US_FMCSA_STRICT_V1.json"
BALANCED_PROFILE_PATH = PROJECT_ROOT / "profiles" / "verification" / "US_FMCSA_BALANCED_V1.json"
REGISTRY_SCHEMA_PATH = PROJECT_ROOT / "conformance" / "certification_registry.schema.json"
REGISTRY_SAMPLE_PATH = PROJECT_ROOT / "conformance" / "certification_registry.sample.json"
ADAPTER_PROFILE_SCHEMA_PATH = PROJECT_ROOT / "conformance" / "adapter_profile.schema.json"
ADAPTER_PROFILE_SAMPLE_PATH = PROJECT_ROOT / "conformance" / "adapter_profile.sample.json"
ATTESTATION_KEYS_SAMPLE_PATH = PROJECT_ROOT / "conformance" / "attestation_keys.sample.json"


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _validate(schema: dict, payload: dict, label: str) -> None:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda item: item.path)
    if errors:
        detail = "; ".join(err.message for err in errors[:3])
        raise AssertionError(f"{label} failed schema validation: {detail}")


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _validate_iso_datetime(value: str, context: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AssertionError(f"{context} must be ISO-8601.") from exc


def _assert_tier_coverage(profile: dict, label: str) -> None:
    tiers = [entry.get("tier") for entry in profile.get("riskTiers", [])]
    _assert(sorted(tiers) == [0, 1, 2, 3], f"{label} must define tiers 0..3.")


def main() -> int:
    profile_schema = _load_json(PROFILE_SCHEMA_PATH)
    strict_profile = _load_json(STRICT_PROFILE_PATH)
    balanced_profile = _load_json(BALANCED_PROFILE_PATH)
    registry_schema = _load_json(REGISTRY_SCHEMA_PATH)
    registry_sample = _load_json(REGISTRY_SAMPLE_PATH)
    adapter_profile_schema = _load_json(ADAPTER_PROFILE_SCHEMA_PATH)
    adapter_profile_sample = _load_json(ADAPTER_PROFILE_SAMPLE_PATH)
    attestation_keyring = _load_json(ATTESTATION_KEYS_SAMPLE_PATH)

    _validate(profile_schema, strict_profile, "strict profile")
    _validate(profile_schema, balanced_profile, "balanced profile")
    _validate(registry_schema, registry_sample, "certification registry sample")
    _validate(adapter_profile_schema, adapter_profile_sample, "adapter profile sample")

    _assert_tier_coverage(strict_profile, "strict profile")
    _assert_tier_coverage(balanced_profile, "balanced profile")

    _assert(
        strict_profile["policyDefaults"]["degradedMode"] == "HardBlock",
        "strict profile degraded mode should be HardBlock.",
    )
    _assert(
        balanced_profile["policyDefaults"]["degradedMode"] in {"SoftHold", "GraceCache"},
        "balanced profile degraded mode should permit continuity behavior.",
    )
    _assert(
        balanced_profile["policyDefaults"]["maxFallbackDurationSeconds"]
        >= strict_profile["policyDefaults"]["maxFallbackDurationSeconds"],
        "balanced profile must not be stricter than strict profile fallback duration.",
    )

    entries = registry_sample.get("entries", [])
    _assert(entries, "registry sample must include at least one entry.")
    first_entry = entries[0]
    _assert(
        first_entry["hostingModel"] == "ImplementerHosted",
        "registry sample should reflect implementer-hosted production model.",
    )
    _assert(
        bool(first_entry.get("profilesSupported")),
        "registry sample entry must include supported profiles.",
    )
    _assert(
        isinstance(attestation_keyring.get("keys"), dict) and attestation_keyring["keys"],
        "attestation keyring must contain at least one key.",
    )

    adapter_attestation = adapter_profile_sample.get("selfAttestation", {})
    payload = adapter_attestation.get("payload", {})
    payload_canonical = _canonical_json(payload)
    payload_digest = hashlib.sha256(payload_canonical.encode("utf-8")).hexdigest()
    _assert(
        adapter_attestation.get("payloadDigestSha256") == f"sha256:{payload_digest}",
        "adapter self-attestation payloadDigestSha256 mismatch.",
    )

    signed_at = _validate_iso_datetime(adapter_attestation.get("signedAt", ""), "signedAt")
    expires_at = _validate_iso_datetime(adapter_attestation.get("expiresAt", ""), "expiresAt")
    _assert(expires_at > signed_at, "attestation expiresAt must be later than signedAt.")

    attestation_kid = str(adapter_attestation.get("kid") or "").strip()
    _assert(attestation_kid, "adapter self-attestation kid is required.")
    key_value = attestation_keyring["keys"].get(attestation_kid)
    _assert(bool(key_value), f"attestation kid '{attestation_kid}' not found in keyring.")

    expected_sig = hmac.new(
        str(key_value).encode("utf-8"),
        payload_canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    _assert(
        hmac.compare_digest(expected_sig, str(adapter_attestation.get("sig") or "")),
        "adapter self-attestation signature mismatch.",
    )

    _assert(
        payload.get("adapterId") == adapter_profile_sample["adapterId"],
        "attestation payload.adapterId must match adapter profile adapterId.",
    )
    _assert(
        payload.get("providerType") == adapter_profile_sample["providerType"],
        "attestation payload.providerType must match adapter profile providerType.",
    )
    _assert(
        payload.get("hostingModel") == adapter_profile_sample["hostingModel"],
        "attestation payload.hostingModel must match adapter profile hostingModel.",
    )
    _assert(
        sorted(payload.get("profilesSupported", []))
        == sorted(adapter_profile_sample.get("profilesSupported", [])),
        "attestation payload.profilesSupported must match adapter profile profilesSupported.",
    )
    _assert(
        payload.get("securityCapabilities") == adapter_profile_sample.get("securityCapabilities"),
        "attestation payload.securityCapabilities must match adapter profile securityCapabilities.",
    )

    _assert(
        first_entry["adapterId"] == adapter_profile_sample["adapterId"],
        "registry entry adapterId must match adapter profile adapterId.",
    )
    _assert(
        first_entry["certificationTier"] == adapter_profile_sample["certificationTier"],
        "registry certification tier must match adapter profile tier.",
    )
    _assert(
        first_entry["hostingModel"] == adapter_profile_sample["hostingModel"],
        "registry hosting model must match adapter profile hosting model.",
    )
    _assert(
        sorted(first_entry.get("profilesSupported", []))
        == sorted(adapter_profile_sample.get("profilesSupported", [])),
        "registry profilesSupported must match adapter profile profilesSupported.",
    )
    _assert(
        first_entry.get("selfAttestationKid") == attestation_kid,
        "registry selfAttestationKid must match adapter attestation kid.",
    )
    _assert(
        first_entry.get("adapterProfileRef") == "conformance/adapter_profile.sample.json",
        "registry adapterProfileRef must reference the sample adapter profile.",
    )

    print("Certification artifact checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
