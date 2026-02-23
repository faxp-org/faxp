# A2A Change Management

This runbook defines how FAXP tracks upstream A2A changes while keeping FAXP core independent.

## Objective
- Detect upstream A2A releases/tags on a weekly cadence.
- Triage interoperability impact to FAXP bridge artifacts.
- Keep A2A support in the translator/profile layer only.

## Source of Truth
- Compatibility profile: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/interop/A2A_COMPATIBILITY_PROFILE.md`
- Translator contract: `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/a2a_translator_contract.json`
- Tracking config: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/interop/A2A_UPSTREAM_TRACKING.json`

## Weekly Process
1. Run the watch check (automated in GitHub Actions).
2. If upstream drift is detected, open a governance issue.
3. Classify impact:
   - `NoImpact`: no bridge/contract updates required.
   - `BridgeUpdate`: update profile/contract and tests.
   - `CoreRisk`: requires RFC and governance vote before any core change.
4. If updates are required:
   - Update profile + contract + tests.
   - Update `A2A_UPSTREAM_TRACKING.json` baseline reference.
   - Merge after CI green.

## Escalation Rules
- Any proposal that introduces A2A runtime dependency into FAXP core must go through RFC using `/Users/zglitch009/projects/logistics-ai/FAXP/docs/rfc/RFC_TEMPLATE.md`.
- If translator parity cannot be preserved (signature/replay/TTL semantics), fail closed and do not claim compatibility.

## Manual Command
```bash
cd /Users/zglitch009/projects/logistics-ai/FAXP
python3 scripts/check_a2a_upstream.py \
  --tracking docs/interop/A2A_UPSTREAM_TRACKING.json \
  --output /tmp/a2a_watch_report.json \
  --issue-body /tmp/a2a_watch_issue.md
```
