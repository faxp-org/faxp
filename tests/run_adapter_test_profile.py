#!/usr/bin/env python3
"""Validate FMCSA adapter conformance test profile artifacts."""

from __future__ import annotations

import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from adapter.fmcsa_live import validate_fmcsa_payload  # noqa: E402
from conformance.verifier_translator import translate_verifier_payload  # noqa: E402

PROFILE_SCHEMA_PATH = PROJECT_ROOT / "conformance" / "adapter_test_profile.schema.json"
PROFILE_PATH = PROJECT_ROOT / "conformance" / "fmcsa_adapter_test_profile.v1.json"


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _validate_schema(schema: dict, payload: dict) -> None:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda item: list(item.path))
    if errors:
        detail = "; ".join(error.message for error in errors[:3])
        raise AssertionError(f"Adapter test profile schema validation failed: {detail}")


def main() -> int:
    profile_schema = _load_json(PROFILE_SCHEMA_PATH)
    profile = _load_json(PROFILE_PATH)
    _validate_schema(profile_schema, profile)

    _assert(profile["provider"] == "FMCSA", "provider must be FMCSA")
    _assert(
        profile["requestContract"]["requiredBodyFields"] == ["mcNumber"],
        "request contract must require mcNumber",
    )
    _assert(
        profile["responseContract"]["wrapperRequired"] is True,
        "response wrapper must be required",
    )
    _assert(
        profile["responseContract"]["signatureRequired"] is True,
        "response signature must be required",
    )

    native_payload = {
        "status": "Success",
        "score": 93,
        "mcNumber": "498282",
        "carrier": {
            "usdot": 1292301,
            "mc": "498282",
            "name": "CA FREIGHT XPRESS INC",
            "operatingStatus": "ACTIVE",
            "hasCurrentInsurance": True,
            "interstateAuthorityOk": True,
        },
    }
    translated = translate_verifier_payload(
        "fmcsa",
        native_payload,
        source="hosted-adapter",
        provider_id=profile["providerId"],
    )
    verification_result = translated["VerificationResult"]
    provider_extensions = translated["ProviderExtensions"]

    for field in profile["responseContract"]["verificationResultFields"]:
        _assert(field in verification_result, f"missing VerificationResult field: {field}")
    for field in profile["responseContract"]["providerExtensionsFields"]:
        _assert(field in provider_extensions, f"missing ProviderExtensions field: {field}")

    legacy_payload = {
        "found": True,
        "status": "Success",
        "score": 93,
        "usdot_number": 1292301,
        "mc_number": "498282",
        "carrier_name": "CA FREIGHT XPRESS INC",
        "operating_status": "Common=NONE; Contract=ACTIVE; Broker=NONE",
        "has_current_insurance": True,
        "interstate_authority_ok": True,
    }
    expected_legacy_fields = set(profile["responseContract"]["legacyNormalizedFields"])
    _assert(
        set(legacy_payload.keys()) == expected_legacy_fields,
        "legacy normalized payload fields mismatch profile contract",
    )
    validate_fmcsa_payload(legacy_payload, requested_mc="498282")

    required_checks = {
        "request_contract_shape",
        "response_wrapper_signature",
        "translator_neutral_fields",
        "legacy_normalized_payload_shape",
        "fail_closed_on_signature_error",
    }
    _assert(
        required_checks.issubset(set(profile.get("certificationChecks", []))),
        "adapter test profile is missing required certification checks",
    )

    print("Adapter test profile checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

