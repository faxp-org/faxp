#!/usr/bin/env python3
"""Regression checks for booking-plane driver configuration terms."""

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
        "LoadID": "load-driver-config-001",
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
        "DriverConfiguration": "Team",
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
        invalid_new_load["DriverConfiguration"] = "Duo"
        _expect_validation_error(
            "NewLoad",
            invalid_new_load,
            "NewLoad.DriverConfiguration must be one of",
        )

        valid_search = {
            "OriginState": "TX",
            "DestinationState": "GA",
            "EquipmentType": "Reefer",
            "PickupDate": "2026-03-01",
            "RateModel": "PerMile",
            "UnitBasis": "mile",
            "MaxRate": 2.8,
            "RequiredDriverConfiguration": "Team",
        }
        validate_message_body("LoadSearch", valid_search)

        invalid_search = dict(valid_search)
        invalid_search["RequiredDriverConfiguration"] = "Any"
        _expect_validation_error(
            "LoadSearch",
            invalid_search,
            "LoadSearch.RequiredDriverConfiguration must be one of",
        )

        valid_bid = {
            "LoadID": "load-driver-config-001",
            "Rate": build_rate("PerMile", 2.62),
            "DriverConfigurationAcceptance": {
                "Accepted": True,
                "DriverConfiguration": "Team",
            },
        }
        validate_message_body("BidRequest", valid_bid)

        invalid_bid = {
            "LoadID": "load-driver-config-001",
            "Rate": build_rate("PerMile", 2.62),
            "DriverConfigurationAcceptance": {
                "Accepted": "yes",
            },
        }
        _expect_validation_error(
            "BidRequest",
            invalid_bid,
            "BidRequest.DriverConfigurationAcceptance.Accepted must be boolean",
        )

        broker = BrokerAgent("Broker Agent")
        carrier = CarrierAgent("Carrier Agent")

        load = broker.post_new_load(rate_model="PerMile")
        load["DriverConfiguration"] = "Team"
        bid = carrier.create_bid_request(load, bid_amount=2.62)
        bid["DriverConfigurationAcceptance"]["DriverConfiguration"] = "Single"
        response = broker.respond_to_bid(bid, forced_response="Accept")
        _assert(response["ResponseType"] == "Counter", "driver configuration mismatch should counter")
        _assert(
            response.get("ReasonCode") == "DriverConfigurationDispute",
            "driver configuration mismatch should use DriverConfigurationDispute",
        )

        matched_bid = carrier.create_bid_request(load, bid_amount=2.62)
        matched_bid["DriverConfigurationAcceptance"]["DriverConfiguration"] = "Team"
        matched_response = broker.respond_to_bid(matched_bid, forced_response="Accept")
        _assert(
            matched_response["ResponseType"] == "Accept",
            "matching driver configuration should be accepted",
        )

        truck = carrier.post_new_truck(rate_model="PerMile")
        truck["DriverConfiguration"] = "Team"
        truck_bid = broker.create_truck_bid_request(truck, bid_amount=2.62)
        truck_bid["DriverConfigurationAcceptance"]["DriverConfiguration"] = "Single"
        truck_response = carrier.respond_to_truck_bid(truck_bid, forced_response="Accept")
        _assert(
            truck_response["ResponseType"] == "Counter",
            "truck flow driver configuration mismatch should counter",
        )
        _assert(
            truck_response.get("ReasonCode") == "DriverConfigurationDispute",
            "truck flow mismatch should use DriverConfigurationDispute",
        )

        search_broker = BrokerAgent("Broker Agent")
        team_load = search_broker.post_new_load(rate_model="PerMile")
        team_load["DriverConfiguration"] = "Team"
        single_load = search_broker.post_new_load(rate_model="PerMile")
        single_load["DriverConfiguration"] = "Single"

        team_filter = carrier.create_load_search(force_no_match=False, rate_model="PerMile")
        team_filter["RequiredDriverConfiguration"] = "Team"
        team_results = search_broker.search_loads(team_filter)
        _assert(team_results, "team driver filter should return matches")
        _assert(
            all(item.get("DriverConfiguration") == "Team" for item in team_results),
            "team driver filter returned non-team loads",
        )

        execution_report = {
            "LoadID": "load-driver-config-001",
            "ContractID": "FAXP-20260301-abc12345",
            "Status": "Booked",
            "Timestamp": now_utc(),
            "VerifiedBadge": "Basic",
            "DriverTerms": {"DriverConfiguration": "Single"},
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

        print("Driver configuration term checks passed.")
        return 0
    finally:
        sim.NON_LOCAL_MODE = original["NON_LOCAL_MODE"]
        sim.REQUIRE_SIGNED_VERIFIER = original["REQUIRE_SIGNED_VERIFIER"]
        sim.ENFORCE_TRUSTED_VERIFIER_REGISTRY = original["ENFORCE_TRUSTED_VERIFIER_REGISTRY"]


if __name__ == "__main__":
    raise SystemExit(main())
