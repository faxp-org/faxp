#!/usr/bin/env python3
"""Schema compatibility checks for FAXP v0.1.1 and v0.2."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_V011_PATH = PROJECT_ROOT / "faxp.schema.json"
SCHEMA_V020_PATH = PROJECT_ROOT / "faxp.v0.2.schema.json"


def _load_schema(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _validator(schema: dict) -> Draft202012Validator:
    return Draft202012Validator(schema)


def _is_valid(validator: Draft202012Validator, payload: dict) -> bool:
    return not any(validator.iter_errors(payload))


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _legacy_execution_report_v011() -> dict:
    return {
        "Protocol": "FAXP",
        "ProtocolVersion": "0.1.1",
        "MessageType": "ExecutionReport",
        "From": "Broker Agent",
        "To": "Carrier Agent",
        "Timestamp": "2026-02-21T18:00:00Z",
        "Body": {
            "LoadID": "load-011-abc",
            "ContractID": "FAXP-20260221-legacy",
            "Status": "Booked",
            "Timestamp": "2026-02-21T18:00:00Z",
            "VerifiedBadge": "Basic",
            "VerificationResult": {
                "status": "Success",
                "provider": "FMCSA",
                "score": 88,
                "token": "legacy-token-opaque",
                "source": "carrier-finder",
                "sourceAuthority": "FMCSA",
                "mcNumber": "498282",
                "carrier": {"mc": "498282", "operatingStatus": "A"},
            },
        },
    }


def _neutral_execution_report_v020(provider: str = "provider-opaque-id") -> dict:
    return {
        "Protocol": "FAXP",
        "ProtocolVersion": "0.2.0",
        "MessageType": "ExecutionReport",
        "From": "Broker Agent",
        "To": "Carrier Agent",
        "Timestamp": "2026-02-21T18:01:00Z",
        "Body": {
            "LoadID": "load-020-abc",
            "ContractID": "FAXP-20260221-neutral",
            "Status": "Booked",
            "Timestamp": "2026-02-21T18:01:00Z",
            "VerifiedBadge": "Premium",
            "VerificationResult": {
                "status": "Success",
                "category": "Biometric",
                "method": "LivenessPlusDocument",
                "provider": provider,
                "assuranceLevel": "AAL2",
                "score": 94,
                "token": "opaque-verification-token",
                "evidenceRef": "sha256:ab12cd34ef56",
                "verifiedAt": "2026-02-21T18:01:00Z",
                "attestation": {
                    "alg": "ED25519",
                    "kid": "verifier-20260221",
                    "sig": "base64-signature",
                },
            },
        },
    }


def main() -> int:
    schema_v011 = _load_schema(SCHEMA_V011_PATH)
    schema_v020 = _load_schema(SCHEMA_V020_PATH)
    validator_v011 = _validator(schema_v011)
    validator_v020 = _validator(schema_v020)
    verification_result_schema_v020 = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$defs": schema_v020.get("$defs", {}),
        "$ref": "#/$defs/VerificationResult",
    }
    validator_v020_verification = _validator(verification_result_schema_v020)

    # v0.2 schema must explicitly support v0.1.1 and v0.2.0 envelopes.
    version_enum = (
        schema_v020.get("properties", {})
        .get("ProtocolVersion", {})
        .get("enum", [])
    )
    _assert(
        set(version_enum) == {"0.1.1", "0.2.0"},
        "v0.2 schema must accept ProtocolVersion 0.1.1 and 0.2.0.",
    )

    legacy_msg = _legacy_execution_report_v011()
    _assert(_is_valid(validator_v011, legacy_msg), "legacy v0.1.1 message should pass v0.1.1 schema")
    _assert(_is_valid(validator_v020, legacy_msg), "legacy v0.1.1 message should pass v0.2 schema")

    neutral_msg = _neutral_execution_report_v020()
    _assert(
        not _is_valid(validator_v011, neutral_msg),
        "v0.2 message should fail v0.1.1 schema due ProtocolVersion const.",
    )
    _assert(_is_valid(validator_v020, neutral_msg), "v0.2 message should pass v0.2 schema")

    vendor_agnostic_msg = _neutral_execution_report_v020(provider="future-provider-x")
    _assert(
        _is_valid(validator_v020, vendor_agnostic_msg),
        "v0.2 schema should accept arbitrary provider names.",
    )
    _assert(
        _is_valid(
            validator_v020_verification,
            vendor_agnostic_msg["Body"]["VerificationResult"],
        ),
        "v0.2 VerificationResult def should accept arbitrary provider names.",
    )

    provider_shape = (
        schema_v020.get("$defs", {})
        .get("VerificationResult", {})
        .get("properties", {})
        .get("provider", {})
    )
    _assert(
        "enum" not in provider_shape and "const" not in provider_shape,
        "provider field must stay vendor-agnostic (no enum/const).",
    )

    biometric_leak_msg = copy.deepcopy(neutral_msg)
    biometric_leak_msg["Body"]["VerificationResult"]["rawBiometric"] = "forbidden"
    _assert(
        not _is_valid(
            validator_v020_verification,
            biometric_leak_msg["Body"]["VerificationResult"],
        ),
        "v0.2 VerificationResult def must reject raw biometric artifacts.",
    )

    print("Schema compatibility checks passed (v0.1.1 <-> v0.2).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
