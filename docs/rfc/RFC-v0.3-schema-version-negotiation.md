# RFC: v0.3 Schema Version Negotiation

## RFC Metadata
- RFC ID: `rfc-v0.3-schema-version-negotiation`
- Title: `Define schema/version negotiation for mixed v0.2 and v0.3 agents`
- Author(s): `FAXP Governance Working Group`
- Status: `Accepted (Implemented)`
- Target Version: `v0.3.0`
- Created: `2026-02-23`
- Last Updated: `2026-02-23`

## Summary
Define deterministic version negotiation rules so agents with different supported schema/protocol versions can interoperate safely, fail closed when incompatible, and preserve backward compatibility across `v0.2.x` and `v0.3.x`.

## Motivation
As FAXP evolves, agents will run mixed versions in production. Without explicit negotiation rules, interop becomes ambiguous and can cause silent parsing failures or unsafe fallback behavior.

## Scope Gate (Required)
- Scope Classification: `In-Scope`
- Protocol-Core Impacted Files:
  - `/Users/zglitch009/projects/logistics-ai/FAXP/faxp.v0.2.schema.json`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/faxp_mvp_simulation.py`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/tests/run_schema_compatibility.py`
- Message Types Added/Changed:
  - No new message types required.
  - Existing envelope metadata validation rules are clarified.
- Schema Fields Added/Changed:
  - Envelope compatibility/negotiation semantics for `ProtocolVersion`.
  - Optional capability metadata for supported schema range (if adopted).

### Required Checks
- [x] This RFC stays within booking-plane protocol scope.
- [x] No new dispatch-orchestration message or state model is introduced.
- [x] No new tracking lifecycle model (telematics/POD/BOL custody) is introduced.
- [x] No new settlement lifecycle model (invoice/payment/remittance/factoring) is introduced.
- [x] If `Scope Expansion`, this RFC includes full security/compliance/interoperability/migration analysis and explicit approval request.

## Detailed Design
1. Keep `Protocol` and `ProtocolVersion` as the core compatibility anchors.
2. Define compatibility classes:
   - `Compatible`: message can be validated and processed without lossy behavior.
   - `Degradable`: message can be processed with explicit downgraded semantics.
   - `Incompatible`: message rejected fail-closed with reason code.
3. Define default rule:
   - Agent must process only versions explicitly declared as supported.
   - Unknown major/minor versions fail closed unless compatibility mapping exists.
4. Optional enhancement:
   - Add negotiation metadata describing supported versions (range/list) during session startup or capability advertisement.
5. Keep message contracts stable:
   - No transport lock-in.
   - No A2A/MCP mandatory dependency.

## Security Considerations
1. Prevent downgrade attacks by requiring explicit compatibility mapping.
2. Reject ambiguous version values and malformed semver-like strings.
3. Preserve signing, replay, and TTL controls during compatibility fallback.
4. Include compatibility decision reason in audit logs.

## Compliance and Governance Considerations
1. Keep negotiation rules deterministic and test-enforced.
2. Require migration notes for each compatibility exception.
3. Require conformance evidence before marking a version pair as `Compatible`.
4. Keep governance ownership over compatibility matrix updates.

## Backward Compatibility
1. `v0.2.x` agents continue to process `v0.2.x` payloads unchanged.
2. `v0.3.x` agents must retain compatibility behavior for approved `v0.2.x` payloads.
3. Unsupported version pairs fail closed with explicit reason code and traceable logs.

## Test Plan
1. Schema tests:
   - version parsing/validation vectors.
   - compatibility matrix pass/fail vectors.
2. Integration tests:
   - mixed-version load and truck happy-path vectors.
3. Failure-mode tests:
   - invalid version string.
   - unsupported version pair.
   - forced downgrade mismatch.

## Rollout Plan
1. RFC reviewed and accepted.
2. Formal compatibility profile artifact added.
3. Parser/validator logic and compatibility checks implemented.
4. Schema compatibility and conformance suite assertions expanded and release-gated.
5. Shipped in v0.3.x with green CI evidence.

## Alternatives Considered
1. Strict exact-version-only processing: rejected (too brittle for rollout).
2. Implicit best-effort fallback: rejected (non-deterministic and unsafe).
3. Out-of-band negotiation only: rejected (weak auditability in protocol flow).

## Resolved Questions
1. Supported-version compatibility is governed by profile artifacts and validator behavior, not a required new envelope field.
2. Protocol version parsing/compatibility uses constrained protocol profile logic and explicit fail-closed behavior.
3. Compatibility retention policy is controlled via governance profiles and release-readiness checks.

## Implementation Evidence
- Runtime:
  - `/Users/zglitch009/projects/logistics-ai/FIX-F/faxp_mvp_simulation.py`
- Conformance/Profile:
  - `/Users/zglitch009/projects/logistics-ai/FIX-F/conformance/protocol_compatibility_profile.v1.json`
- Tests:
  - `/Users/zglitch009/projects/logistics-ai/FIX-F/tests/run_protocol_version_negotiation.py`
  - `/Users/zglitch009/projects/logistics-ai/FIX-F/tests/run_protocol_compatibility_profile.py`
  - `/Users/zglitch009/projects/logistics-ai/FIX-F/tests/run_cross_version_fixtures.py`

## Approval
- Maintainer Approval: Approved
- Governance Approval (if required): Recorded in governance index + release readiness gates
- Date: 2026-02-27
