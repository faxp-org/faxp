#!/usr/bin/env python3
"""Minimal regression checks for optional shipper -> broker -> carrier orchestration."""

from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from faxp_mvp_simulation import (  # noqa: E402
    BrokerAgent,
    CarrierAgent,
    ShipperAgent,
    VERIFICATION_POLICY_PROFILE_ID,
    evaluate_verification_policy_decision,
)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _mock_success_verification_result() -> dict:
    return {
        "status": "Success",
        "provider": "MockBiometricProvider",
        "category": "Biometric",
        "method": "LivenessPlusDocument",
        "assuranceLevel": "AAL2",
        "score": 94,
        "token": "test-token-shipper-flow",
        "source": "simulated",
        "provenance": "simulated",
        "verifiedAt": "2026-02-27T00:00:00Z",
        "evidenceRef": "sha256:testshipperorchestration",
    }


def _run_positive_flow() -> None:
    broker = BrokerAgent("Broker Agent")
    carrier = CarrierAgent("Carrier Agent")
    shipper = ShipperAgent("Shipper Agent")

    tender = shipper.post_tender()
    ingested = broker.ingest_shipper_tender(tender)

    load_search = carrier.create_load_search_for_load(ingested, force_no_match=False)
    matches = broker.search_loads(load_search)
    _assert(matches, "Expected carrier to find shipper-origin load.")
    selected = matches[0]
    _assert(
        selected.get("LoadID") == ingested.get("LoadID"),
        "Expected selected load to match ingested shipper tender LoadID.",
    )

    bid_request = carrier.create_bid_request(selected)
    bid_response = broker.respond_to_bid(bid_request, forced_response="Accept")
    _assert(bid_response.get("ResponseType") == "Accept", "Expected bid to be accepted.")

    verification_result = _mock_success_verification_result()
    policy_decision = evaluate_verification_policy_decision(
        verification_result,
        profile_id=VERIFICATION_POLICY_PROFILE_ID,
        risk_tier=1,
    )
    _assert(policy_decision.get("ShouldBook") is True, "Expected policy decision to allow booking.")

    report = broker.create_execution_report(
        load_id=selected["LoadID"],
        bid_request=bid_request,
        verified_badge="Premium",
        verification_result=verification_result,
        policy_decision=policy_decision,
    )
    carrier.mark_booking_complete(report)

    _assert(report.get("Status") == "Booked", "ExecutionReport status must be Booked.")
    _assert(selected["LoadID"] in broker.completed_bookings, "Broker booking should be marked complete.")
    _assert(selected["LoadID"] in carrier.completed_bookings, "Carrier booking should be marked complete.")


def _run_invalid_tender_negative() -> None:
    broker = BrokerAgent("Broker Agent")
    shipper = ShipperAgent("Shipper Agent")
    invalid = shipper.post_tender()
    invalid.pop("Origin", None)
    try:
        broker.ingest_shipper_tender(invalid)
    except ValueError as exc:
        _assert("NewLoad missing required fields" in str(exc), f"Unexpected error: {exc}")
        _assert("Origin" in str(exc), f"Unexpected error: {exc}")
        return
    raise AssertionError("Expected invalid shipper tender ingestion to fail closed.")


def _run_force_no_match_branch() -> None:
    broker = BrokerAgent("Broker Agent")
    carrier = CarrierAgent("Carrier Agent")
    shipper = ShipperAgent("Shipper Agent")

    ingested = broker.ingest_shipper_tender(shipper.post_tender())
    load_search = carrier.create_load_search_for_load(ingested, force_no_match=True)
    matches = broker.search_loads(load_search)
    _assert(not matches, "Force-no-match branch should return no search results.")


def main() -> int:
    _run_positive_flow()
    _run_invalid_tender_negative()
    _run_force_no_match_branch()
    print("Shipper orchestration minimal checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
