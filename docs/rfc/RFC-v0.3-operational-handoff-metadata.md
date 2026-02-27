# RFC: v0.3 Operational Handoff Metadata

## RFC Metadata
- RFC ID: `rfc-v0.3-operational-handoff-metadata`
- Title: `Define neutral post-booking operational handoff metadata`
- Author(s): `FAXP Governance Working Group`
- Status: `Draft`
- Target Version: `v0.3.x`
- Created: `2026-02-27`
- Last Updated: `2026-02-27`

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
- but downstream operational routing details do not need to be universally mandatory in protocol core.

## Scope Gate (Required)
- Scope Classification: `In-Scope`
- Protocol-Core Impacted Files:
  - None required for base proposal.
  - Optional schema/runtime changes only if this RFC is later accepted.
- Message Types Added/Changed:
  - No new message types required.
  - `ExecutionReport` may later carry optional handoff metadata if approved.
- Schema Fields Added/Changed:
  - Planning target only: optional `OperationalHandoff` or equivalent metadata object.

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
4. Candidate required identity/reference field set:
   - `CounterpartyID`
   - `CounterpartyRole`
   - `AgentID`
   - `BookingReference`
   - `OperationalReference`
5. Candidate optional operational routing field set:
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
   - booking identity/reference data is required for a meaningful booked relationship,
   - routing metadata remains optional in protocol core,
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
1. Operational routing metadata must remain optional and additive in protocol core.
2. Existing `ExecutionReport` payloads must remain valid without operational routing fields.
3. If mandatory booking counterparty/reference data is already satisfied elsewhere in existing envelope/body semantics, no breaking change is required.
4. Implementations not using structured operational routing metadata must remain conformant, though local policy may still require manual fallback handling.

## Test Plan (If Implemented Later)
1. Schema tests for optional handoff object shape and allowed values.
2. Runtime tests proving malformed metadata does not create implicit dispatch states.
3. Conformance checks ensuring handoff object remains routing-only and does not transport dispatch content.

## Rollout Plan
1. Governance review and acceptance.
2. Decide whether handoff metadata belongs in `ExecutionReport`, capability profiles, or both.
3. If accepted, add optional profile/schema contract and tests.
4. Keep all operational execution artifacts external to FAXP core.

## Alternatives Considered
1. Put dispatch details directly into FAXP: rejected as out of scope.
2. Leave handoff entirely undefined: rejected due to interoperability friction.
3. Use vendor-specific portal/TMS conventions only: rejected due to lock-in and inconsistent automation behavior.

## Open Questions
1. Should mandatory counterparty identity/reference data be formalized in `ExecutionReport`, party profiles, or existing envelope/body references?
2. Should routing metadata live only in `ExecutionReport`, or also in party capability/profile artifacts?
3. Should `SetupStatus` be fully standardized or left implementation-defined?
4. Should `SupportedHandoffActions` use a canonical small enum or remain profile-driven?

## Approval
- Maintainer Approval:
- Governance Approval (if required):
- Date:
