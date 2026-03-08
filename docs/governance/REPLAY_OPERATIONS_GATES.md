# Replay Operations Gates

This document tracks required operational gates before production scale-out of replay enforcement.

## Gate Table

| Gate | Owner | Due | Status | Evidence |
| --- | --- | --- | --- | --- |
| Define replay-claim SLO, error budget, and paging thresholds | truckingadvantage (Security Owner) | 2026-03-12 | In Progress | [REPLAY_SLO_ALERTING.md](REPLAY_SLO_ALERTING.md) |
| Add replay reject-rate anomaly detection and alerting | truckingadvantage (Runtime Owner) | 2026-03-13 | Planned | [REPLAY_REJECT_RATE_ALERTING.md](REPLAY_REJECT_RATE_ALERTING.md) |
| Require documented Redis HA/failover test pass | truckingadvantage (Platform Owner) | 2026-03-14 | Done | [REDIS_HA_FAILOVER_TEST_PLAN.md](REDIS_HA_FAILOVER_TEST_PLAN.md), [REPLAY_REDTEAM_DELTA_2026-03-08.md](REPLAY_REDTEAM_DELTA_2026-03-08.md) |
| Require replay incident runbook review and signoff | truckingadvantage (Incident Lead) | 2026-03-15 | Planned | [REPLAY_INCIDENT_RUNBOOK.md](REPLAY_INCIDENT_RUNBOOK.md) |
| Verify on-call ownership for replay incidents and override audit review | truckingadvantage (On-call Owner) | 2026-03-16 | Planned | [REPLAY_ONCALL_OWNERSHIP.md](REPLAY_ONCALL_OWNERSHIP.md), [REPLAY_OVERRIDE_AUDIT_REVIEW_LOG.md](REPLAY_OVERRIDE_AUDIT_REVIEW_LOG.md) |

## Normative Gate Manifest (Test-Enforced)

<!-- REPLAY_OPERATIONS_GATES_BEGIN -->
{
  "updatedAt": "2026-03-08T23:35:00Z",
  "gates": [
    {
      "id": "replay_claim_slo_error_budget",
      "owner": "truckingadvantage (Security Owner)",
      "due": "2026-03-12",
      "status": "in_progress",
      "evidence": [
        "docs/governance/REPLAY_SLO_ALERTING.md",
        "tests/run_replay_runtime_policy.py"
      ]
    },
    {
      "id": "replay_reject_rate_alerting",
      "owner": "truckingadvantage (Runtime Owner)",
      "due": "2026-03-13",
      "status": "planned",
      "evidence": [
        "docs/governance/REPLAY_REJECT_RATE_ALERTING.md",
        "tests/run_replay_runtime_policy.py"
      ]
    },
    {
      "id": "replay_redis_ha_failover",
      "owner": "truckingadvantage (Platform Owner)",
      "due": "2026-03-14",
      "status": "done",
      "evidence": [
        "docs/governance/REDIS_HA_FAILOVER_TEST_PLAN.md",
        "docs/governance/REPLAY_RUNTIME_POLICY.md",
        "docs/governance/REPLAY_REDTEAM_DELTA_2026-03-08.md"
      ]
    },
    {
      "id": "replay_incident_runbook_signoff",
      "owner": "truckingadvantage (Incident Lead)",
      "due": "2026-03-15",
      "status": "planned",
      "evidence": [
        "docs/governance/REPLAY_INCIDENT_RUNBOOK.md"
      ]
    },
    {
      "id": "replay_oncall_ownership_and_override_review",
      "owner": "truckingadvantage (On-call Owner)",
      "due": "2026-03-16",
      "status": "planned",
      "evidence": [
        "docs/governance/REPLAY_ONCALL_OWNERSHIP.md",
        "docs/governance/REPLAY_OVERRIDE_AUDIT_REVIEW_LOG.md"
      ]
    }
  ]
}
<!-- REPLAY_OPERATIONS_GATES_END -->
