# FAXP v0.2.1 Release Notes

Date: 2026-03-06  
Release type: Patch  
Tag: `v0.2.1`

## Summary

`v0.2.1` is a scope/governance hardening patch.

This release clarifies protocol-core ownership while preserving a public reference-runtime for contributor testing.

No wire-level protocol breaking changes are introduced in this patch.

## Included in v0.2.1

1. Scope boundary hardening
- Explicit protocol-core vs reference-runtime boundary document:
  - `REFERENCE_RUNTIME_BOUNDARY.md`
- Scope guidance updates in:
  - `README.md`
  - `docs/BUILDERS_START_HERE.md`
  - `docs/governance/SCOPE_GUARDRAILS.md`

2. Builder/runtime migration planning
- Added explicit migration planning artifacts:
  - `docs/roadmap/BUILDER_RUNTIME_MIGRATION_PLAN.md`
  - `docs/roadmap/SCOPE_AUDIT_2026-03-06.md`

3. Contribution governance hardening
- Scope-aware PR template classification updates.
- Issue template classification updates.
- Path-scoped ownership guidance in `.github/CODEOWNERS`.

4. CI lane visibility
- Added dedicated CI lanes:
  - `Protocol Core Lane`
  - `Reference Runtime Lane`
- Existing `verify` job remains the primary required gate path for compatibility with current branch protection.

## What v0.2.1 Does Not Change

- FAXP does not become a hosted FMCSA/compliance/biometric service.
- FAXP does not take ownership of provider execution logic.
- Dispatch, tracking, custody, invoicing, and payment workflows remain out of protocol-core scope.

## Conformance Evidence

Post-patch conformance suite summary:
- `totalChecks`: `65`
- `passedChecks`: `65`
- `failedChecks`: `0`
- `passed`: `true`

Verification command used:

```bash
.venv/bin/python conformance/run_all_checks.py --output /tmp/faxp_conformance_suite_report_v0.2.1_scope_patch.json
```
