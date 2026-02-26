# RFC: v0.3 Equipment Taxonomy Expansion

## RFC Metadata
- RFC ID: `rfc-v0.3-equipment-taxonomy-expansion`
- Title: `Expand booking-plane equipment taxonomy for specialty trailers and dimensional compatibility`
- Author(s): `FAXP Governance Working Group`
- Status: `Draft`
- Target Version: `v0.3.x`
- Created: `2026-02-26`
- Last Updated: `2026-02-26`

## Summary
Standardize expanded booking-plane equipment taxonomy semantics across `EquipmentType`, `EquipmentClass`, `EquipmentSubClass`, `EquipmentTags`, and trailer length ranges so specialty trailer compatibility can be negotiated consistently without adding operations-plane behavior.

## Motivation
Current equipment support covers common classes and core matching behavior, but adoption requires consistent handling for specialty trailer requests and dimensional constraints. This RFC formalizes vocabulary and compatibility rules so brokers, carriers, and builders can interoperate deterministically.

## Scope Gate (Required)
- Scope Classification: `In-Scope`
- Protocol-Core Impacted Files:
  - `/Users/zglitch009/projects/logistics-ai/FIX-F/faxp_mvp_simulation.py`
  - `/Users/zglitch009/projects/logistics-ai/FIX-F/faxp.schema.json`
  - `/Users/zglitch009/projects/logistics-ai/FIX-F/faxp.v0.2.schema.json`
  - `/Users/zglitch009/projects/logistics-ai/FIX-F/conformance/equipment_profile.v1.json`
- Message Types Added/Changed:
  - `NewLoad` (equipment term normalization/validation only)
  - `LoadSearch` (equipment filter normalization/validation only)
  - `NewTruck` (equipment term normalization/validation only)
  - `TruckSearch` (equipment filter normalization/validation only)
  - `BidRequest` (equipment acceptance normalization/validation only)
  - `BidResponse` (existing mismatch counter reason code path only)
  - `ExecutionReport` (equipment terms snapshot only)
- Schema Fields Added/Changed:
  - `EquipmentClass`
  - `EquipmentSubClass`
  - `EquipmentTags`
  - `TrailerLengthMin`
  - `TrailerLengthMax`
  - `EquipmentSpecialDescription`

### Required Checks
- [x] This RFC stays within booking-plane protocol scope.
- [x] No new dispatch-orchestration message or state model is introduced.
- [x] No new tracking lifecycle model (telematics/POD/BOL custody) is introduced.
- [x] No new settlement lifecycle model (invoice/payment/remittance/factoring) is introduced.
- [x] If `Scope Expansion`, this RFC includes full security/compliance/interoperability/migration analysis and explicit approval request.

## Detailed Design
1. Preserve current canonical equipment dimensions:
   - primary class (`EquipmentClass`)
   - optional subclass (`EquipmentSubClass`)
   - optional tags (`EquipmentTags`)
2. Normalize `EquipmentType` aliases (including compact and typo-variant forms) into canonical class/subclass values before compatibility checks.
3. Allow deterministic `EquipmentTags` inference from canonical subclass signals when tags are omitted.
4. Keep `EquipmentType` as a user-facing label while requiring deterministic class/subclass/tag normalization.
5. Standardize dimensional compatibility semantics:
   - `TrailerLengthMin` and `TrailerLengthMax` express a required range when size flexibility exists.
   - a single `TrailerLength` with no range remains valid and is treated as strict length.
6. Keep mismatch behavior deterministic:
   - incompatibility may trigger `BidResponse.Counter` with `ReasonCode=EquipmentCompatibilityDispute`.
7. Keep `Special` class support:
   - `EquipmentSpecialDescription` is required for non-canonical/special requests.
8. No new message types are introduced.

## Security Considerations
1. Canonical normalization reduces spoofing/ambiguity via inconsistent free-text equipment labels.
2. Strict validation reduces manipulation risk from conflicting dimensional terms.
3. Existing signature, replay, and TTL controls remain unchanged and continue to protect message integrity.

## Compliance and Governance Considerations
1. Keep taxonomy vendor-neutral and implementation-agnostic.
2. Maintain conformance profile coverage for class/subclass/tag/range semantics.
3. Keep operations activities (dispatch assignment, trailer dispatching, execution tracking) out of scope.

## Backward Compatibility
1. Existing loads using only `EquipmentType` remain valid.
2. Existing `EquipmentClass`/`EquipmentSubClass`/`EquipmentTags` behavior remains compatible.
3. Existing strict trailer length semantics remain valid; range semantics remain additive.

## Test Plan
1. Runtime tests:
   - class/subclass/tag validation and alias normalization
   - strict and range-based trailer length compatibility
   - deterministic mismatch counter behavior
2. Profile tests:
   - equipment profile artifact alignment with runtime constants/contract
3. Integration checks:
   - load and truck flows preserve compatibility behavior in happy-path and mismatch-path scenarios

## Rollout Plan
1. Approve this RFC.
2. Land incremental profile/runtime/schema updates with conformance gates.
3. Keep release gating on equipment runtime + profile tests in CI.
4. Publish compatibility notes in release notes for builders.

## Alternatives Considered
1. Leave equipment as free-text only: rejected due to interoperability drift.
2. Add operations-plane dispatch asset model now: rejected as scope expansion.
3. Split into per-equipment message types: rejected as unnecessary complexity.

## Open Questions
1. Should canonical equipment vocabulary be maintained as one profile artifact or split by region/market profile?
2. Should future dimensional constraints include width/height in booking plane or remain deferred?

## Approval
- Maintainer Approval:
- Governance Approval (if required):
- Date:
