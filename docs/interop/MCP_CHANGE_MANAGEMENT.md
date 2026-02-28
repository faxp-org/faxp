# MCP Change Management

This runbook defines how FAXP tracks upstream MCP changes while keeping FAXP core independent.

## Objective
- Detect upstream MCP releases/tags on a weekly cadence.
- Triage interoperability impact to FAXP MCP profile/contract artifacts.
- Keep MCP support in the interop/tool layer only.

## Source of Truth
- Compatibility profile: `docs/interop/MCP_COMPATIBILITY_PROFILE.md`
- Tooling contract: `conformance/mcp_tooling_contract.json`
- Tracking config: `docs/interop/MCP_UPSTREAM_TRACKING.json`

## Weekly Process
1. Run the watch check (automated in GitHub Actions).
2. If upstream drift is detected, open a governance issue.
3. Classify impact:
   - `NoImpact`: no profile/contract updates required.
   - `InteropUpdate`: update profile/contract/tests.
   - `CoreRisk`: requires RFC and governance vote before any core change.
4. If updates are required:
   - Update MCP profile + contract + tests.
   - Update `MCP_UPSTREAM_TRACKING.json` baseline reference.
   - Merge only after CI green.

## Escalation Rules
- Any proposal that introduces mandatory MCP dependency into FAXP core must go through RFC using `docs/rfc/RFC_TEMPLATE.md`.
- If security controls (least-privilege, allowlist, audit correlation, fail-closed) cannot be preserved, do not claim compatibility.

## Builder Quickstart
1. Pull profile + contract artifacts into your adapter project.
2. Run one-command local check:
```bash
cd <repo-root>
./scripts/run_mcp_conformance.sh
```
3. Submit conformance artifacts with certification bundle.

## Manual Command
```bash
cd <repo-root>
python3 scripts/check_mcp_upstream.py \
  --tracking docs/interop/MCP_UPSTREAM_TRACKING.json \
  --output /tmp/mcp_watch_report.json \
  --issue-body /tmp/mcp_watch_issue.md
```
