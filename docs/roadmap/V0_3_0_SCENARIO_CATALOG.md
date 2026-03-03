# FAXP v0.3 Scenario Catalog

Status: Active planning artifact  
Purpose: Concrete scenarios used to drive RFC decisions and acceptance tests.

## Scenario Rules

1. Every scenario must map to one RFC.
2. Every scenario must define expected booking decision output.
3. Every scenario must define backward-compatibility impact.

## Scenarios

### S1: PerMile with Agreed Miles

- Description: Broker posts `PerMile` load with proposed miles; carrier accepts or counters miles.
- RFC: `docs/rfc/RFC-v0.3-rate-model-extensibility.md`
- Target: `v0.3.0`
- Expected outcome:
  - Final contract contains agreed miles and agreed rate.
  - Dispute reason code captured when countered.

### S2: PerPallet Negotiation

- Description: Broker posts palletized freight with `PerPallet` pricing.
- RFC: `docs/rfc/RFC-v0.3-rate-model-extensibility.md`
- Target: `v0.3.0`
- Expected outcome:
  - Pallet terms validated.
  - Execution report reflects agreed pallet-based pricing.

### S3: CWT Negotiation

- Description: Load priced per hundredweight (`CWT`).
- RFC: `docs/rfc/RFC-v0.3-rate-model-extensibility.md`
- Target: `v0.3.0`
- Expected outcome:
  - Weight basis and units validated.
  - Execution report reflects weight-based agreed pricing.

### S4: LineHaul + Fuel Surcharge Split

- Description: Rate is negotiated as two components: linehaul plus FSC.
- RFC: `docs/rfc/RFC-v0.3-rate-model-extensibility.md`
- Target: `v0.3.0`
- Expected outcome:
  - Component values preserved.
  - Total agreed amount derivable and auditable.

### S5: Multi-Pick / Multi-Drop

- Description: Load includes multiple pickups and drops.
- RFC: `docs/governance/BOOKING_PLANE_COMMERCIAL_TERMS.md`
- Target: `v0.3.1`
- Expected outcome:
  - Ordered stop list and constraints.
  - Single-stop compatibility retained.
  - Stop-plan acceptance mismatch can trigger deterministic counter response.

### S6: Reefer Temperature Requirement

- Description: Reefer load requires specific temperature range and monitoring instructions.
- RFC: `docs/governance/BOOKING_PLANE_COMMERCIAL_TERMS.md`
- Target: `v0.3.1`
- Expected outcome:
  - Requirement can be represented in `SpecialInstructions`.
  - Carrier explicitly accepts or returns exceptions in bid negotiation.

### S7: Open-Deck Securement and Handling Requirements

- Description: Open-deck load requires securement and handling notes such as tarping, chains, straps, pipe stakes, dunnage, or other booking-time handling requirements.
- RFC: `docs/governance/BOOKING_PLANE_COMMERCIAL_TERMS.md`
- Target: `v0.3.1`
- Expected outcome:
  - Requirements can be represented in `SpecialInstructions`.
  - Carrier explicitly accepts or returns exceptions in bid negotiation.
  - Unresolved securement/handling mismatch can trigger deterministic counter or reject behavior.

### S8: Verification Degraded Path with Provisional Hold

- Description: Verification provider outage triggers `SoftHold` or `GraceCache` path.
- RFC: `docs/rfc/RFC-v0.3-provisional-booking-policy-contract.md`
- Target: `v0.3.0`
- Expected outcome:
  - Deterministic policy decision.
  - Explicit reason codes and exception references.

### S9: Delivery Commitment Window

- Description: Shipper/broker requires delivery by specific date/time window.
- RFC: `docs/governance/BOOKING_PLANE_COMMERCIAL_TERMS.md`
- Target: `v0.3.1`
- Expected outcome:
  - Delivery commitment fields are structured and validated.
  - Pickup date range remains required.
  - Carrier can accept/counter based on `ScheduleAcceptance` constraints.

### S10: Equipment Dimension Compatibility

- Description: Load requires specific reefer trailer size.
- RFC: `docs/rfc/RFC-v0.3-equipment-taxonomy-expansion.md`
- Target: `v0.3.x`
- Expected outcome:
  - Equipment matching distinguishes size-sensitive requirements.
  - Incompatible size triggers no-match or negotiation path.

### S11: Specialty Trailer Match (Hopper / StepDeck)

- Description: Load requires non-standard trailer class.
- RFC: `docs/rfc/RFC-v0.3-equipment-taxonomy-expansion.md`
- Target: `v0.3.x`
- Expected outcome:
  - Specialty equipment taxonomy is structured and validated.
  - Matching and negotiation logic use standardized trailer classes.

### S12: Expedited Team Driver Requirement

- Description: Expedited shipment requires team drivers.
- RFC: `docs/governance/BOOKING_PLANE_COMMERCIAL_TERMS.md`
- Target: `v0.3.1`
- Expected outcome:
  - Driver configuration requirement is explicit in load terms.
  - Carrier bid declares single/team capability.
  - Policy handles mismatch deterministically.

### S13: External Load Reference Correlation

- Description: Broker and shipper need neutral cross-system reference numbers distinct from protocol `LoadID`.
- RFC: `docs/governance/BOOKING_PLANE_COMMERCIAL_TERMS.md`
- Target: `v0.3.1`
- Expected outcome:
  - `NewLoad` can include `LoadReferenceNumbers` with neutral primary/secondary reference numbers.
  - Additional typed references support partner-specific identifiers without schema churn.
  - `ExecutionReport` preserves references for downstream TMS/document handoff.

### S14: PerHour Negotiation for Local or Time-Based Service

- Description: Broker and carrier negotiate a `PerHour` booking-plane rate with explicit hours basis for a local or delay-sensitive load.
- RFC: `docs/rfc/RFC-v0.3-rate-model-hourly-lane-minimum.md`
- Target: `v0.3.x`
- Expected outcome:
  - `RateModel=PerHour` validates model-specific fields and unit basis deterministically.
  - Counter path preserves reason codes and does not break existing `PerMile`/`Flat` behavior.
  - `ExecutionReport` preserves time-based agreed-rate semantics for downstream handoff.

### S15: LaneMinimum Commercial Floor Contract

- Description: Carrier and broker negotiate a lane floor where `LaneMinimum` applies when computed components fall below a minimum total.
- RFC: `docs/rfc/RFC-v0.3-rate-model-hourly-lane-minimum.md`
- Target: `v0.3.x`
- Expected outcome:
  - `RateModel=LaneMinimum` validates required minimum semantics and fails closed when incomplete.
  - Final agreed-rate normalization remains auditable and deterministic in `ExecutionReport`.
  - Backward compatibility is preserved for existing rate models and profiles.

### S16: Detention Terms Agreed at Booking

- Description: Broker and carrier agree detention commercial terms at booking time, including rate basis and responsibility.
- RFC: `docs/rfc/RFC-v0.3-accessorial-lifecycle-booking-plane.md`
- Target: `v0.3.x`
- Expected outcome:
  - Accessorial terms are explicit (type, pricing mode, payer/payee, pre-approval/evidence requirements).
  - Bid accept/counter paths preserve deterministic reason codes for accessorial disputes.
  - `ExecutionReport` snapshots agreed booking-plane accessorial framework.

### S17: First-Time Carrier Booking with Manual Follow-Up

- Description: Broker books a first-time carrier with explicit identity and commercial agreement, but downstream setup status remains unknown or required.
- RFC: `docs/rfc/RFC-v0.3-operational-handoff-metadata.md`
- Target: `v0.4.x`
- Expected outcome:
  - Booking remains valid with explicit counterparty identity and booking references.
  - `OperationalHandoff` can indicate neutral routing intent and `SetupStatus=Unknown|Required`.
  - No automated dispatch assumptions are required; manual follow-up remains conformant.

### S18: Known Carrier Booking with Straight-Through Handoff

- Description: Broker books a known carrier and includes structured post-booking routing metadata so downstream systems can continue without custom conventions.
- RFC: `docs/rfc/RFC-v0.3-operational-handoff-metadata.md`
- Target: `v0.4.x`
- Expected outcome:
  - Booking remains valid and attributable through envelope identity and booking references.
  - `OperationalHandoff` carries routing-only metadata with `SetupStatus=Known`.
  - Downstream automation can route cleanly without expanding FAXP into dispatch state.

### S19: Composite Expedited Service Booking

- Description: Booking combines expedited service commitments such as pickup window, delivery deadline, appointment constraints, team-driver requirement, and detention terms agreed up front.
- RFC: `docs/governance/BOOKING_PLANE_COMMERCIAL_TERMS.md`
- Target: `v0.4.x`
- Expected outcome:
  - Multiple booking-time commitments validate and compose without schema ambiguity.
  - Carrier can accept or counter schedule and driver terms deterministically.
  - Final execution record snapshots the agreed booking-plane commercial framework only.

### S20: Composite Specialty Equipment Booking

- Description: Booking combines specialty equipment requirements, dimensional constraints, and securement/handling instructions in one negotiation.
- RFC: `docs/rfc/RFC-v0.3-equipment-taxonomy-expansion.md`
- Target: `v0.4.x`
- Expected outcome:
  - Equipment class/subclass, dimensional compatibility, and special instructions compose cleanly.
  - Carrier can return targeted exceptions rather than forcing a generic reject path.
  - Booking remains strictly within negotiation and confirmation scope.

## Deferred / Future Scenario Candidates

### F1: Commodity and Cargo Value Fit

- Description: Load declares commodity type and cargo value so a carrier-side builder can determine whether the freight is a fit before negotiation, based on local coverage/risk rules.
- RFC: `docs/governance/BOOKING_PLANE_COMMERCIAL_TERMS.md`
- Target: `deferred`
- Expected outcome:
  - FAXP carries neutral booking/discovery facts such as `CommodityType`, `CommodityDescription`, and `DeclaredCargoValue`.
  - Carrier-side builder uses local insurance, exclusion, and risk rules to decide whether to surface, bid, block, or require review.
  - FAXP does not determine whether the carrier is eligible to haul the commodity or whether additional cargo coverage is required.

### F2: Shipment Mode Fit (TL vs LTL)

- Description: Load declares whether the shipment is `TL` or `LTL` so builders can filter and route discovery appropriately before negotiation.
- RFC: `docs/governance/BOOKING_PLANE_COMMERCIAL_TERMS.md`
- Target: `deferred`
- Expected outcome:
  - FAXP carries a neutral shipment/service mode fact for discovery and booking fit.
  - Builder-side logic uses that fact to determine whether the opportunity belongs in a TL-oriented or LTL-oriented workflow.
  - FAXP does not attempt to model full LTL workflow semantics such as freight class, terminal routing, consolidation, or LTL-specific rating behavior.

## Scenario Expansion Policy

1. New scenario proposals must be added here first.
2. Scenario must map to an RFC before implementation.
3. Scenario cannot be implemented after release freeze unless classified as bugfix/security fix.
