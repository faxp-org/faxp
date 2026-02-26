#!/usr/bin/env python3
"""Regression checks for booking-plane multi-stop commercial terms."""

from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from faxp_mvp_simulation import BrokerAgent, CarrierAgent, build_rate, validate_message_body  # noqa: E402


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
        "LoadID": "load-multi-stop-001",
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
        "Stops": [
            {
                "StopSequence": 1,
                "StopType": "Pickup",
                "Location": {"city": "Dallas", "state": "TX", "zip": "75201"},
                "WindowOpen": "2026-03-01",
                "WindowClose": "2026-03-02",
            },
            {
                "StopSequence": 2,
                "StopType": "Pickup",
                "Location": {"city": "Little Rock", "state": "AR", "zip": "72201"},
                "WindowOpen": "2026-03-01",
                "WindowClose": "2026-03-02",
            },
            {
                "StopSequence": 3,
                "StopType": "Drop",
                "Location": {"city": "Atlanta", "state": "GA", "zip": "30301"},
                "WindowOpen": "2026-03-03",
                "WindowClose": "2026-03-04",
            },
        ],
    }


def main() -> int:
    valid_load = _base_new_load()
    validate_message_body("NewLoad", valid_load)

    bad_sequence = _base_new_load()
    bad_sequence["Stops"][1]["StopSequence"] = 3
    _expect_validation_error(
        "NewLoad",
        bad_sequence,
        "StopSequence values must be contiguous starting at 1",
    )

    bad_origin = _base_new_load()
    bad_origin["Stops"][0]["Location"]["zip"] = "73301"
    _expect_validation_error(
        "NewLoad",
        bad_origin,
        "NewLoad.Stops[0].Location must match NewLoad.Origin",
    )

    valid_search = {
        "OriginState": "TX",
        "DestinationState": "GA",
        "EquipmentType": "Reefer",
        "PickupDate": "2026-03-01",
        "RateModel": "PerMile",
        "UnitBasis": "mile",
        "MaxRate": 2.8,
        "RequireMultiStop": True,
        "StopCountMin": 3,
        "StopCountMax": 6,
        "RequiredStopTypes": ["Pickup", "Drop"],
        "RequireTracking": True,
    }
    validate_message_body("LoadSearch", valid_search)

    bad_search = dict(valid_search)
    bad_search["RequiredStopTypes"] = ["Pickup", "Unload"]
    _expect_validation_error(
        "LoadSearch",
        bad_search,
        "RequiredStopTypes[1] must be one of",
    )

    broker = BrokerAgent("Broker Agent")
    carrier = CarrierAgent("Carrier Agent")
    posted_load = broker.post_new_load(rate_model="PerMile")
    bid = carrier.create_bid_request(posted_load, bid_amount=2.62)
    bid["StopPlanAcceptance"]["StopCount"] = bid["StopPlanAcceptance"]["StopCount"] + 1
    response = broker.respond_to_bid(bid, forced_response="Accept")
    _assert(response["ResponseType"] == "Counter", "stop mismatch must produce counter response")
    _assert(
        response.get("ReasonCode") == "StopPlanDispute",
        "stop mismatch counter must use StopPlanDispute reason code",
    )

    rejected_acceptance = {
        "LoadID": "load-multi-stop-001",
        "Rate": build_rate("PerMile", 2.60),
        "StopPlanAcceptance": {
            "Accepted": False,
            "StopCount": 3,
            "StopTypes": ["Pickup", "Drop"],
        },
    }
    validate_message_body("BidRequest", rejected_acceptance)

    invalid_acceptance = {
        "LoadID": "load-multi-stop-001",
        "Rate": build_rate("PerMile", 2.60),
        "StopPlanAcceptance": {
            "Accepted": True,
            "StopCount": 1,
        },
    }
    _expect_validation_error(
        "BidRequest",
        invalid_acceptance,
        "StopCount must be an integer >= 2",
    )

    print("Multi-stop commercial-term checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
