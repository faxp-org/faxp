#!/usr/bin/env python3
"""Regression checks for booking-plane accessorial commercial term validation."""

from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import faxp_mvp_simulation as sim  # noqa: E402
from faxp_mvp_simulation import build_rate, now_utc, validate_message_body  # noqa: E402


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


def _base_accessorial_policy() -> dict:
    return {
        "AllowedTypes": ["UnloadingFee", "OverweightPermit", "EscortVehicle"],
        "RequiresApproval": True,
        "MaxTotal": 300.0,
        "Currency": "USD",
        "Terms": [
            {
                "Type": "UnloadingFee",
                "PricingMode": "Reimbursable",
                "PayerParty": "Broker",
                "PayeeParty": "Carrier",
                "ApprovalRequired": True,
                "EvidenceRequired": True,
                "EvidenceType": "Receipt",
                "CapAmount": 300.0,
                "Currency": "USD",
            },
            {
                "Type": "OverweightPermit",
                "PricingMode": "PassThrough",
                "PayerParty": "Broker",
                "PayeeParty": "Carrier",
                "ApprovalRequired": True,
                "EvidenceRequired": True,
                "EvidenceType": "Permit",
                "Currency": "USD",
            },
            {
                "Type": "EscortVehicle",
                "PricingMode": "TBD",
                "PayerParty": "Broker",
                "PayeeParty": "Vendor",
                "ApprovalRequired": True,
                "EvidenceRequired": True,
                "EvidenceType": "EscortInvoice",
                "Currency": "USD",
            },
        ],
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
        policy = _base_accessorial_policy()

        new_load = {
            "LoadID": "load-accessorial-001",
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
            "AccessorialPolicy": policy,
            "Accessorials": [],
            "RequireTracking": True,
        }
        validate_message_body("NewLoad", new_load)

        bad_mode = _base_accessorial_policy()
        bad_mode["Terms"][0]["PricingMode"] = "Hourly"
        _expect_validation_error(
            "NewLoad",
            {**new_load, "AccessorialPolicy": bad_mode},
            "PricingMode must be one of",
        )

        bad_pass_through = _base_accessorial_policy()
        del bad_pass_through["Terms"][1]["PayerParty"]
        _expect_validation_error(
            "NewLoad",
            {**new_load, "AccessorialPolicy": bad_pass_through},
            "missing required fields",
        )

        bad_type = _base_accessorial_policy()
        bad_type["Terms"][2]["Type"] = "Detention"
        _expect_validation_error(
            "NewLoad",
            {**new_load, "AccessorialPolicy": bad_type},
            "Type must be present in NewLoad.AccessorialPolicy.AllowedTypes",
        )

        bid_request = {
            "LoadID": "load-accessorial-001",
            "Rate": build_rate("PerMile", 2.62),
            "AvailabilityDate": "2026-03-01",
            "AccessorialPolicyAcceptance": {
                "Accepted": True,
                "AllowedTypes": ["UnloadingFee", "OverweightPermit", "EscortVehicle"],
            },
        }
        validate_message_body("BidRequest", bid_request)

        bad_acceptance = {
            **bid_request,
            "AccessorialPolicyAcceptance": {"Accepted": "yes"},
        }
        _expect_validation_error(
            "BidRequest",
            bad_acceptance,
            "BidRequest.AccessorialPolicyAcceptance.Accepted must be boolean",
        )

        execution_report = {
            "LoadID": "load-accessorial-001",
            "ContractID": "FAXP-20260301-abc12345",
            "Status": "Booked",
            "Timestamp": now_utc(),
            "VerifiedBadge": "Basic",
            "AgreedRate": build_rate("PerMile", 2.62),
            "AccessorialPolicy": policy,
            "Accessorials": [
                {
                    "Type": "OverweightPermit",
                    "Amount": 145.25,
                    "Currency": "USD",
                    "Status": "Approved",
                    "ApprovedAt": now_utc(),
                    "PricingMode": "PassThrough",
                    "PayerParty": "Broker",
                    "PayeeParty": "Carrier",
                    "EvidenceRequired": True,
                    "EvidenceType": "Permit",
                    "EvidenceRef": "permit-2026-03-01-001",
                }
            ],
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

        bad_execution = {
            **execution_report,
            "Accessorials": [
                {"Type": "Detention", "Amount": 80.0, "Currency": "USD", "Status": "Approved"}
            ],
        }
        _expect_validation_error(
            "ExecutionReport",
            bad_execution,
            "Type must be present in AccessorialPolicy.AllowedTypes",
        )

        print("Accessorial commercial-term checks passed.")
        return 0
    finally:
        sim.NON_LOCAL_MODE = original["NON_LOCAL_MODE"]
        sim.REQUIRE_SIGNED_VERIFIER = original["REQUIRE_SIGNED_VERIFIER"]
        sim.ENFORCE_TRUSTED_VERIFIER_REGISTRY = original["ENFORCE_TRUSTED_VERIFIER_REGISTRY"]


if __name__ == "__main__":
    raise SystemExit(main())
