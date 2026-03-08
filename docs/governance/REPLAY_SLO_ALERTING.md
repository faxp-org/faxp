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
