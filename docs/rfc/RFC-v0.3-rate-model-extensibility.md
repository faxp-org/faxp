# RFC: v0.3 Rate Model Extensibility

## RFC Metadata
- RFC ID: `rfc-v0.3-rate-model-extensibility`
- Title: `Extend booking-plane rate model taxonomy beyond PerMile/Flat`
- Author(s): `FAXP Governance Working Group`
- Status: `Accepted (Implemented)`
- Target Version: `v0.3.0`
- Created: `2026-02-23`
- Last Updated: `2026-02-23`

## Summary
Add a versioned, extensible rate model taxonomy for booking-plane negotiation so FAXP can represent additional commercial pricing structures while preserving compatibility with existing `PerMile` and `Flat` flows.

## Motivation
Initial behavior supported `PerMile` and `Flat` only. This was too narrow for broader adoption. A structured extension path enabled common pricing patterns without forking protocol semantics.

## Scope Gate (Required)
- Scope Classification: `In-Scope`
- Protocol-Core Impacted Files:
  - `faxp.v0.2.schema.json` (compatibility bridge updates for v0.3 migration)
  - `faxp_mvp_simulation.py`
  - `streamlit_app.py`
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
3. Add v0.3-compatible model identifiers:
   - `PerMile`
   - `Flat`
   - `PerPallet`
   - `CWT`
   - `PerHour`
   - `LaneMinimum`
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
1. RFC reviewed and accepted.
2. Schema + simulation support implemented with strict fail-closed validation.
3. Conformance checks and Streamlit scenario controls added for active models.
4. Released as part of v0.3.x with regression and compatibility evidence.

## Alternatives Considered
1. Keep fixed enum forever (`PerMile`, `Flat` only): rejected due to adoption limits.
2. Free-form string models with no schema constraints: rejected due to interoperability risk.
3. Separate message types per model: rejected due to unnecessary protocol complexity.

## Resolved Questions
1. Active set includes `PerMile`, `Flat`, `PerPallet`, `CWT`, `PerHour`, and `LaneMinimum`.
2. Unit normalization and required field semantics are enforced via runtime validation plus conformance profiles.
3. Unsupported models fail closed unless explicitly activated by protocol/runtime profile.

## Implementation Evidence
- Runtime:
  - `faxp_mvp_simulation.py`
  - `streamlit_app.py`
- Schema:
  - `faxp.schema.json`
  - `faxp.v0.2.schema.json`
- Conformance/Profile:
  - `conformance/rate_model_profile.v1.json`
- Tests:
  - `tests/run_rate_model_extensibility.py`
  - `tests/run_rate_model_requirements.py`
  - `tests/run_rate_search_requirements.py`
  - `tests/run_rate_model_profile.py`

## Approval
- Maintainer Approval: Approved
- Governance Approval (if required): Recorded in governance index + release readiness gates
- Date: 2026-02-27
