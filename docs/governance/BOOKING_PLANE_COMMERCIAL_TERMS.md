# Booking-Plane Commercial Terms

## Purpose
Define how FAXP core represents booking-time commercial terms without expanding into operations or settlement workflows.

## Scope Boundary
FAXP core supports commercial agreement metadata for booking outcomes.
It does not run dispatch operations, document adjudication, or payment execution.

## In Scope (Protocol Core)
1. Accessorial and addendum terms agreed at booking time.
2. Structured commercial fields used in policy and validation:
- `PricingMode`
- `PayerParty`
- `PayeeParty`
- optional `CapAmount`
- evidence intent (`EvidenceRequired`, `EvidenceType`)
3. Special instructions as negotiated booking terms (`SpecialInstructions`) with explicit acceptance/counter semantics.
4. Schedule commitments as booking terms (`PickupEarliest`/`PickupLatest`, optional `DeliveryEarliest`/`DeliveryLatest`, and optional pickup/delivery time windows) with explicit acceptance/counter semantics (`ScheduleAcceptance`).
5. Equipment taxonomy terms as booking compatibility commitments (`EquipmentClass`, optional `EquipmentSubClass`, optional `EquipmentTags`, optional trailer length range via `TrailerLengthMin`/`TrailerLengthMax`, optional `TrailerCount`) with explicit acceptance/counter semantics (`EquipmentAcceptance`).
6. Driver configuration terms (`DriverConfiguration`) as booking commitments (`Single` or `Team`) with explicit acceptance/counter semantics (`DriverConfigurationAcceptance`).
7. Detention commercial policy terms as booking metadata (for example grace period, hourly amount, billing increment, and delay/location evidence intent).
8. Multi-stop terms as booking commitments (ordered pickup/drop plan, stop-count expectations, and stop-plan acceptance/counter semantics).
9. Carrier acceptance of these terms in booking negotiation.
10. Execution report snapshot of the agreed commercial terms.

## Out of Scope (Protocol Core)
Settlement and payment execution are out of scope for FAXP core.

1. Receipt verification and permit/invoice adjudication.
2. POD/BOL custody and proof workflows.
3. Claims/dispute workflows and settlement state machines.
4. Payment rails, reimbursement execution, remittance, and factoring.

## Canonical Pricing Modes
- `IncludedInBaseRate`
- `Reimbursable`
- `PassThrough`
- `TBD`

## Design Rules
1. `CapAmount` is optional and only used when commercial policy requires it.
2. `PassThrough`, `Reimbursable`, and `TBD` require explicit payer/payee allocation.
3. Terms are valid only as booking-plane contract metadata in FAXP core.
4. Operational evidence handling is delegated to external systems (TMS, carrier portals, claims workflows).
5. Detention evidence intent fields are commercial preconditions only; proof adjudication remains external.
6. Multi-stop terms are booking-plane commercial commitments; stop-by-stop dispatch tracking remains out of scope.
7. Special instructions are commercial agreement terms; operations workflow execution remains external.
8. Schedule commitments are booking-plane commercial commitments; dispatch appointment execution remains external.
9. Equipment taxonomy commitments are booking-plane compatibility terms; trailer/driver assignment operations remain external.
10. Driver configuration terms are booking-plane compatibility terms; driver assignment operations remain external.

## Future Expansion Policy
Operations-plane messaging is a scope expansion track and must be introduced through a separate RFC/governance process (for example a future `FAXP-OPS` profile).
