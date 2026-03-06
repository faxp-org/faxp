# FAXP Policy Profiles (Normative)

This document defines booking-time degraded-mode semantics for verification policy profiles.

## Scope
- These profiles govern booking decision behavior in degraded verification conditions.
- They do not define dispatch lifecycle orchestration, settlement, or operational tracking workflows.

## Degraded Modes

### `HardBlock`
- Verification outage or verification unavailability results in fail-closed booking behavior.
- Default outcome: `DispatchAuthorization=Blocked`, `ShouldBook=false`.
- Human exception metadata may still be required by profile rules, but tier policy can still deny override.

### `SoftHold`
- Verification outage keeps booking in provisional state.
- Default outcome: `DispatchAuthorization=Hold`, `ShouldBook=true`.
- Dispatch is held pending re-verification and/or human escalation per risk tier policy.

### `GraceCache`
- Verification outage uses tiered continuity logic.
- Tier outcome is driven by `decisionOnOutage`:
  - `AllowProvisional` -> allow provisional flow (`Allowed` or `Hold` per tier dispatch setting)
  - `HoldDispatch` -> `Hold`
  - `Block` -> `Blocked`
- Human approval rules can escalate or deny exceptions by tier.

## Profile Catalog
- `US_VERIFICATION_STRICT_V1` -> `HardBlock`
- `US_VERIFICATION_SOFTHOLD_V1` -> `SoftHold`
- `US_VERIFICATION_BALANCED_V1` -> `GraceCache`

## Verification Source Labels
- Canonical verifier source classes are:
  - `vendor-direct`
  - `implementer-adapter`
  - `authority-only`
  - `self-attested`
- Legacy label `hosted-adapter` remains valid as a backward-compatible alias for `implementer-adapter`.

## Normative Test Matrix
The following matrix is normative and consumed by conformance tests.

<!-- POLICY_TEST_MATRIX_BEGIN -->
[
  {
    "id": "balanced_success_t1",
    "profileId": "US_VERIFICATION_BALANCED_V1",
    "riskTier": 1,
    "verification": {
      "status": "Success",
      "source": "implementer-adapter",
      "provider": "compliance.authority-record.live"
    },
    "expected": {
      "DispatchAuthorization": "Allowed",
      "ShouldBook": true,
      "DecisionReasonCode": "VerificationSuccess"
    }
  },
  {
    "id": "balanced_negative_fail_t0",
    "profileId": "US_VERIFICATION_BALANCED_V1",
    "riskTier": 0,
    "verification": {
      "status": "Fail",
      "source": "implementer-adapter",
      "provider": "compliance.authority-record.live"
    },
    "expected": {
      "DispatchAuthorization": "Blocked",
      "ShouldBook": false,
      "DecisionReasonCode": "VerificationNegativeResult"
    }
  },
  {
    "id": "balanced_gracecache_outage_t0",
    "profileId": "US_VERIFICATION_BALANCED_V1",
    "riskTier": 0,
    "verification": {
      "status": "Fail",
      "source": "implementer-adapter",
      "error": "Implementer adapter network error."
    },
    "expected": {
      "DispatchAuthorization": "Allowed",
      "ShouldBook": true,
      "DecisionReasonCode": "VerificationUnavailableGraceCache"
    }
  },
  {
    "id": "balanced_gracecache_outage_t2_pending",
    "profileId": "US_VERIFICATION_BALANCED_V1",
    "riskTier": 2,
    "verification": {
      "status": "Fail",
      "source": "implementer-adapter",
      "error": "Implementer adapter network error."
    },
    "expected": {
      "DispatchAuthorization": "Hold",
      "ShouldBook": true,
      "DecisionReasonCode": "PendingHumanApproval"
    }
  },
  {
    "id": "balanced_gracecache_outage_t2_approved",
    "profileId": "US_VERIFICATION_BALANCED_V1",
    "riskTier": 2,
    "exceptionApproved": true,
    "exceptionApprovalRef": "APPROVAL-123",
    "verification": {
      "status": "Fail",
      "source": "implementer-adapter",
      "error": "Implementer adapter network error."
    },
    "expected": {
      "DispatchAuthorization": "Allowed",
      "ShouldBook": true,
      "DecisionReasonCode": "HumanExceptionApproved"
    },
    "expectedExceptionApprovalRef": "APPROVAL-123"
  },
  {
    "id": "strict_hardblock_outage_t1",
    "profileId": "US_VERIFICATION_STRICT_V1",
    "riskTier": 1,
    "verification": {
      "status": "Fail",
      "source": "implementer-adapter",
      "error": "Implementer adapter network error."
    },
    "expected": {
      "DispatchAuthorization": "Blocked",
      "ShouldBook": false,
      "DecisionReasonCode": "PendingHumanApproval"
    }
  },
  {
    "id": "softhold_outage_t1",
    "profileId": "US_VERIFICATION_SOFTHOLD_V1",
    "riskTier": 1,
    "verification": {
      "status": "Fail",
      "source": "implementer-adapter",
      "error": "Implementer adapter network error."
    },
    "expected": {
      "DispatchAuthorization": "Hold",
      "ShouldBook": true,
      "DecisionReasonCode": "VerificationUnavailableSoftHold"
    }
  },
  {
    "id": "balanced_gracecache_outage_t3_approved_denied",
    "profileId": "US_VERIFICATION_BALANCED_V1",
    "riskTier": 3,
    "exceptionApproved": true,
    "exceptionApprovalRef": "APPROVAL-CRITICAL-1",
    "verification": {
      "status": "Fail",
      "source": "implementer-adapter",
      "error": "Implementer adapter network error."
    },
    "expected": {
      "DispatchAuthorization": "Blocked",
      "ShouldBook": false,
      "DecisionReasonCode": "HumanExceptionDeniedByTierPolicy"
    },
    "expectedExceptionApprovalRef": "APPROVAL-CRITICAL-1"
  }
]
<!-- POLICY_TEST_MATRIX_END -->
