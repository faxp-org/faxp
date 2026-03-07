# FAXP Phase 2 Implementation Roadmap

Status: Active (Close-out Execution)  
Scope Class: Booking-plane implementation maturity  
Updated: 2026-03-07

Project maturity note: this roadmap tracks experimental-to-production hardening; items should be treated as pilot-stage until release readiness gates are met.

## Progress Snapshot (2026-03-07)

1. Protocol-core and conformance baseline are stable (`conformance/run_all_checks.py` passing on main).
2. Security/governance hardening workstreams are active and now part of normal CI enforcement.
3. Remaining Phase 2 risk is primarily adoption packaging, roadmap hygiene, and builder-facing clarity.

Current execution plan:
- `docs/roadmap/VNEXT_EXECUTION_CHECKLIST_2026-03-07.md`

Execution state matrix:
- Workstream A (roadmap hygiene): Done
- Workstream B (private partner demo): In Progress
- Workstream C (public anonymized adapter package): Next
- Workstream D (security/governance continuation): Ongoing
- Workstream E (adoption execution): Blocked on C

Local check baseline (CI-aligned):
- `.venv/bin/python tests/run_open_source_guardrails.py`
- `.venv/bin/python tests/run_release_readiness.py`
- `.venv/bin/python tests/run_conformance_suite.py`

## Phase 2 Goal

Turn FAXP from a well-scoped booking protocol into a practical implementation standard that outside builders can integrate without expanding FAXP into dispatch, tracking, document custody, or settlement.

## Scope Boundary

Phase 2 remains within FAXP's current boundary:

In scope:
- booking-plane handoff and implementation maturity
- builder integration guidance
- optional extension planning and implementation where additive
- certification and conformance hardening
- scenario and interoperability coverage expansion

Out of scope:
- dispatch execution workflows
- live tracking and telematics lifecycle
- POD/BOL custody and document adjudication
- invoicing, remittance, payment rails, and settlement
- FAXP-hosted verifier or operational infrastructure
- benchmark/reference pricing standardization without a demonstrated interoperability need; pricing models and market benchmarks remain builder-side by default

Apply the scope litmus test in `docs/governance/SCOPE_GUARDRAILS.md` before proposing any new protocol field, profile, or workflow.

## Priority Order

1. Operational Handoff Metadata
2. Counterparty Identity and Booking Reference Hardening
3. Builder Integration Profiles
4. Certification and Contributor Onboarding
5. Scenario Expansion

## 1) Operational Handoff Metadata

Objective:
Define how a valid `ExecutionReport` can be handed into downstream TMS, portal, ops-agent, or human workflow without moving dispatch into FAXP core.

Primary references:
- `docs/rfc/RFC-v0.3-operational-handoff-metadata.md`
- `docs/governance/SCOPE_GUARDRAILS.md`
- `docs/roadmap/V0_3_0_RFC_BACKLOG.md`

Target deliverables:
- accepted RFC and implementation checklist
- neutral handoff metadata profile
- explicit distinction between required booking identity and optional ops-routing metadata
- conformance tests proving routing-only semantics
- optional demo visibility if it helps explain downstream handoff

Guardrails:
- no dispatch packet content
- no appointment lifecycle model
- no dispatch state machine
- no settlement or document-custody behavior

Success criteria:
- booking remains valid without dispatch content
- required booking identity is explicit and testable
- optional handoff metadata is neutral, additive, and routing-only
- builders can route post-booking workflow consistently without custom one-off conventions

## 2) Counterparty Identity and Booking Reference Hardening

Objective:
Strengthen the minimum identity and booking-reference contract so a booking is operationally meaningful even before downstream dispatch workflow begins.

Target deliverables:
- explicit booking identity profile
- clearer guidance for `AgentID`, counterparty identity, and booking references
- neutral booking reference requirements for external system correlation
- tests for minimum viable booking identity on confirmed bookings

Guardrails:
- no global participant registry
- no universal commercial trust score
- no FAXP-owned business reputation system

Success criteria:
- a valid booking always identifies the counterparty and booking references
- identity requirements are separated cleanly from optional operational routing metadata
- downstream systems can correlate bookings without requiring custom local conventions

## 3) Builder Integration Profiles

Objective:
Make it easier for TMSs, load boards, portals, and agent builders to implement FAXP in a repeatable, certifiable way.

Target deliverables:
- builder implementation guides for booking-plane integration
- clearer vendor-direct verifier guidance
- clearer implementer-hosted adapter guidance
- implementation claim matrix for supported profiles
- improved handoff documentation for external builders

Primary references:
- `docs/builders/BUILDER_VERIFICATION_RUNTIME_HANDOFF.md`
- `docs/governance/CERTIFICATION_PLAYBOOK.md`
- `docs/governance/VERIFICATION_RESPONSIBILITY_MODEL.md`

Guardrails:
- no FAXP-hosted adapter service
- no mandated verifier vendor
- no protocol-core dependency on a builder-specific deployment pattern

Success criteria:
- an outside builder can identify the minimum artifacts, tests, and profiles needed for conformance
- verifier integration patterns stay provider-neutral
- certification expectations are concrete and reproducible

## 4) Certification and Contributor Onboarding

Objective:
Turn the repo into something outside builders and contributors can navigate productively after the public launch.

Target deliverables:
- clearer starter implementation issues
- certification submission examples and review expectations
- contributor-facing docs polish where needed
- a more explicit "start here" path for implementers
- early PR review conventions for public contributors

Guardrails:
- maintain PR-based merge control
- avoid scope drift through issue triage
- keep certification evidence-based rather than vendor-relationship-based

Success criteria:
- new contributors can identify where to start
- builders can find certification expectations without reverse-engineering the repo
- public issues and PRs stay aligned to current scope boundaries

## 5) Scenario Expansion

Objective:
Expand booking-plane realism through more scenario coverage without drifting into operations execution.

Primary references:
- `docs/roadmap/V0_3_0_SCENARIO_CATALOG.md`
- `docs/roadmap/V0_3_0_COMMERCIAL_MODEL_BACKLOG.md`

Target deliverables:
- more real-world booking scenarios
- more commercial edge-case fixtures
- richer examples across shipper, broker, and carrier roles
- expanded interop and conformance test vectors

Guardrails:
- keep all new scenarios within booking-plane semantics
- use external references or notes for downstream operational evidence rather than embedding dispatch or settlement logic

Success criteria:
- broader real-world commercial coverage
- fewer ambiguous semantics for implementers
- stronger regression confidence as adoption grows

## What Phase 2 Is Not

Phase 2 does not expand FAXP into:
- dispatch execution
- telematics/tracking lifecycle
- POD/BOL custody
- invoice/payment/remittance/factoring workflows
- FAXP-hosted verification or operational services

## Exit Criteria

Phase 2 is complete when:
1. operational handoff metadata has a clear RFC-backed path and implementation guidance
2. booking identity and reference requirements are explicit and testable
3. builder implementation guidance is materially easier to follow
4. certification and contributor workflows are ready for sustained external participation
5. scenario coverage is strong enough to support implementation feedback without expanding protocol scope
