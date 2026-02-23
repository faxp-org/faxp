# FAXP v0.2.0 Release Notes

Date: 2026-02-23  
Release type: General Availability  
Tag: `v0.2.0`

## Summary

`v0.2.0` finalizes FAXP’s scope-guarded protocol and interoperability model:
- Core FAXP remains focused on agent-to-agent freight booking and trust controls.
- A2A interoperability is supported through translator-layer artifacts.
- MCP interoperability is supported through loose-coupled tool-layer artifacts.
- Builder-hosted adapter model and certification governance are the default production path.

## Included in v0.2.0

1. Protocol and trust baseline
- Signed envelopes and verifier results
- Replay/TTL protections and fail-closed validation paths
- Schema compatibility track for v0.2 (`faxp.v0.2.schema.json`)

2. Governance and certification baseline
- Scope guardrails and governance model
- Registry admission/changelog/runbook controls
- Decision record template + decision operations runbook
- Release-readiness gate checks

3. A2A interop track (optional, non-core dependency)
- Compatibility profile + translator contract
- Deterministic round-trip translation checks
- Weekly upstream watch workflow + tracking baseline + artifact checks

4. MCP interop track (optional, non-core dependency)
- Compatibility profile + tooling contract
- Weekly upstream watch workflow + tracking baseline + artifact checks
- One-command MCP conformance wrapper

## Conformance Evidence

Final suite report artifact:
- `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/reports/faxp_conformance_suite_v0.2.0.json`

Report summary:
- `totalChecks`: `20`
- `passedChecks`: `20`
- `failedChecks`: `0`
- `passed`: `true`
- `runId`: `c95a11db-354d-4dd5-9395-00a9bb75482f`
- `startedAt`: `2026-02-23T13:26:07Z`

## Final Scope Boundary

In scope:
- Agent-to-agent freight booking message flows and protocol trust controls
- Verification result normalization and adapter/certification contracts

Out of scope:
- Dispatch operations
- Telematics/tracking operations
- POD/BOL custody workflows
- Invoicing, payments, and settlement rails

## Verification Commands (Release Gate)

```bash
cd /Users/zglitch009/projects/logistics-ai/FAXP
./scripts/run_a2a_conformance.sh
./scripts/run_mcp_conformance.sh
.venv/bin/python tests/run_release_readiness.py
.venv/bin/python conformance/run_all_checks.py --output conformance/reports/faxp_conformance_suite_v0.2.0.json --log-dir /tmp/faxp-v020-logs
```

