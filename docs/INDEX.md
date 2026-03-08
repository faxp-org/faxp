# FAXP Docs Index

This index keeps governance, roadmap, and release artifacts discoverable while keeping the repo root clean.

Project status note: FAXP is currently experimental and early-stage; use these docs for pilot/evaluation work unless a specific release document states otherwise.

Current execution snapshot (2026-03-07):
- Workstream A (roadmap/status hygiene): Done
- Workstream B (private partner demo finalization): In Progress
- Workstream C (public anonymized adapter package): Done
- Workstream D (security/governance continuation): Ongoing
- Workstream E (adoption execution): In Progress

Checkpoint status:
- Completed this cycle: A, C.
- Remaining active execution: B, D, E.

Local CI-aligned check baseline:
- `.venv/bin/python tests/run_open_source_guardrails.py`
- `.venv/bin/python tests/run_release_readiness.py`
- `.venv/bin/python tests/run_conformance_suite.py`

## Start Here

- New reader: `README.md`
- Builder / TMS / load board implementer: `docs/BUILDERS_START_HERE.md`
- Demo user: `docs/STREAMLIT_QUICKSTART.md`
- Conformance / certification reviewer: `conformance/README.md`
- Runtime boundary clarification: `REFERENCE_RUNTIME_BOUNDARY.md`

## Governance
- `docs/governance/FAXP_GOVERNANCE_MODEL.md`
- `docs/governance/SCOPE_GUARDRAILS.md`
- `docs/governance/DECISION_RECORD_a2a-bridge-translator-only_2026-02-23.md`
- `docs/governance/DECISION_RECORD_a2a-mcp-interop-boundary_2026-02-23.md`
- `docs/governance/POLICY_PROFILES.md`
- `docs/governance/REPLAY_RUNTIME_POLICY.md`
- `docs/governance/REGISTRY_ADMISSION_POLICY.md`
- `docs/governance/REGISTRY_CHANGELOG_POLICY.md`
- `docs/governance/REGISTRY_OPERATIONS_RUNBOOK.md`
- `docs/governance/CERTIFICATION_PLAYBOOK.md`
- `docs/governance/CERTIFICATION_DECISION_RECORD_TEMPLATE.md`
- `docs/governance/DECISION_RECORDS_RUNBOOK.md`
- `docs/governance/GOVERNANCE_INDEX.json`
- `docs/governance/RELEASE_READINESS_CHECKLIST.md`

## RFCs
- `docs/rfc/RFC_TEMPLATE.md`
- `docs/rfc/RFC-v0.2-verification-neutrality.md`
- `docs/rfc/RFC-v0.3-rate-model-extensibility.md`
- `docs/rfc/RFC-v0.3-shipper-orchestration-minimal.md`
- `docs/rfc/RFC-v0.3-schema-version-negotiation.md`
- `docs/rfc/RFC-v0.3-adapter-certification-profile-v2.md`
- `docs/rfc/RFC-v0.3-provisional-booking-policy-contract.md`
- `docs/rfc/RFC-v0.3-a2a-mcp-interop-maturity.md`

## Interop
- `docs/interop/A2A_COMPATIBILITY_PROFILE.md`
- `docs/interop/A2A_CHANGE_MANAGEMENT.md`
- `docs/interop/A2A_UPSTREAM_TRACKING.json`
- `docs/interop/MCP_COMPATIBILITY_PROFILE.md`
- `docs/interop/MCP_CHANGE_MANAGEMENT.md`
- `docs/interop/MCP_UPSTREAM_TRACKING.json`

## Roadmap
- `docs/roadmap/PHASE_2_IMPLEMENTATION_ROADMAP.md`
- `docs/roadmap/VNEXT_EXECUTION_CHECKLIST_2026-03-07.md`
- `docs/roadmap/V2_IMPLEMENTATION_CHECKLIST.md` (historical)
- `docs/roadmap/TEST_MATRIX_v0.2.md`
- `docs/roadmap/SCOPE_AUDIT_2026-03-06.md`
- `docs/roadmap/BUILDER_RUNTIME_MIGRATION_PLAN.md`
- `docs/roadmap/FAXP_DEFERRED_ITEMS.md`
- `docs/roadmap/V0_2_1_PATCH_PLAN.md`
- `docs/roadmap/V0_3_0_RFC_BACKLOG.md`
- `docs/roadmap/V0_3_0_GOVERNANCE_CHECKPOINT.md`
- `docs/roadmap/V0_3_0_COMMERCIAL_MODEL_BACKLOG.md`
- `docs/roadmap/V0_3_0_SCENARIO_CATALOG.md`

## Releases
- `docs/releases/RELEASE_NOTES_v0.2.1.md`
- `docs/releases/RELEASE_NOTES_v0.2.0-alpha.1.md`
- `docs/releases/RELEASE_CANDIDATE_v0.2.0-rc.1.md`
- `docs/releases/RELEASE_CANDIDATE_v0.2.0-rc.2.md`
- `docs/releases/RELEASE_CANDIDATE_v0.2.0-rc.3.md`
- `docs/releases/RELEASE_NOTES_v0.2.0.md`

## Adapter Guidance
- `docs/builders/BUILDER_VERIFICATION_RUNTIME_HANDOFF.md`
- `docs/builders/BUILDER_INTEGRATION_PROFILE.md`
- `docs/builders/PUBLIC_ANONYMIZED_ADAPTER_PACKAGE.md`
- `docs/builders/PUBLIC_OUTREACH_EVALUATION_PACKET.md`
- `docs/builders/ADOPTION_EXECUTION_RUNBOOK.md`
- `docs/builders/examples/public_adapter_contract/README.md`
- `adapter/INTERFACE.md`

## Demo and Contributor Quick Start
- `docs/BUILDERS_START_HERE.md`
- `docs/STREAMLIT_QUICKSTART.md`
- `docs/STREAMLIT_DEMO_WALKTHROUGH.md`
- `scripts/bootstrap_demo_env.sh`

## Reference Assets
- No in-repo reference asset snapshots are currently published.
