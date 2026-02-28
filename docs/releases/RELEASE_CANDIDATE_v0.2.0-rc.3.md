# FAXP v0.2.0-rc.3 Release Candidate

Date: 2026-02-23  
Release type: Release Candidate  
Target tag: `v0.2.0-rc.3`

## 1) Candidate Summary

`v0.2.0-rc.3` formalizes the A2A + MCP interoperability boundary for v0.2:
- A2A remains translator-layer interoperability.
- MCP remains loose-coupled tool-layer interoperability.
- FAXP core remains dependency-independent and scope-guarded.

Current recommendation: `GO` for RC tag based on passing conformance and release-readiness evidence.

## 2) Scope Included in RC

1. Governance decision artifact:
- `docs/governance/DECISION_RECORD_a2a-mcp-interop-boundary_2026-02-23.md`

2. Interop governance + tracking controls:
- `docs/interop/A2A_CHANGE_MANAGEMENT.md`
- `docs/interop/A2A_UPSTREAM_TRACKING.json`
- `.github/workflows/a2a-watch.yml`
- `scripts/check_a2a_upstream.py`
- `tests/run_a2a_watch_artifacts.py`
- `docs/interop/MCP_CHANGE_MANAGEMENT.md`
- `docs/interop/MCP_UPSTREAM_TRACKING.json`
- `.github/workflows/mcp-watch.yml`
- `scripts/check_mcp_upstream.py`
- `tests/run_mcp_watch_artifacts.py`

3. One-command interop conformance wrappers:
- `scripts/run_a2a_conformance.sh`
- `scripts/run_mcp_conformance.sh`

4. Conformance suite and CI parity updates:
- `conformance/run_all_checks.py`
- `tests/run_conformance_suite.py`
- `.github/workflows/ci.yml`

## 3) Conformance Evidence

RC suite report artifact:
- `conformance/reports/faxp_conformance_suite_v0.2.0-rc.3.json`

Report summary:
- `totalChecks`: `20`
- `passedChecks`: `20`
- `failedChecks`: `0`
- `passed`: `true`
- `runId`: `6936f6f3-2783-4121-a3dd-357b213388ce`
- `startedAt`: `2026-02-23T13:17:16Z`

## 4) Release Gate Evidence (passed)

- `.venv/bin/python tests/run_release_readiness.py`
- `.venv/bin/python tests/run_conformance_suite.py`
- `.venv/bin/python conformance/run_all_checks.py --output conformance/reports/faxp_conformance_suite_v0.2.0-rc.3.json --log-dir /tmp/faxp-rc3-logs`
- `./scripts/run_a2a_conformance.sh`
- `./scripts/run_mcp_conformance.sh`

## 5) Scope Guardrail Confirmation

This RC does **not** expand FAXP into dispatch, telematics, POD/BOL, invoicing, payment, or settlement.
A2A and MCP compatibility remain interop/certification concerns, not FAXP core protocol dependencies.

## 6) RC Tag Command Set

Verify working tree:

```bash
cd <repo-root>
git status
```

Run release gates:

```bash
cd <repo-root>
.venv/bin/python tests/run_release_readiness.py
.venv/bin/python conformance/run_all_checks.py --output conformance/reports/faxp_conformance_suite_v0.2.0-rc.3.json --log-dir /tmp/faxp-rc3-logs
```

Commit RC package artifacts:

```bash
cd <repo-root>
git add docs/releases/RELEASE_CANDIDATE_v0.2.0-rc.3.md docs/governance/DECISION_RECORD_a2a-mcp-interop-boundary_2026-02-23.md conformance/reports/faxp_conformance_suite_v0.2.0-rc.3.json
git commit -m "Add v0.2.0-rc.3 interop boundary decision and release package"
git push
```

Tag RC:

```bash
cd <repo-root>
git tag -a v0.2.0-rc.3 -m "FAXP v0.2.0-rc.3"
git push origin v0.2.0-rc.3
```
