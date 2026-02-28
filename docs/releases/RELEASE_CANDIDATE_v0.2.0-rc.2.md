# FAXP v0.2.0-rc.2 Release Candidate

## Summary
`v0.2.0-rc.2` freezes the A2A bridge compatibility track while preserving FAXP core scope and neutrality.

This release candidate confirms:
- FAXP core remains independent of A2A runtime dependencies.
- A2A compatibility is bridge/translator-based.
- Translator parity is enforced with bidirectional deterministic round-trip checks.
- Upstream A2A drift monitoring is operational.
- Builder onboarding is simplified with one-command A2A conformance checks.

## Scope Included in RC2

### A2A Bridge Compatibility
- Compatibility profile:
  - `docs/interop/A2A_COMPATIBILITY_PROFILE.md`
- Translator contract:
  - `conformance/a2a_translator_contract.json`
- Reference translator module:
  - `conformance/a2a_bridge_translator.py`

### Deterministic Translation Validation
- Bidirectional round-trip checks:
  - `FAXP -> A2A -> FAXP`
  - `A2A -> FAXP -> A2A`
- Test:
  - `tests/run_a2a_roundtrip_translation.py`
- Canonical fixtures:
  - `conformance/a2a_roundtrip_fixtures.json`

### A2A Governance + Operations
- Change management runbook:
  - `docs/interop/A2A_CHANGE_MANAGEMENT.md`
- Upstream tracking baseline:
  - `docs/interop/A2A_UPSTREAM_TRACKING.json`
- Weekly watch workflow:
  - `.github/workflows/a2a-watch.yml`
- Watch checker:
  - `scripts/check_a2a_upstream.py`
- Artifact test:
  - `tests/run_a2a_watch_artifacts.py`

### Builder Usability
- One-command A2A conformance wrapper:
  - `scripts/run_a2a_conformance.sh`

## Evidence

### Required Checks (passed)
- `./scripts/run_a2a_conformance.sh`
- `.venv/bin/python tests/run_conformance_suite.py`
- `.venv/bin/python tests/run_release_readiness.py`
- `.venv/bin/python conformance/run_all_checks.py --output /tmp/faxp_conformance_suite_report.rc2.json`

### Conformance Report Artifact
- `conformance/reports/faxp_conformance_suite_v0.2.0-rc.2.json`

## Scope Guardrail Confirmation
This RC does **not** expand FAXP into dispatch, telematics, POD/BOL, invoicing, payment, or settlement.
A2A support remains translator-layer interoperability and conformance policy, not core protocol embedding.

## Deferred / Next Track
- MCP compatibility profile and contract (loose-coupled, interop-layer only).
- External builder pilot intake using `scripts/run_a2a_conformance.sh`.
- Certification registry pilot entries for translator-capable implementers.
