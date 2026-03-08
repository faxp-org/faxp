# Redis HA/Failover Test Plan (Replay Backend)

## Objective

Validate that replay claim behavior remains fail-closed and operationally observable during Redis disruptions.

## Mandatory Scenarios

1. Primary Redis restart during active replay traffic.
2. Network timeout/partition between runtime and Redis.
3. Replica promotion/failover in managed Redis.
4. Clock skew tolerance validation for TTL behavior.

## Pass Criteria

- Replay claims do not silently succeed when Redis is unavailable.
- Runtime fails closed according to replay policy.
- Alerting triggers based on thresholds in `REPLAY_REJECT_RATE_ALERTING.md`.
- Incident steps are executable from `REPLAY_INCIDENT_RUNBOOK.md`.

## Evidence to Attach

- Timestamped command transcript and environment.
- Replay reject/allow counts before, during, after failover event.
- Alert firing and acknowledgment timestamps.
