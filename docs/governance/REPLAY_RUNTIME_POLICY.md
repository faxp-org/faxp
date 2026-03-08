# Replay Runtime Policy

This document defines runtime replay protection requirements for FAXP reference/runtime deployments.

Project status note: this is an experimental/early-stage project. Treat these controls as required for non-local pilot deployments and refine them further before production claims.

## Purpose

- Prevent cross-instance replay acceptance.
- Keep replay decisions deterministic across deployment topologies.
- Require explicit, auditable exceptions for temporary single-instance non-local operation.

## Deployment Modes

Configured by `FAXP_REPLAY_DEPLOYMENT_MODE`:

- `local_dev`
- `single_instance`
- `multi_instance`
- `auto_scaling`

Configured replay backend by `FAXP_REPLAY_BACKEND`:

- `sqlite_local`
- `redis_shared`

## Runtime Rules

1. Local/dev:
- `local_dev` may use `sqlite_local`.

2. Non-local `multi_instance` or `auto_scaling`:
- `redis_shared` is required.
- `FAXP_REPLAY_REDIS_URL` is required.

3. Non-local `single_instance` using `sqlite_local`:
- Allowed only with explicit temporary override in `FAXP_REPLAY_SINGLE_INSTANCE_OVERRIDE`.
- Override must include:
  - `reason`
  - `owner`
  - `expires_at_utc`
  - `ticket_id`
- Override max lifetime is 24h from process start validation.
- Startup fails closed on malformed, missing-field, non-UTC, expired, or >24h override.

## Override Example

```json
{
  "reason": "temporary single-node maintenance window",
  "owner": "ops@example.org",
  "expires_at_utc": "2026-03-08T18:00:00Z",
  "ticket_id": "SEC-142"
}
```

## Startup Audit Control

When a non-local single-instance override is accepted, startup emits a structured audit event:

- `event_type`: `replay_single_instance_override_active`
- `details.reason`
- `details.owner`
- `details.expires_at_utc`
- `details.ticket_id`
- `details.duration_seconds`
- `details.max_duration_seconds`

This event is written to the configured audit sink and is intended to make temporary exceptions explicit and reviewable.

## Atomic Shared Replay Claim

`redis_shared` mode uses a single Lua operation to claim both replay keys (`MessageID` and `Nonce`) atomically:

1. check if either key already exists
2. claim both keys with `NX + EX` in one script execution

This avoids race conditions where split operations could allow cross-instance replay gaps.
