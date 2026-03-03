# FAXP v0.3 Commercial Model Backlog

Status: Active planning artifact  
Purpose: Central place to capture commercial model requirements before implementation.

## How to Use

1. Add requirement.
2. Assign target phase (`v0.3.0`, `v0.3.x`, or `deferred`).
3. Link to RFC.
4. Add acceptance criteria and compatibility notes.

## Backlog Items

### A) Rate Model Extensions

1. `PerPallet` rate model
- Target: `v0.3.0`
- RFC: `docs/rfc/RFC-v0.3-rate-model-extensibility.md`
- Acceptance:
  - Negotiation supports `PerPallet`.
  - Validation enforces pallet-count terms.
  - Existing `PerMile`/`Flat` behavior unchanged.

2. `CWT` (Hundredweight) rate model
- Target: `v0.3.0`
- RFC: `docs/rfc/RFC-v0.3-rate-model-extensibility.md`
- Acceptance:
  - Negotiation supports weight-unit terms.
  - Validation enforces weight basis.
  - Backward compatibility preserved.

3. LineHaul + Fuel Surcharge componentized rates
- Target: `v0.3.0`
- RFC: `docs/rfc/RFC-v0.3-rate-model-extensibility.md`
- Acceptance:
  - `RateComponents` supports at least `LineHaul` and `FuelSurcharge`.
  - Total agreed-rate can be derived deterministically.

### B) Mileage Contract Terms

1. Agreed miles field for `PerMile`
- Target: `v0.3.0`
- RFC: `docs/rfc/RFC-v0.3-rate-model-extensibility.md`
- Acceptance:
  - `AgreedMiles` captured in commercial terms.
  - `MilesSource` and timestamp/version are auditable.

2. Miles dispute/negotiation flow
- Target: `v0.3.0`
- RFC: `docs/rfc/RFC-v0.3-rate-model-extensibility.md`
- Acceptance:
  - Counter/reason code supports mileage disputes.
  - Final agreed miles immutable in execution record.

### C) Multi-Stop and Service Requirements

1. Multi-pick / multi-drop stop model
- Target: `v0.3.1`
- RFC: `docs/governance/BOOKING_PLANE_COMMERCIAL_TERMS.md`
- Acceptance:
  - Ordered stop list with pickup/drop semantics.
  - Backward-compatible single-stop default.
  - Conformance profile and runtime checks are release-gated.

2. Service requirements (reefer temp bands, open-deck securement, handling constraints)
- Target: `v0.3.1`
- RFC: `docs/governance/BOOKING_PLANE_COMMERCIAL_TERMS.md`
- Acceptance:
  - Booking-time `SpecialInstructions` terms with explicit accept/counter semantics.
  - Carrier can return exceptions through `SpecialInstructionsAcceptance`.
  - Deterministic dispute reason code for unresolved instructions.

3. Required delivery date / service commitment windows
- Target: `v0.3.1`
- RFC: `docs/governance/BOOKING_PLANE_COMMERCIAL_TERMS.md`
- Acceptance:
  - Pickup date range remains required and validated (`PickupEarliest`/`PickupLatest`).
  - Delivery date range and pickup/delivery time windows are structured and validated when provided.
  - Commitments can be negotiated with explicit acceptance/counter semantics (`ScheduleAcceptance`).

4. Equipment taxonomy expansion (specialty trailers + dimensional constraints)
- Target: `v0.3.x`
- RFC: `docs/rfc/RFC-v0.3-equipment-taxonomy-expansion.md`
- Acceptance:
  - Trailer type vocabulary includes `Hopper`, `StepDeck`, and others.
  - Trailer size/length is normalized and validated by equipment type.
  - Compatibility matching handles `53' Reefer` vs `48' Reefer` correctly.

5. Driver configuration requirements (single vs team) for expedited freight
- Target: `v0.3.1`
- RFC: `docs/governance/BOOKING_PLANE_COMMERCIAL_TERMS.md`
- Acceptance:
  - Load can declare required driver configuration.
  - Carrier bid can declare provided configuration.
  - Mismatch can trigger negotiation or fail-closed per policy.

6. Neutral external load reference metadata
- Target: `v0.3.1`
- RFC: `docs/governance/BOOKING_PLANE_COMMERCIAL_TERMS.md`
- Acceptance:
  - Load carries `LoadReferenceNumbers` distinct from protocol `LoadID`.
  - Supports neutral `PrimaryReferenceNumber` / `SecondaryReferenceNumber` and typed additional references.
  - Execution report snapshots references for cross-system correlation.

7. Commodity and declared cargo value discovery facts
- Target: `deferred`
- RFC: `docs/governance/BOOKING_PLANE_COMMERCIAL_TERMS.md`
- Acceptance:
  - Load can declare neutral fit-related facts such as commodity type, commodity description, and declared cargo value.
  - Builders can use those facts in local insurance/risk logic before negotiation without FAXP standardizing the eligibility decision.
  - Protocol core remains limited to carrying neutral booking/discovery facts rather than commodity-coverage adjudication.

8. Shipment/service mode discovery fact (`TL` vs `LTL`)
- Target: `deferred`
- RFC: `docs/governance/BOOKING_PLANE_COMMERCIAL_TERMS.md`
- Acceptance:
  - Load can declare a neutral shipment/service mode fact for discovery and booking fit.
  - Builders can use that fact to separate TL-oriented and LTL-oriented workflows before negotiation.
  - Protocol core remains limited to the neutral fit signal and does not standardize full LTL workflow semantics, classing, consolidation, or rating logic.

### D) Future Commercial Scenarios

1. Additional rate structures (hourly, lane-minimums, tiered pricing)
- Target: `v0.3.x`
- RFC: `docs/rfc/RFC-v0.3-rate-model-hourly-lane-minimum.md`
- Acceptance:
  - Added only via RFC with compatibility plan.

2. Additional composite booking-plane commercial scenarios
- Target: `v0.3.x`
- RFC: `docs/governance/BOOKING_PLANE_COMMERCIAL_TERMS.md`
- Acceptance:
  - Combines multiple booking-time commercial commitments in a single scenario.
  - Explicit booking-time payer/payee responsibility semantics remain preserved.
  - No post-booking claim workflow, settlement handling, or document-custody logic is introduced.

### E) Scope-Lock Baseline (Commercial Terms)

1. Booking-plane accessorial/addendum contract baseline
- Target: `v0.3.0`
- RFC: `docs/rfc/RFC-v0.3-rate-model-extensibility.md`
- Acceptance:
  - Commercial terms are structured for booking (`PricingMode`, `PayerParty`, `PayeeParty`, optional `CapAmount`).
  - Settlement/payment execution remains explicitly out of scope in governance docs.
  - Conformance tests enforce booking-plane-only semantics.

2. Operations-plane communications track (`FAXP-OPS`) governance placeholder
- Target: `deferred`
- RFC: `TBD (separate scope-expansion RFC required)`
- Acceptance:
  - Track is documented as separate from protocol core.
  - No protocol-core implementation until RFC/governance approval.

## Intake Template (for new items)

- Requirement name:
- Business scenario:
- Target phase:
- RFC link:
- Message/schema impact:
- Backward compatibility risk:
- Required tests:
- Decision owner:
