# Reference Runtime Boundary

## Purpose
This document prevents confusion between:
- protocol-core requirements (normative for interoperable implementations), and
- reference-runtime/demo behavior (non-normative builder guidance).

## Normative (Protocol-Core)
Normative behavior is defined by:
- `faxp.schema.json`
- `faxp.v0.2.schema.json`
- governance policy in `docs/governance/`
- conformance contracts/profiles in `conformance/`

If a rule is not represented in protocol contracts/governance/conformance, it is not protocol law.

## Non-Normative (Reference Runtime)
The following are reference-runtime artifacts:
- `faxp_mvp_simulation.py`
- `streamlit_app.py`
- `streamlit_state_logic.py`
- demo helper scripts under `scripts/` (for example `run_secure_demo.sh`)

These artifacts can illustrate integration patterns and developer workflows.
They must not be treated as mandatory protocol semantics.

## Verification Ownership Boundary
FAXP may carry neutral verification evidence in messages.
FAXP does not execute verifier operations.

Builder-side ownership includes:
- FMCSA/compliance lookup execution
- biometric verification execution
- provider-specific scoring logic
- provider credential operations

## Contribution Rule
If a change affects only runtime/demo behavior and is not required for independent interoperability, classify it as `reference-runtime` and keep protocol contracts unchanged.
