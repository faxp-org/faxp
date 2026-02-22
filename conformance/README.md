# FAXP Conformance and Certification

FAXP is a protocol and certification authority model, not a centralized transaction host.

This folder defines machine-readable artifacts for implementer-hosted adapters:

- `certification_registry.schema.json`: schema for registry metadata.
- `certification_registry.sample.json`: sample registry entry.
- `adapter_profile.schema.json`: schema for adapter self-attestation profile.
- `adapter_profile.sample.json`: sample adapter profile with self-attestation payload.
- `attestation_keys.sample.json`: test-only keyring for local/CI attestation verification.

Adapter hosting model:

1. FAXP foundation publishes protocol/profile specs and conformance tests.
2. Implementers (agent builders, TMS integrators, brokers) host adapters.
3. Registry entries record conformance/security tier and supported profiles.

Suggested certification tiers:

1. `SelfAttested`: developer/self-reported compliance.
2. `Conformant`: passes FAXP conformance test harness.
3. `TrustedProduction`: conformant plus operational security/SLA evidence.

Required minimum controls for `Conformant`:

1. Signed adapter requests and responses.
2. Replay protection and timestamp skew enforcement.
3. Auditable decision trail.

Self-attestation profile checks:

1. Profile JSON must validate against `adapter_profile.schema.json`.
2. `selfAttestation.payloadDigestSha256` must match canonical payload hash.
3. `selfAttestation.sig` must verify using the declared `kid` in the attestation keyring.
4. Registry and adapter profile must agree on adapter ID, tier, hosting model, and supported profiles.

Note:

- `attestation_keys.sample.json` is intentionally non-secret and for conformance harness testing only.
- Production implementers should store attestation keys in their own secure key management system.
