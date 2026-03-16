# Replay Incident Drill Evidence (2026-03-16)

## Scope

Replay incident runbook signoff evidence for sandbox readiness.

## Execution Summary

- Date: 2026-03-16 UTC
- Drill script: `scripts/incident_drill.sh`
- Mode: sandbox/local drill execution
- Provider path: `MockBiometricProvider`
- Outcome:
  - baseline verification: `pass`
  - incident fail-close check: `pass`
  - security gate check: `pass`
  - rotation response: `skipped`

## Commands Used

1. Run drill:

```bash
FAXP_INCIDENT_DRILL_PROVIDER=MockBiometricProvider ./scripts/incident_drill.sh <env-file>
```

2. Validate machine-checkable artifact schema:

```bash
python tests/run_replay_incident_artifacts.py
```

## Notes

- Non-local deployments still require runtime-complete replay prerequisites (`redis_shared`, adapter connectivity when applicable, and policy-compliant trust settings).
- This evidence closes runbook signoff for sandbox/builder-beta progression.
