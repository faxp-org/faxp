# FAXP Trust Model

## Purpose
Define what trust controls FAXP enforces at the protocol layer and what stays outside FAXP ownership.

## Trust Controls In Scope
1. Message authenticity and integrity checks on FAXP envelopes.
2. Replay protection and TTL/clock-skew validation.
3. Signed verifier attestation validation (`alg`, `kid`, `sig`).
4. Trusted verifier registry policy enforcement in non-local mode.
5. Fail-closed behavior when required trust checks are missing or invalid.

## Trust Controls Out of Scope
1. Hosting verifier services or adapter infrastructure.
2. Operating FMCSA, identity, or compliance provider APIs.
3. Storing provider API credentials for implementers.
4. Acting as a global participant identity authority or onboarding registry.

## Canonical Source Classes
- `vendor-direct`
- `implementer-adapter`
- `authority-only`
- `self-attested`

Notes:
- `hosted-adapter` remains a backward-compatible alias for `implementer-adapter`.
- `authority-only` and `self-attested` are policy-restricted for production use and cannot satisfy non-local trusted booking requirements by themselves.

## Non-Local Baseline
1. Require trusted verifier registry membership.
2. Require active provider status.
3. Require source and assurance-level allowlist match.
4. Require signed attestation when configured by trust policy.
5. Fail closed on verifier errors or missing trust evidence.

## Governance Artifacts
- Machine-readable trust profile: `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/trust_profile.v1.json`
- Verifier admission policy: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/governance/TRUSTED_VERIFIER_ADMISSION_REQUIREMENTS.md`
- Verification boundary policy: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/governance/VERIFICATION_RESPONSIBILITY_MODEL.md`

## Certification Impact
Implementers are certified against trust conformance evidence, not against vendor preference.
Any external verifier can be admitted if it satisfies the same objective requirements.
