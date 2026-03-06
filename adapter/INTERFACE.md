# FAXP Adapter Interface (Compliance v1)

This document defines the implementer-facing adapter contract for compliance verification.

Goal:
- FAXP (non-profit) owns the contract, conformance checks, and certification profile.
- Implementers own hosted runtime, operations, and SLAs.

Scope:
- Applies to builder-hosted compliance adapters used by FAXP clients.
- Keeps FAXP core protocol logic independent from provider-specific API shapes.

## 1) Endpoint Contract

Method:
- `POST`

Path:
- `/v1/compliance/verify`

Content type:
- `application/json`

Request body:
```json
{
  "carrierReference": "carrier-498282"
}
```

Required request fields:
- `carrierReference`

## 2) Request Security Contract

Recommended minimum (`Conformant` tier):
- Signed request verification enabled.
- Nonce replay protection enabled.
- Timestamp skew enforcement enabled.

Signed request headers:
- `X-FAXP-Key-Id`
- `X-FAXP-Timestamp` (ISO-8601 UTC)
- `X-FAXP-Nonce` (hex)
- `X-FAXP-Signature` (hex HMAC)

Request signature canonical string:
1. `METHOD`
2. `PATH`
3. `TIMESTAMP`
4. `NONCE`
5. `SHA256(body)`

Joined by newline (`\n`) and signed with request HMAC key for `X-FAXP-Key-Id`.

## 3) Response Wrapper Contract

Adapter responses for verification should be signed wrapper objects:

```json
{
  "payload": {
    "ok": true,
    "VerificationResult": { "...": "..." },
    "ProviderExtensions": { "...": "..." }
  },
  "signature_algorithm": "HMAC_SHA256",
  "signature_key_id": "verifier-kid",
  "signature": "hex-or-base64-signature"
}
```

Wrapper fields:
- `payload`
- `signature_algorithm`
- `signature_key_id`
- `signature`

Allowed signature algorithms:
- `HMAC_SHA256`
- `ED25519`

## 4) Normalized Payload Contract

`payload.ok`:
- `true` when verification call succeeded and payload is valid.
- `false` when verification failed or upstream is unavailable.

`payload.VerificationResult` required fields:
- `status`
- `category`
- `method`
- `provider`
- `assuranceLevel`
- `score`
- `token`
- `evidenceRef`
- `verifiedAt`

`payload.ProviderExtensions` expected fields:
- `carrierReference`
- `sourceAuthority`
- `carrier`

`payload.ProviderExtensions.carrier` expected fields:
- `name`
- `authorityOk`

Legacy normalized payload (accepted for compatibility when no `VerificationResult` object):
- `found`
- `status`
- `score`
- `carrier_reference`
- `carrier_name`
- `authority_ok`

## 5) Fail-Closed Rules

Adapter client and verifier should fail closed on:
- Missing or invalid request signature (when signed requests are required).
- Replay nonce detected.
- Timestamp skew exceeds policy.
- Missing response signature wrapper (when required).
- Untrusted `signature_key_id`.
- Signature verification mismatch.
- Invalid normalized payload shape.

## 6) Certification and Conformance

Authoritative artifacts:
- `conformance/adapter_test_profile.schema.json`
- `conformance/compliance_adapter_test_profile.v1.json`
- `conformance/adapter_profile.schema.json`
- `conformance/certification_registry.schema.json`

Reference tests:
- `tests/run_adapter_test_profile.py`
- `tests/run_certification_artifacts.py`

Minimum bar for `Conformant` tier:
1. Request contract shape checks pass.
2. Response wrapper signature checks pass.
3. Translator neutral-field checks pass.
4. Legacy normalized payload checks pass.
5. Fail-closed signature-path checks pass.

## 7) Versioning and Compatibility

Profile ID:
- `FAXP_COMPLIANCE_ADAPTER_TEST_V1`

Compatibility guidance:
- Additive fields are allowed if backward compatible.
- Breaking contract changes require a new profile version (for example `..._V2`).
- FAXP core should continue consuming normalized output only.

## 8) Portability for Builder Handoff

To transfer from reference adapter to implementer adapter:
1. Keep endpoint and signed wrapper contract unchanged.
2. Keep normalized payload fields unchanged.
3. Pass the same conformance and certification test suite.
4. Update only deployment, secrets, monitoring, and SLA operations.
