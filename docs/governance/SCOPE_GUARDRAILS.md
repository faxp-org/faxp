# FAXP Scope Guardrails

## Purpose
FAXP remains a booking-plane protocol for agent-to-agent freight matching and booking confirmation.  
These guardrails prevent scope creep into dispatch operations, tracking operations, and settlement operations.

## In Scope (v0.1.x -> v0.2)
- Agent messaging envelopes, signatures, replay/TTL checks, validation.
- Booking workflows:
  - `NewLoad`, `LoadSearch`
  - `NewTruck`, `TruckSearch`
  - `BidRequest`, `BidResponse`
  - `ExecutionReport`, `AmendRequest`
- Verification attestations and policy decisions that influence booking outcome.
- Conformance/certification artifacts, schemas, and test harnesses.

## Out of Scope (Protocol Core)
- Dispatch execution workflows:
  - driver assignment
  - route optimization
  - stop-level dispatch updates
- Operational tracking workflows:
  - telematics ingestion
  - proof-of-delivery (POD) lifecycle
  - bill-of-lading (BOL) custody workflows
- Financial settlement workflows:
  - invoicing
  - remittance
  - payment rails
  - factoring
- Direct verifier operations:
  - hosting third-party compliance or biometric services
  - running ongoing carrier monitoring infrastructure
  - managing provider credentials for implementer deployments

## Clarification
- `DispatchAuthorization` in `ExecutionReport` is currently treated as a booking-time policy gate only.
- It must not expand into dispatch orchestration message types or downstream dispatch lifecycle state in protocol core.
- Optional post-booking operational handoff metadata may describe neutral routing intent only; it must not carry dispatch packet content or operational execution state.
- FAXP may enforce trusted-attestation policy and verifier admission criteria, but verifier execution remains implementer-hosted.
- FAXP does not determine regulatory eligibility; it authenticates protocol messages and can transport optional verifier evidence.
- Verification ownership boundaries are documented in `docs/governance/VERIFICATION_RESPONSIBILITY_MODEL.md`.
- Accessorials in protocol core are booking-time commercial terms/addenda only (allowed types, pricing mode, payer/payee allocation, optional caps, and approval intent).
- Accessorial evidence adjudication (receipt/POD/BOL validation), dispute handling, and settlement/payment execution remain out of scope for protocol core.
- Reference pricing, market benchmarks, and internal pricing logic remain builder-side concerns unless a future RFC demonstrates a clear interoperability need for standardized transport.
- FAXP may carry neutral booking/discovery facts such as commodity type, declared cargo value, and handling-sensitive cargo descriptors when those facts affect fit or negotiation.
- Insurance interpretation, commodity-eligibility decisions, underwriting exceptions, and internal risk-acceptance logic remain builder-side unless a future RFC demonstrates a narrow interoperability need for standardizing a shared outcome.
- FAXP may carry neutral shipment/service mode facts such as `TL` versus `LTL` when those facts affect discovery or booking fit.
- Full LTL workflow modeling (classification, terminal routing, consolidation, rehandling, and LTL-specific rating logic) remains deferred until a future RFC demonstrates a clear booking-plane interoperability need.

## Litmus Test For New Protocol Fields
Before adding a new protocol field, profile, or behavior, answer all four questions:

1. Is it needed to negotiate or confirm a booking?
2. Would two independent implementations need the same field or behavior in a standardized form?
3. Does the counterparty actually need to receive it across a system boundary?
4. Can it be modeled without turning FAXP into dispatch, settlement, or hosted operations infrastructure?

If the answer to any question is "no" or unclear, the feature should remain builder-side until a stronger interoperability case is proven.

## Change Control
- Any proposed expansion into an out-of-scope domain requires an RFC using `/docs/rfc/RFC_TEMPLATE.md`.
- RFCs that cross scope boundaries must be marked as `Scope Expansion` and approved before implementation.
- Scope-expanding changes must include:
  - security and compliance impact
  - interoperability impact
  - migration/backward-compatibility plan
  - rationale for why this cannot remain adapter-side or system-side

## CI Enforcement
- CI runs `python tests/run_scope_guardrails.py`.
- The linter scans protocol-core artifacts and fails on forbidden out-of-scope terms.
- Current protocol-core lint targets:
  - `/faxp_mvp_simulation.py`
  - `/faxp.schema.json`
  - `/faxp.v0.2.schema.json`
