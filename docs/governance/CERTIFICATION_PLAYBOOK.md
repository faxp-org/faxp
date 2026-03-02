# FAXP Certification Playbook

This playbook defines how implementers submit adapter certification bundles and how FAXP evaluates them.

Purpose:
- Keep FAXP protocol governance separate from adapter operations.
- Standardize certification intake for any builder-hosted adapter.
- Provide deterministic pass/fail checks before registry acceptance.
- Responsibility boundary reference:
  - `docs/governance/VERIFICATION_RESPONSIBILITY_MODEL.md`

Builder capability claim reference:
- `docs/adapters/BUILDER_INTEGRATION_PROFILE.md`
- `conformance/builder_integration_profile.v1.json`

## 1) Certification Tiers

1. `SelfAttested`
- Implementer submits profile and self-attestation.
- FAXP validates schema and signature consistency.

2. `Conformant`
- Implementer passes conformance and adapter test-profile checks.
- Submission manifest and bundle consistency checks must pass.

3. `TrustedProduction`
- Includes all `Conformant` requirements plus operational evidence:
  - incident response runbook,
  - security review artifact,
  - SLA/availability policy,
  - key management and rotation policy.

## 1.1) Certification Profile v2

FAXP also maintains a v2 certification profile artifact for builder-hosted adapter certification maturity.

Reference artifact:
- `conformance/adapter_certification_profile.v2.json`

v2 additions:
1. explicit evidence classes:
- `SchemaEvidence`
- `SecurityEvidence`
- `OperationalEvidence`
- `InteropEvidence`
2. deterministic registry metadata requirements:
- `adapterProfileVersion`
- `evidenceFreshnessCheckedAt`
- `keyLifecyclePolicyRef`
- `decisionRecordRef`
3. additive migration posture:
- v1 remains accepted during transition
- v1 retirement requires future governance approval

Certification decisions should treat v2 as the normative maturity target while preserving dual-support during the transition window.

## 2) Submission Package (Required)

Required bundle files:
1. Adapter profile JSON (schema valid).
2. Registry entry JSON (schema valid; entry for same adapter ID).
3. Adapter test profile JSON list (at least one).
4. Attestation keyring JSON for signature verification.
5. Conformance report JSON (`summary.passed == true` for `Conformant` and above).
6. Submission manifest JSON (schema valid; references all files above).

Reference paths:
- `conformance/adapter_profile.schema.json`
- `conformance/certification_registry.schema.json`
- `conformance/adapter_test_profile.schema.json`
- `conformance/submission_manifest.schema.json`
- `conformance/submission_manifest_keys.sample.json`
- `conformance/create_submission_manifest.py`
- `conformance/key_lifecycle_policy.schema.json`
- `conformance/key_lifecycle_policy.sample.json`
- `conformance/registry_update.schema.json`
- `conformance/registry_update_keys.sample.json`
- `conformance/create_registry_update.py`
- `docs/governance/REGISTRY_OPERATIONS_RUNBOOK.md`
- `docs/governance/REGISTRY_CHANGELOG_POLICY.md`
- `docs/governance/TRUSTED_VERIFIER_ADMISSION_REQUIREMENTS.md`
- `docs/governance/BOOKING_PLANE_COMMERCIAL_TERMS.md`
- `docs/governance/TRUST_MODEL.md`
- `docs/governance/VERIFICATION_RESPONSIBILITY_MODEL.md`
- `docs/governance/GOVERNANCE_INDEX.json`
- `docs/governance/RELEASE_READINESS_CHECKLIST.md`
- `conformance/apply_registry_update.py`
- `conformance/trusted_verifier_registry.sample.json`
- `conformance/vendor_direct_verifier_profile.v1.json`
- `conformance/trust_profile.v1.json`
- `conformance/accessorial_terms_profile.v1.json`
- `conformance/builder_integration_profile.v1.json`

## 2.1) Builder Integration Claims

Builders may also declare a normalized implementation claim using the builder integration profile.

Purpose:
1. make it easier for outside implementers to understand what a builder actually supports
2. make supported roles, flows, profiles, and verification patterns comparable across implementations
3. keep claims tied to evidence rather than marketing language

The builder integration profile does not replace certification evidence. It standardizes the claim surface around that evidence.

## 3) Intake Workflow

1. Implementer assembles submission bundle.
2. Implementer runs local checks:
- `python3 tests/run_certification_artifacts.py`
- `python3 tests/run_conformance_bundle.py`
- `python3 tests/run_adapter_test_profile.py`
- `python3 tests/run_submission_manifest.py`
- `python3 tests/run_create_submission_manifest.py`
- `python3 tests/run_key_lifecycle_policy.py`
- `python3 tests/run_registry_ops_artifacts.py`
- `python3 tests/run_registry_changelog_artifacts.py`
- `python3 tests/run_trusted_verifier_registry.py`
- `python3 tests/run_vendor_direct_profile.py`
- `python3 tests/run_trust_profile.py`
- `python3 tests/run_accessorial_terms.py`
- `python3 tests/run_accessorial_terms_profile.py`
- `python3 tests/run_booking_plane_commercial_terms_doc.py`
- `python3 tests/run_governance_index.py`
- `python3 tests/run_release_readiness.py`
- `python3 tests/run_apply_registry_update.py`
- `python3 tests/run_create_registry_update.py`
- `python3 tests/run_conformance_suite.py`
  - or run one-command full suite:
  - `python3 conformance/run_all_checks.py --output /tmp/faxp_conformance_suite_report.json`
3. Implementer submits bundle and conformance output.
4. FAXP verifier reruns checks in CI.
5. If all checks pass, registry entry is accepted/updated.
6. If checks fail, submission is rejected with explicit failing check IDs.
7. Reviewer emits a decision artifact using:
- `docs/governance/CERTIFICATION_DECISION_RECORD_TEMPLATE.md`
8. Reviewer follows decision-record operations runbook:
- `docs/governance/DECISION_RECORDS_RUNBOOK.md`

## 4) Pass/Fail Gates

Mandatory gates:
1. JSON schema validity for profile, registry entry, test profiles, and manifest.
2. Attestation digest/signature verification.
3. Bundle cross-reference integrity:
- adapter ID alignment,
- tier alignment,
- hosting model alignment,
- supported profile alignment.
4. Conformance report pass status for requested tier (`Conformant` or `TrustedProduction`).
5. Policy profile conformance synchronization:
- Normative profile matrix in `docs/governance/POLICY_PROFILES.md` is valid.
- All three degraded modes are represented by active profile artifacts:
  - `HardBlock`
  - `SoftHold`
  - `GraceCache`
- Conformance suite includes `policy_profile_sync` and passes.
6. Decision record template checks pass:
- `python3 tests/run_decision_record_template.py`
- Decision artifact includes required evidence links and reason codes.
7. Decision record artifact checks pass:
- `python3 tests/run_decision_record_artifacts.py`
- Sample/active decision record cross-links are coherent with conformance + registry artifacts.
8. Registry changelog artifact checks pass:
- `python3 tests/run_registry_changelog_artifacts.py`
- Changelog entries match update operations and snapshot end state.
9. Governance index checks pass:
- `python3 tests/run_governance_index.py`
- `GOVERNANCE_INDEX.json` coverage matches required artifacts, suite checks, and CI references.
10. Release readiness checks pass:
- `python3 tests/run_release_readiness.py`
- `RELEASE_READINESS_CHECKLIST.md` coverage matches required artifacts, tests, suite checks, and governance-index sync.
11. Trusted verifier admission checks pass:
- `python3 tests/run_trusted_verifier_registry.py`
- trusted verifier registry artifact is present and runtime trust checks reject non-admitted providers in non-local mode.
12. Vendor-direct profile checks pass:
- `python3 tests/run_vendor_direct_profile.py`
- vendor-direct profile artifact and trusted-registry alignment are valid for non-local certification policy.
13. Trust profile checks pass:
- `python3 tests/run_trust_profile.py`
- trust profile artifact remains aligned with registry policy, source class semantics, and non-local trust requirements.
14. Accessorial commercial-term profile checks pass:
- `python3 tests/run_accessorial_terms.py`
- `python3 tests/run_accessorial_terms_profile.py`
- `python3 tests/run_booking_plane_commercial_terms_doc.py`
- booking-plane accessorial semantics remain explicit, and settlement operations remain out of scope for protocol core.

Additional gates for `TrustedProduction`:
1. Operational evidence references are present in manifest.
2. Evidence fields are non-empty and reviewable.

## 5) Registry Decision Rules

Accept when:
1. All mandatory gates pass.
2. Requested tier is justified by evidence and checks.
3. No revoked/suspended conflicts exist for the same adapter ID.

Reject when:
1. Any mandatory gate fails.
2. Tier/evidence mismatch exists.
3. Manifest references missing or invalid bundle files.

## 6) Renewal and Expiry

1. Every active entry should include an expiry timestamp.
2. Implementers must resubmit before expiry for renewal.
3. Any key rotation affecting attestation signer must trigger revalidation.

## 7) Revocation Triggers

1. Proven signature/control compromise.
2. Material contract violations in production.
3. Failure to remediate critical findings within policy SLA.

Revocation action:
- Mark registry entry `Revoked` or `Suspended`.
- Record rationale and timestamp in registry notes/audit logs.

## 8) Policy Profile Conformance (Required)

Implementers must declare and prove how outage handling maps to FAXP policy profiles.

Required evidence:
1. Claimed policy profile IDs (`VerificationPolicyProfileID`) used in production.
2. Outage behavior traces for at least:
- negative verification fail (`VerificationNegativeResult`)
- degraded verification path with provider outage/error
- human exception path where applicable
3. Proof that decision outcomes match profile semantics:
- `HardBlock` -> fail-closed (`DispatchAuthorization=Blocked`)
- `SoftHold` -> provisional hold (`DispatchAuthorization=Hold`)
- `GraceCache` -> tier-based continuity (`Allowed`/`Hold`/`Blocked` per policy)
4. Auditability evidence for exception approvals:
- exception approval reference present when approved
- decision reason code aligns with policy rule

Required local checks before submission:
1. `python3 tests/run_verification_policy_profile.py`
2. `python3 tests/run_policy_decisions.py`
3. `python3 tests/run_policy_profile_sync.py`
4. `python3 conformance/run_all_checks.py --output /tmp/faxp_conformance_suite_report.json`

## 9) Optional Interop Maturity Claims

Implementers that claim A2A and/or MCP interoperability maturity must back that claim with objective evidence.

Reference artifact:
- `conformance/interop_maturity_profile.v1.json`

Rules:
1. Interop maturity claims are optional and must not imply mandatory FAXP core dependencies on A2A or MCP.
2. Maturity is inferred from evidence, not asserted as a free-form badge.
3. A2A claims require:
- compatibility profile,
- translator contract,
- round-trip fixtures,
- upstream tracking artifact,
- active watch workflow,
- passing local conformance checks.
4. MCP claims require:
- compatibility profile,
- tooling contract,
- upstream tracking artifact,
- active watch workflow,
- passing local conformance checks.
5. `L4-Certifiable` for v0.3 means the evidence package is sufficient for certification review; it does not require interop-specific production incident drills.

Required local checks before claiming interop maturity:
1. `./scripts/run_a2a_conformance.sh`
2. `./scripts/run_mcp_conformance.sh`
3. `python3 tests/run_interop_maturity_profile.py`
4. `python3 conformance/run_all_checks.py --output /tmp/faxp_conformance_suite_report.json`
