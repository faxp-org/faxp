# FAXP v0.2.1 Patch Plan

Status: Open  
Branch target: `codex/v0.2.1-patch`  
Scope: Patch-only (`bugfix`, `docs correction`, `test hardening`)  
No new protocol features in this track.

## Patch Acceptance Rules

1. Must fix a regression, correctness issue, security issue, or release-note/docs mismatch.
2. Must not add new message types or expand protocol scope.
3. Must include/adjust automated checks when behavior changes.
4. Must pass:
   - `./scripts/run_a2a_conformance.sh`
   - `./scripts/run_mcp_conformance.sh`
   - `.venv/bin/python tests/run_release_readiness.py`
   - `.venv/bin/python conformance/run_all_checks.py`

## Candidate Patch Queue

1. CI/test flake hardening if any intermittent failure appears post-`v0.2.0`.
2. Documentation consistency fixes (release notes, runbook command drift, path references).
3. Streamlit UX safety fixes that do not alter core protocol behavior.
4. Interop watch reliability fixes (`a2a-watch`, `mcp-watch`) if alert noise or parsing drift occurs.

## Non-Goals for v0.2.1

1. New protocol message types.
2. New settlement/dispatch/tracking lifecycle behavior.
3. A2A or MCP hard dependencies in FAXP core.
4. Adapter-hosting architecture changes.

## Exit Criteria

1. Patch queue is empty or deferred to `v0.3.0`.
2. All release gates green on patch branch.
3. Release notes published as `RELEASE_NOTES_v0.2.1.md`.
