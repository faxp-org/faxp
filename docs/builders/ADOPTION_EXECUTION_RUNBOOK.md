# Adoption Execution Runbook (Public-Safe)

Use this runbook to execute external outreach using only public artifacts.

Maturity status:
- Experimental and early-stage.
- Not production-ready as a universal standard at this stage.
- Outreach should position FAXP as a pilot/evaluation protocol.

## Required Packet

Default packet to share:
1. `docs/builders/PUBLIC_OUTREACH_EVALUATION_PACKET.md`
2. `docs/builders/PUBLIC_ANONYMIZED_ADAPTER_PACKAGE.md`
3. `docs/builders/ANONYMIZED_INTEGRATION_OUTCOME_TEMPLATE.md`
4. `docs/builders/PUBLIC_PROTOCOL_VS_ADAPTER_SUMMARY.md`
5. `docs/builders/examples/public_adapter_contract/README.md`
6. `docs/BUILDERS_START_HERE.md`

## Public Outreach Checklist (Use Every Time)

1. Share all links from **Required Packet** in the first technical follow-up.
2. Include this exact disclaimer line:
   - `FAXP is experimental and early-stage. This is a sandbox-first evaluation, not a production rollout.`
3. Keep partner-specific details private:
   - no partner names (unless approved),
   - no private API docs/screenshots,
   - no credentials/tokens/IDs,
   - no local absolute filesystem paths.
4. Publish only vendor-neutral and synthetic materials in public channels.
5. Capture feedback publicly using issue templates:
   - defects/regressions: `.github/ISSUE_TEMPLATE/bug_report.md`
   - enhancements/ambiguity requests: `.github/ISSUE_TEMPLATE/feature_request.md`
6. Add classification labels for triage:
   - one domain label: `protocol-core`, `reference-runtime`, `governance`, or `interop`
   - one type label: `bug` or `enhancement`

## Execution Flow

1. Send a short intro message with protocol boundary and explicit experimental status.
2. Share the public outreach packet.
3. Ask for sandbox-only evaluation first.
4. Capture feedback in issues before proposing protocol changes.
5. Keep partner-specific implementation details in private channels.

## Scope Guardrail Language (Use Verbatim)

FAXP is a booking-plane messaging protocol.  
FAXP is experimental and early-stage at this time.  
It does not replace dispatch, tracking, document custody, or settlement.  
Builder-side operational logic remains builder-owned.

## Public-Safe Outreach Templates

### 1) Cold Intro Email (Short)

Subject: Open booking-plane protocol evaluation (FAXP)

Hi team,

I am sharing FAXP, an open and vendor-neutral booking-plane protocol for agent-to-agent freight discovery, negotiation, and booking confirmation.

FAXP is experimental and early-stage. It is intended for sandbox evaluation first and is not a dispatch or settlement replacement.

If useful, here is the public evaluation packet:
- `docs/builders/PUBLIC_OUTREACH_EVALUATION_PACKET.md`

If you are open to testing, I can provide a concise sandbox-first walkthrough.

Thanks,

### 2) Follow-Up Message (After Initial Interest)

Thanks for taking a look.

Reminder: FAXP is experimental and early-stage, so we are treating this as a sandbox-first evaluation.

For the first pass, the most useful feedback is:
1. whether your system can map booking-plane messages through an adapter layer,
2. where contract ambiguity exists in the sample payloads, and
3. which conformance/profile docs are still unclear.

### 3) Public Social Post (Short)

FAXP remains experimental and early-stage.  
Current focus is booking-plane interoperability with anonymized, public-safe adapter artifacts.  
If you build freight software and want to run a sandbox evaluation, feedback is welcome.

## What Not To Publish

Do not publish:
1. partner names unless explicitly approved,
2. private API docs or screenshots,
3. credentials, tokens, IDs, or local paths,
4. payloads containing traceable partner identifiers.

## Tracking

Track outreach and feedback as:
1. docs clarity issues,
2. adapter contract ambiguity issues,
3. conformance usability issues.

Do not file partner-private implementation details in public issues.
