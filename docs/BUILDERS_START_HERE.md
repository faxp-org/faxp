# FAXP Builders: Start Here

This is the fastest path for a TMS team, load board team, or agent builder to understand the repo without reverse-engineering the whole project.

Use this document when you want to implement or evaluate FAXP.
Do not use it as the full certification or governance reference; those are linked only after the implementation path is clear.

## Maturity Notice

FAXP is currently experimental and early-stage.

Use sandbox/test environments first.
Treat current implementation guidance as evolving until release-readiness and interoperability criteria are met across independent builders.

## 1) Understand the Boundary First

Read these first:
- `docs/governance/SCOPE_GUARDRAILS.md`
- `docs/governance/VERIFICATION_RESPONSIBILITY_MODEL.md`

You should come away with this understanding:
1. FAXP is a booking-plane protocol.
2. FAXP standardizes booking messages and related conformance profiles.
3. FAXP does not do dispatch execution, tracking, document custody, or settlement.
4. Builder-hosted integrations (including FMCSA/compliance and biometric verification execution) remain builder-side unless there is a clear interoperability reason to standardize them.

## 2) Understand the Core Message Flow

Read:
- `README.md`
- `faxp_mvp_simulation.py`

The core booking path is:
1. `NewLoad` or `NewTruck`
2. `LoadSearch` or `TruckSearch`
3. `BidRequest`
4. `BidResponse`
5. `ExecutionReport`

That is the heart of the protocol.

If you only need the interactive demo first, stop here and use:
- `docs/STREAMLIT_QUICKSTART.md`
- `docs/STREAMLIT_DEMO_WALKTHROUGH.md`

Implementation note:
- Demo/runtime artifacts in this repo are reference material and are planned for migration into a dedicated builder-runtime workspace per `docs/roadmap/BUILDER_RUNTIME_MIGRATION_PLAN.md`.

## 3) Understand What Has Already Been Standardized

Read:
- `docs/governance/BOOKING_PLANE_COMMERCIAL_TERMS.md`
- `conformance/README.md`
- `docs/builders/BUILDER_INTEGRATION_PROFILE.md`
- `docs/builders/PUBLIC_ANONYMIZED_ADAPTER_PACKAGE.md`

Important existing protocol/profile areas:
1. booking identity
2. operational handoff metadata
3. equipment taxonomy
4. schedule commitments
5. driver configuration
6. special instructions
7. multi-stop planning
8. load reference numbers

## 4) Decide What Kind of Builder You Are

The main builder patterns currently supported are:

1. TMS or brokerage platform
   - wants to send/receive booking-plane messages
   - may use FAXP as an interoperability layer without replacing its internal ops stack

2. Agent runtime / orchestration builder
   - wants broker/carrier/shipper agents to negotiate through FAXP

3. Verifier or integration implementer
   - wants to plug in optional verification evidence or external routing patterns while staying outside protocol-core

## 5) Minimum Viable Implementation

A practical minimum first implementation is:

1. build and validate envelopes correctly
2. support one booking flow end-to-end
   - usually `NewLoad -> BidRequest -> BidResponse -> ExecutionReport`
3. pass the core conformance suite
4. keep out-of-scope concerns out of protocol messages

If you want a deeper capability declaration after that, look at:
- `conformance/builder_integration_profile.v1.json`
- `docs/builders/PUBLIC_ANONYMIZED_ADAPTER_PACKAGE.md`
- `docs/builders/PUBLIC_OUTREACH_EVALUATION_PACKET.md`
- `docs/builders/ADOPTION_EXECUTION_RUNBOOK.md`

## 6) Fastest Local Evaluation Path

If you want to understand behavior quickly before integrating:

1. `docs/STREAMLIT_QUICKSTART.md`
2. `docs/STREAMLIT_DEMO_WALKTHROUGH.md`
3. `scripts/bootstrap_demo_env.sh`

If you want the full test surface:

```bash
python3 conformance/run_all_checks.py --output /tmp/faxp_conformance_suite_report.json
```

## 7) Which Tests Matter First

For a builder doing an initial evaluation, start with:

```bash
python3 tests/run_schema_compatibility.py
python3 tests/run_booking_identity_terms.py
python3 tests/run_operational_handoff_terms.py
python3 tests/run_builder_integration_profile.py
python3 tests/run_conformance_suite.py
```

Then move to the full suite if the initial fit looks good.

## 8) What To Ignore At First

Do not start by trying to understand everything in the repo.

You can ignore these on day one unless they are directly relevant to your implementation:
1. registry operations artifacts
2. certification submission bundle mechanics
3. A2A/MCP compatibility details
4. deployment-specific runbooks

Those matter later, not first.

When you are ready for deeper implementation claims or certification review, move next to:
1. `docs/builders/BUILDER_INTEGRATION_PROFILE.md`
2. `conformance/README.md`
3. `docs/governance/CERTIFICATION_PLAYBOOK.md`

## 9) Common Mistakes

1. Treating FAXP as dispatch software
2. Treating FAXP as a hosted compliance service
3. Treating builder-side logic as protocol-core material
4. Adding fields because they are useful internally, not because they need standardization across parties

Use the scope litmus test before proposing new protocol fields:
- `docs/governance/SCOPE_GUARDRAILS.md`

## 10) If You Want To Contribute

Read:
- `CONTRIBUTING.md`
- `docs/roadmap/PHASE_2_IMPLEMENTATION_ROADMAP.md`

Then pick an issue that fits one of these categories:
1. docs clarity
2. builder usability
3. conformance/test coverage
4. booking-plane scenario coverage

That is the intended starting path for outside implementers.
