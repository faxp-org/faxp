# GitHub Policy Snapshot Runbook

## Purpose

Capture a weekly JSON snapshot of GitHub security/policy settings to detect drift in auth-gated controls.

## Workflow

- Workflow file: `.github/workflows/policy-snapshot.yml`
- Trigger modes:
  - Manual: `workflow_dispatch`
  - Scheduled: every Monday at `14:15 UTC`

## Required Secret

- Repository secret: `POLICY_SNAPSHOT_TOKEN`
- Minimum required scope: read access for repository administration/security settings used by:
  - Actions permissions endpoints
  - Branch protection endpoint
  - Dependabot/code scanning/secret scanning alert endpoints

## Outputs

- Artifact name: `policy-snapshot-<run_id>`
- Artifact path in workflow: `artifacts/policy-snapshot/<timestamp>/`
- Snapshot files:
  - `summary.json`
  - `repo.json`
  - `rulesets.json`
  - `rulesets/<id>.json` (per-ruleset detail)
  - `actions_permissions.json`
  - `actions_workflow_permissions.json`
  - `actions_selected_actions.json`
  - `actions_fork_pr_approval.json`
  - `branch_protection_main.json`
  - `dependabot_alerts_sample.json`
  - `code_scanning_alerts_sample.json`
  - `secret_scanning_alerts_sample.json`

## Local Run (optional)

```bash
export POLICY_SNAPSHOT_TOKEN='<redacted-token>'
python3 scripts/export_github_policy_snapshot.py --repo faxp-org/faxp --output-dir artifacts/policy-snapshot
```

## Failure Semantics

- Script exits non-zero if any auth-gated endpoint returns HTTP `>=400`.
- This fail-closed behavior is intentional so missing permissions/token drift is visible immediately.
