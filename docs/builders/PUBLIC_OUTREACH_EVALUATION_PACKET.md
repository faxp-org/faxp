# Public Outreach Evaluation Packet (Experimental)

This packet is the default public-safe artifact set for outbound FAXP evaluation conversations.

Maturity status:
- Experimental and early-stage.
- Intended for sandbox/test evaluation first.
- Not production-ready as a universal standard at this stage.

## Why This Exists

Outreach should start with consistent, anonymized, technically useful material.

This packet gives prospective implementers enough context to evaluate integration fit without:
1. private credentials,
2. partner-specific docs, or
3. local/internal artifacts.

## Packet Contents

1. Protocol boundary and scope:
   - `docs/governance/SCOPE_GUARDRAILS.md`
2. Builder onboarding path:
   - `docs/BUILDERS_START_HERE.md`
3. Adapter contract guidance:
   - `adapter/INTERFACE.md`
   - `docs/builders/BUILDER_INTEGRATION_PROFILE.md`
4. Public anonymized examples:
   - `docs/builders/PUBLIC_ANONYMIZED_ADAPTER_PACKAGE.md`
   - `docs/builders/examples/public_adapter_contract/README.md`

## Suggested Outreach Sequence

1. Start with protocol scope and what FAXP is not.
2. Share anonymized adapter contract examples.
3. Confirm builder-side responsibilities remain builder-side.
4. Offer sandbox-first evaluation path.
5. Keep partner/private implementation details out of public channels.

## Evaluation Questions for Prospective Builders

1. Can your system emit or consume booking-plane messages at the NewLoad/Bid/ExecutionReport level?
2. Do you have a builder-side adapter layer where protocol translation should live?
3. Which booking-plane profiles are most relevant for your first implementation?
4. Can your team run the public conformance checks in a sandbox workflow?

## Public-Safe Checklist (Before Sharing)

1. No partner names in text or examples.
2. No private domains, tokens, credentials, or local paths.
3. All IDs and payloads are synthetic.
4. Scope language stays booking-plane only.

## Feedback Filing Path (For External Evaluators)

When outreach recipients send feedback, file it using repo templates:

1. Defects/regressions:
   - `.github/ISSUE_TEMPLATE/bug_report.md`
2. Enhancements/contract ambiguity:
   - `.github/ISSUE_TEMPLATE/feature_request.md`

Apply labels for triage:

1. Domain label (pick one):
   - `protocol-core`
   - `reference-runtime`
   - `governance`
   - `interop`
2. Type label (pick one):
   - `bug`
   - `enhancement`

Public hygiene reminder:
- Do not include partner-specific identifiers, private docs/screenshots, credentials/tokens, or local absolute filesystem paths.

## Local Validation Baseline

Use:

1. `.venv/bin/python tests/run_open_source_guardrails.py`
2. `.venv/bin/python tests/run_release_readiness.py`
3. `.venv/bin/python tests/run_conformance_suite.py`
