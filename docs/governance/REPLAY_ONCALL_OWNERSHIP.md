# Replay Backend On-Call Ownership

## Primary Ownership

- Primary on-call: truckingadvantage
- Backup on-call: truckingadvantage-backup

## Responsibilities

- Review replay backend alerts and incidents.
- Approve/deny temporary single-instance override requests.
- Ensure override audit entries are reviewed weekly.
- Validate completion of Redis HA/failover tests before production scale-out.

## Weekly Review Cadence

- Review alert history and reject-rate anomalies.
- Review override entries in `REPLAY_OVERRIDE_AUDIT_REVIEW_LOG.md`.
- Confirm all active overrides are within policy window.
