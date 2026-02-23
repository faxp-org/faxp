# FAXP v0.3.0 Governance Checkpoint

Date: 2026-02-23  
Status: Active planning checkpoint

## Decision Summary

This checkpoint converts the merged v0.3 RFC drafts into an execution order with clear scope control.

### Must-Have for v0.3.0

1. `RFC-v0.3-rate-model-extensibility`
- Why now: direct commercial value and adoption (supports additional rate structures like `CWT` and `PerPallet` via controlled extension model).
- Gate: backward compatibility for `PerMile` and `Flat` remains intact.

2. `RFC-v0.3-schema-version-negotiation`
- Why now: required for safe mixed-version interop and fail-closed behavior.
- Gate: deterministic compatibility matrix and rejection reason codes.

3. `RFC-v0.3-provisional-booking-policy-contract`
- Why now: outage/exception behavior must be deterministic and auditable.
- Gate: normalized `HardBlock` / `SoftHold` / `GraceCache` semantics with policy evidence.

### Deferred to v0.3.x (after v0.3.0)

1. `RFC-v0.3-shipper-orchestration-minimal`
- Reason: expand flow surface area only after core negotiation/policy foundations are stable.

2. `RFC-v0.3-adapter-certification-profile-v2`
- Reason: governance/certification maturity update can follow once v0.3.0 core behavior is fixed.

3. `RFC-v0.3-a2a-mcp-interop-maturity`
- Reason: current interop baseline is already operational; maturity grading can be layered afterward.

## Execution Order

1. Implement `schema-version-negotiation` first (safety baseline).
2. Implement `provisional-booking-policy-contract` second (deterministic degraded behavior).
3. Implement `rate-model-extensibility` third (commercial surface expansion).
4. Re-run full conformance and release-readiness before tagging any v0.3.0 pre-release.

## Supporting Planning Artifacts

1. Commercial model backlog:
- `/Users/zglitch009/projects/logistics-ai/FAXP/docs/roadmap/V0_3_0_COMMERCIAL_MODEL_BACKLOG.md`
2. Scenario catalog:
- `/Users/zglitch009/projects/logistics-ai/FAXP/docs/roadmap/V0_3_0_SCENARIO_CATALOG.md`

## Scope Guardrails (Reconfirmed)

This checkpoint does not authorize:
1. Dispatch operations model.
2. Telematics/tracking lifecycle model.
3. POD/BOL custody workflow model.
4. Invoice/payment/settlement rails.

## Exit Criteria for v0.3.0 Planning Phase

1. Must-have RFCs moved from `Draft` to `Review` with no unresolved scope conflicts.
2. Implementation checklist published for the three must-have RFCs only.
3. Deferred RFCs remain planning-only and excluded from v0.3.0 release gate.
