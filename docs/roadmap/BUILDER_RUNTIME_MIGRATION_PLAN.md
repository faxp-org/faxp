# Builder Runtime Migration Plan (Builder-Side Artifacts)

## Purpose
Keep `FAXP` focused on protocol-core responsibilities and move builder/reference implementation artifacts to a dedicated builder-runtime workspace.

## Protocol-Core Stays In FAXP
- Schemas and message contracts (`faxp.schema.json`, `faxp.v0.2.schema.json`)
- Envelope integrity/signature/replay governance and related conformance artifacts
- Booking-plane message semantics and booking identity requirements
- Governance policy, RFCs, and certification artifacts that are protocol-level

## Builder-Side Moves To Builder Runtime Workspace
These artifacts represent implementation strategy, provider simulation, runtime orchestration, or demo UX, not normative protocol-core.

### Wave 1: Immediate Move Candidates
- `faxp_mvp_simulation.py`
- `streamlit_app.py`
- `streamlit_state_logic.py`
- `scripts/run_secure_demo.sh`
- `scripts/incident_drill.sh`
- `scripts/bootstrap_demo_env.sh`

### Wave 2: Builder Verification/Adapter Runtime Candidates
- `conformance/verifier_translator.py`
- `tests/run_verifier_translator.py`
- `tests/run_trusted_verifier_registry.py`
- `tests/run_shipper_orchestration_minimal.py`
- `tests/run_composite_booking_scenarios.py`

### Wave 3: Builder-Focused Demo/Release Docs Candidates
- `docs/STREAMLIT_QUICKSTART.md`
- `docs/STREAMLIT_DEMO_WALKTHROUGH.md`
- `docs/roadmap/TEST_MATRIX_v0.2.md`
- `docs/releases/RELEASE_NOTES_v0.2.0-alpha.1.md`

## Migration Rule
If an artifact answers "how a specific builder/runtime/provider behaves" instead of
"what every interoperable FAXP implementation must honor", it belongs in
the builder-runtime workspace.

## Operational Note
During migration, keep compatibility aliases only where needed to avoid breaking
existing demos/tests. New protocol-core artifacts must stay provider-neutral.
