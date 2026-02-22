#!/usr/bin/env python3
"""Shared signing helpers for registry update request artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import json


def now_utc() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def canonical_payload_json(request_payload: dict) -> str:
    payload = {k: v for k, v in request_payload.items() if k != "requestSignature"}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def payload_digest_sha256(request_payload: dict) -> str:
    canonical = canonical_payload_json(request_payload)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def build_request_signature(
    request_payload: dict,
    *,
    kid: str,
    secret: str,
    signed_at: str | None = None,
    alg: str = "HMAC_SHA256",
) -> dict:
    if alg != "HMAC_SHA256":
        raise ValueError(f"Unsupported registry update signature algorithm: {alg}")
    canonical = canonical_payload_json(request_payload)
    signature = hmac.new(secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()
    return {
        "alg": alg,
        "kid": kid,
        "payloadDigestSha256": payload_digest_sha256(request_payload),
        "sig": signature,
        "signedAt": signed_at or now_utc(),
    }


def verify_request_signature(request_payload: dict, *, keyring: dict, require_signature: bool = True) -> None:
    signature = request_payload.get("requestSignature")
    if not signature:
        if require_signature:
            raise ValueError("Missing requestSignature.")
        return

    alg = str(signature.get("alg") or "")
    if alg != "HMAC_SHA256":
        raise ValueError(f"Unsupported requestSignature.alg: {alg}")

    kid = str(signature.get("kid") or "").strip()
    if not kid:
        raise ValueError("Missing requestSignature.kid.")
    keys = keyring.get("keys") or {}
    secret = str(keys.get(kid) or "").strip()
    if not secret:
        raise ValueError(f"Unknown requestSignature kid: {kid}")

    expected_digest = payload_digest_sha256(request_payload)
    actual_digest = str(signature.get("payloadDigestSha256") or "")
    if not hmac.compare_digest(expected_digest, actual_digest):
        raise ValueError("requestSignature payload digest mismatch.")

    canonical = canonical_payload_json(request_payload)
    expected_sig = hmac.new(secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()
    actual_sig = str(signature.get("sig") or "")
    if not hmac.compare_digest(expected_sig, actual_sig):
        raise ValueError("requestSignature verification failed.")

