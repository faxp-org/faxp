#!/usr/bin/env python3
"""Fixture-based protocol-version conformance checks."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4
import json
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


FIXTURES_PATH = PROJECT_ROOT / "tests" / "protocol_version_fixtures.json"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _load_fixtures() -> list[dict]:
    with FIXTURES_PATH.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    fixtures = payload.get("fixtures")
    _assert(isinstance(fixtures, list) and fixtures, "Fixture list must be non-empty.")
    return fixtures


def _build_envelope(version: str) -> dict:
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
            "LoadID": "fixture-load-id",
            "AmendmentType": "UpdateRate",
            "ReasonCode": "MarketShift",
        },
    }


def _validate_fixture_envelope(
    fixture_id: str,
    runtime_version: str,
    incoming_version: str,
    expect_pass: bool,
    expected_validation_reason: str,
) -> None:
    original_runtime = FaxpProtocol.VERSION
    try:
        FaxpProtocol.VERSION = runtime_version
        envelope = _build_envelope(incoming_version)
        if expect_pass:
            validate_envelope(envelope, track_replay=False, track_state=False)
            return
        try:
            validate_envelope(envelope, track_replay=False, track_state=False)
        except ValueError as exc:
            _assert(
                expected_validation_reason in str(exc),
                f"{fixture_id}: expected validation reason {expected_validation_reason}, got: {exc}",
            )
            return
        raise AssertionError(f"{fixture_id}: expected validation failure but got success")
    finally:
        FaxpProtocol.VERSION = original_runtime


def main() -> int:
    fixtures = _load_fixtures()
    for fixture in fixtures:
        fixture_id = str(fixture.get("id") or "").strip()
        _assert(fixture_id, "each fixture requires a non-empty id")

        runtime_version = str(fixture.get("runtimeVersion") or "").strip()
        incoming_version = str(fixture.get("incomingVersion") or "").strip()
        expected_status = str(fixture.get("expectedStatus") or "").strip()
        expected_reason = str(fixture.get("expectedReasonCode") or "").strip()

        _assert(runtime_version, f"{fixture_id}: runtimeVersion is required")
        _assert(incoming_version, f"{fixture_id}: incomingVersion is required")
        _assert(expected_status, f"{fixture_id}: expectedStatus is required")
        _assert(expected_reason, f"{fixture_id}: expectedReasonCode is required")

        decision = negotiate_protocol_version(incoming_version, runtime_version=runtime_version)
        _assert(
            decision.get("status") == expected_status,
            (
                f"{fixture_id}: expected status {expected_status}, "
                f"got {decision.get('status')}"
            ),
        )
        _assert(
            decision.get("reasonCode") == expected_reason,
            (
                f"{fixture_id}: expected reasonCode {expected_reason}, "
                f"got {decision.get('reasonCode')}"
            ),
        )
        _assert(
            decision.get("incomingVersion") == incoming_version,
            f"{fixture_id}: incomingVersion mismatch in decision payload",
        )
        _assert(
            decision.get("runtimeVersion") == runtime_version,
            f"{fixture_id}: runtimeVersion mismatch in decision payload",
        )

        expect_validation_pass = bool(fixture.get("expectEnvelopeValidationPass", False))
        expected_validation_reason = str(
            fixture.get("expectedValidationReasonCode") or expected_reason
        ).strip()

        _validate_fixture_envelope(
            fixture_id=fixture_id,
            runtime_version=runtime_version,
            incoming_version=incoming_version,
            expect_pass=expect_validation_pass,
            expected_validation_reason=expected_validation_reason,
        )

    print("Cross-version fixture conformance checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
