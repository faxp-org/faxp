# Adoption Execution Tracker Template (Public-Safe)

Use this template to track outreach progress without publishing partner-private details.

Maturity status:
- Experimental and early-stage.
- Sandbox-first outreach tracking only.
- Not a production deployment tracker.

## Privacy and Scope Guardrails

1. Use implementer aliases only (no partner names unless explicitly approved).
2. Do not include credentials, tokens, cookies, local paths, or private domains.
3. Keep notes limited to booking-plane interoperability scope.
4. Route implementation-specific defects/enhancements into GitHub issues.

## Tracker Table

| DateUTC | ImplementerAlias | Channel | Stage | ScopeConfirmed | PacketVersion | PublicIssueRefs | NextAction | Owner |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-03-16 | implementer_a | Email | Intro Sent | Yes | packet-v1 | #123 | Send sandbox walkthrough | maintainer |

Stage values:
- `Intro Sent`
- `Packet Shared`
- `Sandbox Access Requested`
- `Sandbox Access Granted`
- `Technical Evaluation Active`
- `Feedback Received`
- `Paused`
- `Closed`

## Required Companion Artifacts

1. `docs/builders/PUBLIC_OUTREACH_EVALUATION_PACKET.md`
2. `docs/builders/ADOPTION_EXECUTION_RUNBOOK.md`
3. `docs/builders/SECOND_IMPLEMENTER_DEMO_CHECKLIST.md`
4. `docs/builders/SECOND_IMPLEMENTER_EVIDENCE_BUNDLE_TEMPLATE.json`

## Usage Notes

1. Keep one row per meaningful outreach checkpoint.
2. Track only public-safe references in `PublicIssueRefs`.
3. If an outreach thread becomes private/partner-specific, summarize only anonymized status in this tracker.
4. Before any beta-promotion discussion, confirm the second implementer demo evidence bundle is complete.
