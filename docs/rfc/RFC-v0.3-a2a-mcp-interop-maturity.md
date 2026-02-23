# RFC: v0.3 A2A/MCP Interop Maturity

## RFC Metadata
- RFC ID: `rfc-v0.3-a2a-mcp-interop-maturity`
- Title: `Define maturity criteria for A2A translator and MCP tool-layer interop`
- Author(s): `FAXP Governance Working Group`
- Status: `Draft`
- Target Version: `v0.3.0`
- Created: `2026-02-23`
- Last Updated: `2026-02-23`

## Summary
Establish a maturity model and acceptance criteria for A2A and MCP interoperability artifacts so implementers can claim interop readiness consistently without introducing mandatory A2A/MCP dependencies in FAXP core.

## Motivation
FAXP already has compatibility profiles, contracts, conformance scripts, and watch workflows for A2A and MCP. A maturity framework is needed to classify implementation readiness, avoid overclaiming, and support certification decisions.

## Scope Gate (Required)
- Scope Classification: `In-Scope`
- Protocol-Core Impacted Files:
  - None required for base proposal.
  - Interop/conformance/governance artifacts only.
- Message Types Added/Changed:
  - None.
- Schema Fields Added/Changed:
  - Potential maturity metadata in certification profile/registry artifacts (not core envelope).

### Required Checks
- [x] This RFC stays within booking-plane protocol scope.
- [x] No new dispatch-orchestration message or state model is introduced.
- [x] No new tracking lifecycle model (telematics/POD/BOL custody) is introduced.
- [x] No new settlement lifecycle model (invoice/payment/remittance/factoring) is introduced.
- [x] If `Scope Expansion`, this RFC includes full security/compliance/interoperability/migration analysis and explicit approval request.

## Detailed Design
1. Define interop maturity levels:
   - `L1-Declared`: profile/contract references present.
   - `L2-Tested`: local conformance scripts pass with required artifacts.
   - `L3-Watched`: upstream drift watch workflows active and governed.
   - `L4-Certifiable`: evidence package maps to registry/certification policy.
2. A2A maturity criteria:
   - compatibility profile maintained
   - round-trip translator checks pass
   - upstream watch artifacts + workflow active
3. MCP maturity criteria:
   - tooling profile/contract maintained
   - watch artifact checks pass
   - upstream watch artifacts + workflow active
4. Preserve strict boundary:
   - A2A/MCP remain optional interop layers.
   - FAXP core protocol has no mandatory runtime dependency on either.
5. Define evidence mapping:
   - maturity level must be backed by named conformance checks and artifact references.

## Security Considerations
1. Prevent maturity badge inflation by requiring objective test evidence.
2. Require fail-closed posture when interop claims lack required artifacts.
3. Ensure upstream watch failures surface governance actions.
4. Preserve least-privilege and audit-correlation controls in MCP tooling claims.

## Compliance and Governance Considerations
1. Keep standards-neutral stance (no provider lock-in).
2. Require governance review when maturity criteria change.
3. Require compatibility contracts to remain aligned with documented scope guardrails.
4. Keep maturity scoring out of protocol-wire requirements.

## Backward Compatibility
1. Existing interop artifacts remain valid; maturity levels are additive classification.
2. No changes required for implementations that do not claim A2A/MCP maturity.
3. Existing v0.2 conformance remains unaffected.

## Test Plan
1. Artifact checks:
   - A2A and MCP profile/contract consistency.
   - watch tracking config validity.
2. Conformance checks:
   - `run_a2a_conformance.sh`
   - `run_mcp_conformance.sh`
   - conformance suite contains required interop checks.
3. Failure-mode checks:
   - missing watch artifact.
   - stale tracking baseline metadata.
   - drift workflow failure path issue creation behavior.

## Rollout Plan
1. RFC review and acceptance.
2. Add maturity model docs and registry mapping fields.
3. Add conformance checks enforcing minimum evidence for each maturity level.
4. Update certification playbook with interop maturity claim guidance.

## Alternatives Considered
1. Binary interop yes/no claim: rejected (insufficient granularity).
2. No maturity framework: rejected (inconsistent certification posture).
3. Mandatory A2A/MCP core embedding: rejected (scope and neutrality violation).

## Open Questions
1. Should maturity level be represented directly in registry entries or inferred from evidence?
2. What review cadence should be required for maintaining `L3-Watched` status?
3. Should `L4-Certifiable` require production incident drill evidence for interop pathways?

## Approval
- Maintainer Approval:
- Governance Approval (if required):
- Date:
