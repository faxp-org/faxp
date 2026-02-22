# FAXP Conformance and Certification

FAXP is a protocol and certification authority model, not a centralized transaction host.

This folder defines machine-readable artifacts for implementer-hosted adapters:

- `certification_registry.schema.json`: schema for registry metadata.
- `certification_registry.sample.json`: sample registry entry.

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
