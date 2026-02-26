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


def _alias_normalization_matrix() -> list[tuple[str, str, str]]:
    return [
        ("Dry Van", "Van", ""),
        ("Reefer", "Reefer", ""),
        ("Flatbed", "Flatbed", ""),
        ("Auto Carrier", "AutoCarrier", ""),
        ("B-Train", "BTrain", ""),
        ("Conestoga", "Flatbed", "Conestoga"),
        ("Container", "Container", ""),
        ("Container - Insultated", "Container", "Insulated"),
        ("Container - Refrigerated", "Container", "Insulated"),
        ("Conveyor", "Conveyor", ""),
        ("Double Drop", "DoubleDrop", "Double"),
        ("Drop Deck Landoll", "StepDeck", "Landoll"),
        ("Dump Trailer", "DumpTrailer", ""),
        ("Flatbed - Air Ride", "Flatbed", "AirRide"),
        ("Flatbed - Contestoga", "Flatbed", "Conestoga"),
        ("Flatbed - Double", "Flatbed", "Double"),
        ("Flatbed - Hazmat", "Flatbed", "Hazmat"),
        ("Flatbed - Hotshot", "Flatbed", "Hotshot"),
        ("Flatbed - Maxi", "Flatbed", "Maxi"),
        ("Flabtbed - Over Dimension", "Flatbed", "OverDimension"),
        ("Hopper Bottom", "HopperBottom", ""),
        ("Lowboy", "Lowboy", ""),
        ("RGN", "RGN", ""),
        ("Lowboy - Over Dimension", "Lowboy", "OverDimension"),
        ("Moving Van", "MovingVan", ""),
        ("Pneumatic", "Pneumatic", ""),
        ("Power Only", "PowerOnly", ""),
        ("Reefer - Air Ride", "Reefer", "AirRide"),
        ("Reefer - Double", "Reefer", "Double"),
        ("Reefer - Hazmat", "Reefer", "Hazmat"),
        ("Reefer - Intermodal", "Reefer", "Intermodal"),
        ("Removeable Gooseneck", "RGN", ""),
        ("Stepdeck", "StepDeck", ""),
        ("Stepdeck - Conestoga", "StepDeck", "Conestoga"),
        ("Straight Box Truck", "StraightBoxTruck", ""),
        ("Stretch Trailer", "Flatbed", "Stretch"),
        ("Tanker - Aluminum", "Tanker", "Aluminum"),
        ("Tanker - Intermodal", "Tanker", "Intermodal"),
        ("Tanker - Steel", "Tanker", "Steel"),
        ("Van - Air Ride", "Van", "AirRide"),
        ("Van - Conestoga", "Van", "Conestoga"),
        ("Van - Hazmat", "Van", "Hazmat"),
        ("Van - Hotshot", "Van", "Hotshot"),
        ("Van - Insulated", "Van", "Insulated"),
        ("Van - Intermodal", "Van", "Intermodal"),
        ("Van - Lift Gate", "Van", "LiftGate"),
        ("Van - Open Top", "Van", "OpenTop"),
        ("Van - Roller Bed", "Van", "RollerBed"),
        ("Van - Triple", "Van", "Triple"),
        ("Van - Vented", "Van", "Vented"),
        ("Sprinter Van", "SprinterVan", ""),
        ("Sprinter Van - Hazmat", "SprinterVan", "Hazmat"),
    ]


def _alias_tag_inference_matrix() -> list[tuple[str, list[str]]]:
    return [
        ("vanhazmat", ["HazmatCapable"]),
        ("reeferintermodal", ["Intermodal"]),
        ("flatbedairride", ["AirRide"]),
        ("flatbeddouble", ["DoubleTrailer"]),
        ("vantriple", ["TripleTrailer"]),
        ("flabtbedoverdimension", ["OverDimensionCapable"]),
    ]


def main() -> int:
    validate_message_body("NewLoad", _base_new_load())

    for equipment_type, expected_class, expected_subclass in _alias_normalization_matrix():
        alias_load = _base_new_load()
        alias_load["EquipmentType"] = equipment_type
        alias_load.pop("EquipmentClass", None)
        alias_load.pop("EquipmentSubClass", None)
        alias_load.pop("EquipmentTags", None)
        validate_message_body("NewLoad", alias_load)
        _assert(
            alias_load["EquipmentClass"] == expected_class,
            f"{equipment_type}: expected EquipmentClass={expected_class}, got {alias_load['EquipmentClass']}",
        )
        actual_subclass = alias_load.get("EquipmentSubClass", "")
        _assert(
            actual_subclass == expected_subclass,
            f"{equipment_type}: expected EquipmentSubClass={expected_subclass}, got {actual_subclass}",
        )

    for equipment_type, expected_tags in _alias_tag_inference_matrix():
        alias_load = _base_new_load()
        alias_load["EquipmentType"] = equipment_type
        alias_load.pop("EquipmentClass", None)
        alias_load.pop("EquipmentSubClass", None)
        alias_load.pop("EquipmentTags", None)
        validate_message_body("NewLoad", alias_load)
        actual_tags = sorted(alias_load.get("EquipmentTags") or [])
        _assert(
            actual_tags == sorted(expected_tags),
            f"{equipment_type}: expected EquipmentTags={sorted(expected_tags)}, got {actual_tags}",
        )

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

    alias_load_search = {
        "OriginState": "TX",
        "DestinationState": "GA",
        "EquipmentType": "Van - Hazmat",
        "EquipmentClass": "van",
        "EquipmentSubClass": "hazmat",
        "RequiredEquipmentTags": ["hazmat"],
        "TrailerLengthMin": 48,
        "TrailerLengthMax": 53,
        "PickupDate": "2026-03-01",
        "RateModel": "PerMile",
        "UnitBasis": "mile",
        "MaxRate": 2.8,
    }
    validate_message_body("LoadSearch", alias_load_search)
    _assert(
        alias_load_search["EquipmentClass"] == "Van",
        "LoadSearch EquipmentClass alias should canonicalize to Van",
    )
    _assert(
        alias_load_search["EquipmentSubClass"] == "Hazmat",
        "LoadSearch EquipmentSubClass alias should canonicalize to Hazmat",
    )
    _assert(
        alias_load_search["RequiredEquipmentTags"] == ["HazmatCapable"],
        "LoadSearch tag aliases should canonicalize to HazmatCapable",
    )

    alias_truck_search = {
        "LocationRadiusMiles": 120,
        "OriginState": "TX",
        "EquipmentType": "Van - Hazmat",
        "EquipmentClass": "van",
        "EquipmentSubClass": "hazmat",
        "RequiredEquipmentTags": ["hazmat"],
        "TrailerLengthMin": 48,
        "TrailerLengthMax": 53,
        "AvailableFrom": "2026-03-01",
        "AvailableTo": "2026-03-03",
        "RateModel": "PerMile",
        "UnitBasis": "mile",
        "MinRate": 2.0,
        "MaxRate": 3.0,
    }
    validate_message_body("TruckSearch", alias_truck_search)
    _assert(
        alias_truck_search["EquipmentClass"] == "Van",
        "TruckSearch EquipmentClass alias should canonicalize to Van",
    )
    _assert(
        alias_truck_search["EquipmentSubClass"] == "Hazmat",
        "TruckSearch EquipmentSubClass alias should canonicalize to Hazmat",
    )
    _assert(
        alias_truck_search["RequiredEquipmentTags"] == ["HazmatCapable"],
        "TruckSearch tag aliases should canonicalize to HazmatCapable",
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

    load["EquipmentType"] = "Van - Hazmat"
    load["EquipmentClass"] = "Van"
    load["EquipmentSubClass"] = "Hazmat"
    load["EquipmentTags"] = ["HazmatCapable"]
    load["TrailerLength"] = 53
    truck = carrier.post_new_truck(rate_model="PerMile")
    truck["EquipmentType"] = "Van - Hazmat"
    truck["EquipmentClass"] = "Van"
    truck["EquipmentSubClass"] = "Hazmat"
    truck["EquipmentTags"] = ["HazmatCapable"]
    truck["TrailerLength"] = 53

    parity_load_filters = dict(alias_load_search)
    parity_load_filters["PickupDate"] = load["PickupEarliest"]
    parity_load_matches = broker.search_loads(parity_load_filters)
    _assert(
        len(parity_load_matches) >= 1,
        "LoadSearch should match using canonicalized alias filters for Van/Hazmat",
    )
    parity_truck_filters = dict(alias_truck_search)
    parity_truck_filters["AvailableFrom"] = truck["AvailabilityDate"]
    parity_truck_filters["AvailableTo"] = truck["AvailabilityDate"]
    parity_truck_matches = carrier.search_trucks(parity_truck_filters)
    _assert(
        len(parity_truck_matches) >= 1,
        "TruckSearch should match using canonicalized alias filters for Van/Hazmat",
    )

    parity_load_filters_no_match = dict(alias_load_search)
    parity_load_filters_no_match["EquipmentSubClass"] = "air ride"
    validate_message_body("LoadSearch", parity_load_filters_no_match)
    _assert(
        not broker.search_loads(parity_load_filters_no_match),
        "LoadSearch subclass mismatch should produce no matches",
    )
    parity_truck_filters_no_match = dict(alias_truck_search)
    parity_truck_filters_no_match["EquipmentSubClass"] = "air ride"
    validate_message_body("TruckSearch", parity_truck_filters_no_match)
    _assert(
        not carrier.search_trucks(parity_truck_filters_no_match),
        "TruckSearch subclass mismatch should produce no matches",
    )

    truck_bid = broker.create_truck_bid_request(truck, bid_amount=2.62)
    truck_bid["EquipmentAcceptance"]["EquipmentClass"] = "Flatbed"
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
