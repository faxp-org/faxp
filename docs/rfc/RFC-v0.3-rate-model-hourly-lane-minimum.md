# RFC: v0.3 Rate Model Expansion (PerHour + LaneMinimum)

## RFC Metadata
- RFC ID: `rfc-v0.3-rate-model-hourly-lane-minimum`
- Title: `Add booking-plane PerHour and LaneMinimum rate models`
- Author(s): `FAXP Governance Working Group`
- Status: `Accepted (Implemented)`
- Target Version: `v0.3.x`
- Created: `2026-02-27`
- Last Updated: `2026-02-27`

## Summary
Add two booking-plane commercial rate models, `PerHour` and `LaneMinimum`, with deterministic validation and execution-report normalization while preserving backward compatibility for existing rate models.

## Motivation
Current FAXP booking-plane support covers `PerMile`, `Flat`, `PerPallet`, and `CWT`. Real broker-carrier negotiations also use:
1. `PerHour` (time-based pricing, often for local/short-haul and specialized handling windows).
2. `LaneMinimum` (lane floor/guarantee semantics where a minimum total applies even if computed variable components are lower).

Adding these models improves practical coverage without expanding into dispatch operations or settlement workflows.

## Scope Gate (Required)
- Scope Classification: `In-Scope`
- Protocol-Core Impacted Files:
  - `/Users/zglitch009/projects/logistics-ai/FIX-F/faxp_mvp_simulation.py`
  - `/Users/zglitch009/projects/logistics-ai/FIX-F/faxp.schema.json`
  - `/Users/zglitch009/projects/logistics-ai/FIX-F/faxp.v0.2.schema.json`
  - `/Users/zglitch009/projects/logistics-ai/FIX-F/conformance/rate_model_profile.v1.json` (or version bump successor)
  - `/Users/zglitch009/projects/logistics-ai/FIX-F/streamlit_app.py`
- Message Types Added/Changed:
  - `NewLoad` (rate object extension only)
  - `LoadSearch` (rate filter extension only)
  - `BidRequest` (rate object extension only)
  - `BidResponse` (counter-rate extension only)
  - `ExecutionReport` (agreed-rate extension only)
- Schema Fields Added/Changed:
  - `Rate.RateModel` enum additions: `PerHour`, `LaneMinimum`
  - model-specific required fields in `Rate`:
    - `PerHour`: `UnitBasis=hour`, `Quantity` required
    - `LaneMinimum`: `UnitBasis=lane`, `Amount` is lane minimum total

### Required Checks
- [x] This RFC stays within booking-plane protocol scope.
- [x] No new dispatch-orchestration message or state model is introduced.
- [x] No new tracking lifecycle model (telematics/POD/BOL custody) is introduced.
- [x] No new settlement lifecycle model (invoice/payment/remittance/factoring) is introduced.
- [x] If `Scope Expansion`, this RFC includes full security/compliance/interoperability/migration analysis and explicit approval request.

## Detailed Design
1. Add `PerHour` model semantics:
   - `Rate.Amount` is interpreted as currency per hour.
   - `Rate.UnitBasis` must be `hour`.
   - `Rate.Quantity` is required for deterministic total.
2. Add `LaneMinimum` model semantics:
   - `Rate.Amount` is interpreted as minimum total lane amount.
   - If rate components are present, final agreed charge is `max(computed_components_total, lane_minimum_amount)`.
   - `Rate.UnitBasis` must be `lane`.
3. Preserve current rate component behavior:
   - `LineHaulAmount` + optional `FuelSurchargeAmount` / `FuelSurchargePercent` remain valid where compatible.
4. Keep fail-closed behavior:
   - Unknown/unsupported model fails validation.
   - Required model-specific fields missing -> validation fail.
5. Maintain deterministic execution output:
   - `ExecutionReport.AgreedRate` must preserve the model and fields needed to reconstruct pricing semantics.

## Security Considerations
1. Strict model-specific field requirements prevent semantic ambiguity attacks.
2. Deterministic normalization prevents hidden arithmetic drift between agents.
3. Existing envelope signatures, nonce, replay, and TTL remain unchanged and required.

## Compliance and Governance Considerations
1. Provider-neutral commercial model support only; no oracle/provider dependency in core.
2. Conformance profile and tests must be updated before runtime activation.
3. Streamlit/demo controls must not bypass validation and fail-closed requirements.

## Backward Compatibility
1. Existing `PerMile`, `Flat`, `PerPallet`, and `CWT` payloads remain valid.
2. Agents that do not support the new models must fail closed with explicit reason.
3. Version negotiation behavior remains governed by protocol compatibility profile.

## Test Plan
1. Unit/schema tests:
   - valid/invalid vectors for `PerHour` and `LaneMinimum`.
   - missing required field failures.
   - unit-basis mismatch failures.
2. Integration tests:
   - broker->carrier and carrier->broker happy paths with each new model.
   - counter/reject semantics preserved.
3. Regression tests:
   - no behavior change for existing models and extension fields.
4. Conformance updates:
   - update/add rate model profile artifact and signature checks.
   - update release readiness/governance index mappings.

## Rollout Plan
1. RFC accepted.
2. Conformance artifact + tests landed and gate-checked.
3. Runtime/schema changes landed with fail-closed behavior.
4. Streamlit controls and validation messaging updated.
5. Included in RC soak cycle.

## Alternatives Considered
1. Defer all new models to post-v0.3: rejected due to immediate commercial coverage gaps.
2. Implement ad-hoc free-form model strings: rejected due to interoperability risk.
3. Expand directly into settlement semantics: rejected as out of scope.

## Resolved Questions
1. Time quantity naming: `Quantity` + `UnitBasis=hour`.
2. `LaneMinimum` supports minimum-only contract form and does not require components.
3. Model-specific rounding remains profile/policy-level, not protocol-core arithmetic policy.

## Implementation Evidence
- Runtime:
  - `/Users/zglitch009/projects/logistics-ai/FIX-F/faxp_mvp_simulation.py`
  - `/Users/zglitch009/projects/logistics-ai/FIX-F/streamlit_app.py`
- Conformance/Profile:
  - `/Users/zglitch009/projects/logistics-ai/FIX-F/conformance/rate_model_profile.v1.json`
- Schema:
  - `/Users/zglitch009/projects/logistics-ai/FIX-F/faxp.schema.json`
  - `/Users/zglitch009/projects/logistics-ai/FIX-F/faxp.v0.2.schema.json`
- Tests:
  - `/Users/zglitch009/projects/logistics-ai/FIX-F/tests/run_rate_model_extensibility.py`
  - `/Users/zglitch009/projects/logistics-ai/FIX-F/tests/run_rate_model_requirements.py`
  - `/Users/zglitch009/projects/logistics-ai/FIX-F/tests/run_rate_search_requirements.py`

## Approval
- Maintainer Approval: Approved
- Governance Approval (if required): Recorded in roadmap + conformance gate set
- Date: 2026-02-27
