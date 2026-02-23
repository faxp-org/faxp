#!/usr/bin/env python3
"""Regression checks for verification policy decision behavior."""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from faxp_mvp_simulation import evaluate_verification_policy_decision  # noqa: E402
from policy_profile_matrix import load_policy_test_matrix  # noqa: E402


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _run_case(case: dict) -> None:
    case_id = str(case["id"])
    decision = evaluate_verification_policy_decision(
        case["verification"],
        profile_id=case["profileId"],
        risk_tier=case["riskTier"],
        exception_approved=bool(case.get("exceptionApproved", False)),
        exception_approval_ref=str(case.get("exceptionApprovalRef", "")),
    )

    _assert(
        decision["VerificationPolicyProfileID"] == case["profileId"],
        f"{case_id}: policy profile mismatch",
    )
    _assert(decision["RiskTier"] == int(case["riskTier"]), f"{case_id}: risk tier mismatch")

    for key, expected_value in case["expected"].items():
        actual = decision.get(key)
        _assert(
            actual == expected_value,
            f"{case_id}: expected {key}={expected_value!r} but got {actual!r}",
        )

    expected_exception_ref = str(case.get("expectedExceptionApprovalRef", "")).strip()
    if expected_exception_ref:
        _assert(
            decision.get("ExceptionApprovalRef") == expected_exception_ref,
            f"{case_id}: exception approval ref mismatch",
        )

    _assert(bool(decision.get("PolicyRuleID")), f"{case_id}: PolicyRuleID must be present")
    _assert(bool(decision.get("ReverifyBy")), f"{case_id}: ReverifyBy must be present")


def main() -> int:
    cases = load_policy_test_matrix(PROJECT_ROOT)
    for case in cases:
        _run_case(case)

    print(f"Verification policy decision regression checks passed ({len(cases)} cases).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
