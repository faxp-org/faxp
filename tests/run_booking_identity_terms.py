#!/usr/bin/env python3
"""Regression checks for booking identity and reference semantics."""

from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import faxp_mvp_simulation as sim  # noqa: E402
from faxp_mvp_simulation import (  # noqa: E402
    BrokerAgent,
    build_envelope,
    build_rate,
    now_utc,
    resolve_agent_id,
    validate_envelope,
    validate_message_body,
)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _expect_envelope_error(envelope: dict, text: str) -> None:
    try:
        validate_envelope(envelope, track_replay=False, track_state=False)
    except ValueError as exc:
        _assert(text in str(exc), f"expected '{text}' in error, got: {exc}")
        return
    raise AssertionError(f"validate_envelope should fail with: {text}")


def _expect_body_error(body: dict, text: str) -> None:
    try:
        validate_message_body("ExecutionReport", body)
    except ValueError as exc:
        _assert(text in str(exc), f"expected '{text}' in error, got: {exc}")
        return
    raise AssertionError(f"ExecutionReport should fail validation with: {text}")


def _base_execution_report() -> dict:
    return {
        "LoadID": "load-booking-identity-001",
        "ContractID": "FAXP-20260302-deadbeef",
        "Status": "Booked",
        "Timestamp": now_utc(),
        "VerifiedBadge": "Basic",
        "VerificationResult": {
            "status": "Success",
            "provider": "test-provider",
            "score": 95,
            "token": "opaque-token",
            "source": "implementer-adapter",
            "evidenceRef": "sha256:abcdef",
            "verifiedAt": now_utc(),
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
        envelope = build_envelope(
            "Carrier Agent",
            "Broker Agent",
            "BidRequest",
            {"LoadID": "load-1", "Rate": build_rate("Flat", 1000.0)},
        )
        _assert(
            envelope.get("FromAgentID") == resolve_agent_id("Carrier Agent"),
            "sender agent ID must be populated from the configured resolver",
        )
        _assert(
            envelope.get("ToAgentID") == resolve_agent_id("Broker Agent"),
            "receiver agent ID must be populated from the configured resolver",
        )
        validate_envelope(envelope, track_replay=False, track_state=False)

        mismatched_agent = dict(envelope)
        mismatched_agent["FromAgentID"] = "faxp.agent.someone-else"
        _expect_envelope_error(mismatched_agent, "does not match expected sender AgentID")

        sim.NON_LOCAL_MODE = True
        missing_agent = dict(envelope)
        missing_agent.pop("FromAgentID", None)
        _expect_envelope_error(missing_agent, "Envelope.FromAgentID is required in non-local mode.")
        sim.NON_LOCAL_MODE = False

        validate_message_body("ExecutionReport", _base_execution_report())

        missing_contract = _base_execution_report()
        del missing_contract["ContractID"]
        _expect_body_error(missing_contract, "missing required fields: ['ContractID']")

        broker = BrokerAgent("Broker Agent")
        load = broker.post_new_load()
        execution_report = broker.create_execution_report(
            load_id=load["LoadID"],
            bid_request={"LoadID": load["LoadID"], "Rate": load["Rate"]},
            verified_badge="Basic",
            verification_result={
                "status": "Success",
                "provider": "test-provider",
                "score": 92,
                "token": "opaque-token",
                "source": "implementer-adapter",
                "evidenceRef": "sha256:feedface",
                "verifiedAt": now_utc(),
            },
            policy_decision={
                "VerificationMode": "Live",
                "VerificationPolicyProfileID": "US_VERIFICATION_BALANCED_V1",
                "DispatchAuthorization": "Allowed",
                "DecisionReasonCode": "Verified",
                "PolicyRuleID": "balanced-tier1",
                "ReverifyBy": now_utc(),
                "EvidenceRefs": ["sha256:feedface"],
            },
        )
        _assert("ContractID" in execution_report, "ExecutionReport must carry ContractID")
        _assert("LoadID" in execution_report, "ExecutionReport must carry LoadID")
        _assert(
            "LoadReferenceNumbers" in execution_report,
            "ExecutionReport should preserve optional external correlation metadata when present",
        )

        print("Booking identity checks passed.")
        return 0
    finally:
        sim.NON_LOCAL_MODE = original["NON_LOCAL_MODE"]
        sim.REQUIRE_SIGNED_VERIFIER = original["REQUIRE_SIGNED_VERIFIER"]
        sim.ENFORCE_TRUSTED_VERIFIER_REGISTRY = original["ENFORCE_TRUSTED_VERIFIER_REGISTRY"]


if __name__ == "__main__":
    raise SystemExit(main())
