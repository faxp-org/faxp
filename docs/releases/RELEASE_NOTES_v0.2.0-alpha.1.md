# FAXP v0.2.0-alpha.1 Release Notes

Date: 2026-02-21  
Release type: Alpha checkpoint (protocol neutrality + security hardening)

## Summary

This alpha consolidates the v0.2 neutrality/security foundation while preserving v0.1.1 compatibility.

## Included

1. Provider-neutral verification model
- Neutral `VerificationResult.provider` IDs in simulation outputs.
- Legacy compatibility preserved via `providerAlias` and legacy metadata fields.
- v0.2 compatibility schema file added:
  - `/Users/zglitch009/projects/logistics-ai/FAXP/faxp.v0.2.schema.json`

2. Signed verifier attestation enforcement
- `ExecutionReport.VerificationResult.attestation` enforced when signed verifier mode is enabled.
- Trust checks enforce expected algorithm, trusted key ID, and signature validity.

3. Fail-closed validation hardening
- Raw biometric payload rejection.
- Unknown verification category/method rejection.
- Invalid category/method pair rejection.

4. CI conformance expansion
- Schema compatibility checks (`v0.1.1` + `v0.2`).
- Streamlit state regression checks.
- Missing attestation rejection check.
- Malformed attestation rejection check.
- Unknown taxonomy rejection check.
- Two-provider neutrality smoke vectors:
  - MockBiometric provider neutral ID assertion.
  - FMCSA mock neutral ID assertion.

5. Documentation/governance updates
- Runbook expansion in README.
- Protocol neutrality boundary documented.
- Legacy field deprecation timeline documented.
- Governance conformance snippet added in deferred items doc.
- v0.2 checklist and test matrix updated with evidence-linked status.

## Compatibility

- Runtime protocol remains `0.1.1`.
- `faxp.v0.2.schema.json` provides compatibility-track validation for `0.1.1` and `0.2.0` envelopes.
- Legacy provider aliases (including `iDenfy`) still function.

## Known Remaining Work

1. Optional live FMCSA contract test against sandbox/stub API in CI.
2. Dedicated compatibility suite for deprecation warnings through v0.3.x.
3. Formal protocol version bump in runtime when v0.2 wire semantics are promoted from compatibility track.

## Suggested Verification After Tag

1. `python3 tests/run_schema_compatibility.py`
2. `python3 tests/run_streamlit_state_logic.py`
3. `./scripts/run_secure_demo.sh sim --use-kms-command --provider MockBiometricProvider --verification-status Success`
4. `./scripts/run_secure_demo.sh sim --use-kms-command --provider FMCSA --verification-status Success`
