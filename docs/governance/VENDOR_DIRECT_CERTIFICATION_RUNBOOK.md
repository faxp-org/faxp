# Vendor-Direct Certification Runbook

This runbook defines the minimum operator workflow for vendor-direct verifier certification artifacts.

Purpose:
- Keep FAXP protocol governance and certification deterministic.
- Ensure vendor-direct attestation evidence is signed, auditable, and referenced by decision artifacts.
- Prevent release drift where profile/registry/decision records are not linked.

Scope:
- In scope: certification artifacts and conformance checks for vendor-direct verification evidence.
- Out of scope: hosting verifier infrastructure, operating vendor APIs, or managing vendor production credentials.

## Required Artifacts
1. `conformance/vendor_direct_verifier_profile.v1.json`
2. `conformance/vendor_direct_attestation.sample.json`
3. `conformance/trusted_verifier_registry.sample.json`
4. `conformance/certification_decision_record.sample.json`
5. `conformance/attestation_keys.sample.json`

## Procedure
1. Ensure provider identity in attestation matches trusted registry `providerId`.
2. Ensure attestation `source` and `provenance` normalize to `vendor-direct`.
3. Ensure attestation `attestation.alg/kid/sig` are present and valid.
4. Ensure decision record includes:
- `VENDOR_DIRECT_ATTESTATION_PASS` in `decisionReasonCodes`
- `VendorDirectAttestation` evidence link to `conformance/vendor_direct_attestation.sample.json`
5. Run required checks (below) and keep outputs green before merge/release.

## Validation Commands
```bash
./.venv/bin/python tests/run_vendor_direct_profile.py
./.venv/bin/python tests/run_vendor_direct_attestation_flow.py
./.venv/bin/python tests/run_decision_record_artifacts.py
FAXP_APP_MODE=local ./.venv/bin/python conformance/run_all_checks.py --output /tmp/faxp_vendor_direct_conformance.json
```

## Expected Outcomes
1. Vendor-direct profile and trusted-registry alignment pass.
2. Vendor-direct attestation signature/provenance checks pass.
3. Certification decision record links attestation evidence and reason code correctly.
4. Conformance suite includes and passes `vendor_direct_attestation_flow`.

## Governance References
1. `docs/governance/CERTIFICATION_PLAYBOOK.md`
2. `docs/governance/TRUSTED_VERIFIER_ADMISSION_REQUIREMENTS.md`
3. `docs/governance/VERIFICATION_RESPONSIBILITY_MODEL.md`
4. `docs/governance/RELEASE_READINESS_CHECKLIST.md`
