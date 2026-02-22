#!/usr/bin/env python3
"""Regression checks for verification policy decision behavior."""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from faxp_mvp_simulation import evaluate_verification_policy_decision  # noqa: E402


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    success_result = {
        "status": "Success",
        "source": "hosted-adapter",
        "provider": "compliance.authority-record.live",
    }
    success_decision = evaluate_verification_policy_decision(
        success_result,
        profile_id="US_FMCSA_BALANCED_V1",
        risk_tier=1,
    )
    _assert(success_decision["DispatchAuthorization"] == "Allowed", "success should allow dispatch")
    _assert(success_decision["ShouldBook"] is True, "success should keep booking")

    hard_fail = {
        "status": "Fail",
        "source": "hosted-adapter",
        "provider": "compliance.authority-record.live",
    }
    hard_fail_decision = evaluate_verification_policy_decision(
        hard_fail,
        profile_id="US_FMCSA_BALANCED_V1",
        risk_tier=0,
    )
    _assert(
        hard_fail_decision["DispatchAuthorization"] == "Blocked",
        "negative verification result should block",
    )
    _assert(hard_fail_decision["ShouldBook"] is False, "negative verification should not book")

    outage_low = {
        "status": "Fail",
        "source": "hosted-adapter",
        "error": "Hosted adapter network error.",
    }
    outage_low_decision = evaluate_verification_policy_decision(
        outage_low,
        profile_id="US_FMCSA_BALANCED_V1",
        risk_tier=0,
    )
    _assert(
        outage_low_decision["DispatchAuthorization"] == "Allowed",
        "balanced tier-0 outage should allow provisional booking",
    )
    _assert(outage_low_decision["ShouldBook"] is True, "tier-0 outage should keep booking")

    outage_high_pending = evaluate_verification_policy_decision(
        outage_low,
        profile_id="US_FMCSA_BALANCED_V1",
        risk_tier=2,
        exception_approved=False,
    )
    _assert(
        outage_high_pending["DispatchAuthorization"] == "Hold",
        "balanced tier-2 outage should hold when no exception approval",
    )
    _assert(
        outage_high_pending["DecisionReasonCode"] == "PendingHumanApproval",
        "tier-2 outage should require human approval",
    )
    _assert(outage_high_pending["ShouldBook"] is True, "hold should retain provisional booking")

    outage_high_approved = evaluate_verification_policy_decision(
        outage_low,
        profile_id="US_FMCSA_BALANCED_V1",
        risk_tier=2,
        exception_approved=True,
        exception_approval_ref="APPROVAL-123",
    )
    _assert(
        outage_high_approved["DispatchAuthorization"] == "Allowed",
        "approved tier-2 exception should allow dispatch",
    )
    _assert(
        outage_high_approved.get("ExceptionApprovalRef") == "APPROVAL-123",
        "exception reference should be retained",
    )

    strict_outage = evaluate_verification_policy_decision(
        outage_low,
        profile_id="US_FMCSA_STRICT_V1",
        risk_tier=1,
    )
    _assert(
        strict_outage["DispatchAuthorization"] == "Blocked",
        "strict profile outage should hard block",
    )
    _assert(strict_outage["ShouldBook"] is False, "strict outage should not book")

    critical_outage_approved = evaluate_verification_policy_decision(
        outage_low,
        profile_id="US_FMCSA_BALANCED_V1",
        risk_tier=3,
        exception_approved=True,
        exception_approval_ref="APPROVAL-CRITICAL-1",
    )
    _assert(
        critical_outage_approved["DispatchAuthorization"] == "Blocked",
        "critical outage should remain blocked even with exception",
    )
    _assert(
        critical_outage_approved["DecisionReasonCode"] == "HumanExceptionDeniedByTierPolicy",
        "critical block reason mismatch",
    )
    _assert(critical_outage_approved["ShouldBook"] is False, "critical outage should not book")

    print("Verification policy decision regression checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
