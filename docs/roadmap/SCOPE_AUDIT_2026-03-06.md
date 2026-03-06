# Scope Audit (2026-03-06)

## Decision
`FAXP` remains a booking-plane messaging protocol.

Builder-side execution concerns (including FMCSA/compliance checks, biometric checks, provider orchestration, and provider-specific scoring logic) should live in a dedicated builder-runtime workspace.

## Protocol-Core (Keep in FAXP)
- `faxp.schema.json`
- `faxp.v0.2.schema.json`
- `conformance/booking_identity_profile.v1.json`
- `conformance/operational_handoff_profile.v1.json`
- `docs/governance/SCOPE_GUARDRAILS.md`
- `docs/governance/VERIFICATION_RESPONSIBILITY_MODEL.md`
- `docs/governance/TRUST_MODEL.md`

## Builder/Reference Runtime (Migrate to Builder Runtime Workspace)
- `faxp_mvp_simulation.py`
- `streamlit_app.py`
- `streamlit_state_logic.py`
- `scripts/run_secure_demo.sh`
- `scripts/incident_drill.sh`
- `scripts/bootstrap_demo_env.sh`
- `conformance/verifier_translator.py`
- `tests/run_verifier_translator.py`
- `tests/run_trusted_verifier_registry.py`
- `tests/run_composite_booking_scenarios.py`
- `tests/run_shipper_orchestration_minimal.py`
- `docs/STREAMLIT_QUICKSTART.md`
- `docs/STREAMLIT_DEMO_WALKTHROUGH.md`
- `docs/roadmap/TEST_MATRIX_v0.2.md`
- `docs/releases/RELEASE_NOTES_v0.2.0-alpha.1.md`

## Boundary Clarification
FAXP may carry optional neutral verification evidence in message payloads.
FAXP does not perform verifier operations.

That means:
- in scope: message authenticity, envelope validation, replay/nonce checks, neutral message contracts.
- out of scope: regulator/vendor API execution, biometric matching, operational verifier hosting, provider-specific runtime logic.

## Current State
- FMCSA hosted adapter/server artifacts were removed in this cleanup cycle.
- Scope guardrail CI now lint-checks protocol-core schema artifacts only.
- Remaining provider-specific runtime logic is tracked as migration backlog to the builder-runtime workspace.
