# RFC: v0.3 Adapter Certification Profile v2

## RFC Metadata
- RFC ID: `rfc-v0.3-adapter-certification-profile-v2`
- Title: `Advance builder-hosted adapter certification profile and registry policy`
- Author(s): `FAXP Governance Working Group`
- Status: `Accepted (Implemented)`
- Target Version: `v0.3.0`
- Created: `2026-02-23`
- Last Updated: `2026-02-28`

## Summary
Define version 2 of FAXP adapter certification profile requirements to strengthen consistency, auditability, and trust signals for builder-hosted adapters while preserving provider neutrality and no mandatory core coupling.

## Motivation
Current certification artifacts establish baseline conformance and governance controls. As adoption grows, we need a clearer tiered profile contract for operational maturity, evidence quality, and registry lifecycle behavior.

## Scope Gate (Required)
- Scope Classification: `In-Scope`
- Protocol-Core Impacted Files:
  - None required for base proposal.
  - Conformance/certification artifacts only unless approved otherwise.
- Message Types Added/Changed:
  - None.
- Schema Fields Added/Changed:
  - Certification/profile schemas in `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/` (planning target).
  - Registry metadata fields for profile versioning and evidence classing (planning target).

### Required Checks
- [x] This RFC stays within booking-plane protocol scope.
- [x] No new dispatch-orchestration message or state model is introduced.
- [x] No new tracking lifecycle model (telematics/POD/BOL custody) is introduced.
- [x] No new settlement lifecycle model (invoice/payment/remittance/factoring) is introduced.
- [x] If `Scope Expansion`, this RFC includes full security/compliance/interoperability/migration analysis and explicit approval request.

## Detailed Design
1. Introduce profile v2 with explicit evidence classes:
   - `SchemaEvidence`
   - `SecurityEvidence`
   - `OperationalEvidence`
   - `InteropEvidence`
2. Define tier requirements with stricter mapping:
   - `SelfAttested`
   - `Conformant`
   - `TrustedProduction`
3. Require deterministic registry metadata:
   - profile version
   - evidence freshness timestamp
   - key lifecycle evidence reference
   - decision record reference
4. Keep builder-hosted architecture as normative:
   - FAXP certifies, builders host adapters.
5. Require conformance suite linkage:
   - profile v2 checks must map to explicit suite check names.

## Security Considerations
1. Strengthen evidence integrity requirements (signed attestations and key lifecycle proof).
2. Require fail-closed policy if mandatory evidence classes are missing.
3. Require stronger replay/audit traceability around registry update operations.
4. Ensure no raw sensitive payloads are required for certification evidence.

## Compliance and Governance Considerations
1. Keep neutrality: no provider-specific implementation mandates.
2. Require decision-record linkage for each admission/renewal/revocation event.
3. Require registry changelog integrity and update traceability.
4. Enforce reviewer accountability fields in certification decisions.

## Backward Compatibility
1. Existing profile v1 submissions remain valid during deprecation window.
2. v2 fields should be additive first; migration timeline documented before v1 retirement.
3. Conformance tooling should support dual validation during transition period.

## Test Plan
1. Schema tests:
   - new profile v2 schema validity.
   - registry metadata completeness.
2. Conformance tests:
   - v2 evidence class presence checks.
   - tier-rule matrix checks.
3. Failure-mode tests:
   - missing evidence class rejection.
   - stale evidence rejection.
   - invalid registry linkage rejection.

## Rollout Plan
1. RFC review and acceptance.
2. Add v2 schemas + sample artifacts + migration notes.
3. Add conformance checks for v1/v2 dual support.
4. Update governance runbooks and certification playbook.
5. Announce v1 deprecation timeline (target: post-`v0.3.x` stabilization).

## Alternatives Considered
1. Keep v1 indefinitely: rejected due to maturity and auditability limits.
2. Replace v1 immediately: rejected due to migration risk.
3. Builder-specific profiles without core schema: rejected due to interoperability fragmentation.

## Resolved Decisions
1. The normative evidence freshness window is 30 days for all tiers in v0.3.
2. `TrustedProduction` requires policy/operational evidence, not mandatory external audit attestation, in v0.3.
3. v1/v2 dual-validation overlap remains active until future governance approval retires v1.

## Implementation Evidence
1. v2 profile artifact:
   - `/Users/zglitch009/projects/logistics-ai/FIX-F/conformance/adapter_certification_profile.v2.json`
2. v2 validation test:
   - `/Users/zglitch009/projects/logistics-ai/FIX-F/tests/run_adapter_certification_profile_v2.py`
3. Certification/governance updates:
   - `/Users/zglitch009/projects/logistics-ai/FIX-F/docs/governance/CERTIFICATION_PLAYBOOK.md`
   - `/Users/zglitch009/projects/logistics-ai/FIX-F/docs/governance/GOVERNANCE_INDEX.json`
   - `/Users/zglitch009/projects/logistics-ai/FIX-F/docs/governance/RELEASE_READINESS_CHECKLIST.md`
4. Conformance/CI wiring:
   - `/Users/zglitch009/projects/logistics-ai/FIX-F/conformance/run_all_checks.py`
   - `/Users/zglitch009/projects/logistics-ai/FIX-F/tests/run_conformance_suite.py`
   - `/Users/zglitch009/projects/logistics-ai/FIX-F/.github/workflows/ci.yml`

## Approval
- Maintainer Approval:
- Governance Approval (if required):
- Date:
