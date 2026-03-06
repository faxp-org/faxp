#!/usr/bin/env python3
"""Regression checks for conformance/a2a_bridge_translator.py."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from conformance.a2a_bridge_translator import (  # noqa: E402
    A2ABridgeError,
    a2a_task_to_faxp,
    assert_round_trip_from_a2a,
    assert_round_trip,
    faxp_to_a2a_task,
    faxp_to_a2a_task_sanitized_export,
    load_contract,
)

FIXTURES_PATH = PROJECT_ROOT / "conformance" / "a2a_roundtrip_fixtures.json"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _load_fixtures() -> dict:
    with FIXTURES_PATH.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    _assert(isinstance(payload, dict), "A2A fixture payload must be an object.")
    _assert(
        isinstance(payload.get("envelopeFixtures"), list) and payload["envelopeFixtures"],
        "A2A fixture payload must include non-empty envelopeFixtures.",
    )
    _assert(
        isinstance(payload.get("taskFixtures"), list) and payload["taskFixtures"],
        "A2A fixture payload must include non-empty taskFixtures.",
    )
    return payload


def main() -> int:
    contract = load_contract()
    fixtures = _load_fixtures()
    envelope_fixtures = fixtures["envelopeFixtures"]
    task_fixtures = fixtures["taskFixtures"]

    envelope_by_id: dict[str, dict] = {}
    for item in envelope_fixtures:
        fixture_id = str(item.get("id") or "").strip()
        envelope = item.get("envelope")
        _assert(fixture_id, "Each envelope fixture requires non-empty id.")
        _assert(isinstance(envelope, dict), f"Envelope fixture {fixture_id} must include envelope object.")
        envelope_by_id[fixture_id] = envelope

    task_by_id: dict[str, dict] = {}
    for item in task_fixtures:
        fixture_id = str(item.get("id") or "").strip()
        task = item.get("task")
        _assert(fixture_id, "Each task fixture requires non-empty id.")
        _assert(isinstance(task, dict), f"Task fixture {fixture_id} must include task object.")
        task_by_id[fixture_id] = task

    for item in envelope_fixtures:
        fixture_id = str(item["id"])
        envelope = envelope_by_id[fixture_id]
        expected_task_type = str(item.get("expectedA2ATaskType") or "").strip()

        task = faxp_to_a2a_task(envelope, contract=contract)
        _assert(expected_task_type, f"{fixture_id}: expectedA2ATaskType must be present.")
        _assert(
            task.get("a2aTaskType") == expected_task_type,
            f"{fixture_id}: translated a2aTaskType mismatch.",
        )
        if fixture_id in task_by_id:
            _assert(
                _canonical_json(task) == _canonical_json(task_by_id[fixture_id]),
                f"{fixture_id}: translated task drifted from canonical fixture.",
            )

        restored = a2a_task_to_faxp(task, contract=contract)
        _assert(
            _canonical_json(envelope) == _canonical_json(restored),
            f"{fixture_id}: envelope round-trip mismatch.",
        )
        assert_round_trip(envelope, contract=contract)
        assert_round_trip_from_a2a(task, contract=contract)

    for fixture_id, task in task_by_id.items():
        restored = a2a_task_to_faxp(task, contract=contract)
        translated = faxp_to_a2a_task(restored, contract=contract)
        _assert(
            _canonical_json(task) == _canonical_json(translated),
            f"{fixture_id}: task round-trip mismatch.",
        )
        assert_round_trip_from_a2a(task, contract=contract)
        if fixture_id in envelope_by_id:
            _assert(
                _canonical_json(restored) == _canonical_json(envelope_by_id[fixture_id]),
                f"{fixture_id}: restored envelope mismatch versus canonical fixture.",
            )

    _assert("msg-newload-001" in envelope_by_id, "Fixture pack must include msg-newload-001 test case.")
    bad_envelope = deepcopy(envelope_by_id["msg-newload-001"])
    bad_envelope["Body"] = {"LoadID": "load-x"}
    try:
        faxp_to_a2a_task(bad_envelope, contract=contract)
    except A2ABridgeError as exc:
        _assert("Missing required Body field" in str(exc), "Unexpected error for bad envelope")
    else:
        raise AssertionError("Expected failure for missing required NewLoad body fields.")

    valid_task = deepcopy(task_by_id["msg-newload-001"])
    valid_task["a2aTaskType"] = "faxp.unknown_task"
    try:
        a2a_task_to_faxp(valid_task, contract=contract)
    except A2ABridgeError as exc:
        _assert("Unmapped A2A task type" in str(exc), "Unexpected error for unmapped task type")
    else:
        raise AssertionError("Expected failure for unmapped A2A task type.")

    export_envelope = {
        "Protocol": "FAXP",
        "ProtocolVersion": "0.2",
        "MessageType": "ExecutionReport",
        "From": "Broker Agent",
        "To": "Carrier Agent",
        "Timestamp": "2026-03-06T12:00:00Z",
        "MessageID": "msg-export-001",
        "Nonce": "nonce-export-001",
        "Signature": "signature-material",
        "SignatureAlgorithm": "HMAC_SHA256",
        "SignatureKeyID": "kid-1",
        "Body": {
            "Status": "Booked",
            "Timestamp": "2026-03-06T12:00:00Z",
            "VerifiedBadge": "Basic",
            "VerificationResult": {
                "status": "Success",
                "provider": "vendor",
                "score": 90,
                "token": "realistic-sensitive-token",
                "nested": {"token": "nested-sensitive-token"},
                "source": "vendor-adapter",
                "evidenceRef": "sha256:abcd",
                "verifiedAt": "2026-03-06T12:00:00Z",
            },
        },
    }
    sanitized_export = faxp_to_a2a_task_sanitized_export(export_envelope, contract=contract)
    sanitized_envelope = sanitized_export["payload"]["faxpEnvelope"]
    _assert(
        sanitized_envelope.get("Nonce") == "[REDACTED]",
        "Sanitized export must redact envelope nonce.",
    )
    _assert("Signature" not in sanitized_envelope, "Sanitized export must remove Signature.")
    _assert(
        "SignatureAlgorithm" not in sanitized_envelope,
        "Sanitized export must remove SignatureAlgorithm.",
    )
    _assert(
        "SignatureKeyID" not in sanitized_envelope,
        "Sanitized export must remove SignatureKeyID.",
    )
    verification_result = (sanitized_envelope.get("Body") or {}).get("VerificationResult") or {}
    _assert("token" not in verification_result, "Sanitized export must remove VerificationResult token.")
    _assert(
        (verification_result.get("nested") or {}).get("token") is None,
        "Sanitized export must scrub nested token fields in VerificationResult.",
    )
    _assert("tokenRef" in verification_result, "Sanitized export must add VerificationResult tokenRef.")
    _assert(
        sanitized_export.get("metadata", {}).get("sanitizedExport") is True,
        "Sanitized export metadata marker missing.",
    )

    invalid_export_envelope = {
        "Protocol": "FAXP",
        "ProtocolVersion": "0.2",
        "MessageType": "ExecutionReport",
        "From": "Broker Agent",
        "To": "Carrier Agent",
        "Timestamp": "2026-03-06T12:00:00Z",
        "MessageID": "msg-export-002",
        "Nonce": "nonce-export-002",
        "Body": {
            "Status": "Booked",
            "Timestamp": "2026-03-06T12:00:00Z",
            "VerifiedBadge": "Basic",
            "VerificationResult": "not-an-object",
        },
    }
    try:
        faxp_to_a2a_task_sanitized_export(invalid_export_envelope, contract=contract)
    except A2ABridgeError as exc:
        _assert(
            "VerificationResult must be an object" in str(exc),
            "Unexpected error for invalid VerificationResult object type.",
        )
    else:
        raise AssertionError("Expected failure for non-object ExecutionReport VerificationResult.")

    print("A2A round-trip translator checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
