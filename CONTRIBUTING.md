# Contributing to FAXP

## Contribution Types

- Protocol and schema improvements
- Conformance profile and test additions
- Governance and release-gate documentation improvements
- Bug fixes aligned to current scope guardrails

## Scope Guardrails

Before opening a PR, read:
- `docs/governance/SCOPE_GUARDRAILS.md`
- `docs/governance/BOOKING_PLANE_COMMERCIAL_TERMS.md`

Changes that expand into dispatch/tracking/settlement domains require an RFC and explicit approval.

## Development Workflow

1. Create a branch from `main`.
2. Keep PRs focused and small.
3. Add or update tests for any behavior change.
4. Run relevant checks locally before pushing.

Recommended local checks:

```bash
./scripts/run_a2a_conformance.sh
./scripts/run_mcp_conformance.sh
python3 conformance/run_all_checks.py --output /tmp/faxp_conformance_suite_report.local.json
python3 tests/run_release_readiness.py
```

If you need the fastest local demo/testing setup first, use:
- `docs/STREAMLIT_QUICKSTART.md`
- `docs/STREAMLIT_DEMO_WALKTHROUGH.md`
- `./scripts/bootstrap_demo_env.sh`

## RFC Requirement

Use RFC flow for:
- new message contracts
- schema compatibility changes
- new governance profiles
- scope-adjacent policy shifts

Template:
- `docs/rfc/RFC_TEMPLATE.md`

## Commit and PR Expectations

- Use clear, action-oriented commit messages.
- Link related RFCs/issues in PR description.
- Include validation commands and results.
- Keep sensitive material out of commits.

## Security and Secrets

- Never commit private keys, tokens, or local secret bundles.
- Follow `SECURITY.md` for vulnerability reporting.

## Review and Merge

- Required CI checks must pass.
- Changes to governance artifacts must keep governance index and release-readiness checks green.
