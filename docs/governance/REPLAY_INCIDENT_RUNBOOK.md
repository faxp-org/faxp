# Replay Incident Runbook

## Trigger Conditions

- Replay backend unavailable in non-local mode.
- Replay reject-rate alert exceeds critical threshold.
- Unexpected spike in replay acceptance after deployment change.

## Initial Response

1. Confirm current replay backend and deployment mode.
2. Check runtime logs for replay startup audit events and backend errors.
3. Confirm Redis health and connectivity.
4. Validate whether temporary single-instance override is active.

## Containment

1. Keep fail-closed behavior enabled; do not disable replay checks.
2. If temporary override is required, enforce policy fields and 24h max duration.
3. Record override in `REPLAY_OVERRIDE_AUDIT_REVIEW_LOG.md`.

## Recovery

1. Restore Redis availability and verify replay claim success metrics.
2. Re-run replay policy verification (`tests/run_replay_runtime_policy.py`).
3. Verify alert conditions return to normal.

## Post-Incident Requirements

- Publish incident summary with root cause, timeline, and corrective actions.
- Update gate status in `REPLAY_OPERATIONS_GATES.md`.
