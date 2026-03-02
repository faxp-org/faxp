#!/usr/bin/env python3
"""Regression checks for composite booking-plane scenarios."""

from __future__ import annotations

from pathlib import Path
import json
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import faxp_mvp_simulation as sim  # noqa: E402
from faxp_mvp_simulation import BrokerAgent, CarrierAgent, now_utc, validate_message_body  # noqa: E402


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _build_execution_report() -> dict:
    broker = BrokerAgent("Broker Agent")
    carrier = CarrierAgent("Carrier Agent")
    load = broker.post_new_load(rate_model="PerMile")
    bid = carrier.create_bid_request(load, bid_amount=2.62)
    return broker.create_execution_report(
        load_id=bid["LoadID"],
        bid_request=bid,
        verified_badge="Basic",
        verification_result={
            "status": "Success",
            "provider": "test-provider",
            "score": 94,
            "token": "opaque-token",
            "source": "implementer-adapter",
            "evidenceRef": "sha256:feedbeef",
            "verifiedAt": now_utc(),
        },
        policy_decision={
            "VerificationMode": "Live",
            "VerificationPolicyProfileID": "US_FMCSA_BALANCED_V1",
            "DispatchAuthorization": "Allowed",
            "DecisionReasonCode": "Verified",
            "PolicyRuleID": "balanced-tier1",
            "ReverifyBy": now_utc(),
            "EvidenceRefs": ["sha256:feedbeef"],
        },
    )


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
        # S17: first-time carrier booking remains valid, but downstream flow is manual.
        first_time_report = _build_execution_report()
        validate_message_body("ExecutionReport", first_time_report)
        first_time_handoff = first_time_report.get("OperationalHandoff") or {}
        _assert(first_time_report.get("Status") == "Booked", "S17 booking must still complete.")
        _assert(
            first_time_handoff.get("SetupStatus") == "Unknown",
            "S17 should preserve neutral/unknown setup status for first-time counterparties.",
        )
        _assert(
            "RequestCarrierSetup" in (first_time_handoff.get("SupportedHandoffActions") or []),
            "S17 should allow manual follow-up via RequestCarrierSetup.",
        )
        _assert(
            "LoadReferenceNumbers" in first_time_report,
            "S17 should preserve external booking correlation metadata.",
        )

        # S18: known carrier booking can advertise straight-through routing intent.
        known_carrier_report = json.loads(json.dumps(first_time_report))
        known_carrier_report["OperationalHandoff"] = {
            "OperationalReference": first_time_handoff["OperationalReference"],
            "SystemOfRecordType": "TMS",
            "SystemOfRecordRef": first_time_handoff["SystemOfRecordRef"],
            "HandoffEndpointType": "InternalQueue",
            "HandoffEndpointRef": first_time_handoff["HandoffEndpointRef"],
            "SupportedHandoffActions": [
                "GenerateRateConfirmation",
                "RetrieveDispatchInstructions",
            ],
            "SetupStatus": "Known",
        }
        validate_message_body("ExecutionReport", known_carrier_report)
        known_handoff = known_carrier_report["OperationalHandoff"]
        _assert(
            known_handoff.get("SetupStatus") == "Known",
            "S18 should express known/setup-complete counterparty state.",
        )
        _assert(
            "RequestCarrierSetup" not in known_handoff.get("SupportedHandoffActions", []),
            "S18 should not require setup follow-up action for known counterparties.",
        )
        _assert(
            set(known_handoff.get("SupportedHandoffActions", []))
            == {"GenerateRateConfirmation", "RetrieveDispatchInstructions"},
            "S18 should keep routing intent focused on straight-through handoff actions.",
        )

        # S19: expedited service can combine schedule, driver, instructions, and detention terms.
        broker = BrokerAgent("Broker Agent")
        carrier = CarrierAgent("Carrier Agent")
        expedited_load = broker.post_new_load(rate_model="PerMile")
        expedited_load["DriverConfiguration"] = "Team"
        expedited_load["SpecialInstructions"] = [
            "Expedited service: arrive in pickup window without rollover.",
            "Broker must be notified immediately if delivery window is at risk.",
        ]
        expedited_load["AccessorialPolicy"]["Terms"] = [
            term for term in expedited_load["AccessorialPolicy"]["Terms"] if term["Type"] == "Detention"
        ]
        expedited_bid = carrier.create_bid_request(expedited_load, bid_amount=2.62)
        validate_message_body("BidRequest", expedited_bid)
        expedited_response = broker.respond_to_bid(expedited_bid, forced_response="Accept")
        _assert(
            expedited_response["ResponseType"] == "Accept",
            "S19 matching expedited booking terms should remain acceptable.",
        )

        expedited_report = broker.create_execution_report(
            load_id=expedited_bid["LoadID"],
            bid_request=expedited_bid,
            verified_badge="Basic",
            verification_result={
                "status": "Success",
                "provider": "test-provider",
                "score": 96,
                "token": "opaque-token",
                "source": "implementer-adapter",
                "evidenceRef": "sha256:expedited",
                "verifiedAt": now_utc(),
            },
            policy_decision={
                "VerificationMode": "Live",
                "VerificationPolicyProfileID": "US_FMCSA_BALANCED_V1",
                "DispatchAuthorization": "Allowed",
                "DecisionReasonCode": "Verified",
                "PolicyRuleID": "balanced-tier1",
                "ReverifyBy": now_utc(),
                "EvidenceRefs": ["sha256:expedited"],
            },
        )
        validate_message_body("ExecutionReport", expedited_report)
        _assert(
            expedited_report.get("DriverTerms", {}).get("DriverConfiguration") == "Team",
            "S19 should preserve the expedited team-driver requirement in DriverTerms.",
        )
        _assert(
            "PickupTimeWindow" in (expedited_report.get("ScheduleTerms") or {}),
            "S19 should preserve booking-time pickup window commitments.",
        )
        _assert(
            len(expedited_report.get("SpecialInstructions") or []) == 2,
            "S19 should preserve explicit expedited service instructions.",
        )
        detention_terms = (expedited_report.get("AccessorialPolicy") or {}).get("Terms") or []
        _assert(
            len(detention_terms) == 1 and detention_terms[0].get("Type") == "Detention",
            "S19 should preserve the agreed detention booking terms without adding post-booking workflow.",
        )

        print("Composite booking scenario checks passed.")
        return 0
    finally:
        sim.NON_LOCAL_MODE = original["NON_LOCAL_MODE"]
        sim.REQUIRE_SIGNED_VERIFIER = original["REQUIRE_SIGNED_VERIFIER"]
        sim.ENFORCE_TRUSTED_VERIFIER_REGISTRY = original["ENFORCE_TRUSTED_VERIFIER_REGISTRY"]


if __name__ == "__main__":
    raise SystemExit(main())
