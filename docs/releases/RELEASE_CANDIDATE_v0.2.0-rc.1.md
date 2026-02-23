# FAXP v0.2.0-rc.1 Release Candidate

Date: 2026-02-23  
Release type: Release Candidate  
Target tag: `v0.2.0-rc.1`

## 1) Candidate Summary

This release candidate packages the v0.2 governance and conformance hardening completed after `v0.2.0-alpha.1`.

Current recommendation: `GO` for RC tag based on local conformance evidence and green CI.

## 2) Scope Included in RC

1. Protocol simulation and schema baseline:
- `/Users/zglitch009/projects/logistics-ai/FAXP/faxp_mvp_simulation.py`
- `/Users/zglitch009/projects/logistics-ai/FAXP/faxp.schema.json`
- `/Users/zglitch009/projects/logistics-ai/FAXP/faxp.v0.2.schema.json`

2. Policy and governance controls:
- `/Users/zglitch009/projects/logistics-ai/FAXP/docs/governance/SCOPE_GUARDRAILS.md`
- `/Users/zglitch009/projects/logistics-ai/FAXP/docs/governance/POLICY_PROFILES.md`
- `/Users/zglitch009/projects/logistics-ai/FAXP/docs/governance/REGISTRY_ADMISSION_POLICY.md`
- `/Users/zglitch009/projects/logistics-ai/FAXP/docs/governance/REGISTRY_CHANGELOG_POLICY.md`
- `/Users/zglitch009/projects/logistics-ai/FAXP/docs/governance/CERTIFICATION_DECISION_RECORD_TEMPLATE.md`
- `/Users/zglitch009/projects/logistics-ai/FAXP/docs/governance/DECISION_RECORDS_RUNBOOK.md`
- `/Users/zglitch009/projects/logistics-ai/FAXP/docs/governance/RELEASE_READINESS_CHECKLIST.md`
- `/Users/zglitch009/projects/logistics-ai/FAXP/docs/governance/GOVERNANCE_INDEX.json`

3. Conformance and certification artifact gates:
- `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/run_all_checks.py`
- `/Users/zglitch009/projects/logistics-ai/FAXP/tests/run_conformance_suite.py`
- `/Users/zglitch009/projects/logistics-ai/FAXP/.github/workflows/ci.yml`

## 3) Security and Trust Posture (RC Snapshot)

1. Signed protocol/verifier trust validation and fail-closed checks remain active.
2. Replay, TTL, and validation gates are enforced.
3. Certification operations are evidence-linked and auditable:
- registry operations
- registry admission policy
- registry changelog policy
- decision record template + artifact validation
- governance index and release readiness synchronization

## 4) Conformance Evidence

Local RC suite report artifact:
- `/Users/zglitch009/projects/logistics-ai/FAXP/conformance/reports/faxp_conformance_suite_v0.2.0-rc.1.json`

Report summary:
- `totalChecks`: `16`
- `passedChecks`: `16`
- `failedChecks`: `0`
- `passed`: `true`
- `runId`: `5f545389-f9a8-403b-bd4d-ff993fc071bc`
- `startedAt`: `2026-02-23T01:32:05Z`

## 5) Known Deferrals (Not in RC Scope)

From `/Users/zglitch009/projects/logistics-ai/FAXP/docs/roadmap/FAXP_DEFERRED_ITEMS.md`:
1. Centralized `rulesync.jsonc`-style orchestration.
2. Lockfile-driven frozen installs for all agent tooling.
3. CI frozen dependency/config policy gates.
4. Automated protocol-change approval workflow integration.
5. Full external white-label SDK/export packaging.

## 6) RC Tag Command Set

Verify working tree:

```bash
cd /Users/zglitch009/projects/logistics-ai/FAXP
git status
```

Run release-readiness and conformance suite:

```bash
cd /Users/zglitch009/projects/logistics-ai/FAXP
.venv/bin/python tests/run_release_readiness.py
.venv/bin/python conformance/run_all_checks.py --output conformance/reports/faxp_conformance_suite_v0.2.0-rc.1.json --log-dir /tmp/faxp-rc1-logs
```

Review report summary quickly:

```bash
cd /Users/zglitch009/projects/logistics-ai/FAXP
python3 - <<'PY'
import json
with open("conformance/reports/faxp_conformance_suite_v0.2.0-rc.1.json", "r", encoding="utf-8") as f:
    data = json.load(f)
print(json.dumps(data.get("summary", {}), indent=2))
PY
```

Commit RC package artifacts:

```bash
cd /Users/zglitch009/projects/logistics-ai/FAXP
git add docs/releases/RELEASE_CANDIDATE_v0.2.0-rc.1.md conformance/reports/faxp_conformance_suite_v0.2.0-rc.1.json
git commit -m "Add v0.2.0-rc.1 release candidate package and conformance report"
git push
```

Tag RC:

```bash
cd /Users/zglitch009/projects/logistics-ai/FAXP
git tag -a v0.2.0-rc.1 -m "FAXP v0.2.0-rc.1"
git push origin v0.2.0-rc.1
```
