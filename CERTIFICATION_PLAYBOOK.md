# FAXP Certification Playbook

This playbook defines how implementers submit adapter certification bundles and how FAXP evaluates them.

Purpose:
- Keep FAXP protocol governance separate from adapter operations.
- Standardize certification intake for any builder-hosted adapter.
- Provide deterministic pass/fail checks before registry acceptance.

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

## 2) Submission Package (Required)

Required bundle files:
1. Adapter profile JSON (schema valid).
2. Registry entry JSON (schema valid; entry for same adapter ID).
3. Adapter test profile JSON list (at least one).
4. Attestation keyring JSON for signature verification.
5. Conformance report JSON (`summary.passed == true` for `Conformant` and above).
6. Submission manifest JSON (schema valid; references all files above).

Reference paths:
- `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/adapter_profile.schema.json`
- `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/certification_registry.schema.json`
- `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/adapter_test_profile.schema.json`
- `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/submission_manifest.schema.json`
- `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/submission_manifest_keys.sample.json`
- `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/create_submission_manifest.py`
- `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/registry_update.schema.json`
- `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/registry_update_keys.sample.json`
- `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/create_registry_update.py`
- `/Users/zglitch009/projects/logistics-ai/FAXP/REGISTRY_OPERATIONS_RUNBOOK.md`
- `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/apply_registry_update.py`

## 3) Intake Workflow

1. Implementer assembles submission bundle.
2. Implementer runs local checks:
- `python3 tests/run_certification_artifacts.py`
- `python3 tests/run_conformance_bundle.py`
- `python3 tests/run_adapter_test_profile.py`
- `python3 tests/run_submission_manifest.py`
- `python3 tests/run_create_submission_manifest.py`
- `python3 tests/run_registry_ops_artifacts.py`
- `python3 tests/run_apply_registry_update.py`
- `python3 tests/run_create_registry_update.py`
3. Implementer submits bundle and conformance output.
4. FAXP verifier reruns checks in CI.
5. If all checks pass, registry entry is accepted/updated.
6. If checks fail, submission is rejected with explicit failing check IDs.

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
