#!/usr/bin/env python3
"""Regression checks for conformance/a2a_bridge_translator.py."""

from __future__ import annotations

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
    load_contract,
)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _build_envelope(message_type: str, body: dict, *, sender: str = "Broker Agent", receiver: str = "Carrier Agent") -> dict:
    return {
        "Protocol": "FAXP",
        "ProtocolVersion": "0.1.1",
        "MessageType": message_type,
        "From": sender,
        "To": receiver,
        "Timestamp": "2026-02-23T00:00:00Z",
        "MessageID": f"msg-{message_type.lower()}-001",
        "Nonce": f"nonce-{message_type.lower()}-001",
        "Body": body,
        "SignatureAlgorithm": "ED25519",
        "SignatureKeyID": "broker-20260220193123",
        "Signature": "demo-signature",
    }


def main() -> int:
    contract = load_contract()

    cases = [
        _build_envelope(
            "NewLoad",
            {
                "LoadID": "load-1",
                "Origin": {"city": "Dallas", "state": "TX", "zip": "75201"},
                "Destination": {"city": "Atlanta", "state": "GA", "zip": "30301"},
                "Rate": {"RateModel": "PerMile", "Amount": 2.45, "Currency": "USD"},
            },
        ),
        _build_envelope(
            "LoadSearch",
            {
                "OriginState": "TX",
                "DestinationState": "GA",
                "EquipmentType": "Reefer",
            },
            sender="Carrier Agent",
            receiver="Broker Agent",
        ),
        _build_envelope(
            "NewTruck",
            {
                "TruckID": "truck-1",
                "Location": {"city": "Fort Worth", "state": "TX", "zip": "76102"},
                "AvailabilityDate": "2026-02-23",
                "RateMin": {"RateModel": "PerMile", "Amount": 2.35, "Currency": "USD"},
            },
            sender="Carrier Agent",
            receiver="Broker Agent",
        ),
        _build_envelope(
            "TruckSearch",
            {
                "OriginState": "TX",
                "EquipmentType": "Reefer",
                "AvailableFrom": "2026-02-23",
            },
        ),
        _build_envelope(
            "BidRequest",
            {
                "LoadID": "load-1",
                "AvailabilityDate": "2026-02-23",
                "Rate": {"RateModel": "PerMile", "Amount": 2.62, "Currency": "USD"},
            },
            sender="Carrier Agent",
            receiver="Broker Agent",
        ),
        _build_envelope(
            "BidResponse",
            {
                "LoadID": "load-1",
                "ResponseType": "Accept",
            },
        ),
        _build_envelope(
            "ExecutionReport",
            {
                "LoadID": "load-1",
                "ContractID": "FAXP-20260223-demo",
                "Status": "Booked",
                "Timestamp": "2026-02-23T00:00:10Z",
                "VerifiedBadge": "Premium",
            },
        ),
        _build_envelope(
            "AmendRequest",
            {
                "LoadID": "load-1",
                "AmendmentType": "UpdateRate",
            },
        ),
    ]

    for envelope in cases:
        task = faxp_to_a2a_task(envelope, contract=contract)
        restored = a2a_task_to_faxp(task, contract=contract)
        _assert(
            _canonical_json(envelope) == _canonical_json(restored),
            f"Round-trip mismatch for {envelope['MessageType']}",
        )
        assert_round_trip(envelope, contract=contract)
        assert_round_trip_from_a2a(task, contract=contract)

    bad_envelope = _build_envelope("NewLoad", {"LoadID": "load-x"})
    try:
        faxp_to_a2a_task(bad_envelope, contract=contract)
    except A2ABridgeError as exc:
        _assert("Missing required Body field" in str(exc), "Unexpected error for bad envelope")
    else:
        raise AssertionError("Expected failure for missing required NewLoad body fields.")

    valid_task = faxp_to_a2a_task(cases[0], contract=contract)
    valid_task["a2aTaskType"] = "faxp.unknown_task"
    try:
        a2a_task_to_faxp(valid_task, contract=contract)
    except A2ABridgeError as exc:
        _assert("Unmapped A2A task type" in str(exc), "Unexpected error for unmapped task type")
    else:
        raise AssertionError("Expected failure for unmapped A2A task type.")

    print("A2A round-trip translator checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
