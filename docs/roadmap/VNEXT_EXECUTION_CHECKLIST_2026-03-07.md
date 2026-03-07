# FAXP vNext Execution Checklist (2026-03-07)

Status: Active  
Scope Class: Phase 2 close-out and adoption readiness  
Owner: Maintainer

## Objective

Close the remaining execution gap between:
1. protocol-core readiness (already passing), and
2. builder adoption readiness (private partner demo polish + public anonymized guidance).

## Constraints

1. Keep FAXP within booking-plane scope.
2. Keep partner-specific Diesel artifacts private unless explicitly approved.
3. Do not block contributor usability while reference-runtime migration decisions remain open.

## Workstream A: Roadmap and Status Hygiene

Owner: Maintainer  
Priority: P0

Tasks:
1. Update Phase 2 roadmap status from planned to active close-out.
2. Reclassify v0.2 implementation checklist as historical evidence.
3. Keep docs index aligned with active vs historical planning artifacts.

Exit criteria:
1. No roadmap document implies that already-completed work is still unstarted.
2. New contributors can identify one current execution plan in under 2 minutes.

## Workstream B: Diesel Private Demo Finalization

Owner: Maintainer  
Priority: P0

Tasks:
1. Freeze one deterministic private smoke run and outputs.
2. Produce a concise "protocol vs adapter" handoff explanation for the Diesel demo.
3. Lock a stable request/response packet set for Jamie review.
4. Confirm deterministic stop update contract using stop IDs from GET response.

Exit criteria:
1. Private runbook can be replayed end-to-end without ad hoc fixes.
2. Demo packet clearly separates FAXP responsibilities from adapter responsibilities.
3. Jamie has a single clean artifact set to review.

## Workstream C: Public Anonymized Adapter Spec Package

Owner: Maintainer  
Priority: P1

Tasks:
1. Create synthetic, vendor-neutral request/response examples.
2. Publish "reference adapter contract" docs with no partner identifiers.
3. Add explicit experimental maturity notice on those pages.

Exit criteria:
1. Public contributors can understand adapter contract shape without Diesel access.
2. No partner-specific names, domains, tokens, IDs, or local environment details appear.

## Workstream D: Security and Governance Continuation

Owner: Maintainer  
Priority: P1

Tasks:
1. Keep CI/release-readiness green on main.
2. Continue red-team follow-up items in the security thread.
3. Keep branch protection and required checks consistent with workflow behavior.

Exit criteria:
1. Conformance and release-readiness remain passing.
2. Security hardening changes do not regress contributor usability.

## Workstream E: Adoption Execution

Owner: Maintainer  
Priority: P2

Tasks:
1. Use final anonymized package as the default outreach artifact.
2. Keep partner-specific implementation details in private channels.
3. Track outreach progress separately from protocol-core changes.

Exit criteria:
1. Outreach conversations can start from a consistent, public-safe technical packet.
2. New integration prospects can evaluate FAXP without private credentials.

## Sequencing

1. Complete Workstream A.
2. Complete Workstream B.
3. Complete Workstream C.
4. Run Workstream D continuously.
5. Execute Workstream E after C is published.

