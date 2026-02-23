# RFC: v0.3 Rate Model Extensibility

## RFC Metadata
- RFC ID: `rfc-v0.3-rate-model-extensibility`
- Title: `Extend booking-plane rate model taxonomy beyond PerMile/Flat`
- Author(s): `FAXP Governance Working Group`
- Status: `Draft`
- Target Version: `v0.3.0`
- Created: `2026-02-23`
- Last Updated: `2026-02-23`

## Summary
Add a versioned, extensible rate model taxonomy for booking-plane negotiation so FAXP can represent additional commercial pricing structures while preserving compatibility with existing `PerMile` and `Flat` flows.

## Motivation
Current v0.2 behavior supports `PerMile` and `Flat` only. This is sufficient for MVP demos but too narrow for broader adoption. A structured extension path enables implementers to add common pricing patterns without forking protocol semantics.

## Scope Gate (Required)
- Scope Classification: `In-Scope`
- Protocol-Core Impacted Files:
  - `/Users/zglitch009/projects/logistics-ai/FAXP/faxp.v0.2.schema.json` (compatibility bridge updates for v0.3 migration)
  - `/Users/zglitch009/projects/logistics-ai/FAXP/faxp_mvp_simulation.py`
  - `/Users/zglitch009/projects/logistics-ai/FAXP/streamlit_app.py`
- Message Types Added/Changed:
  - `NewLoad` (rate object extension only)
  - `LoadSearch` (rate filter extension only)
  - `BidRequest` (rate object extension only)
  - `BidResponse` (counter-rate extension only)
  - `ExecutionReport` (agreed-rate extension only)
- Schema Fields Added/Changed:
  - `Rate.RateModel` enum/list handling and compatible extension fields
  - Optional `RateTerms` object for model-specific parameters

### Required Checks
- [x] This RFC stays within booking-plane protocol scope.
- [x] No new dispatch-orchestration message or state model is introduced.
- [x] No new tracking lifecycle model (telematics/POD/BOL custody) is introduced.
- [x] No new settlement lifecycle model (invoice/payment/remittance/factoring) is introduced.
- [x] If `Scope Expansion`, this RFC includes full security/compliance/interoperability/migration analysis and explicit approval request.

## Detailed Design
1. Keep existing rate object contract shape and introduce extension points:
   - Base fields remain: `RateModel`, `Amount`, `Currency`.
   - Add optional `RateTerms` object for model-specific parameters.
2. Preserve required behavior for legacy models:
   - `PerMile`: `Amount` interpreted as USD/mile (or currency/mile).
   - `Flat`: `Amount` interpreted as total trip price.
3. Add v0.3-compatible model identifiers (initial draft set for discussion):
   - `PerMile`
   - `Flat`
   - `PerHour` (optional in v0.3 pending approval)
   - `PerWeightUnit` (optional in v0.3 pending approval)
4. Validation behavior:
   - Unknown `RateModel` fails closed unless explicitly listed in negotiated compatibility profile.
   - `RateTerms` keys must be schema-validated per model.
5. Do not introduce new message types in this RFC.

## Security Considerations
1. Prevent semantic ambiguity attacks by requiring strict model-specific validation.
2. Reject malformed or mixed unit payloads (`PerMile` + incompatible `RateTerms`).
3. Preserve signing and replay/TTL controls for all updated payloads.
4. Ensure rate normalization occurs before policy decisions and audit logging.

## Compliance and Governance Considerations
1. Keep extensibility provider-neutral and implementation-agnostic.
2. Require conformance artifacts for each newly enabled rate model.
3. Document any model-specific assumptions (units, currency, rounding) in test vectors.
4. Keep post-booking accessorial policy semantics unchanged in this RFC.

## Backward Compatibility
1. Existing `PerMile` and `Flat` messages remain valid without changes.
2. `RateTerms` remains optional; absent for legacy payloads.
3. v0.2 agents that do not support new models must fail closed and surface clear reason codes.

## Test Plan
1. Schema tests:
   - valid/invalid vectors for each approved `RateModel`.
   - strict validation for `RateTerms` per model.
2. Integration tests:
   - end-to-end load and truck happy paths for `PerMile` and `Flat` unchanged.
   - optional new-model negotiation vectors when enabled.
3. Failure-mode tests:
   - unknown model rejection.
   - invalid terms/unit mismatch rejection.
   - compatibility mismatch rejection (broker/carrier model support mismatch).

## Rollout Plan
1. RFC review and governance approval.
2. Implement schema + simulation support behind explicit v0.3 compatibility guard.
3. Add conformance checks and Streamlit scenario toggles for approved models only.
4. Release as part of `v0.3.0` after regression and compatibility suite passes.

## Alternatives Considered
1. Keep fixed enum forever (`PerMile`, `Flat` only): rejected due to adoption limits.
2. Free-form string models with no schema constraints: rejected due to interoperability risk.
3. Separate message types per model: rejected due to unnecessary protocol complexity.

## Open Questions
1. Which additional models are in `v0.3.0` minimum set vs deferred to `v0.3.x`?
2. Should unit normalization rules be protocol-level or profile-level?
3. Should model support be declared in `VerificationCapabilities`-style commercial capabilities metadata?

## Approval
- Maintainer Approval:
- Governance Approval (if required):
- Date:
