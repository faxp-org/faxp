# FAXP Registry Operations Runbook

This runbook defines how registry updates are proposed, validated, and applied.

Scope:
- Registry metadata changes only.
- No runtime adapter hosting or key custody by FAXP.

Goals:
- Ensure deterministic, auditable registry changes.
- Support secure state transitions for `Active`, `Suspended`, and `Revoked`.
- Provide safe rollback workflow for incorrect or premature actions.

## 1) Supported Change Actions

1. `UPSERT`
- Update registry metadata for an existing adapter entry.
- Examples: tier upgrade, expiry refresh, profile list update, notes update.

2. `SUSPEND`
- Temporarily disable trust for an adapter pending investigation/remediation.

3. `REVOKE`
- Mark adapter as not trusted due to material security/control failure.

4. `ROLLBACK`
- Revert status impact of a prior change operation using `targetOpId`.

## 2) Required Inputs

Required artifacts:
1. Base registry JSON (`conformance/certification_registry.sample.json` pattern).
2. Registry update request JSON (`conformance/registry_update.sample.json` pattern).
3. Registry update signing keyring (`conformance/registry_update_keys.sample.json` pattern for CI/local harness).
4. Evidence references for security-impacting actions.
5. CI validation output from:
- `python3 tests/run_registry_ops_artifacts.py`
- `python3 tests/run_certification_artifacts.py`

## 3) Processing Workflow

1. Author change set:
- Populate `changeSetId`, `submittedAt`, `requestedBy`, and `operations`.
- Include `baseRegistryRef` and `approvals` metadata.
- Generate/refresh request signature with:
  - `python3 conformance/create_registry_update.py --template <request.json> --keyring <keyring.json> --kid <kid> --in-place`

2. Pre-merge checks:
- Schema validity for registry update payload.
- Registry update signature validity (`kid`, digest, signature).
- Operation ordering and `opId` uniqueness.
- Transition validity (`Active -> Suspended -> Revoked`).
- Rollback target integrity (`targetOpId` must exist and match adapter).

3. Human review:
- Confirm reason code and evidence references.
- Confirm impact scope and expiry expectations.

4. Merge and apply:
- Merge change set only after green CI and reviewer approval.
- Apply to registry artifact in a traceable commit.

5. Post-merge audit:
- Record `changeSetId` and resulting state in audit notes.
- Confirm downstream consumers can ingest updated registry payload.

## 4) Transition Policy

Allowed transitions:
1. `Active -> Suspended`
2. `Active -> Revoked`
3. `Suspended -> Revoked`
4. `Suspended -> Active` (via `UPSERT` or `ROLLBACK`)
5. `Revoked -> Active` only via explicit `ROLLBACK` of a known prior op with documented approval.

Blocked transitions:
1. Implicit `Revoked -> Active` without rollback target and approval.
2. Rollback targeting a missing or mismatched operation.

## 5) Reason Codes (Recommended)

1. `SECURITY_INCIDENT`
2. `KEY_COMPROMISE`
3. `CONTROL_FAILURE`
4. `ATTESTATION_MISMATCH`
5. `EXPIRY_RENEWAL`
6. `REMEDIATION_COMPLETE`
7. `ERRONEOUS_ACTION`

## 6) Emergency Revocation

When an active compromise is suspected:
1. Submit `REVOKE` change with `reasonCode=KEY_COMPROMISE` or `SECURITY_INCIDENT`.
2. Include incident reference in notes/evidence.
3. Execute immediate CI validation and merge path.
4. Notify implementer and instruct key rotation/remediation workflow.

## 7) Rollback Procedure

Use rollback only for erroneous actions or validated false positives.

Required rollback fields:
1. `action=ROLLBACK`
2. `adapterId`
3. `rollback.targetOpId`
4. `reasonCode=ERRONEOUS_ACTION` (or equivalent)

Validation requirements:
1. Target operation exists in the same change set.
2. Target operation belongs to same `adapterId`.
3. Restored status equals target operation pre-status.

## 8) Operational Notes

1. All registry changes should be additive and auditable.
2. Do not silently mutate history; represent corrective actions explicitly.
3. Prefer `SUSPEND` first when incident facts are incomplete.
4. Use `REVOKE` when risk is confirmed or control integrity is lost.
