# Replay Claim SLO and Error Budget

## Scope

Defines service-level expectations for replay key claims in non-local environments using `redis_shared`.

## Proposed SLO (Initial)

- Availability SLO: `99.90%` successful replay-claim operations per rolling 30 days.
- Latency SLO: p95 replay claim latency under `75ms`, p99 under `150ms`.
- Error budget: `0.10%` replay claim failures per rolling 30 days.

## Paging Thresholds

- Page immediately if replay claim failure rate exceeds `2%` for `5 minutes`.
- Page immediately if p99 replay claim latency exceeds `500ms` for `10 minutes`.
- Open non-paging ticket if p95 latency exceeds `75ms` for `30 minutes`.

## Evidence

- Runtime policy: `docs/governance/REPLAY_RUNTIME_POLICY.md`
- Policy test: `tests/run_replay_runtime_policy.py`
- Executable monitoring profile: `docs/governance/REPLAY_OPS_MONITORING_PROFILE.json`
- Executable evaluator: `scripts/evaluate_replay_ops.py`
- Executable threshold checks: `tests/run_replay_ops_monitoring.py`

## Clear/Recovery Enforcement

Use evaluator state mode to enforce clear/recovery transitions:

`python3 scripts/evaluate_replay_ops.py --profile docs/governance/REPLAY_OPS_MONITORING_PROFILE.json --metrics /tmp/replay_metrics.json --state /tmp/replay_ops_state.json`

Evaluator hardening notes:

- Requires all core metrics (`availability_percent`, `failure_rate_percent`, `reject_rate_percent`, `p95_latency_ms`, `p99_latency_ms`, `backend_unavailable_seconds`).
- Treats missing/invalid metric snapshots as `critical` with explicit input-validation breaches.
- Enforces metric domain ranges (for example rates/availability must be `0..100`, latency/downtime must be non-negative).
- Enforces `clearConditions.max_sample_window_minutes` (`1` by default) and rejects non-finite values (`nan`, `inf`) to prevent de-escalation bypass.
