#!/usr/bin/env python3
"""Regression checks for booking-plane load reference number terms."""

from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import faxp_mvp_simulation as sim  # noqa: E402
from faxp_mvp_simulation import BrokerAgent, CarrierAgent, now_utc, validate_message_body  # noqa: E402


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
    broker = BrokerAgent("Broker Agent")
    return broker.post_new_load(rate_model="PerMile")


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
        valid_new_load = _base_new_load()
        validate_message_body("NewLoad", valid_new_load)

        invalid_empty_refs = _base_new_load()
        invalid_empty_refs["LoadReferenceNumbers"] = {}
        _expect_validation_error(
            "NewLoad",
            invalid_empty_refs,
            "must include at least one reference number",
        )

        invalid_unknown_field = _base_new_load()
        invalid_unknown_field["LoadReferenceNumbers"] = {"LegacyReference": "LEG-1"}
        _expect_validation_error(
            "NewLoad",
            invalid_unknown_field,
            "contains unsupported fields",
        )

        invalid_additional_entry = _base_new_load()
        invalid_additional_entry["LoadReferenceNumbers"] = {
            "PrimaryReferenceNumber": "BRK-1",
            "Additional": [{"ReferenceType": "PartnerReference"}],
        }
        _expect_validation_error(
            "NewLoad",
            invalid_additional_entry,
            "missing required fields",
        )

        broker = BrokerAgent("Broker Agent")
        carrier = CarrierAgent("Carrier Agent")
        load = broker.post_new_load(rate_model="PerMile")
        bid = carrier.create_bid_request(load, bid_amount=2.62)
        response = broker.respond_to_bid(bid, forced_response="Accept")
        _assert(response["ResponseType"] == "Accept", "valid bid should be accepted")

        execution_report = broker.create_execution_report(
            load_id=load["LoadID"],
            bid_request=bid,
            verified_badge="Basic",
            verification_result={
                "status": "Success",
                "provider": "test-provider",
                "score": 91,
                "token": "opaque-token",
                "source": "implementer-adapter",
                "evidenceRef": "sha256:abcdef",
                "verifiedAt": now_utc(),
            },
        )
        _assert(
            "LoadReferenceNumbers" in execution_report,
            "ExecutionReport should snapshot LoadReferenceNumbers when present in NewLoad",
        )
        validate_message_body("ExecutionReport", execution_report)

        invalid_execution_report = dict(execution_report)
        invalid_execution_report["LoadReferenceNumbers"] = {"SecondaryReferenceNumber": 123}
        _expect_validation_error(
            "ExecutionReport",
            invalid_execution_report,
            "ExecutionReport.LoadReferenceNumbers.SecondaryReferenceNumber must be a string",
        )

        print("Load reference number term checks passed.")
        return 0
    finally:
        sim.NON_LOCAL_MODE = original["NON_LOCAL_MODE"]
        sim.REQUIRE_SIGNED_VERIFIER = original["REQUIRE_SIGNED_VERIFIER"]
        sim.ENFORCE_TRUSTED_VERIFIER_REGISTRY = original["ENFORCE_TRUSTED_VERIFIER_REGISTRY"]


if __name__ == "__main__":
    raise SystemExit(main())
