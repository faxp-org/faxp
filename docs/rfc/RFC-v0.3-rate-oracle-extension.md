# RFC-v0.3-rate-oracle-extension

Status: Draft (Planning-only)  
Scope class: In-Scope (optional extension metadata only)  
Target: v0.3.x

## Summary
Define an optional, provider-agnostic rate-oracle extension for FAXP booking-plane messages.
This RFC standardizes how benchmark/reference pricing evidence can be carried in messages.
FAXP does not host or mandate any oracle service.

## Motivation
Participants may want to attach lane benchmark context (for example market index references) during negotiation.
Without a common extension shape, each integration becomes custom and non-interoperable.

## Non-Goals
- No required dependency on any oracle vendor.
- No FAXP-hosted oracle service.
- No dispatch, tracking, POD/BOL, invoicing, or settlement expansion.

## Proposed Extension (Planning Draft)
Optional metadata block (name TBD): `ReferenceRateEvidence`

Candidate fields:
- `source` (string): provider/system name (opaque)
- `sourceType` (string enum candidate): `BenchmarkAPI`, `InternalModel`, `ManualReference`
- `retrievedAt` (RFC3339 string)
- `rateModel` (enum aligned with active FAXP rate models)
- `amount` (number)
- `currency` (string)
- `laneDescriptor` (string/object, optional)
- `confidence` (number 0-1, optional)
- `evidenceRef` (string, optional)
- `attestation` (optional signature envelope if provided externally)

## Scope Guardrail Alignment
- Extension is optional and additive.
- Core booking decision logic must not require this block.
- Verification/authentication of FAXP messages remains separate from market-data quality.
- Regulatory eligibility decisions remain out of scope for FAXP core.

## Backward Compatibility
- Omitted extension must not break validation.
- Unknown extension keys should be ignored or fail-closed by local policy, not protocol mandate.

## Conformance Impact (Deferred)
If accepted later:
- add profile artifact under `conformance/`
- add dedicated tests under `tests/`
- add checklist entry in release readiness governance docs

## Open Questions
1. Should `confidence` be standardized or provider-defined only?
2. Should benchmark staleness thresholds be protocol-level or policy-profile-level?
3. Should extension be attached to `BidRequest`, `BidResponse`, both, or `ExecutionReport` snapshots only?
