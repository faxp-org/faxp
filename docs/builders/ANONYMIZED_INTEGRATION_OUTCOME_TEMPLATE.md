# Public Vendor-Neutral Integration Outcome (Template)

Use this template for public publication only when all content is synthetic,
vendor-neutral, and non-attributable to any partner implementation.

## Scope
- Adapter/demo execution only (API auth, payload mapping, deterministic update behavior, validation artifacts).
- No governance or outreach narrative in this write-up.

## Privacy Guardrails
- No partner names.
- No partner domains/URLs.
- No tokens, cookies, credentials.
- No partner payloads with traceable IDs.
- No screenshots containing partner UI details.
- No local absolute filesystem paths.
- No references that imply which specific partner system was tested.

## Protocol vs Adapter Boundary
- Protocol (FAXP): booking-plane message contract and envelope/body validation.
- Adapter (implementation bridge): source API auth/session handling, source-specific payload extraction, deterministic update mechanics, and field mapping.

## What Was Validated
1. Source-system auth/login works.
2. Create/load retrieval flow works.
3. Deterministic update works when existing stop IDs from `GET /loads/:id` are reused.
4. Follow-up retrieval confirms no duplicate stop creation.
5. Source payload maps into valid FAXP `NewLoad` JSON.
6. FAXP body + envelope validation pass.

## Contract Finding
- Deterministic stop updates require source stop IDs from the current load state.
- ID reuse forms the stable update contract for adapter behavior.

## Public Artifacts to Include
1. Synthetic/anonymized source payload sample.
2. Synthetic/anonymized deterministic update payload sample.
3. Synthetic/anonymized FAXP `NewLoad` body sample.
4. Synthetic/anonymized FAXP envelope sample.
5. Validation pass output snippet (no internal metadata).
6. Synthetic deterministic stop-ID update sample:
   - `docs/builders/examples/public_adapter_contract/deterministic_stop_update.sample.json`

## Public Artifacts to Exclude
1. Partner-private request/response traces.
2. Debug headers with session data.
3. Internal IDs not needed for protocol understanding.
4. Any local machine path references.

## Repro Notes (Public-Safe)
- Keep commands generic and portable.
- Use placeholder values (`<LOAD_ID>`, `<STOP_ID_1>`, `<STOP_ID_2>`) only.
- Include exact expected pass checks.

## Public Publishing Checklist
1. Replace all real IDs and timestamps with synthetic placeholders.
2. Confirm no source-system brand, hostname, or UI text appears anywhere.
3. Keep examples limited to booking-plane semantics.
4. Keep protocol claims separate from adapter implementation behavior.
5. Re-run open-source guardrails before publish.

## Status
- Result: `PASS` / `PARTIAL` / `BLOCKED`
- Remaining work: presentation polish only / adapter behavior follow-up / source-system follow-up.
