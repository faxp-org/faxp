# Adapter Hosting and Trust Boundary (Public)

This document defines who should host the adapter and who should hold credentials in a vendor-neutral way.

## Core Rule

FAXP is the protocol contract and validation layer.
FAXP is not the credential custodian for source-system API access.

## Supported Hosting Models

1. TMS-hosted adapter (default production model)
   - TMS operates the adapter runtime.
   - TMS stores customer credentials/tokens in TMS-controlled secret infrastructure.
   - TMS owns runtime monitoring, incidents, and customer support path.

2. Builder-hosted integration service (pilot/transition model)
   - Builder operates adapter runtime with strict security controls.
   - Builder stores credentials/tokens in builder-controlled secret infrastructure.
   - Use this for sandbox/pilot phases when TMS-native hosting is not ready.

## Out of Scope Model

Customer-hosted adapter is out of scope for standard rollout unless the customer also operates its own TMS/runtime stack.

## Credential Custody and Data Handling

1. Credentials/tokens stay with the adapter operator (TMS or builder).
2. Credentials/tokens must never appear in FAXP protocol payloads.
3. Logs must redact auth/session fields.
4. Public artifacts must remain synthetic and non-attributable.

## Security Baseline

1. Managed secrets storage.
2. Least-privilege integration credentials.
3. Rotation policy and incident-triggered rotation.
4. TLS for all transport.
5. Request-id based auditability without secret leakage.

## Operational Ownership

1. Adapter operator owns runtime availability and incident response.
2. FAXP maintainers own protocol specification, validation, and conformance artifacts.
3. Contract ambiguity triage is shared.

## Release Gate

Before broad rollout:
1. Deterministic update invariants pass (ID reuse, no duplicates, stable counts).
2. Mapping and validation gates pass (body + envelope).
3. Security signoff is complete.
