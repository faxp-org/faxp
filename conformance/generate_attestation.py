#!/usr/bin/env python3
"""Generate or refresh adapter self-attestation digest/signature fields."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import argparse
import hashlib
import hmac
import json
import sys


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: dict) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def _now_utc() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _default_expires_at(days: int = 180) -> str:
    return (
        (datetime.now(timezone.utc) + timedelta(days=days))
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _build_payload(profile: dict) -> dict:
    return {
        "adapterId": profile["adapterId"],
        "providerType": profile["providerType"],
        "hostingModel": profile["hostingModel"],
        "profilesSupported": profile["profilesSupported"],
        "securityCapabilities": profile["securityCapabilities"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate or refresh digest/signature in adapter self-attestation."
    )
    parser.add_argument(
        "--profile",
        required=True,
        help="Path to adapter profile JSON (for example: conformance/adapter_profile.sample.json).",
    )
    parser.add_argument(
        "--keyring",
        default="conformance/attestation_keys.sample.json",
        help="Path to keyring JSON with format: {\"keys\": {\"kid\": \"secret\"}}.",
    )
    parser.add_argument(
        "--kid",
        default="",
        help="Signing key ID to use. Defaults to selfAttestation.kid from profile.",
    )
    parser.add_argument(
        "--secret",
        default="",
        help="Raw HMAC secret override. If set, keyring lookup is skipped.",
    )
    parser.add_argument(
        "--signed-at",
        default="",
        help="Override signedAt ISO timestamp. Defaults to current UTC timestamp.",
    )
    parser.add_argument(
        "--expires-at",
        default="",
        help="Override expiresAt ISO timestamp. Defaults to now + 180 days.",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Write updated attestation back to the profile file instead of stdout.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    profile_path = Path(args.profile).expanduser().resolve()
    keyring_path = Path(args.keyring).expanduser().resolve()

    profile = _load_json(profile_path)
    self_attestation = dict(profile.get("selfAttestation") or {})

    payload = _build_payload(profile)
    payload_canonical = _canonical_json(payload)
    payload_digest = hashlib.sha256(payload_canonical.encode("utf-8")).hexdigest()

    kid = (args.kid or self_attestation.get("kid") or "").strip()
    if not kid:
        raise SystemExit("Missing key ID. Provide --kid or set selfAttestation.kid in profile.")

    secret_value = (args.secret or "").strip()
    if not secret_value:
        keyring = _load_json(keyring_path)
        keys = keyring.get("keys") or {}
        secret_value = str(keys.get(kid) or "").strip()
    if not secret_value:
        raise SystemExit(f"No secret found for kid '{kid}'.")

    signature = hmac.new(
        secret_value.encode("utf-8"),
        payload_canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    self_attestation["payload"] = payload
    self_attestation["payloadDigestSha256"] = f"sha256:{payload_digest}"
    self_attestation["alg"] = "HMAC_SHA256"
    self_attestation["kid"] = kid
    self_attestation["sig"] = signature
    self_attestation["signedAt"] = (args.signed_at or _now_utc()).strip()
    self_attestation["expiresAt"] = (args.expires_at or _default_expires_at()).strip()
    profile["selfAttestation"] = self_attestation

    if args.in_place:
        _write_json(profile_path, profile)
        print(f"Updated attestation in {profile_path}")
    else:
        print(json.dumps(profile, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
