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
- `REFERENCE_RUNTIME_BOUNDARY.md`

Changes that expand into dispatch/tracking/settlement domains require an RFC and explicit approval.
Changes that affect only simulation/demo behavior should be treated as reference-runtime updates, not protocol-core changes.

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
python3 tests/run_public_redaction_guardrails.py
python3 tests/run_open_source_guardrails.py
```

If you need the fastest local demo/testing setup first, use:
- `docs/BUILDERS_START_HERE.md`
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

Public artifact hygiene rules:
1. Do not include partner-specific names in public docs or templates.
2. Do not include local machine absolute paths.
3. Use neutral identifiers and synthetic examples in public-facing artifacts.
4. Use one branch per PR; do not reuse merged branch names.

## Security and Secrets

- Never commit private keys, tokens, or local secret bundles.
- Follow `SECURITY.md` for vulnerability reporting.

## Community Conduct and Support

- `CODE_OF_CONDUCT.md` defines expected contributor behavior.
- `SUPPORT.md` defines support channels and maintainer expectations.

## Review and Merge

- Required CI checks must pass.
- Changes to governance artifacts must keep governance index and release-readiness checks green.
