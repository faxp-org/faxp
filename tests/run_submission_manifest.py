#!/usr/bin/env python3
"""Validate adapter certification submission manifest and referenced bundle artifacts."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import argparse
import json
import sys

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from conformance.submission_manifest_signing import verify_submission_signature  # noqa: E402

CONFORMANCE_DIR = PROJECT_ROOT / "conformance"

MANIFEST_SCHEMA_PATH = CONFORMANCE_DIR / "submission_manifest.schema.json"
MANIFEST_SAMPLE_PATH = CONFORMANCE_DIR / "submission_manifest.sample.json"
MANIFEST_KEYS_SAMPLE_PATH = CONFORMANCE_DIR / "submission_manifest_keys.sample.json"
ADAPTER_PROFILE_SCHEMA_PATH = CONFORMANCE_DIR / "adapter_profile.schema.json"
REGISTRY_SCHEMA_PATH = CONFORMANCE_DIR / "certification_registry.schema.json"
ADAPTER_TEST_PROFILE_SCHEMA_PATH = CONFORMANCE_DIR / "adapter_test_profile.schema.json"


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


def _validate_iso_datetime(value: str, context: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AssertionError(f"{context} must be ISO-8601.") from exc


def _resolve_ref(path_ref: str) -> Path:
    ref = Path(path_ref)
    if ref.is_absolute():
        resolved = ref
    else:
        resolved = (PROJECT_ROOT / ref).resolve()
    _assert(resolved.exists(), f"Referenced file does not exist: {path_ref}")
    return resolved


def _registry_entry_for_adapter(registry_payload: dict, adapter_id: str) -> dict | None:
    if isinstance(registry_payload.get("entries"), list):
        for entry in registry_payload["entries"]:
            if entry.get("adapterId") == adapter_id:
                return entry
        return None
    if registry_payload.get("adapterId") == adapter_id:
        return registry_payload
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate FAXP certification submission manifest bundle."
    )
    parser.add_argument(
        "--manifest",
        default=str(MANIFEST_SAMPLE_PATH),
        help="Path to submission manifest JSON.",
    )
    parser.add_argument(
        "--keyring",
        default=str(MANIFEST_KEYS_SAMPLE_PATH),
        help="Submission manifest signing keyring JSON path.",
    )
    parser.add_argument(
        "--allow-unsigned",
        action="store_true",
        help="Allow unsigned manifests (default requires valid submissionSignature).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest).expanduser().resolve()
    keyring_path = Path(args.keyring).expanduser().resolve()
    manifest = _load_json(manifest_path)
    keyring = _load_json(keyring_path)
    manifest_schema = _load_json(MANIFEST_SCHEMA_PATH)
    _validate(manifest_schema, manifest, "submission manifest")

    _validate_iso_datetime(str(manifest["submittedAt"]), "manifest submittedAt")
    verify_submission_signature(
        manifest,
        keyring=keyring,
        require_signature=not args.allow_unsigned,
    )
    submission_signature = manifest.get("submissionSignature") or {}
    if submission_signature:
        _validate_iso_datetime(
            str(submission_signature.get("signedAt") or ""),
            "manifest submissionSignature.signedAt",
        )

    adapter_id = str(manifest["adapterId"]).strip()
    requested_tier = str(manifest["requestedTier"]).strip()
    bundle = manifest["bundle"]
    declarations = manifest["declarations"]

    profile_path = _resolve_ref(bundle["adapterProfileRef"])
    registry_path = _resolve_ref(bundle["registryEntryRef"])
    keyring_path = _resolve_ref(bundle["attestationKeyringRef"])
    report_path = _resolve_ref(bundle["conformanceReportRef"])
    adapter_test_profile_paths = [_resolve_ref(item) for item in bundle["adapterTestProfiles"]]

    adapter_profile_schema = _load_json(ADAPTER_PROFILE_SCHEMA_PATH)
    registry_schema = _load_json(REGISTRY_SCHEMA_PATH)
    adapter_test_profile_schema = _load_json(ADAPTER_TEST_PROFILE_SCHEMA_PATH)

    adapter_profile = _load_json(profile_path)
    registry_payload = _load_json(registry_path)
    keyring_payload = _load_json(keyring_path)
    conformance_report = _load_json(report_path)

    _validate(adapter_profile_schema, adapter_profile, "adapter profile")
    if isinstance(registry_payload.get("entries"), list):
        _validate(registry_schema, registry_payload, "registry payload")
    else:
        # Accept a single entry object by wrapping it in a valid registry envelope.
        _validate(
            registry_schema,
            {
                "registryVersion": "1.0.0",
                "generatedAt": manifest["submittedAt"],
                "entries": [registry_payload],
            },
            "registry entry",
        )

    entry = _registry_entry_for_adapter(registry_payload, adapter_id)
    _assert(entry is not None, f"No registry entry found for adapterId '{adapter_id}'.")

    _assert(adapter_profile.get("adapterId") == adapter_id, "adapterId mismatch in profile.")
    _assert(entry.get("adapterId") == adapter_id, "adapterId mismatch in registry entry.")
    _assert(
        adapter_profile.get("certificationTier") == requested_tier,
        "requestedTier must match adapter profile certificationTier.",
    )
    _assert(
        entry.get("certificationTier") == requested_tier,
        "requestedTier must match registry entry certificationTier.",
    )

    expected_hosting = "ImplementerHosted" if declarations["implementerHosted"] else "ReferenceOnly"
    _assert(
        adapter_profile.get("hostingModel") == expected_hosting,
        "hosting model mismatch between manifest declarations and adapter profile.",
    )
    _assert(
        entry.get("hostingModel") == expected_hosting,
        "hosting model mismatch between manifest declarations and registry entry.",
    )

    security = adapter_profile.get("securityCapabilities") or {}
    security_attestation = entry.get("securityAttestation") or {}
    _assert(
        bool(security.get("signedRequests")) == bool(declarations["signedRequests"]),
        "signedRequests mismatch between manifest and adapter profile.",
    )
    _assert(
        bool(security.get("signedResponses")) == bool(declarations["signedResponses"]),
        "signedResponses mismatch between manifest and adapter profile.",
    )
    _assert(
        bool(security.get("replayProtection")) == bool(declarations["replayProtection"]),
        "replayProtection mismatch between manifest and adapter profile.",
    )
    _assert(
        bool(security_attestation.get("signedRequests")) == bool(declarations["signedRequests"]),
        "signedRequests mismatch between manifest and registry entry.",
    )
    _assert(
        bool(security_attestation.get("signedResponses")) == bool(declarations["signedResponses"]),
        "signedResponses mismatch between manifest and registry entry.",
    )
    _assert(
        bool(security_attestation.get("replayProtection")) == bool(declarations["replayProtection"]),
        "replayProtection mismatch between manifest and registry entry.",
    )

    attestation = adapter_profile.get("selfAttestation") or {}
    kid = str(attestation.get("kid") or "").strip()
    keys = keyring_payload.get("keys") or {}
    _assert(kid, "adapter selfAttestation.kid is required.")
    _assert(keys.get(kid), f"attestation kid '{kid}' not present in keyring.")

    require_conformance_pass = bool(declarations.get("requireConformancePass"))
    if require_conformance_pass or requested_tier in {"Conformant", "TrustedProduction"}:
        summary = conformance_report.get("summary") or {}
        _assert(
            bool(summary.get("passed")),
            "conformance report must include summary.passed=true for this submission tier.",
        )

    if "adapterId" in conformance_report:
        _assert(
            conformance_report.get("adapterId") == adapter_id,
            "conformance report adapterId must match manifest adapterId.",
        )

    for profile_ref, test_profile_path in zip(bundle["adapterTestProfiles"], adapter_test_profile_paths):
        test_profile = _load_json(test_profile_path)
        _validate(adapter_test_profile_schema, test_profile, f"adapter test profile '{profile_ref}'")
        _assert(
            bool(test_profile.get("certificationChecks")),
            f"adapter test profile '{profile_ref}' must define certificationChecks.",
        )

    if requested_tier == "TrustedProduction":
        evidence = manifest.get("evidence") or {}
        required_evidence = [
            "runbookRef",
            "incidentResponseRef",
            "securityReviewRef",
            "slaPolicyRef",
            "keyManagementRef",
        ]
        for field in required_evidence:
            _assert(
                str(evidence.get(field) or "").strip(),
                f"TrustedProduction requires evidence.{field}.",
            )

    print("Submission manifest checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
