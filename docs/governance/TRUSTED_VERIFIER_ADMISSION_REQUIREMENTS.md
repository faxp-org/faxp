# Trusted Verifier Admission Requirements

This policy defines minimum admission criteria for verifier providers whose attestations can be trusted in non-local FAXP runs.

## Purpose
- Keep FAXP protocol-core vendor-neutral.
- Require objective trust controls before verifier outputs influence booking decisions.
- Ensure certification reviewers can evaluate verifier trust posture deterministically.

## Scope
- Applies to trusted verifier registry artifacts:
  - `conformance/trusted_verifier_registry.sample.json`
  - `conformance/vendor_direct_verifier_profile.v1.json`
- Applies to non-local runtime enforcement paths in protocol and Streamlit demo.
- Applies to certification review for builder-hosted compliance and identity adapters.
- Does not require FAXP foundation to host verifier infrastructure.

## Normative Requirements

1. Non-local mode must enforce trusted verifier registry membership.
2. Trusted verifier entries must be status `Active` (or `Approved`) to be accepted.
3. Registry entries must declare:
   - `providerId`
   - `providerType`
   - `status`
   - `allowedSources`
   - `allowedAssuranceLevels`
   - Canonical `allowedSources` values should use:
     - `vendor-direct`
     - `implementer-adapter`
     - `authority-only`
     - `self-attested`
   - Legacy source labels may be retained for backward compatibility (for example, `hosted-adapter`).
4. Verification result provider IDs must match a trusted registry entry.
5. Verification result source must be in entry `allowedSources`.
6. Verification result assurance level must be in entry `allowedAssuranceLevels`.
7. If `allowedAttestationKids` is non-empty, attestation `kid` must be in that allowlist.
8. Mock providers may exist in registry for testing, but must remain non-active.

## Certification Review Checklist

1. Verify trusted registry artifact is present and schema-consistent with policy.
2. Verify non-local runtime rejects providers missing from trusted registry.
3. Verify non-local runtime rejects non-active providers.
4. Verify non-local runtime rejects disallowed source values.
5. Verify non-local runtime rejects disallowed assurance levels.
6. Verify trusted verifier checks are part of CI and conformance suite.

## Required Test Evidence

- `tests/run_trusted_verifier_registry.py`
- `tests/run_vendor_direct_profile.py`
- `conformance/run_all_checks.py` includes `trusted_verifier_registry`
- CI workflow runs trusted verifier registry checks

## Operational Boundary

- FAXP validates signed attestations and trust policy.
- Builder-hosted adapters perform external compliance and identity verification.
- FAXP certification governs admission criteria and conformance evidence, not adapter hosting operations.
