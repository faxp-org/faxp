# RFC: v0.3 Shipper Orchestration (Minimal)

## RFC Metadata
- RFC ID: `rfc-v0.3-shipper-orchestration-minimal`
- Title: `Activate minimal shipper -> broker -> carrier booking orchestration`
- Author(s): `FAXP Governance Working Group`
- Status: `Draft`
- Target Version: `v0.3.0`
- Created: `2026-02-23`
- Last Updated: `2026-02-23`

## Summary
Activate the existing `ShipperAgent` stub as an optional orchestration entry point so a shipper-originated tender can flow through broker and carrier booking interactions without changing the existing broker-carrier happy path.

## Motivation
FAXP already demonstrates broker-carrier and load/truck happy paths. A minimal shipper orchestration path improves real-world modeling while preserving the current protocol boundary and keeping scope constrained to booking-plane handoff logic.

## Scope Gate (Required)
- Scope Classification: `In-Scope`
- Protocol-Core Impacted Files:
  - `/Users/zglitch009/projects/logistics-ai/FAXP/faxp_mvp_simulation.py`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/streamlit_app.py` (optional toggle-only update)
  - `/Users/zglitch009/projects/logistics-ai/FAXP/faxp.v0.2.schema.json` (only if metadata fields are added)
- Message Types Added/Changed:
  - No new required message types.
  - Existing booking-plane message types remain primary (`NewLoad`, `LoadSearch`, `BidRequest`, `BidResponse`, `ExecutionReport`, `AmendRequest`).
- Schema Fields Added/Changed:
  - None required in base proposal.
  - Optional orchestration metadata fields may be proposed for traceability (`TenderSource`, `InitiatorRole`) if needed.

### Required Checks
- [x] This RFC stays within booking-plane protocol scope.
- [x] No new dispatch-orchestration message or state model is introduced.
- [x] No new tracking lifecycle model (telematics/POD/BOL custody) is introduced.
- [x] No new settlement lifecycle model (invoice/payment/remittance/factoring) is introduced.
- [x] If `Scope Expansion`, this RFC includes full security/compliance/interoperability/migration analysis and explicit approval request.

## Detailed Design
1. Keep existing broker-carrier flow as default and unchanged.
2. Add an optional scenario where:
   - `ShipperAgent.post_tender()` produces a tender payload.
   - Broker converts tender into existing `NewLoad` shape.
   - Carrier discovery/bid/verification/execution continues using current message flow.
3. Preserve current verification/policy logic and conformance checks.
4. Avoid introducing a shipper-only transport contract in this phase.
5. Maintain compatibility with current streamlit/CLI demos by making shipper path opt-in.

## Security Considerations
1. Preserve envelope signing, replay checks, and TTL checks across shipper-initiated path.
2. Ensure tender normalization rejects malformed/unsafe fields before broker emission.
3. Keep verification trust model unchanged; no bypass path for shipper-originated loads.
4. Ensure audit logs include origin attribution for tender-to-load mapping.

## Compliance and Governance Considerations
1. Keep shipper role handling provider-neutral and implementation-neutral.
2. Preserve certified adapter boundaries (no new verifier coupling).
3. Ensure governance docs clearly state this is still booking-plane orchestration only.
4. Require conformance evidence showing existing broker-carrier path remains stable.

## Backward Compatibility
1. Existing CLI and Streamlit flows must run unchanged when shipper path is disabled.
2. Existing message contracts remain valid without shipper metadata.
3. Shipper path uses existing message types to avoid breaking downstream consumers.

## Test Plan
1. Positive tests:
   - Existing broker-carrier happy path unchanged.
   - Optional shipper-initiated flow reaches booked execution report.
2. Negative tests:
   - Invalid tender normalization fails closed.
   - Missing required load fields from tender are rejected.
3. Regression:
   - Existing conformance suite remains green.

## Rollout Plan
1. RFC review and governance approval.
2. Implement optional shipper orchestration path in simulation.
3. Add focused tests and docs updates.
4. Promote to v0.3.0 only after regression evidence.

## Alternatives Considered
1. Introduce new shipper-specific message type immediately: rejected for minimal-scope phase.
2. Full multi-party orchestration state machine: rejected as too broad for v0.3.0.
3. Keep shipper stub permanently unused: rejected due to adoption/value gap.

## Open Questions
1. Should shipper-origin metadata be standardized in protocol envelope or body extensions?
2. Is a streamlit UI mode toggle sufficient, or should shipper flow remain CLI-only initially?
3. What is the minimum required audit field set for tender provenance?

## Approval
- Maintainer Approval:
- Governance Approval (if required):
- Date:
