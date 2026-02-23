#!/usr/bin/env python3
"""Regression checks for protocol-version negotiation behavior."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from faxp_mvp_simulation import (  # noqa: E402
    FaxpProtocol,
    negotiate_protocol_version,
    now_utc,
    validate_envelope,
)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _base_envelope(version: str) -> dict:
    return {
        "Protocol": "FAXP",
        "ProtocolVersion": version,
        "MessageType": "AmendRequest",
        "From": "Broker Agent",
        "To": "Carrier Agent",
        "Timestamp": now_utc(),
        "MessageID": str(uuid4()),
        "Nonce": uuid4().hex,
        "Body": {
            "LoadID": "example-load-id",
            "AmendmentType": "UpdateRate",
            "ReasonCode": "MarketShift",
        },
    }


def _expect_validation_error(envelope: dict, reason_code: str) -> None:
    try:
        validate_envelope(envelope, track_replay=False, track_state=False)
    except ValueError as exc:
        _assert(reason_code in str(exc), f"expected reason code {reason_code}, got: {exc}")
        return
    raise AssertionError(f"validation should fail with reason {reason_code}")


def main() -> int:
    runtime_version = FaxpProtocol.VERSION
    runtime_decision = negotiate_protocol_version(runtime_version)
    _assert(runtime_decision["status"] == "Compatible", "runtime version must be compatible")

    # Ensure the other known version is accepted as degradable/compatible.
    alternate_versions = [
        version
        for version in FaxpProtocol.SUPPORTED_PROTOCOL_VERSIONS
        if version != runtime_version
    ]
    _assert(alternate_versions, "expected at least one alternate supported protocol version")
    alternate_decision = negotiate_protocol_version(alternate_versions[0])
    _assert(
        alternate_decision["status"] in {"Compatible", "Degradable"},
        "alternate supported protocol version should not be incompatible",
    )
    _assert(
        alternate_decision["reasonCode"] in {"ProtocolVersionCompatible", "ProtocolVersionDegradable"},
        "alternate version should produce compatible/degradable reason code",
    )

    # Envelope validation accepts current and alternate supported versions.
    validate_envelope(_base_envelope(runtime_version), track_replay=False, track_state=False)
    validate_envelope(
        _base_envelope(alternate_versions[0]),
        track_replay=False,
        track_state=False,
    )

    unsupported_decision = negotiate_protocol_version("9.9.9")
    _assert(
        unsupported_decision["status"] == "Incompatible"
        and unsupported_decision["reasonCode"] == "ProtocolVersionUnsupported",
        "unsupported version should be rejected with ProtocolVersionUnsupported",
    )
    _expect_validation_error(_base_envelope("9.9.9"), "ProtocolVersionUnsupported")

    invalid_format_decision = negotiate_protocol_version("v0.3")
    _assert(
        invalid_format_decision["status"] == "Incompatible"
        and invalid_format_decision["reasonCode"] == "ProtocolVersionInvalidFormat",
        "invalid format should be rejected with ProtocolVersionInvalidFormat",
    )
    _expect_validation_error(_base_envelope("v0.3"), "ProtocolVersionInvalidFormat")

    missing_decision = negotiate_protocol_version("")
    _assert(
        missing_decision["status"] == "Incompatible"
        and missing_decision["reasonCode"] == "ProtocolVersionMissing",
        "missing version should be rejected with ProtocolVersionMissing",
    )
    _expect_validation_error(_base_envelope(""), "ProtocolVersionMissing")

    bad_runtime_decision = negotiate_protocol_version(runtime_version, runtime_version="broken")
    _assert(
        bad_runtime_decision["status"] == "Incompatible"
        and bad_runtime_decision["reasonCode"] == "RuntimeProtocolVersionInvalid",
        "invalid runtime version should produce RuntimeProtocolVersionInvalid",
    )

    print("Protocol version negotiation checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
