#!/usr/bin/env python3
"""Validate replay backend runtime policy, override controls, and Redis claim atomicity."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import textwrap


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _base_env() -> dict[str, str]:
    env = dict(os.environ)
    for key in list(env.keys()):
        if key.startswith("FAXP_"):
            env.pop(key, None)
    return env


def _run_validate(extra_env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    code = textwrap.dedent(
        """
        import faxp_mvp_simulation as sim
        sim._validate_replay_runtime_policy()
        print("OK")
        """
    )
    env = _base_env()
    env.update(extra_env)
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(PROJECT_ROOT),
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


def _expect_failure(extra_env: dict[str, str], message_fragment: str) -> None:
    completed = _run_validate(extra_env)
    combined = f"{completed.stdout}\n{completed.stderr}"
    _assert(completed.returncode != 0, f"Expected failure but got success: {combined}")
    _assert(
        message_fragment in combined,
        f"Expected message '{message_fragment}' not found in output: {combined}",
    )


def _expect_success(extra_env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    completed = _run_validate(extra_env)
    combined = f"{completed.stdout}\n{completed.stderr}"
    _assert(completed.returncode == 0, f"Expected success but failed: {combined}")
    _assert("OK" in completed.stdout, "Validation success marker missing.")
    return completed


def _validate_override_and_audit_event() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        audit_path = Path(temp_dir) / "startup_audit.log"
        expires_at = (
            datetime.now(timezone.utc) + timedelta(hours=2)
        ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        override = {
            "reason": "temporary single-node maintenance window",
            "owner": "ops@example.org",
            "expires_at_utc": expires_at,
            "ticket_id": "SEC-142",
        }
        _expect_success(
            {
                "FAXP_APP_MODE": "production",
                "FAXP_REPLAY_BACKEND": "sqlite_local",
                "FAXP_REPLAY_DEPLOYMENT_MODE": "single_instance",
                "FAXP_REPLAY_SINGLE_INSTANCE_OVERRIDE": json.dumps(override),
                "FAXP_AUDIT_LOG_PATH": str(audit_path),
            }
        )
        _assert(audit_path.exists(), "Expected startup audit log to be written.")
        lines = [line for line in audit_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        _assert(lines, "Expected at least one startup audit event.")
        payload = json.loads(lines[-1])
        _assert(
            payload.get("event_type") == "replay_single_instance_override_active",
            "Startup audit event_type must be replay_single_instance_override_active.",
        )
        details = payload.get("details") or {}
        _assert(details.get("reason") == override["reason"], "Audit details.reason mismatch.")
        _assert(details.get("owner") == override["owner"], "Audit details.owner mismatch.")
        _assert(
            details.get("expires_at_utc") == override["expires_at_utc"],
            "Audit details.expires_at_utc mismatch.",
        )
        _assert(details.get("ticket_id") == override["ticket_id"], "Audit details.ticket_id mismatch.")
        _assert(
            isinstance(details.get("duration_seconds"), int) and details["duration_seconds"] > 0,
            "Audit details.duration_seconds must be a positive integer.",
        )
        _assert(
            details.get("max_duration_seconds") == 86400,
            "Audit details.max_duration_seconds must equal 86400.",
        )


def _validate_redis_lua_atomic_contract() -> None:
    code = textwrap.dedent(
        """
        import inspect
        import json
        import faxp_mvp_simulation as sim

        lua = sim.REPLAY_CLAIM_LUA_SCRIPT.lower()
        if "keys[1]" not in lua or "keys[2]" not in lua:
            raise SystemExit("lua script missing both key references")
        if lua.count('redis.call("set"') < 2:
            raise SystemExit("lua script must write both message and nonce keys")
        if '"nx"' not in lua or '"ex"' not in lua:
            raise SystemExit("lua script must enforce NX+EX semantics")

        source = inspect.getsource(sim._claim_replay_pair_redis)
        if ".eval(" not in source:
            raise SystemExit("replay claim must use Redis eval()")

        class FakeRedis:
            def __init__(self, result):
                self.result = result
                self.calls = []
            def eval(self, *args):
                self.calls.append(args)
                return self.result

        original_client = sim.REPLAY_REDIS_CLIENT
        original_prefix = sim.REPLAY_REDIS_KEY_PREFIX
        original_mode = sim.APP_MODE
        original_retention = sim.REPLAY_RETENTION_SECONDS
        try:
            fake_ok = FakeRedis(1)
            sim.REPLAY_REDIS_CLIENT = fake_ok
            sim.REPLAY_REDIS_KEY_PREFIX = "faxp:test"
            sim.APP_MODE = "production"
            sim.REPLAY_RETENTION_SECONDS = 3600
            ok = sim._claim_replay_pair_redis("sender-1", "mid-1", "nonce-1")
            if not ok:
                raise SystemExit("expected successful claim")
            if len(fake_ok.calls) != 1:
                raise SystemExit("expected exactly one eval call")
            script, num_keys, key1, key2, ttl, now_epoch = fake_ok.calls[0]
            if script != sim.REPLAY_CLAIM_LUA_SCRIPT:
                raise SystemExit("eval script mismatch")
            if int(num_keys) != 2:
                raise SystemExit("eval must operate on exactly 2 keys")
            if ":message:mid-1" not in key1:
                raise SystemExit("message key format mismatch")
            if ":nonce:nonce-1" not in key2:
                raise SystemExit("nonce key format mismatch")
            if key1 == key2:
                raise SystemExit("message and nonce keys must be distinct")
            if str(ttl) != "3600":
                raise SystemExit("ttl argument mismatch")
            int(str(now_epoch))

            fake_replay = FakeRedis(0)
            sim.REPLAY_REDIS_CLIENT = fake_replay
            replay = sim._claim_replay_pair_redis("sender-1", "mid-1", "nonce-1")
            if replay:
                raise SystemExit("expected replay claim to return False when eval returns 0")
        finally:
            sim.REPLAY_REDIS_CLIENT = original_client
            sim.REPLAY_REDIS_KEY_PREFIX = original_prefix
            sim.APP_MODE = original_mode
            sim.REPLAY_RETENTION_SECONDS = original_retention

        print(json.dumps({"ok": True}))
        """
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(PROJECT_ROOT),
        env=_base_env(),
        check=False,
        capture_output=True,
        text=True,
    )
    _assert(
        completed.returncode == 0,
        f"Redis atomic replay contract check failed:\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}",
    )


def main() -> int:
    _expect_failure(
        {
            "FAXP_APP_MODE": "production",
            "FAXP_REPLAY_BACKEND": "invalid_backend",
            "FAXP_REPLAY_DEPLOYMENT_MODE": "single_instance",
        },
        "Unsupported FAXP_REPLAY_BACKEND",
    )
    _expect_failure(
        {
            "FAXP_APP_MODE": "production",
            "FAXP_REPLAY_BACKEND": "sqlite_local",
            "FAXP_REPLAY_DEPLOYMENT_MODE": "local_dev",
        },
        "FAXP_REPLAY_DEPLOYMENT_MODE=local_dev is invalid in non-local mode.",
    )
    _expect_failure(
        {
            "FAXP_APP_MODE": "production",
            "FAXP_REPLAY_BACKEND": "sqlite_local",
            "FAXP_REPLAY_DEPLOYMENT_MODE": "multi_instance",
        },
        "Replay backend must be redis_shared for multi-instance/auto-scaling non-local deployments.",
    )
    _expect_failure(
        {
            "FAXP_APP_MODE": "production",
            "FAXP_REPLAY_BACKEND": "sqlite_local",
            "FAXP_REPLAY_DEPLOYMENT_MODE": "single_instance",
        },
        "Single-instance non-local replay exception requires FAXP_REPLAY_SINGLE_INSTANCE_OVERRIDE JSON.",
    )
    _expect_failure(
        {
            "FAXP_APP_MODE": "production",
            "FAXP_REPLAY_BACKEND": "sqlite_local",
            "FAXP_REPLAY_DEPLOYMENT_MODE": "single_instance",
            "FAXP_REPLAY_SINGLE_INSTANCE_OVERRIDE": "{not-json",
        },
        "FAXP_REPLAY_SINGLE_INSTANCE_OVERRIDE must be valid JSON.",
    )
    _expect_failure(
        {
            "FAXP_APP_MODE": "production",
            "FAXP_REPLAY_BACKEND": "sqlite_local",
            "FAXP_REPLAY_DEPLOYMENT_MODE": "single_instance",
            "FAXP_REPLAY_SINGLE_INSTANCE_OVERRIDE": json.dumps(
                {
                    "reason": "maintenance",
                    "owner": "ops@example.org",
                    "expires_at_utc": "2099-01-01T00:00:00Z",
                }
            ),
        },
        "FAXP_REPLAY_SINGLE_INSTANCE_OVERRIDE missing required field 'ticket_id'.",
    )
    _expect_failure(
        {
            "FAXP_APP_MODE": "production",
            "FAXP_REPLAY_BACKEND": "sqlite_local",
            "FAXP_REPLAY_DEPLOYMENT_MODE": "single_instance",
            "FAXP_REPLAY_SINGLE_INSTANCE_OVERRIDE": json.dumps(
                {
                    "reason": "maintenance",
                    "owner": "ops@example.org",
                    "expires_at_utc": (
                        datetime.now(timezone.utc) - timedelta(minutes=2)
                    ).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                    "ticket_id": "SEC-100",
                }
            ),
        },
        "FAXP_REPLAY_SINGLE_INSTANCE_OVERRIDE is expired.",
    )
    _expect_failure(
        {
            "FAXP_APP_MODE": "production",
            "FAXP_REPLAY_BACKEND": "sqlite_local",
            "FAXP_REPLAY_DEPLOYMENT_MODE": "single_instance",
            "FAXP_REPLAY_SINGLE_INSTANCE_OVERRIDE": json.dumps(
                {
                    "reason": "maintenance",
                    "owner": "ops@example.org",
                    "expires_at_utc": (
                        datetime.now(timezone.utc) + timedelta(hours=25)
                    ).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                    "ticket_id": "SEC-101",
                }
            ),
        },
        "FAXP_REPLAY_SINGLE_INSTANCE_OVERRIDE exceeds max duration (24h).",
    )
    _expect_failure(
        {
            "FAXP_APP_MODE": "production",
            "FAXP_REPLAY_BACKEND": "sqlite_local",
            "FAXP_REPLAY_DEPLOYMENT_MODE": "single_instance",
            "FAXP_REPLAY_SINGLE_INSTANCE_OVERRIDE": json.dumps(
                {
                    "reason": "maintenance",
                    "owner": "ops@example.org",
                    "expires_at_utc": "2099-01-01T00:00:00+05:00",
                    "ticket_id": "SEC-102",
                }
            ),
        },
        "FAXP_REPLAY_SINGLE_INSTANCE_OVERRIDE.expires_at_utc must be UTC (Z or +00:00).",
    )
    _expect_failure(
        {
            "FAXP_APP_MODE": "production",
            "FAXP_REPLAY_BACKEND": "redis_shared",
            "FAXP_REPLAY_DEPLOYMENT_MODE": "multi_instance",
        },
        "FAXP_REPLAY_REDIS_URL is required when FAXP_REPLAY_BACKEND=redis_shared.",
    )

    _validate_override_and_audit_event()
    _validate_redis_lua_atomic_contract()

    print("Replay runtime policy checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
