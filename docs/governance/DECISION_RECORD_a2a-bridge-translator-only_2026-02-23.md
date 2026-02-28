# Decision Record: A2A Compatibility via Translator (No FAXP Core Dependency)

## Summary
FAXP will support A2A interoperability through a builder-hosted translator profile.
FAXP core protocol envelopes, message types, and validation/security controls remain unchanged.

## Decision Metadata
- Decision ID: `faxp-arch-decision-20260223-a2a-bridge-v1`
- Decision Date: `2026-02-23`
- Status: `Accepted`
- Owners: `FAXP Governance Working Group`

## Decision
1. A2A compatibility is **translator-only** in FAXP v0.x.
2. FAXP core has **no runtime dependency** on A2A transports/protocol objects.
3. Production translator/adapters are **builder-hosted**, not foundation-hosted.
4. FAXP certification may validate translator conformance using profile+contract artifacts.

## Rationale
- Preserves FAXP scope: booking/execution messaging and trust controls.
- Avoids protocol bloat and external runtime lock-in.
- Enables ecosystem interoperability with minimal core risk.
- Aligns with open-standard neutrality and builder-operated deployment model.

## Normative Artifacts
- A2A profile: `docs/interop/A2A_COMPATIBILITY_PROFILE.md`
- Translator contract: `conformance/a2a_translator_contract.json`
- Conformance check: `tests/run_a2a_profile_check.py`

## Guardrails
- Any proposal to embed A2A objects directly into FAXP core schemas or envelope rules requires a new RFC and governance vote.
- Translator mappings must preserve FAXP signatures/replay/TTL semantics and fail closed on invalid round-trip mapping.

## Rollout
- Effective immediately for v0.2 planning and onward.
- Included in conformance suite via `a2a_profile` check.
- Upstream monitoring is handled by `.github/workflows/a2a-watch.yml` and `scripts/check_a2a_upstream.py`.
