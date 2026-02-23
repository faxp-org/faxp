# RFC v0.2: Verification Neutrality and Provider-Agnostic Design

Status: Draft  
Protocol: FAXP (Freight Agent eXchange Protocol)  
Version Target: v0.2  
Authors: FAXP Project Team  
Last Updated: 2026-02-21

## 1. Summary

This RFC defines how FAXP remains provider-neutral for verification workflows (compliance, identity, biometric, and future methods) while preserving auditable, secure message exchange.

Core decision: verification stays protocol-level generic, while vendor implementations live in adapters/plugins outside the core protocol.

## 2. Motivation

FAXP is intended as an open standard. Embedding a specific verification vendor in the protocol schema or default behavior creates lock-in risk, governance friction, and reduced interoperability.

The protocol should define:
- message structure and validation rules,
- security controls (signatures, TTL, replay prevention),
- neutral verification semantics.

It should not require:
- a specific vendor,
- a specific API,
- raw biometric payload exchange.

## 3. Scope

In scope:
- neutral verification object model,
- capability negotiation fields,
- conformance requirements.

Out of scope:
- direct integration with any specific provider API,
- governance/legal policy text beyond technical conformance statements.

## 4. Design Principles

- Provider agnostic: no required vendor names in protocol fields.
- Backward compatible: additive changes where possible.
- Security first: signed attestations, replay/TTL checks, verifier trust controls.
- Privacy preserving: only references/tokens/proofs on-wire, no raw biometric data.

## 5. Proposed Protocol Changes (v0.2)

## 5.1 VerificationResult normalization

Extend `ExecutionReport.VerificationResult` to a neutral structure:

```json
{
  "status": "Success",
  "category": "Biometric",
  "method": "LivenessPlusDocument",
  "provider": "provider-opaque-id",
  "assuranceLevel": "AAL2",
  "score": 94,
  "token": "opaque-verification-token",
  "evidenceRef": "sha256:ab12...",
  "verifiedAt": "2026-02-21T17:30:00Z",
  "expiresAt": "2026-02-22T17:30:00Z",
  "attestation": {
    "alg": "ED25519",
    "kid": "verifier-20260221",
    "sig": "base64-signature"
  }
}
```

Notes:
- `provider` is an opaque ID string, not a protocol-enforced vendor enum.
- `category` and `method` are semantic descriptors for interoperability.
- `attestation` binds result integrity to trusted verifier keys.

## 5.2 Capability negotiation (agent-level)

Add optional capabilities metadata to participating agents (transport-specific placement allowed), for example:

```json
{
  "VerificationCapabilities": {
    "supportedCategories": ["Compliance", "Biometric", "Identity"],
    "supportedMethods": ["AuthorityRecordCheck", "LivenessPlusDocument"],
    "minAssuranceLevel": "AAL1",
    "requiresSignedAttestation": true
  }
}
```

This allows deterministic matching without encoding provider-specific dependencies.

## 5.3 VerifiedBadge mapping

`VerifiedBadge` remains protocol-level and provider-neutral:
- `None`
- `Basic`
- `Premium`

Mapping from verification evidence to badge is implementation policy, not vendor identity.

## 6. Conformance Requirements

Implementations claiming FAXP v0.2 compliance MUST:
- accept verification results without requiring any specific provider name,
- validate attestation signature when signed verification is required by policy,
- enforce message TTL/replay protections for verification-bearing messages,
- reject raw biometric artifacts in protocol payloads.

Implementations SHOULD:
- support both `HMAC_SHA256` and `ED25519` verifier/message signing modes,
- publish supported verification categories/methods via capabilities,
- keep provider adapters outside protocol-core modules.

Implementations MUST NOT:
- make one vendor mandatory in protocol schema,
- hardcode vendor-specific fields as required protocol fields,
- transmit raw biometric images/templates in FAXP message bodies.

## 7. Migration from v0.1.1

Current v0.1.1 behavior (e.g., provider labels like FMCSA/iDenfy) can be preserved behind adapters.

Recommended migration path:
1. Keep existing message types and flow.
2. Normalize `VerificationResult` fields per Section 5.1.
3. Add capability negotiation metadata as optional fields.
4. Move vendor-specific logic into adapter layer modules.
5. Add conformance tests for vendor neutrality.

## 8. Security and Privacy Notes

- Signed verifier attestations should include algorithm and key ID (`kid`) for trust verification.
- Key rotation support is required operationally.
- Token/evidence references should be opaque and non-PII where possible.
- Storage/logging should redact sensitive fields.

## 9. Open Questions

- Should FAXP define a minimal canonical method taxonomy in-core, or leave all methods implementation-defined?
- Should assurance level vocabulary be fixed (e.g., AAL-like) or extensible via profile namespaces?
- Should capabilities be transported in a dedicated protocol message in v0.3?

## 10. Acceptance Criteria for v0.2

- RFC-approved schema updates merged.
- Protocol tests pass with at least two mocked providers using same neutral object model.
- No required vendor-specific fields remain in core schema validation.
- Documentation updated with adapter pattern guidance.
