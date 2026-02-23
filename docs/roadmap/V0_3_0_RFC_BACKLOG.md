# FAXP v0.3.0 RFC Backlog (Planning Only)

Status: Draft backlog  
Implementation policy: **No implementation before RFC acceptance**  
Scope policy: Booking-plane and certification governance only.

## Process

1. Create RFC from `/Users/zglitch009/projects/logistics-ai/FAXP/docs/rfc/RFC_TEMPLATE.md`.
2. Classify scope gate in each RFC (`In-Scope` or `Scope Expansion`).
3. Require security and conformance impact section.
4. Require migration/backward-compatibility note for schema/runtime changes.
5. Only after governance acceptance: move item into implementation checklist.

## Priority Backlog

1. `RFC-v0.3-rate-model-extensibility`
- Goal: Extend booking-plane rate model taxonomy beyond `PerMile` and `Flat` while preserving backward compatibility.
- Scope class: `In-Scope`
- Notes: Keep accessorial lifecycle consistent with current post-booking policy semantics.
- Draft file: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/rfc/RFC-v0.3-rate-model-extensibility.md`

2. `RFC-v0.3-shipper-orchestration-minimal`
- Goal: Wire existing ShipperAgent stub into an optional shipper -> broker -> carrier booking path.
- Scope class: `In-Scope`
- Notes: Preserve current broker-carrier happy path unchanged.
- Draft file: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/rfc/RFC-v0.3-shipper-orchestration-minimal.md`

3. `RFC-v0.3-schema-version-negotiation`
- Goal: Formalize version negotiation and compatibility behavior for mixed v0.2/v0.3 agents.
- Scope class: `In-Scope`
- Notes: No transport lock-in; conformance tests required.
- Draft file: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/rfc/RFC-v0.3-schema-version-negotiation.md`

4. `RFC-v0.3-adapter-certification-profile-v2`
- Goal: Advance certification profile and registry policy requirements for builder-hosted adapters.
- Scope class: `In-Scope`
- Notes: Keep provider neutrality and no core vendor coupling.
- Draft file: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/rfc/RFC-v0.3-adapter-certification-profile-v2.md`

5. `RFC-v0.3-provisional-booking-policy-contract`
- Goal: Standardize policy semantics for `HardBlock`, `SoftHold`, and `GraceCache` outcomes.
- Scope class: `In-Scope`
- Notes: Keep as policy/decision contract, not dispatch-state expansion.
- Draft file: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/rfc/RFC-v0.3-provisional-booking-policy-contract.md`

6. `RFC-v0.3-a2a-mcp-interop-maturity`
- Goal: Define maturity criteria for translator/tool evidence interoperability across A2A and MCP tracks.
- Scope class: `In-Scope`
- Notes: No mandatory A2A/MCP runtime dependency in FAXP core.

## Deferred / Explicitly Out-of-Scope for v0.3.0 RFC Batch

1. Dispatch operations model.
2. Telematics/tracking lifecycle model.
3. POD/BOL custody and document workflow standards.
4. Invoice/payment/settlement rails.

These remain scope expansions and require separate governance track beyond current protocol boundary.
