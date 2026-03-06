# RFC: v0.3 Operational Handoff Metadata

## RFC Metadata
- RFC ID: `rfc-v0.3-operational-handoff-metadata`
- Title: `Define neutral post-booking operational handoff metadata`
- Author(s): `FAXP Governance Working Group`
- Status: `Accepted (Implemented)`
- Target Version: `v0.4.x`
- Created: `2026-02-27`
- Last Updated: `2026-03-02`

## Summary
Define a neutral post-booking handoff model that separates:
1. mandatory booking counterparty identity/reference data, and
2. optional downstream operational routing metadata

This allows a receiving system to route a completed booking into the correct downstream operational workflow after `ExecutionReport`, without expanding FAXP into dispatch, document custody, or settlement workflows.

## Motivation
FAXP intentionally ends at booking confirmation. In practice, the parties still need a clean handoff into their own TMS, portal, operations agent, or human workflow to complete dispatch, rate confirmation, onboarding/setup exceptions, and other downstream actions.

Without a standard handoff shape, each implementation must invent its own post-booking routing conventions. This creates unnecessary integration friction even when the booking itself is already standardized.

This RFC also clarifies an important boundary:
- a valid booking must always identify the counterparty and the booking reference,
- but downstream operational routing details do not need to be universally mandatory in protocol-core.

## Scope Gate (Required)
- Scope Classification: `In-Scope`
- Protocol-Core Impacted Files:
  - `faxp_mvp_simulation.py`
  - `faxp.schema.json`
  - `faxp.v0.2.schema.json`
  - `conformance/operational_handoff_profile.v1.json`
- Message Types Added/Changed:
  - No new message types required.
  - `ExecutionReport` carries optional `OperationalHandoff` metadata.
- Schema Fields Added/Changed:
  - Optional `ExecutionReport.OperationalHandoff` metadata object.

### Required Checks
- [x] This RFC stays within booking-plane protocol scope.
- [x] No new dispatch-orchestration message or state model is introduced.
- [x] No new tracking lifecycle model (telematics/POD/BOL custody) is introduced.
- [x] No new settlement lifecycle model (invoice/payment/remittance/factoring) is introduced.
- [x] If `Scope Expansion`, this RFC includes full security/compliance/interoperability/migration analysis and explicit approval request.

## Detailed Design
1. Keep `ExecutionReport` as the booking confirmation boundary.
2. Separate handoff data into two layers:
   - required booking identity/reference layer
   - optional operational routing layer
3. Required booking identity/reference data (or equivalent already-declared fields/profile references) must allow both sides to know:
   - who the counterparty is,
   - which agent/system represented them,
   - which booking/operational reference identifies the deal.
4. Current implementation uses existing booked identity/reference anchors:
   - envelope `From` / `To`
   - `ExecutionReport.LoadID` or `ExecutionReport.TruckID`
   - `ExecutionReport.ContractID`
   - optional `LoadReferenceNumbers` for external correlation
5. Implemented optional operational routing field set:
   - `OperationalReference`
   - `SystemOfRecordType`
   - `SystemOfRecordRef`
   - `HandoffEndpointType`
   - `HandoffEndpointRef`
   - `SupportedHandoffActions`
   - `SetupStatus`
6. Intended use:
   - tell the receiving side which internal/external workflow to invoke next,
   - identify the correct system-of-record reference,
   - surface whether setup/onboarding is already complete or still required.
7. Required/optional distinction:
   - booking identity/reference data remains required for a meaningful booked relationship,
   - routing metadata remains optional in protocol-core,
   - profiles/policies may require routing metadata for straight-through automation.
8. Strict non-goals:
   - no dispatch packet payloads,
   - no appointment details lifecycle,
   - no rate confirmation document transport,
   - no financial/accounting workflow states.

## Security Considerations
1. Handoff metadata must remain signed as part of the message envelope if added to protocol messages.
2. Metadata should be opaque/neutral where possible to avoid overexposing internal operational details.
3. Unsupported or malformed handoff metadata must fail closed or be ignored by local policy without altering booking validity.
4. Handoff routing references must not be treated as proof of operational execution.
5. Counterparty identity/reference data must be sufficient to prevent ambiguous or anonymous “bookings” that cannot be operationally attributed.

## Compliance and Governance Considerations
1. Preserve vendor neutrality and transport neutrality.
2. Keep handoff metadata as routing intent, not operational truth.
3. Ensure governance docs explicitly preserve dispatch, document custody, and settlement boundaries.
4. If later implemented, require conformance profile/tests proving handoff metadata does not mutate booking-plane scope.

## Backward Compatibility
1. Operational routing metadata must remain optional and additive in protocol-core.
2. Existing `ExecutionReport` payloads must remain valid without operational routing fields.
3. If mandatory booking counterparty/reference data is already satisfied elsewhere in existing envelope/body semantics, no breaking change is required.
4. Implementations not using structured operational routing metadata must remain conformant, though local policy may still require manual fallback handling.

## Implementation Evidence
1. Runtime validation and default example generation:
   - `faxp_mvp_simulation.py`
2. Conformance profile:
   - `conformance/operational_handoff_profile.v1.json`
3. Runtime/profile tests:
   - `tests/run_operational_handoff_terms.py`
   - `tests/run_operational_handoff_profile.py`
4. Governance/release wiring:
   - `docs/governance/GOVERNANCE_INDEX.json`
   - `docs/governance/RELEASE_READINESS_CHECKLIST.md`
   - `conformance/run_all_checks.py`
   - `.github/workflows/ci.yml`

## Rollout Plan
1. Implement optional `ExecutionReport.OperationalHandoff` object and keep booking validity independent from it.
2. Keep all operational execution artifacts external to FAXP core.
3. Revisit capability-profile publication of routing hints only after builder feedback.

## Alternatives Considered
1. Put dispatch details directly into FAXP: rejected as out of scope.
2. Leave handoff entirely undefined: rejected due to interoperability friction.
3. Use vendor-specific portal/TMS conventions only: rejected due to lock-in and inconsistent automation behavior.

## Open Questions
1. Whether handoff routing hints should also be published in party capability/profile artifacts.
2. Whether `SetupStatus` should remain a small canonical enum or become profile-extensible.
3. Whether additional neutral routing targets are needed based on builder feedback.

## Approval
- Maintainer Approval: Accepted (Implemented)
- Governance Approval (if required):
- Date: 2026-03-02
