# FAXP Governance Model (Protocol vs Operations)

FAXP is intended to remain an open protocol and certification framework.

## Protocol Responsibilities

FAXP foundation responsibilities:

1. Protocol schemas, message semantics, and versioning.
2. Verification profile specifications.
3. Conformance/security test harness and vectors.
4. Certification registry metadata and governance rules.
5. Reference adapter code for interoperability testing.

## Non-Centralized Operations Boundary

FAXP should not be the default production operator for:

1. FMCSA/identity verification hosting.
2. Insurance or compliance provider hosting.
3. Payment or settlement services.
4. Telematics/tracking infrastructure.
5. Document custody (BOL/POD/invoice storage).
6. Message relay as a mandatory central hub.
7. Key custody for participants.
8. Global risk-scoring authority.

Implementers host these runtime services and prove conformance through certification.

## Certification Registry Intent

Registry entries communicate:

1. Adapter identity and hosting model.
2. Certification tier and status.
3. Supported verification policy profiles.
4. Security attestation controls.
5. Conformance report references and expiry.
