#!/usr/bin/env python3
"""Regression checks for booking-plane equipment taxonomy and compatibility terms."""

from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from faxp_mvp_simulation import (  # noqa: E402
    BrokerAgent,
    CarrierAgent,
    build_rate,
    validate_message_body,
)


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
        "LoadID": "load-equipment-001",
        "Origin": {"city": "Dallas", "state": "TX", "zip": "75201"},
        "Destination": {"city": "Atlanta", "state": "GA", "zip": "30301"},
        "PickupEarliest": "2026-03-01",
        "PickupLatest": "2026-03-02",
        "LoadType": "Full",
        "EquipmentType": "Reefer - Air Ride",
        "EquipmentClass": "Reefer",
        "EquipmentSubClass": "AirRide",
        "EquipmentTags": ["AirRide"],
        "TrailerLength": 53,
        "Weight": 42000,
        "Commodity": "Frozen Poultry",
        "Rate": build_rate("PerMile", 2.35),
        "RequireTracking": True,
    }


def main() -> int:
    validate_message_body("NewLoad", _base_new_load())

    special_missing_desc = _base_new_load()
    special_missing_desc["EquipmentClass"] = "Special"
    special_missing_desc["EquipmentType"] = "Custom Platform"
    special_missing_desc.pop("EquipmentSpecialDescription", None)
    _expect_validation_error(
        "NewLoad",
        special_missing_desc,
        "EquipmentSpecialDescription is required when EquipmentClass is 'Special'",
    )

    valid_search = {
        "OriginState": "TX",
        "DestinationState": "GA",
        "EquipmentType": "Reefer",
        "EquipmentClass": "Reefer",
        "EquipmentSubClass": "AirRide",
        "RequiredEquipmentTags": ["AirRide"],
        "TrailerLengthMin": 53,
        "TrailerLengthMax": 53,
        "PickupDate": "2026-03-01",
        "RateModel": "PerMile",
        "UnitBasis": "mile",
        "MaxRate": 2.8,
    }
    validate_message_body("LoadSearch", valid_search)

    invalid_search = dict(valid_search)
    invalid_search["RequiredEquipmentTags"] = ["UnknownTag"]
    _expect_validation_error(
        "LoadSearch",
        invalid_search,
        "RequiredEquipmentTags[0] must be one of",
    )

    valid_bid = {
        "LoadID": "load-equipment-001",
        "Rate": build_rate("PerMile", 2.62),
        "EquipmentAcceptance": {
            "Accepted": True,
            "EquipmentClass": "Reefer",
            "EquipmentSubClass": "AirRide",
            "EquipmentTags": ["AirRide"],
            "TrailerLength": 53,
            "TrailerLengthMin": 48,
            "TrailerLengthMax": 53,
        },
    }
    validate_message_body("BidRequest", valid_bid)

    invalid_bid = {
        "LoadID": "load-equipment-001",
        "Rate": build_rate("PerMile", 2.62),
        "EquipmentAcceptance": {
            "Accepted": True,
            "EquipmentClass": "ReeferX",
        },
    }
    _expect_validation_error(
        "BidRequest",
        invalid_bid,
        "BidRequest.EquipmentAcceptance.EquipmentClass must be one of",
    )

    broker = BrokerAgent("Broker Agent")
    carrier = CarrierAgent("Carrier Agent")
    load = broker.post_new_load(rate_model="PerMile")
    search_results = broker.search_loads(carrier.create_load_search(False, "PerMile"))
    _assert(search_results, "equipment-compatible load search should return results")

    bid = carrier.create_bid_request(load, bid_amount=2.62)
    bid["EquipmentAcceptance"]["EquipmentClass"] = "Flatbed"
    response = broker.respond_to_bid(bid, forced_response="Accept")
    _assert(response["ResponseType"] == "Counter", "equipment mismatch must produce counter response")
    _assert(
        response.get("ReasonCode") == "EquipmentCompatibilityDispute",
        "equipment mismatch counter must carry EquipmentCompatibilityDispute reason code",
    )

    relaxed_length_load = broker.post_new_load(rate_model="PerMile")
    relaxed_length_load["TrailerLength"] = 48
    relaxed_length_bid = carrier.create_bid_request(relaxed_length_load, bid_amount=2.62)
    relaxed_length_bid["EquipmentAcceptance"]["TrailerLength"] = 53
    relaxed_length_bid["EquipmentAcceptance"]["TrailerLengthMin"] = 48
    relaxed_length_bid["EquipmentAcceptance"]["TrailerLengthMax"] = 53
    relaxed_length_response = broker.respond_to_bid(relaxed_length_bid, forced_response="Accept")
    _assert(
        relaxed_length_response["ResponseType"] == "Accept",
        "larger trailer length should be accepted when it satisfies requested range",
    )

    strict_length_bid = carrier.create_bid_request(relaxed_length_load, bid_amount=2.62)
    strict_length_bid["EquipmentAcceptance"].pop("TrailerLengthMin", None)
    strict_length_bid["EquipmentAcceptance"].pop("TrailerLengthMax", None)
    strict_length_bid["EquipmentAcceptance"]["TrailerLength"] = 53
    strict_length_response = broker.respond_to_bid(strict_length_bid, forced_response="Accept")
    _assert(
        strict_length_response["ResponseType"] == "Counter",
        "without explicit trailer length range, trailer length mismatch should counter",
    )
    _assert(
        strict_length_response.get("ReasonCode") == "EquipmentCompatibilityDispute",
        "strict trailer length mismatch should use EquipmentCompatibilityDispute",
    )

    truck = carrier.post_new_truck(rate_model="PerMile")
    truck_bid = broker.create_truck_bid_request(truck, bid_amount=2.62)
    truck_bid["EquipmentAcceptance"]["EquipmentClass"] = "Van"
    truck_response = carrier.respond_to_truck_bid(truck_bid, forced_response="Accept")
    _assert(truck_response["ResponseType"] == "Counter", "truck equipment mismatch must counter")
    _assert(
        truck_response.get("ReasonCode") == "EquipmentCompatibilityDispute",
        "truck equipment mismatch should carry EquipmentCompatibilityDispute reason code",
    )

    print("Equipment taxonomy and compatibility checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
