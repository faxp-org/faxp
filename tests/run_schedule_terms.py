#!/usr/bin/env python3
"""Regression checks for booking-plane schedule commitment terms."""

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
        "LoadID": "load-schedule-001",
        "Origin": {"city": "Dallas", "state": "TX", "zip": "75201"},
        "Destination": {"city": "Atlanta", "state": "GA", "zip": "30301"},
        "PickupEarliest": "2026-03-01",
        "PickupLatest": "2026-03-02",
        "DeliveryEarliest": "2026-03-03",
        "DeliveryLatest": "2026-03-04",
        "PickupTimeWindow": {
            "Start": "2026-03-01T08:00:00-05:00",
            "End": "2026-03-01T12:00:00-05:00",
            "TimeZone": "America/Chicago",
        },
        "DeliveryTimeWindow": {
            "Start": "2026-03-03T10:00:00-05:00",
            "End": "2026-03-03T10:00:00-05:00",
            "TimeZone": "America/New_York",
        },
        "LoadType": "Full",
        "EquipmentType": "Reefer",
        "TrailerLength": 53,
        "Weight": 42000,
        "Commodity": "Frozen Poultry",
        "Rate": build_rate("PerMile", 2.35),
        "RequireTracking": True,
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

        bad_pickup_range = _base_new_load()
        bad_pickup_range["PickupEarliest"] = "2026-03-03"
        bad_pickup_range["PickupLatest"] = "2026-03-01"
        _expect_validation_error(
            "NewLoad",
            bad_pickup_range,
            "PickupEarliest must be <= PickupLatest",
        )

        bad_delivery_pair = _base_new_load()
        del bad_delivery_pair["DeliveryLatest"]
        _expect_validation_error(
            "NewLoad",
            bad_delivery_pair,
            "must include both DeliveryEarliest and DeliveryLatest",
        )

        bad_window_order = _base_new_load()
        bad_window_order["PickupTimeWindow"] = {
            "Start": "2026-03-01T13:00:00-05:00",
            "End": "2026-03-01T12:00:00-05:00",
            "TimeZone": "America/Chicago",
        }
        _expect_validation_error(
            "NewLoad",
            bad_window_order,
            "PickupTimeWindow.Start must be <= End",
        )

        valid_bid = {
            "LoadID": "load-schedule-001",
            "Rate": build_rate("PerMile", 2.62),
            "ScheduleAcceptance": {
                "Accepted": True,
                "Exceptions": [],
                "PickupTimeWindow": {
                    "Start": "2026-03-01T08:00:00-05:00",
                    "End": "2026-03-01T12:00:00-05:00",
                    "TimeZone": "America/Chicago",
                },
            },
        }
        validate_message_body("BidRequest", valid_bid)

        bad_acceptance = {
            "LoadID": "load-schedule-001",
            "Rate": build_rate("PerMile", 2.62),
            "ScheduleAcceptance": {"Accepted": "yes"},
        }
        _expect_validation_error(
            "BidRequest",
            bad_acceptance,
            "BidRequest.ScheduleAcceptance.Accepted must be boolean",
        )

        broker = BrokerAgent("Broker Agent")
        carrier = CarrierAgent("Carrier Agent")
        load = broker.post_new_load(rate_model="PerMile")
        bid = carrier.create_bid_request(load, bid_amount=2.62)

        bid_with_exception = dict(bid)
        bid_with_exception["ScheduleAcceptance"] = {
            "Accepted": True,
            "Exceptions": ["Cannot guarantee delivery window without shipper confirmation."],
        }
        response = broker.respond_to_bid(bid_with_exception, forced_response="Accept")
        _assert(response["ResponseType"] == "Counter", "schedule exception should counter")
        _assert(
            response.get("ReasonCode") == "ScheduleWindowDispute",
            "schedule exception should counter with ScheduleWindowDispute",
        )

        execution_report = {
            "LoadID": "load-schedule-001",
            "ContractID": "FAXP-20260301-abc12345",
            "Status": "Booked",
            "Timestamp": now_utc(),
            "VerifiedBadge": "Basic",
            "ScheduleTerms": {
                "PickupEarliest": "2026-03-01",
                "PickupLatest": "2026-03-02",
                "DeliveryEarliest": "2026-03-03",
                "DeliveryLatest": "2026-03-04",
                "PickupTimeWindow": {
                    "Start": "2026-03-01T08:00:00-05:00",
                    "End": "2026-03-01T12:00:00-05:00",
                    "TimeZone": "America/Chicago",
                },
            },
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

        print("Schedule commitment checks passed.")
        return 0
    finally:
        sim.NON_LOCAL_MODE = original["NON_LOCAL_MODE"]
        sim.REQUIRE_SIGNED_VERIFIER = original["REQUIRE_SIGNED_VERIFIER"]
        sim.ENFORCE_TRUSTED_VERIFIER_REGISTRY = original["ENFORCE_TRUSTED_VERIFIER_REGISTRY"]


if __name__ == "__main__":
    raise SystemExit(main())
