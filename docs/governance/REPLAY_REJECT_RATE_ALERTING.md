# Replay Reject-Rate Alerting

## Purpose

Detect replay rejection anomalies that may indicate active abuse, key drift, or runtime regression.

## Alert Rules (Initial)

- `warn`: replay rejection rate above `1%` over 15 minutes.
- `critical`: replay rejection rate above `5%` over 5 minutes.
- `critical`: replay backend unavailable for more than 120 seconds.

## Required Dimensions

- `deployment_mode`
- `replay_backend`
- `message_type`
- `sender`

## Escalation Path

1. Page on-call owner listed in `docs/governance/REPLAY_ONCALL_OWNERSHIP.md`.
2. Open incident using `docs/governance/REPLAY_INCIDENT_RUNBOOK.md`.
3. Record override decisions in `docs/governance/REPLAY_OVERRIDE_AUDIT_REVIEW_LOG.md`.
