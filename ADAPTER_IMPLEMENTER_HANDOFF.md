# Adapter Implementer Handoff Checklist

This checklist is the implementation handoff for any builder to host an FMCSA adapter while staying FAXP-conformant.

Primary contract references:
- `/Users/zglitch009/projects/logistics-ai/FAXP/adapter/INTERFACE.md`
- `/Users/zglitch009/projects/logistics-ai/FAXP/CERTIFICATION_PLAYBOOK.md`
- `/Users/zglitch009/projects/logistics-ai/FAXP/REGISTRY_OPERATIONS_RUNBOOK.md`
- `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/adapter_test_profile.schema.json`
- `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/fmcsa_adapter_test_profile.v1.json`
- `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/submission_manifest.schema.json`

## 1) Build Scope

Implementer owns:
- Production adapter hosting and uptime.
- Secrets, key management, observability, incident response, and SLAs.
- FMCSA upstream integration runtime.
- Temporary cache/fallback behavior and business continuity policy.

FAXP owns:
- Protocol-neutral adapter contract.
- Certification profile and conformance gates.
- Registry schema and certification lifecycle.

FAXP does not own:
- Production adapter hosting for brokers/carriers.
- Runtime carrier verification operations.
- Customer credentials or secrets for builder-hosted adapters.

## 2) Endpoint Requirements

Required endpoint:
- `POST /v1/fmcsa/verify`

Request:
- `Content-Type: application/json`
- Body requires `mcNumber` string/number-like value.

Response:
- Signed wrapper with:
  - `payload`
  - `signature_algorithm`
  - `signature_key_id`
  - `signature`

Payload minimum:
- `ok`
- `VerificationResult`
- `ProviderExtensions`

## 3) Security Baseline (Conformant Tier)

Required:
1. Signed request validation.
2. Signed response wrapper.
3. Nonce replay protection.
4. Timestamp skew checks.
5. Fail-closed behavior on signature/contract violations.
6. Audit trail for verify decisions and denials.

Recommended:
1. HTTPS-only in non-local runtime.
2. Token auth plus signed request checks.
3. Rate limiting (per IP and global).
4. Key rotation policy with active `kid` tracking.

## 4) Normalized Output Requirements

`VerificationResult` must include:
- `status`
- `category`
- `method`
- `provider`
- `assuranceLevel`
- `score`
- `token`
- `evidenceRef`
- `verifiedAt`

`ProviderExtensions` must include:
- `mcNumber`
- `sourceAuthority`
- `carrier`

`carrier` should include:
- `usdot`
- `mc`
- `name`
- `operatingStatus`
- `hasCurrentInsurance`
- `interstateAuthorityOk`

Legacy normalized payload compatibility must still be accepted by the FAXP reference client for transition periods.

## 5) CI / Certification Gates to Run Before Release

Must pass:
1. `python3 tests/run_adapter_test_profile.py`
2. `python3 tests/run_fmcsa_hosted_adapter.py`
3. `python3 tests/run_adapter_server_translation.py`
4. `python3 tests/run_certification_artifacts.py`
5. `python3 tests/run_conformance_bundle.py`

Recommended local command set:
1. `.venv/bin/python tests/run_adapter_test_profile.py`
2. `.venv/bin/python tests/run_fmcsa_hosted_adapter.py`
3. `.venv/bin/python tests/run_adapter_server_translation.py`
4. `.venv/bin/python tests/run_certification_artifacts.py`
5. `.venv/bin/python tests/run_conformance_bundle.py`

## 6) Deployment Readiness Checklist

1. Endpoint deployed behind TLS.
2. Auth token configured (`Authorization: Bearer ...`).
3. Request signing keys configured and rotated.
4. Verifier response signing keys configured and rotated.
5. Drift and parser logging enabled.
6. Rate limits and body-size limits configured.
7. Health endpoint protected according to policy.

## 7) Certification Submission Package (to FAXP Registry)

Required files:
1. Adapter profile JSON (schema-valid): `conformance/adapter_profile.schema.json`
2. Registry entry JSON (schema-valid): `conformance/certification_registry.schema.json`
3. Adapter test profile ID(s) supported (for FMCSA: `FAXP_FMCSA_ADAPTER_TEST_V1`)
4. Conformance report artifact (bundle output)
5. Active signer key IDs used for adapter response signatures

Required assertions:
1. Hosting model declared accurately (builder-hosted).
2. Tier declared accurately (for example `SelfAttested` or `Conformant`).
3. Signed request/response controls enabled as declared.
4. Translator normalization preserved (no direct provider-shape leakage to FAXP clients).

## 8) Production Cutover Steps

1. Validate staging adapter with full conformance test suite.
2. Register adapter metadata in certification registry artifacts.
3. Point FAXP clients to the implementer adapter base URL.
4. Observe pilot traffic and verify fail-closed behavior.
5. Promote to full production after burn-in.

## 9) Change Management Rules

1. No breaking request/response changes without a new adapter test profile version.
2. Keep current profile ID stable for additive-only updates.
3. Re-run conformance suite on every deployment candidate.
4. Update certification artifacts when tier/status changes.
