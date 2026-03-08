# Verification Responsibility Model

## Purpose
Define clear ownership boundaries for verification in FAXP so protocol governance remains neutral and implementers can integrate trusted providers without vendor lock-in.

## Ownership by Role

### 1) FAXP Foundation / Protocol Governance
- Defines protocol envelope, validation, signing, replay/TTL, and conformance requirements.
- Defines trusted verifier admission policy and certification criteria.
- Validates attestation format, signature, trust-registry membership, and policy decision behavior.
- Does not host verifier services, vendor APIs, or production adapter infrastructure.
- Does not store implementer production credentials for verifier vendors.

### 2) Implementer / Agent Builder / TMS Integrator
- Chooses verifier providers based on business policy and certification status.
- Hosts integration runtime when needed (for example, implementer-adapter model).
- Manages vendor credentials, endpoint security, key rotation, and incident response.
- Emits verification results that satisfy FAXP trust and schema requirements.
- Owns SLA and operational continuity commitments to broker/carrier/shipper users.
- Owns replay backend operations and on-call response for non-local deployments.

### 3) Verifier Vendor (External Service)
- Performs compliance or identity checks under its own operating model.
- Provides signed attestations or API outputs that can be translated into FAXP-compatible verification results.
- Owns source-data quality, service availability, and verifier-specific evidence provenance.

### 4) Broker/Carrier/Shipper Organizations Using Agents
- Set policy thresholds (risk tiers, booking behavior on verifier outage, exception process).
- Approve or deny operational exceptions per internal policy.
- Own legal/compliance accountability for production dispatch and commercial decisions.

## Canonical Source Classes
- `vendor-direct`: agent/integrator consumes verifier vendor attestation directly.
- `implementer-adapter`: implementer-hosted adapter normalizes vendor output to FAXP contract.
- `authority-only`: authority lookup path without higher-trust vendor attestation.
- `self-attested`: lowest-trust source, policy-restricted for production use.

Legacy alias:
- `hosted-adapter` is accepted for backward compatibility and maps to `implementer-adapter`.

## Enforcement Boundary
- FAXP enforces attestation validity and trust policy.
- FAXP does not execute external verification itself.
- Non-local runs fail closed when trusted verification requirements are unmet.
- FAXP does not determine regulatory eligibility; it authenticates protocol messages and can transport optional verifier evidence.

## Recommended Handoff Flow
1. FAXP booking complete (`ExecutionReport`).
2. Broker/carrier systems generate native legal docs (rate con/addendum) from FAXP terms.
3. Existing onboarding/payment/dispatch process executes in TMS/portals.
4. FAXP stays out of dispatch tracking and payment rails.

## Certification Implications
- Admission checks evaluate provider/source/assurance alignment and signature validity.
- Certification approves conformance posture, not vendor business endorsement.
- Multiple verifier vendors can be admitted if they satisfy the same objective criteria.

## Replay Operations Ownership

Replay runtime operational gates are tracked in:

- `docs/governance/REPLAY_OPERATIONS_GATES.md`
