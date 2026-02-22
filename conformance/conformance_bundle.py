#!/usr/bin/env python3
"""Conformance bundle evaluation helpers for adapter certification artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import hmac
import json

from jsonschema import Draft202012Validator


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def now_utc() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _parse_iso_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _validate_schema(schema: dict, payload: dict) -> list[str]:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda item: list(item.path))
    return [error.message for error in errors]


def _read_registry_entry(registry_payload: dict, adapter_id: str | None) -> dict | None:
    if "entries" in registry_payload and isinstance(registry_payload.get("entries"), list):
        entries = registry_payload["entries"]
        if not entries:
            return None
        if adapter_id:
            for entry in entries:
                if entry.get("adapterId") == adapter_id:
                    return entry
        return entries[0]
    return registry_payload


def evaluate_bundle(
    *,
    profile_path: Path,
    registry_path: Path,
    keyring_path: Path,
    conformance_dir: Path | None = None,
) -> dict:
    conformance_root = conformance_dir or profile_path.resolve().parents[0]
    profile_schema_path = conformance_root / "adapter_profile.schema.json"
    registry_schema_path = conformance_root / "certification_registry.schema.json"

    profile_schema = _load_json(profile_schema_path)
    registry_schema = _load_json(registry_schema_path)
    adapter_profile = _load_json(profile_path)
    registry_payload = _load_json(registry_path)
    keyring = _load_json(keyring_path)

    checks: list[dict] = []

    def add_check(check_id: str, passed: bool, details: str) -> None:
        checks.append(
            {
                "id": check_id,
                "passed": bool(passed),
                "details": details,
            }
        )

    profile_schema_errors = _validate_schema(profile_schema, adapter_profile)
    add_check(
        "profile_schema",
        not profile_schema_errors,
        "adapter profile schema validation"
        if not profile_schema_errors
        else "; ".join(profile_schema_errors[:3]),
    )

    registry_envelope = registry_payload
    if "entries" not in registry_payload:
        registry_envelope = {
            "registryVersion": "1.0.0",
            "generatedAt": now_utc(),
            "entries": [registry_payload],
        }
    registry_schema_errors = _validate_schema(registry_schema, registry_envelope)
    add_check(
        "registry_schema",
        not registry_schema_errors,
        "registry schema validation"
        if not registry_schema_errors
        else "; ".join(registry_schema_errors[:3]),
    )

    adapter_id = str(adapter_profile.get("adapterId") or "").strip()
    entry = _read_registry_entry(registry_payload, adapter_id)
    if entry is None:
        add_check("registry_entry_present", False, "no registry entry found")
        entry = {}
    else:
        add_check("registry_entry_present", True, "registry entry present")

    attestation = adapter_profile.get("selfAttestation", {})
    payload = attestation.get("payload", {})
    payload_canonical = canonical_json(payload)
    payload_digest = hashlib.sha256(payload_canonical.encode("utf-8")).hexdigest()
    observed_digest = str(attestation.get("payloadDigestSha256") or "")
    add_check(
        "attestation_digest",
        observed_digest == f"sha256:{payload_digest}",
        "self-attestation payload digest matches canonical payload hash",
    )

    kid = str(attestation.get("kid") or "").strip()
    keys = keyring.get("keys") or {}
    key_value = str(keys.get(kid) or "").strip()
    add_check("attestation_kid_known", bool(key_value), f"attestation kid '{kid}' exists in keyring")
    expected_sig = ""
    if key_value:
        expected_sig = hmac.new(
            key_value.encode("utf-8"),
            payload_canonical.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
    observed_sig = str(attestation.get("sig") or "")
    add_check(
        "attestation_signature",
        bool(expected_sig) and hmac.compare_digest(expected_sig, observed_sig),
        "self-attestation signature verified with keyring",
    )

    try:
        signed_at = _parse_iso_datetime(str(attestation.get("signedAt") or ""))
        expires_at = _parse_iso_datetime(str(attestation.get("expiresAt") or ""))
        add_check(
            "attestation_window",
            expires_at > signed_at,
            "attestation expiration is after signedAt",
        )
    except ValueError:
        add_check("attestation_window", False, "invalid signedAt/expiresAt format")

    add_check(
        "registry_match_adapter_id",
        entry.get("adapterId") == adapter_profile.get("adapterId"),
        "registry adapterId matches adapter profile",
    )
    add_check(
        "registry_match_tier",
        entry.get("certificationTier") == adapter_profile.get("certificationTier"),
        "registry certificationTier matches adapter profile",
    )
    add_check(
        "registry_match_hosting_model",
        entry.get("hostingModel") == adapter_profile.get("hostingModel"),
        "registry hostingModel matches adapter profile",
    )
    add_check(
        "registry_match_profiles",
        sorted(entry.get("profilesSupported") or [])
        == sorted(adapter_profile.get("profilesSupported") or []),
        "registry profilesSupported matches adapter profile",
    )
    add_check(
        "registry_match_attestation_kid",
        entry.get("selfAttestationKid") == kid,
        "registry selfAttestationKid matches adapter profile attestation kid",
    )
    security = adapter_profile.get("securityCapabilities") or {}
    security_attestation = entry.get("securityAttestation") or {}
    add_check(
        "registry_security_signed_requests",
        bool(security_attestation.get("signedRequests")) == bool(security.get("signedRequests")),
        "registry signedRequests matches adapter profile security capabilities",
    )
    add_check(
        "registry_security_signed_responses",
        bool(security_attestation.get("signedResponses")) == bool(security.get("signedResponses")),
        "registry signedResponses matches adapter profile security capabilities",
    )
    add_check(
        "registry_security_replay",
        bool(security_attestation.get("replayProtection")) == bool(security.get("replayProtection")),
        "registry replayProtection matches adapter profile security capabilities",
    )

    total_checks = len(checks)
    passed_checks = sum(1 for check in checks if check["passed"])
    failed_checks = total_checks - passed_checks
    passed = failed_checks == 0

    report = {
        "generatedAt": now_utc(),
        "adapterId": adapter_profile.get("adapterId", ""),
        "profilePath": str(profile_path),
        "registryPath": str(registry_path),
        "keyringPath": str(keyring_path),
        "summary": {
            "totalChecks": total_checks,
            "passedChecks": passed_checks,
            "failedChecks": failed_checks,
            "passed": passed,
        },
        "checks": checks,
    }
    report_hash = hashlib.sha256(canonical_json(report).encode("utf-8")).hexdigest()
    report["reportHash"] = f"sha256:{report_hash}"
    return report

