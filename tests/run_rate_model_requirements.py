#!/usr/bin/env python3
"""Regression checks for active rate model requirement enforcement."""

from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from faxp_mvp_simulation import (  # noqa: E402
    BrokerAgent,
    CarrierAgent,
    RATE_MODEL_REQUIREMENTS,
    build_rate,
    configure_mileage_dispute_policy,
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


def main() -> int:
    per_mile_req = RATE_MODEL_REQUIREMENTS.get("PerMile") or {}
    flat_req = RATE_MODEL_REQUIREMENTS.get("Flat") or {}
    per_pallet_req = RATE_MODEL_REQUIREMENTS.get("PerPallet") or {}
    cwt_req = RATE_MODEL_REQUIREMENTS.get("CWT") or {}
    _assert(per_mile_req.get("status") == "active", "PerMile requirements must be active.")
    _assert(flat_req.get("status") == "active", "Flat requirements must be active.")
    _assert(per_pallet_req.get("status") == "active", "PerPallet requirements must be active.")
    _assert(cwt_req.get("status") == "active", "CWT requirements must be active.")
    _assert("UnitBasis" in (per_mile_req.get("requiredFields") or []), "PerMile must require UnitBasis.")
    _assert("AgreedMiles" in (per_mile_req.get("requiredFields") or []), "PerMile must require AgreedMiles.")
    _assert("MilesSource" in (per_mile_req.get("requiredFields") or []), "PerMile must require MilesSource.")
    _assert("UnitBasis" in (flat_req.get("requiredFields") or []), "Flat must require UnitBasis.")
    _assert("Quantity" in (per_pallet_req.get("requiredFields") or []), "PerPallet must require Quantity.")
    _assert("Quantity" in (cwt_req.get("requiredFields") or []), "CWT must require Quantity.")

    valid_per_mile = build_rate("PerMile", 2.62)
    validate_message_body("BidRequest", {"LoadID": "load-permile-ok", "Rate": valid_per_mile})

    valid_flat = build_rate("Flat", 1950.0)
    validate_message_body("BidRequest", {"LoadID": "load-flat-ok", "Rate": valid_flat})

    valid_per_pallet = build_rate("PerPallet", 82.0)
    validate_message_body("BidRequest", {"LoadID": "load-pallet-ok", "Rate": valid_per_pallet})

    valid_cwt = build_rate("CWT", 5.1)
    validate_message_body("BidRequest", {"LoadID": "load-cwt-ok", "Rate": valid_cwt})

    missing_unit_basis = {"RateModel": "PerMile", "Amount": 2.62, "Currency": "USD"}
    _expect_validation_error(
        "BidRequest",
        {"LoadID": "load-permile-missing-unit", "Rate": missing_unit_basis},
        "UnitBasis is required for RateModel 'PerMile'",
    )

    invalid_per_mile_basis = build_rate("PerMile", 2.62, UnitBasis="load")
    _expect_validation_error(
        "BidRequest",
        {"LoadID": "load-permile-bad-basis", "Rate": invalid_per_mile_basis},
        "UnitBasis must be one of ['mile']",
    )

    invalid_flat_basis = build_rate("Flat", 1950.0, UnitBasis="mile")
    _expect_validation_error(
        "BidRequest",
        {"LoadID": "load-flat-bad-basis", "Rate": invalid_flat_basis},
        "UnitBasis must be one of ['load']",
    )

    missing_miles_source = build_rate("PerMile", 2.62)
    missing_miles_source.pop("MilesSource", None)
    _expect_validation_error(
        "BidRequest",
        {"LoadID": "load-permile-missing-source", "Rate": missing_miles_source},
        "MilesSource is required for RateModel 'PerMile'",
    )

    mismatch_distance_miles = build_rate("PerMile", 2.62, AgreedMiles=925.5, DistanceMiles=920.0)
    _expect_validation_error(
        "BidRequest",
        {"LoadID": "load-permile-distance-mismatch", "Rate": mismatch_distance_miles},
        "DistanceMiles must equal AgreedMiles",
    )

    invalid_per_pallet_quantity = build_rate("PerPallet", 82.0, Quantity=0)
    _expect_validation_error(
        "BidRequest",
        {"LoadID": "load-pallet-bad-quantity", "Rate": invalid_per_pallet_quantity},
        "Quantity must be a positive number for RateModel 'PerPallet'",
    )

    invalid_cwt_basis = build_rate("CWT", 5.1, UnitBasis="pallet")
    _expect_validation_error(
        "BidRequest",
        {"LoadID": "load-cwt-bad-basis", "Rate": invalid_cwt_basis},
        "UnitBasis must be one of ['cwt']",
    )

    broker = BrokerAgent("Broker Agent")
    carrier = CarrierAgent("Carrier Agent")
    posted_load = broker.post_new_load(rate_model="PerMile")
    configure_mileage_dispute_policy(
        policy="balanced",
        abs_tolerance_miles=25.0,
        rel_tolerance_ratio=0.02,
    )
    matched_bid = carrier.create_bid_request(posted_load)
    matched_response = broker.respond_to_bid(matched_bid, forced_response="Accept")
    _assert(matched_response["ResponseType"] == "Accept", "matching agreed miles should accept.")

    tolerated_dispute_bid = carrier.create_bid_request(posted_load)
    tolerated_dispute_bid["Rate"]["AgreedMiles"] = (
        float(tolerated_dispute_bid["Rate"]["AgreedMiles"]) + 15.0
    )
    tolerated_dispute_response = broker.respond_to_bid(tolerated_dispute_bid, forced_response="Accept")
    _assert(
        tolerated_dispute_response["ResponseType"] == "Accept",
        "balanced policy should accept small mileage variances within tolerance.",
    )
    _assert(
        tolerated_dispute_response.get("ReasonCode") == "AcceptedWithinMileageTolerance",
        "balanced policy should annotate accepted within-tolerance mileage variance.",
    )

    disputed_bid = carrier.create_bid_request(posted_load)
    disputed_bid["Rate"]["AgreedMiles"] = float(disputed_bid["Rate"]["AgreedMiles"]) + 40.0
    disputed_response = broker.respond_to_bid(disputed_bid, forced_response="Accept")
    _assert(
        disputed_response["ResponseType"] == "Counter",
        "balanced policy should counter large mileage variances beyond tolerance.",
    )
    _assert(
        disputed_response.get("ReasonCode") == "MileageDispute",
        "mileage mismatch counter should carry MileageDispute reason code.",
    )

    configure_mileage_dispute_policy(
        policy="strict",
        abs_tolerance_miles=25.0,
        rel_tolerance_ratio=0.02,
    )
    strict_dispute_bid = carrier.create_bid_request(posted_load)
    strict_dispute_bid["Rate"]["AgreedMiles"] = (
        float(strict_dispute_bid["Rate"]["AgreedMiles"]) + 2.0
    )
    strict_dispute_response = broker.respond_to_bid(strict_dispute_bid, forced_response="Accept")
    _assert(
        strict_dispute_response["ResponseType"] == "Counter",
        "strict policy should counter any non-zero mileage variance.",
    )
    _assert(
        strict_dispute_response.get("ReasonCode") == "MileageDispute",
        "strict policy should keep MileageDispute reason code for variance counters.",
    )

    print("Rate model requirement checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
