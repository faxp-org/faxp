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
- RFC: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/rfc/RFC-v0.3-rate-model-extensibility.md`
- Target: `v0.3.0`
- Expected outcome:
  - Final contract contains agreed miles and agreed rate.
  - Dispute reason code captured when countered.

### S2: PerPallet Negotiation

- Description: Broker posts palletized freight with `PerPallet` pricing.
- RFC: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/rfc/RFC-v0.3-rate-model-extensibility.md`
- Target: `v0.3.0`
- Expected outcome:
  - Pallet terms validated.
  - Execution report reflects agreed pallet-based pricing.

### S3: CWT Negotiation

- Description: Load priced per hundredweight (`CWT`).
- RFC: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/rfc/RFC-v0.3-rate-model-extensibility.md`
- Target: `v0.3.0`
- Expected outcome:
  - Weight basis and units validated.
  - Execution report reflects weight-based agreed pricing.

### S4: LineHaul + Fuel Surcharge Split

- Description: Rate is negotiated as two components: linehaul plus FSC.
- RFC: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/rfc/RFC-v0.3-rate-model-extensibility.md`
- Target: `v0.3.0`
- Expected outcome:
  - Component values preserved.
  - Total agreed amount derivable and auditable.

### S5: Multi-Pick / Multi-Drop

- Description: Load includes multiple pickups and drops.
- RFC: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/governance/BOOKING_PLANE_COMMERCIAL_TERMS.md`
- Target: `v0.3.1`
- Expected outcome:
  - Ordered stop list and constraints.
  - Single-stop compatibility retained.
  - Stop-plan acceptance mismatch can trigger deterministic counter response.

### S6: Reefer Temperature Requirement

- Description: Reefer load requires specific temperature range and monitoring instructions.
- RFC: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/governance/BOOKING_PLANE_COMMERCIAL_TERMS.md`
- Target: `v0.3.1`
- Expected outcome:
  - Requirement can be represented in `SpecialInstructions`.
  - Carrier explicitly accepts or returns exceptions in bid negotiation.

### S7: Flatbed Tarping Requirement

- Description: Flatbed load requires tarping and securement notes.
- RFC: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/governance/BOOKING_PLANE_COMMERCIAL_TERMS.md`
- Target: `v0.3.1`
- Expected outcome:
  - Requirement can be represented in `SpecialInstructions`.
  - Carrier explicitly accepts or returns exceptions in bid negotiation.

### S8: Verification Degraded Path with Provisional Hold

- Description: Verification provider outage triggers `SoftHold` or `GraceCache` path.
- RFC: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/rfc/RFC-v0.3-provisional-booking-policy-contract.md`
- Target: `v0.3.0`
- Expected outcome:
  - Deterministic policy decision.
  - Explicit reason codes and exception references.

### S9: Required Delivery Date Commitment

- Description: Shipper/broker requires delivery by specific date/time window.
- RFC: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/governance/BOOKING_PLANE_COMMERCIAL_TERMS.md`
- Target: `v0.3.1`
- Expected outcome:
  - Delivery commitment fields are structured and validated.
  - Pickup date range remains required.
  - Carrier can accept/counter based on `ScheduleAcceptance` constraints.

### S10: Trailer Size Match (`53'` vs `48'` Reefer)

- Description: Load requires specific reefer trailer size.
- RFC: `TBD (new RFC required)`
- Target: `v0.3.x`
- Expected outcome:
  - Equipment matching distinguishes size-sensitive requirements.
  - Incompatible size triggers no-match or negotiation path.

### S11: Specialty Trailer Match (Hopper / StepDeck)

- Description: Load requires non-standard trailer class.
- RFC: `TBD (new RFC required)`
- Target: `v0.3.x`
- Expected outcome:
  - Specialty equipment taxonomy is structured and validated.
  - Matching and negotiation logic use standardized trailer classes.

### S12: Expedited Team Driver Requirement

- Description: Expedited shipment requires team drivers.
- RFC: `TBD (new RFC required)`
- Target: `v0.3.x`
- Expected outcome:
  - Driver configuration requirement is explicit in load terms.
  - Carrier bid declares single/team capability.
  - Policy handles mismatch deterministically.

## Scenario Expansion Policy

1. New scenario proposals must be added here first.
2. Scenario must map to an RFC before implementation.
3. Scenario cannot be implemented after release freeze unless classified as bugfix/security fix.
