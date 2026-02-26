#!/usr/bin/env python3
"""Regression checks for booking-plane special-instructions commercial terms."""

from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import faxp_mvp_simulation as sim  # noqa: E402
from faxp_mvp_simulation import BrokerAgent, CarrierAgent, build_rate, now_utc, validate_message_body  # noqa: E402


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _expect_validation_error(message_type: str, body: dict, text: str) -> None:
    try:
        validate_message_body(message_type, body)
    except ValueError as exc:
        _assert(text in str(exc), f"expected '{text}' in error, got: {exc}")
        return
    raise AssertionError(f"{message_type} should fail validation with: {text}")


def _base_new_load() -> dict:
    return {
        "LoadID": "load-special-instructions-001",
        "Origin": {"city": "Dallas", "state": "TX", "zip": "75201"},
        "Destination": {"city": "Atlanta", "state": "GA", "zip": "30301"},
        "PickupEarliest": "2026-03-01",
        "PickupLatest": "2026-03-02",
        "LoadType": "Full",
        "EquipmentType": "Reefer",
        "TrailerLength": 53,
        "Weight": 42000,
        "Commodity": "Frozen Poultry",
        "Rate": build_rate("PerMile", 2.35),
        "RequireTracking": True,
        "SpecialInstructions": [
            "Reefer must be pre-cooled to 34F before pickup.",
            "Driver must call broker before final delivery.",
        ],
    }


def main() -> int:
    original = {
        "NON_LOCAL_MODE": sim.NON_LOCAL_MODE,
        "REQUIRE_SIGNED_VERIFIER": sim.REQUIRE_SIGNED_VERIFIER,
        "ENFORCE_TRUSTED_VERIFIER_REGISTRY": sim.ENFORCE_TRUSTED_VERIFIER_REGISTRY,
    }
    sim.NON_LOCAL_MODE = False
    sim.REQUIRE_SIGNED_VERIFIER = False
    sim.ENFORCE_TRUSTED_VERIFIER_REGISTRY = False

    try:
        validate_message_body("NewLoad", _base_new_load())

        invalid_new_load = _base_new_load()
        invalid_new_load["SpecialInstructions"] = "Call broker before delivery."
        _expect_validation_error(
            "NewLoad",
            invalid_new_load,
            "NewLoad.SpecialInstructions must be a non-empty array",
        )

        valid_bid = {
            "LoadID": "load-special-instructions-001",
            "Rate": build_rate("PerMile", 2.62),
            "SpecialInstructionsAcceptance": {
                "Accepted": True,
                "Exceptions": [],
            },
        }
        validate_message_body("BidRequest", valid_bid)

        invalid_bid = {
            "LoadID": "load-special-instructions-001",
            "Rate": build_rate("PerMile", 2.62),
            "SpecialInstructionsAcceptance": {
                "Accepted": "yes",
            },
        }
        _expect_validation_error(
            "BidRequest",
            invalid_bid,
            "BidRequest.SpecialInstructionsAcceptance.Accepted must be boolean",
        )

        broker = BrokerAgent("Broker Agent")
        carrier = CarrierAgent("Carrier Agent")
        load = broker.post_new_load()
        bid = carrier.create_bid_request(load, bid_amount=2.62)

        bid_missing_acceptance = dict(bid)
        bid_missing_acceptance.pop("SpecialInstructionsAcceptance", None)
        response = broker.respond_to_bid(bid_missing_acceptance, forced_response="Accept")
        _assert(response["ResponseType"] == "Counter", "missing special-instructions acceptance should counter")
        _assert(
            response.get("ReasonCode") == "SpecialInstructionsDispute",
            "missing special-instructions acceptance should counter with SpecialInstructionsDispute",
        )

        bid_with_exception = dict(bid)
        bid_with_exception["SpecialInstructionsAcceptance"] = {
            "Accepted": True,
            "Exceptions": ["Driver must notify broker at each stop arrival/departure."],
        }
        response = broker.respond_to_bid(bid_with_exception, forced_response="Accept")
        _assert(response["ResponseType"] == "Counter", "special-instructions exception should counter")
        _assert(
            response.get("ReasonCode") == "SpecialInstructionsDispute",
            "special-instructions exception should counter with SpecialInstructionsDispute",
        )

        execution_report = {
            "LoadID": "load-special-instructions-001",
            "ContractID": "FAXP-20260301-abc12345",
            "Status": "Booked",
            "Timestamp": now_utc(),
            "VerifiedBadge": "Basic",
            "SpecialInstructions": [
                "Reefer must be pre-cooled to 34F before pickup.",
            ],
            "VerificationResult": {
                "status": "Success",
                "provider": "test-provider",
                "score": 91,
                "token": "opaque-token",
                "source": "implementer-adapter",
                "evidenceRef": "sha256:abcdef",
                "verifiedAt": now_utc(),
            },
        }
        validate_message_body("ExecutionReport", execution_report)

        print("Special-instructions commercial-term checks passed.")
        return 0
    finally:
        sim.NON_LOCAL_MODE = original["NON_LOCAL_MODE"]
        sim.REQUIRE_SIGNED_VERIFIER = original["REQUIRE_SIGNED_VERIFIER"]
        sim.ENFORCE_TRUSTED_VERIFIER_REGISTRY = original["ENFORCE_TRUSTED_VERIFIER_REGISTRY"]


if __name__ == "__main__":
    raise SystemExit(main())
