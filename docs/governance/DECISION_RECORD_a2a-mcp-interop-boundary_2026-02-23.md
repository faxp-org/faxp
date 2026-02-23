# Decision Record: A2A and MCP Interop Boundary (Translator/Tooling Layer Only)

## Summary
FAXP supports A2A and MCP interoperability through builder-hosted translator/tooling layers.
FAXP core protocol remains independent from A2A and MCP runtime dependencies.

## Decision Metadata
- Decision ID: `faxp-arch-decision-20260223-a2a-mcp-boundary-v1`
- Decision Date: `2026-02-23`
- Status: `Accepted`
- Owners: `FAXP Governance Working Group`

## Decision
1. A2A support remains translator-based (`FAXP <-> A2A`) and optional.
2. MCP support remains tool-layer interoperability and optional.
3. FAXP core envelope/schema rules do not require A2A or MCP fields.
4. A2A/MCP upstream watch and compatibility artifacts are required governance controls.
5. Production interop components are builder-hosted and certification-scoped.

## Rationale
- Preserves FAXP protocol scope (agent-to-agent freight booking and trust controls).
- Avoids dependency lock-in and cross-ecosystem coupling risk.
- Keeps adoption path open for diverse builders and enterprise stacks.
- Ensures interop evolution is auditable via profile + contract + watch governance.

## Normative Artifacts
- A2A profile: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/interop/A2A_COMPATIBILITY_PROFILE.md`
- A2A contract: `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/a2a_translator_contract.json`
- A2A watch runbook: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/interop/A2A_CHANGE_MANAGEMENT.md`
- A2A tracking: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/interop/A2A_UPSTREAM_TRACKING.json`
- MCP profile: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/interop/MCP_COMPATIBILITY_PROFILE.md`
- MCP contract: `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/mcp_tooling_contract.json`
- MCP watch runbook: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/interop/MCP_CHANGE_MANAGEMENT.md`
- MCP tracking: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/interop/MCP_UPSTREAM_TRACKING.json`

## Required Checks
- `/Users/zglitch009/projects/logistics-ai/FAXP/tests/run_a2a_profile_check.py`
- `/Users/zglitch009/projects/logistics-ai/FAXP/tests/run_a2a_roundtrip_translation.py`
- `/Users/zglitch009/projects/logistics-ai/FAXP/tests/run_a2a_watch_artifacts.py`
- `/Users/zglitch009/projects/logistics-ai/FAXP/tests/run_mcp_profile_check.py`
- `/Users/zglitch009/projects/logistics-ai/FAXP/tests/run_mcp_watch_artifacts.py`
- `/Users/zglitch009/projects/logistics-ai/FAXP/scripts/run_a2a_conformance.sh`
- `/Users/zglitch009/projects/logistics-ai/FAXP/scripts/run_mcp_conformance.sh`

## Guardrails
- Any proposal to add mandatory A2A or MCP dependencies in FAXP core requires a new RFC and governance vote.
- Any proposal to place raw tool-provider payloads into core protocol-required fields is out of scope and must be rejected.
- Interop translators must preserve FAXP signature, replay, and TTL fail-closed behavior.

## Rollout
- Effective for `v0.2.0-rc.3` and onward.
- Enforced through CI, conformance suite checks, and weekly upstream watch workflows.
