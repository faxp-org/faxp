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
3. Detention commercial policy terms as booking metadata (for example grace period, hourly amount, billing increment, and delay/location evidence intent).
4. Carrier acceptance of these terms in booking negotiation.
5. Execution report snapshot of the agreed commercial terms.

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

## Future Expansion Policy
Operations-plane messaging is a scope expansion track and must be introduced through a separate RFC/governance process (for example a future `FAXP-OPS` profile).
