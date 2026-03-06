#!/usr/bin/env python3
"""Regression checks for post-booking operational handoff metadata."""

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


def _base_execution_report() -> dict:
    return {
        "LoadID": "load-handoff-001",
        "ContractID": "FAXP-20260302-abcd1234",
        "Status": "Booked",
        "Timestamp": now_utc(),
        "AgreedRate": build_rate("PerMile", 2.62, AgreedMiles=781, MilesSource="BrokerDeclared"),
        "VerifiedBadge": "Basic",
        "VerificationResult": {
            "status": "Success",
            "provider": "test-provider",
            "score": 91,
            "token": "opaque-token",
            "source": "implementer-adapter",
            "evidenceRef": "sha256:abcdef",
            "verifiedAt": now_utc(),
        },
        "OperationalHandoff": {
            "OperationalReference": "BRK-2026-000421",
            "SystemOfRecordType": "TMS",
            "SystemOfRecordRef": "broker-agent-load-001",
            "HandoffEndpointType": "InternalQueue",
            "HandoffEndpointRef": "broker-agent:booking-confirmed",
            "SupportedHandoffActions": [
                "GenerateRateConfirmation",
                "RequestCarrierSetup",
                "RetrieveDispatchInstructions",
            ],
            "SetupStatus": "Unknown",
        },
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
        validate_message_body("ExecutionReport", _base_execution_report())

        missing_reference = _base_execution_report()
        del missing_reference["OperationalHandoff"]["OperationalReference"]
        _expect_validation_error(
            "ExecutionReport",
            missing_reference,
            "missing required fields: ['OperationalReference']",
        )

        bad_endpoint_pair = _base_execution_report()
        del bad_endpoint_pair["OperationalHandoff"]["HandoffEndpointRef"]
        _expect_validation_error(
            "ExecutionReport",
            bad_endpoint_pair,
            "must include both HandoffEndpointType and HandoffEndpointRef",
        )

        bad_action = _base_execution_report()
        bad_action["OperationalHandoff"]["SupportedHandoffActions"] = ["ShipDispatchPacket"]
        _expect_validation_error(
            "ExecutionReport",
            bad_action,
            "SupportedHandoffActions[0] must be one of",
        )

        broker = BrokerAgent("Broker Agent")
        carrier = CarrierAgent("Carrier Agent")
        load = broker.post_new_load(rate_model="PerMile")
        bid = carrier.create_bid_request(load, bid_amount=2.62)

        execution_report = broker.create_execution_report(
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
                "VerificationPolicyProfileID": "US_VERIFICATION_BALANCED_V1",
                "DispatchAuthorization": "Allowed",
                "DecisionReasonCode": "Verified",
                "PolicyRuleID": "balanced-tier1",
                "ReverifyBy": now_utc(),
                "EvidenceRefs": ["sha256:feedbeef"],
            },
        )

        handoff = execution_report.get("OperationalHandoff") or {}
        _assert(handoff.get("SystemOfRecordType") == "TMS", "default handoff must target TMS")
        _assert(handoff.get("HandoffEndpointType") == "InternalQueue", "default handoff must use InternalQueue")
        _assert(
            handoff.get("OperationalReference") == "BRK-2026-000421",
            "default handoff should reuse primary load reference when available",
        )
        _assert(
            handoff.get("SetupStatus") == "Unknown",
            "default handoff should preserve neutral setup status",
        )

        print("Operational handoff checks passed.")
        return 0
    finally:
        sim.NON_LOCAL_MODE = original["NON_LOCAL_MODE"]
        sim.REQUIRE_SIGNED_VERIFIER = original["REQUIRE_SIGNED_VERIFIER"]
        sim.ENFORCE_TRUSTED_VERIFIER_REGISTRY = original["ENFORCE_TRUSTED_VERIFIER_REGISTRY"]


if __name__ == "__main__":
    raise SystemExit(main())
