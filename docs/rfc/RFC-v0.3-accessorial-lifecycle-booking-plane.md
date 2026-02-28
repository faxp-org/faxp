# RFC: v0.3 Accessorial Lifecycle (Booking-Plane Contract Only)

## RFC Metadata
- RFC ID: `rfc-v0.3-accessorial-lifecycle-booking-plane`
- Title: `Standardize booking-plane accessorial lifecycle terms and decision states`
- Author(s): `FAXP Governance Working Group`
- Status: `Accepted (Implemented)`
- Target Version: `v0.3.x`
- Created: `2026-02-27`
- Last Updated: `2026-02-27`

## Summary
Define a consistent booking-plane contract for accessorials so parties can negotiate expected charges, payer responsibility, and evidence requirements at booking time without expanding FAXP into dispatch execution or settlement workflows.

## Motivation
Accessorial disputes are a common source of friction and manual rework. Current behavior supports basic policy/cap concepts but lacks a complete lifecycle contract for:
1. upfront declared accessorial terms,
2. responsibility assignment (`PayerParty` / `PayeeParty`),
3. post-booking claim states and required evidence references.

This RFC closes that gap while preserving the scope boundary: FAXP standardizes booking-time terms and message semantics, not payment processing.

## Scope Gate (Required)
- Scope Classification: `In-Scope`
- Protocol-Core Impacted Files:
  - `faxp_mvp_simulation.py`
  - `faxp.schema.json`
  - `faxp.v0.2.schema.json`
  - `streamlit_app.py`
  - `conformance/` (new or updated profile artifact)
- Message Types Added/Changed:
  - `NewLoad` (accessorial contract terms extension only)
  - `BidRequest` (accessorial acceptance/counter semantics extension only)
  - `BidResponse` (counter and reason semantics extension only)
  - `ExecutionReport` (booking snapshot of agreed accessorial framework only)
- Schema Fields Added/Changed:
  - Structured accessorial term fields for booking-time agreement.
  - Optional claim-reference structure for post-booking evidence linkage (IDs/URIs/hashes only, no document custody model).

### Required Checks
- [x] This RFC stays within booking-plane protocol scope.
- [x] No new dispatch-orchestration message or state model is introduced.
- [x] No new tracking lifecycle model (telematics/POD/BOL custody) is introduced.
- [x] No new settlement lifecycle model (invoice/payment/remittance/factoring) is introduced.
- [x] If `Scope Expansion`, this RFC includes full security/compliance/interoperability/migration analysis and explicit approval request.

## Detailed Design
1. Booking-time accessorial terms become explicit contract objects:
   - `AccessorialType` (canonical registry value),
   - `PricingMode` (fixed, per-hour, per-event, etc.),
   - `PayerParty`, `PayeeParty`,
   - optional policy controls (`PreApprovalRequired`, `RequiresEvidence`, `EvidenceTypes`).
2. Negotiation semantics:
   - Carrier can accept terms as-is, counter specific accessorial terms, or reject.
   - Counter path uses deterministic reason codes (for example `AccessorialResponsibilityDispute`, `AccessorialPricingDispute`).
3. Post-booking state contract (booking-plane scope only):
   - Allowed state progression for accessorial claims: `Proposed -> Approved | Rejected`.
   - `ExecutionReport` captures agreed framework and any claim references known at booking close.
4. Evidence model:
   - FAXP carries evidence references/metadata only (hash, external reference ID, URI).
   - FAXP does not standardize file transfer, document custody, or proof adjudication workflows.
5. Settlement boundary:
   - Payment/invoice/remittance remains external to FAXP and must not be modeled as core protocol state.

## Security Considerations
1. Canonical accessorial typing and reason codes reduce semantic spoofing or ambiguity.
2. Signed envelopes with replay/TTL protections continue to protect claim-state messages.
3. Evidence references should be redacted/hashed where needed to avoid leaking sensitive document contents.

## Compliance and Governance Considerations
1. Canonical accessorial type registry remains governance-controlled and vendor-neutral.
2. Profiles must define which accessorial types/terms are certifiable for a given environment.
3. Governance docs must explicitly preserve settlement and document-custody out-of-scope boundaries.

## Backward Compatibility
1. Existing accessorial behavior remains valid; new fields are additive and optional.
2. Agents not supporting extended lifecycle fields must fail closed with explicit validation reasons where required.
3. Existing `PerMile`, `Flat`, `PerPallet`, and `CWT` behavior is unaffected.

## Test Plan
1. Schema validation tests for required/optional accessorial term fields.
2. Negotiation tests for accept/counter/reject paths with deterministic reason codes.
3. Execution-report snapshot tests to ensure agreed accessorial framework is auditable.
4. Failure-mode tests for invalid type values, missing payer/payee responsibility, and invalid state transitions.
5. Conformance profile checks and governance readiness checks updated.

## Rollout Plan
1. RFC accepted.
2. Conformance profile artifact/tests landed and release-gated.
3. Runtime/schema updates landed with strict validation.
4. Streamlit examples updated for booking-plane lifecycle semantics.
5. Included in RC soak cycle.

## Alternatives Considered
1. Keep free-form notes only: rejected due to high ambiguity and interoperability risk.
2. Model full settlement lifecycle in FAXP: rejected as out of scope.
3. Defer all accessorial lifecycle standardization to external systems: rejected due to persistent booking-plane negotiation friction.

## Resolved Questions
1. Canonical claim-state vocabulary: `Proposed`, `Approved`, `Rejected`.
2. External verifier evidence references are optional and policy-driven; evidence adjudication remains external.
3. Profile-level policy may define approval thresholds by accessorial type; protocol core remains neutral.

## Implementation Evidence
- Runtime:
  - `faxp_mvp_simulation.py`
  - `streamlit_app.py`
- Conformance/Profile:
  - `conformance/accessorial_terms_profile.v1.json`
  - `conformance/accessorial_type_registry.v1.json`
  - `conformance/detention_terms_profile.v1.json`
- Tests:
  - `tests/run_accessorial_terms.py`
  - `tests/run_accessorial_terms_profile.py`
  - `tests/run_accessorial_type_registry.py`
  - `tests/run_detention_terms_profile.py`

## Approval
- Maintainer Approval: Approved
- Governance Approval (if required): Recorded in governance index + release readiness gates
- Date: 2026-02-27
