# FAXP v0.2 Test Matrix (Neutral Verification + Capability Negotiation)

Status: Draft  
Updated: 2026-02-21

## 1. Purpose

This matrix tracks conformance and regression tests for v0.2 changes:
- provider-agnostic verification payloads,
- capability negotiation behavior,
- fail-closed security behavior.

## 2. Baseline Regression (Must Stay Green)

1. `./run_secure_demo.sh sim --use-kms-command --provider MockBiometricProvider --verification-status Success`
Expected:
- Load booking completes.
- Truck booking completes.
- Validation errors remain zero.

2. `./run_secure_demo.sh check --use-kms-command`
Expected:
- `SecuritySelfTest ... failed=0`
- Load + truck flows complete.

3. `./incident_drill.sh`
Expected:
- Baseline pass.
- Incident detection confirmed.
- Security gate pass.

## 3. Verification Neutrality Tests

1. Mock biometric provider emits neutral fields
Command:
- `./run_secure_demo.sh sim --use-kms-command --provider MockBiometricProvider --verification-status Success`
Assert in output:
- `VerificationResult.category = Biometric`
- `VerificationResult.method = LivenessPlusDocument`
- `VerificationResult.assuranceLevel = AAL2`
- `VerificationResult.evidenceRef` exists

2. FMCSA mock emits neutral fields
Command:
- `./run_secure_demo.sh sim --use-kms-command --provider FMCSA --verification-status Success --mc-number 498282`
Assert in output:
- `VerificationResult.category = Compliance`
- `VerificationResult.method = AuthorityRecordCheck`
- `VerificationResult.assuranceLevel = AAL1`

3. Backward compatibility fields still accepted
Input shape includes:
- `source`, `mcNumber`, `carrier`, `error`
Expected:
- Validation passes.

4. Legacy provider alias remains accepted
Command:
- `./run_secure_demo.sh sim --use-kms-command --provider iDenfy --verification-status Success`
Assert in output:
- Booking completes.
- `VerificationResult.provider = MockBiometricProvider`
- `VerificationResult.providerAlias = iDenfy`

## 4. Capability Negotiation Tests

1. Default capabilities aligned (happy path)
Command:
- `./run_secure_demo.sh sim --use-kms-command --provider MockBiometricProvider --verification-status Success`
Expected:
- Verification proceeds.

2. Forced mismatch fails closed
Command:
- `python3 faxp_mvp_simulation.py --force-capability-mismatch --provider MockBiometricProvider --verification-status Success`
Expected:
- Explicit capability mismatch message.
- Verification not attempted.
- No booking completion.

3. FMCSA mismatch path
Command:
- `python3 faxp_mvp_simulation.py --force-capability-mismatch --provider FMCSA --verification-status Success --mc-number 498282`
Expected:
- Capability mismatch message in load flow and/or truck flow.

## 5. Negative Security/Validation Tests

1. Reject raw biometric artifacts
Payload contains any of:
- `faceImage`, `selfieImage`, `documentImage`, `biometricTemplate`, `rawBiometric`
Expected:
- Validation fails with biometric artifact rejection.

2. Reject invalid verification score
Input:
- `VerificationResult.score = 101`
Expected:
- Validation fails.

3. Reject invalid attestation shape
Input:
- `attestation` present but missing `alg`/`kid`/`sig`
Expected:
- Validation fails.

4. FMCSA parser regression guard
Fixtures:
- `tests/fmcsa_fixtures/contract_authority_active_with_bipd_amount.json`
- `tests/fmcsa_fixtures/inactive_no_insurance.json`
- `tests/fmcsa_fixtures/no_carrier_match.json`
Command:
- `python3 tests/run_fmcsa_parser_fixtures.py`
Expected:
- One pass per fixture.
- MC normalization and authority/insurance interpretation remain stable.

5. FMCSA contract drift detector guard
Command:
- `python3 - <<'PY'`
- `from faxp_mvp_simulation import _unknown_fmcsa_top_level_keys`
- `print(_unknown_fmcsa_top_level_keys({"content": {}, "meta": {}, "timestamp": "x"}))`
- `PY`
Expected:
- Returns `["meta", "timestamp"]` with default config.
- Runtime logs one non-blocking warning if these keys appear in live responses.

6. Replay and TTL guards unchanged
Expected:
- Existing replay/TTL protections continue to pass/fail as before.

## 6. Cloud Streamlit Tests

1. Cloud-safe mode UI behavior
Secrets:
- `FAXP_APP_MODE=prod`
- `FAXP_CLOUD_SAFE_MODE=1`
Expected:
- Runtime caption shows cloud-safe mode.
- Provider options show `MockBiometricProvider` and `FMCSA (Authority)`.

2. Cloud booking success
Settings:
- Provider `MockBiometricProvider`
- Status `Success`
Expected:
- Booking completed with `VerifiedBadge=Premium`.

3. Cloud FMCSA mock behavior
Settings:
- Provider `FMCSA (Authority)`
Expected:
- No local carrier-finder path dependency.
- No crash.

4. Cloud live FMCSA behavior (when webkey is configured)
Secrets:
- `FAXP_FMCSA_WEBKEY=<valid_webkey>`
Settings:
- Provider `FMCSA (Authority)`
- FMCSA Source `live-fmcsa`
- MC `498282`
Expected:
- Verification source is `live-fmcsa`.
- Verification either succeeds with `VerifiedBadge=Basic` or fails closed with a clear FMCSA/API error.

## 7. CI Coverage Mapping

Current CI workflow (`.github/workflows/ci.yml`) covers:
- shell syntax,
- python compile,
- security gate,
- simulation smoke,
- security self-test,
- FMCSA parser regression check,
- FMCSA contract drift detector check,
- incident drill (CI mode).

Planned CI additions (v0.2+):
- explicit capability-mismatch test invocation,
- explicit raw-biometric rejection test vector,
- schema conformance checks for neutral verification fields.
