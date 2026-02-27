# RFC: v0.3 Provisional Booking Policy Contract

## RFC Metadata
- RFC ID: `rfc-v0.3-provisional-booking-policy-contract`
- Title: `Standardize HardBlock, SoftHold, and GraceCache policy semantics`
- Author(s): `FAXP Governance Working Group`
- Status: `Accepted (Implemented)`
- Target Version: `v0.3.0`
- Created: `2026-02-23`
- Last Updated: `2026-02-23`

## Summary
Define a clear policy contract for provisional booking outcomes so verification outages and exception paths produce deterministic, auditable decisions across implementations.

## Motivation
Current behavior includes the policy concepts (`HardBlock`, `SoftHold`, `GraceCache`) but requires stronger normalization for cross-implementer consistency and certification clarity.

## Scope Gate (Required)
- Scope Classification: `In-Scope`
- Protocol-Core Impacted Files:
  - `/Users/zglitch009/projects/logistics-ai/FAXP/docs/governance/POLICY_PROFILES.md`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/tests/run_policy_decisions.py`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/tests/run_policy_profile_sync.py`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/faxp_mvp_simulation.py` (policy-decision mapping only)
- Message Types Added/Changed:
  - No new message types.
  - Existing booking messages may include standardized policy decision metadata.
- Schema Fields Added/Changed:
  - Policy decision metadata normalization for verification outcome handling.
  - Optional structured reason-code field alignment for provisional/blocked paths.

### Required Checks
- [x] This RFC stays within booking-plane protocol scope.
- [x] No new dispatch-orchestration message or state model is introduced.
- [x] No new tracking lifecycle model (telematics/POD/BOL custody) is introduced.
- [x] No new settlement lifecycle model (invoice/payment/remittance/factoring) is introduced.
- [x] If `Scope Expansion`, this RFC includes full security/compliance/interoperability/migration analysis and explicit approval request.

## Detailed Design
1. Normalize policy outcome categories:
   - `HardBlock`: fail-closed, booking/dispatch blocked.
   - `SoftHold`: provisional booking with explicit hold state pending verification.
   - `GraceCache`: continuity decision based on risk tier and cached trusted evidence.
2. Require explicit decision reason fields:
   - policy profile ID
   - decision mode
   - reason code
   - exception approval reference when used
3. Define precedence order:
   - Hard policy restrictions override discretionary exceptions unless explicitly allowed in profile.
4. Keep policy handling in booking-plane decision logic, not dispatch lifecycle expansion.
5. Ensure all provisional decisions are auditable and machine-checkable.

## Security Considerations
1. Prevent silent policy bypass by requiring deterministic decision path logging.
2. Prevent replay of prior approvals by binding approvals to request scope/time.
3. Preserve fail-closed defaults when policy metadata is missing or invalid.
4. Enforce policy-profile integrity checks in conformance suite.

## Compliance and Governance Considerations
1. Preserve neutrality: contract defines outcomes, not vendor-specific verifiers.
2. Require policy profile documentation and test synchronization.
3. Require human-exception traceability fields for audit and dispute review.
4. Ensure registry/certification profiles can declare supported policy modes.

## Backward Compatibility
1. Existing behavior remains compatible if mapped to normalized decision values.
2. Legacy decision strings may be accepted during transition with explicit normalization.
3. Implementers not supporting normalized fields must fail closed for ambiguous cases.

## Test Plan
1. Positive tests:
   - expected outcomes for each policy mode across risk tiers.
   - valid exception path with required approval reference.
2. Negative tests:
   - missing reason code for provisional decisions.
   - invalid profile ID reference.
   - stale/invalid exception approval reference.
3. Regression:
   - existing happy paths remain unchanged where policy is not degraded.

## Rollout Plan
1. RFC reviewed and accepted.
2. Policy profile docs and conformance checks updated and release-gated.
3. Normalized decision mapping implemented in simulation/runtime checks.
4. Policy decision evidence required in v0.3 certification profiles.

## Alternatives Considered
1. Leave policy semantics implementation-defined: rejected (interoperability risk).
2. Add new protocol message types for policy events: rejected for minimal-scope phase.
3. Collapse to single fail-open/fail-closed toggle: rejected as too coarse.

## Resolved Questions
1. Exception approvals are policy-profile driven and explicitly traceable when used.
2. `GraceCache` cache-age and outage behavior are controlled by normative policy profile matrix.
3. Policy decision metadata is normalized and validated for degraded decision paths and surfaced for auditability.

## Implementation Evidence
- Runtime:
  - `/Users/zglitch009/projects/logistics-ai/FIX-F/faxp_mvp_simulation.py`
  - `/Users/zglitch009/projects/logistics-ai/FIX-F/streamlit_state_logic.py`
- Conformance/Profile:
  - `/Users/zglitch009/projects/logistics-ai/FIX-F/conformance/verification_policy_profile.v1.json`
- Tests:
  - `/Users/zglitch009/projects/logistics-ai/FIX-F/tests/run_verification_policy_profile.py`
  - `/Users/zglitch009/projects/logistics-ai/FIX-F/tests/run_policy_decisions.py`
  - `/Users/zglitch009/projects/logistics-ai/FIX-F/tests/run_policy_profile_sync.py`

## Approval
- Maintainer Approval: Approved
- Governance Approval (if required): Recorded in governance index + release readiness gates
- Date: 2026-02-27
