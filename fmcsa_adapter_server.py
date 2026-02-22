#!/usr/bin/env python3
"""Hardened hosted FMCSA adapter service for FAXP."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
import traceback
from uuid import uuid4

from faxp_mvp_simulation import (
    VERIFIER_ED25519_ACTIVE_KEY_ID,
    VERIFIER_ED25519_PRIVATE_KEYS,
    VERIFIER_SIGNATURE_SCHEME,
    VERIFIER_SIGNING_ACTIVE_KEY_ID,
    VERIFIER_SIGNING_KEYS,
    _ed25519_sign_bytes,
    canonical_json,
    lookup_fmcsa_live_api,
    sign_payload,
)

ADAPTER_HOST = os.getenv("FAXP_ADAPTER_HOST", "127.0.0.1").strip()
ADAPTER_PORT = int(os.getenv("FAXP_ADAPTER_PORT", "8088").strip())
ADAPTER_ENDPOINT = os.getenv("FAXP_ADAPTER_ENDPOINT", "/v1/fmcsa/verify").strip() or "/v1/fmcsa/verify"
ADAPTER_HEALTH_ENDPOINT = os.getenv("FAXP_ADAPTER_HEALTH_ENDPOINT", "/healthz").strip() or "/healthz"
ADAPTER_REQUIRE_AUTH = os.getenv("FAXP_ADAPTER_REQUIRE_AUTH", "1").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
ADAPTER_REQUIRE_SIGNED_REQUESTS = os.getenv(
    "FAXP_ADAPTER_REQUIRE_SIGNED_REQUESTS",
    "1",
).strip().lower() in {"1", "true", "yes", "on"}
ADAPTER_HEALTH_REQUIRE_AUTH = os.getenv("FAXP_ADAPTER_HEALTH_REQUIRE_AUTH", "1").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
ADAPTER_AUTH_TOKEN = os.getenv("FAXP_FMCSA_ADAPTER_AUTH_TOKEN", "").strip()
ADAPTER_DEBUG = os.getenv("FAXP_ADAPTER_DEBUG", "0").strip() == "1"
ADAPTER_MAX_BODY_BYTES = max(256, min(65536, int(os.getenv("FAXP_ADAPTER_MAX_BODY_BYTES", "4096"))))
ADAPTER_AUTH_FAILURE_DELAY_MS = max(
    0,
    min(5000, int(os.getenv("FAXP_ADAPTER_AUTH_FAILURE_DELAY_MS", "250"))),
)
ADAPTER_RATE_LIMIT_WINDOW_SECONDS = max(
    10,
    min(3600, int(os.getenv("FAXP_ADAPTER_RATE_LIMIT_WINDOW_SECONDS", "60"))),
)
ADAPTER_RATE_LIMIT_PER_IP = max(
    5,
    min(5000, int(os.getenv("FAXP_ADAPTER_RATE_LIMIT_PER_IP", "120"))),
)
ADAPTER_RATE_LIMIT_GLOBAL = max(
    20,
    min(20000, int(os.getenv("FAXP_ADAPTER_RATE_LIMIT_GLOBAL", "1000"))),
)
ADAPTER_REQUEST_MAX_CLOCK_SKEW_SECONDS = max(
    5,
    min(600, int(os.getenv("FAXP_ADAPTER_REQUEST_MAX_CLOCK_SKEW_SECONDS", "60"))),
)
ADAPTER_REQUEST_NONCE_TTL_SECONDS = max(
    10,
    min(3600, int(os.getenv("FAXP_ADAPTER_REQUEST_NONCE_TTL_SECONDS", "300"))),
)
ADAPTER_REQUEST_SIGNING_KEYS_RAW = os.getenv("FAXP_ADAPTER_REQUEST_SIGNING_KEYS", "").strip()
ADAPTER_AUDIT_LOG_PATH = os.getenv(
    "FAXP_ADAPTER_AUDIT_LOG_PATH",
    "/var/log/faxp/fmcsa_adapter_audit.log",
).strip()
ADAPTER_AUDIT_HASH_SALT = os.getenv("FAXP_ADAPTER_AUDIT_HASH_SALT", "").strip()

NONCE_PATTERN = re.compile(r"^[a-fA-F0-9]{16,128}$")

REQUEST_TRACKING_LOCK = threading.Lock()
RATE_GLOBAL_WINDOW: deque[float] = deque()
RATE_IP_WINDOWS: dict[str, deque[float]] = {}
NONCE_REPLAY_CACHE: dict[str, float] = {}

AUDIT_LOCK = threading.Lock()
LAST_AUDIT_HASH = ""


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sleep_auth_penalty() -> None:
    if ADAPTER_AUTH_FAILURE_DELAY_MS > 0:
        time.sleep(ADAPTER_AUTH_FAILURE_DELAY_MS / 1000.0)


def _normalize_mc(value: object) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if not digits:
        return ""
    return digits.lstrip("0") or "0"


def _parse_hmac_key_ring(raw_pairs: str) -> dict[str, bytes]:
    key_ring: dict[str, bytes] = {}
    if not raw_pairs:
        return key_ring
    for raw_entry in raw_pairs.split(","):
        entry = raw_entry.strip()
        if not entry:
            continue
        if ":" in entry:
            kid, key_value = entry.split(":", 1)
        elif "=" in entry:
            kid, key_value = entry.split("=", 1)
        else:
            raise RuntimeError("FAXP_ADAPTER_REQUEST_SIGNING_KEYS entries must use 'kid:key'.")
        kid = kid.strip()
        key_value = key_value.strip()
        if not kid or not key_value:
            raise RuntimeError("FAXP_ADAPTER_REQUEST_SIGNING_KEYS contains empty key ID/value.")
        key_ring[kid] = key_value.encode("utf-8")
    return key_ring


ADAPTER_REQUEST_SIGNING_KEYS = _parse_hmac_key_ring(ADAPTER_REQUEST_SIGNING_KEYS_RAW)


def _build_adapter_request_signature(
    method: str,
    path: str,
    timestamp_text: str,
    nonce: str,
    body_bytes: bytes,
    key: bytes,
) -> str:
    body_hash = hashlib.sha256(body_bytes).hexdigest()
    signing_payload = "\n".join(
        [
            method.upper(),
            path or "/",
            timestamp_text,
            nonce,
            body_hash,
        ]
    )
    return hmac.new(key, signing_payload.encode("utf-8"), hashlib.sha256).hexdigest()


def _build_signed_wrapper(payload: dict) -> dict:
    scheme = VERIFIER_SIGNATURE_SCHEME
    if scheme == "HMAC_SHA256":
        key_id = VERIFIER_SIGNING_ACTIVE_KEY_ID
        key = VERIFIER_SIGNING_KEYS.get(key_id, b"")
        if not key_id or not key:
            raise RuntimeError("Missing verifier HMAC signing key configuration.")
        signature = sign_payload(payload, key)
        if not signature:
            raise RuntimeError("Failed to sign hosted adapter payload with HMAC.")
        return {
            "payload": payload,
            "signature_algorithm": "HMAC_SHA256",
            "signature_key_id": key_id,
            "signature": signature,
        }

    if scheme == "ED25519":
        key_id = VERIFIER_ED25519_ACTIVE_KEY_ID
        private_key_path = VERIFIER_ED25519_PRIVATE_KEYS.get(key_id, "")
        if not key_id or not private_key_path:
            raise RuntimeError("Missing verifier ED25519 signing key configuration.")
        signature_bytes = _ed25519_sign_bytes(
            canonical_json(payload).encode("utf-8"),
            private_key_path,
        )
        if not signature_bytes:
            raise RuntimeError("Failed to sign hosted adapter payload with ED25519.")
        return {
            "payload": payload,
            "signature_algorithm": "ED25519",
            "signature_key_id": key_id,
            "signature": base64.b64encode(signature_bytes).decode("ascii"),
        }

    raise RuntimeError(f"Unsupported verifier signature scheme: {scheme}")


def _extract_bearer_token(header_value: str) -> str:
    if not header_value:
        return ""
    parts = header_value.split(" ", 1)
    if len(parts) != 2:
        return ""
    if parts[0].strip().lower() != "bearer":
        return ""
    return parts[1].strip()


def _parse_timestamp(timestamp_text: str) -> datetime:
    text = str(timestamp_text or "").strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _hash_ip(ip_value: str) -> str:
    seed = f"{ADAPTER_AUDIT_HASH_SALT}:{ip_value}" if ADAPTER_AUDIT_HASH_SALT else ip_value
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def _write_audit_event(event_type: str, request_id: str, source_ip: str, outcome: str, detail: str) -> None:
    global LAST_AUDIT_HASH
    event = {
        "timestamp": _now_utc(),
        "eventType": event_type,
        "requestId": request_id,
        "sourceIpHash": _hash_ip(source_ip),
        "outcome": outcome,
        "detail": detail[:240],
        "prevHash": LAST_AUDIT_HASH,
    }
    event_hash = hashlib.sha256(canonical_json(event).encode("utf-8")).hexdigest()
    event["eventHash"] = event_hash
    with AUDIT_LOCK:
        LAST_AUDIT_HASH = event_hash
        try:
            if ADAPTER_AUDIT_LOG_PATH:
                os.makedirs(os.path.dirname(ADAPTER_AUDIT_LOG_PATH), exist_ok=True)
                with open(ADAPTER_AUDIT_LOG_PATH, "a", encoding="utf-8") as handle:
                    handle.write(canonical_json(event) + "\n")
        except Exception:
            if ADAPTER_DEBUG:
                traceback.print_exc()


def _is_rate_limited(source_ip: str) -> bool:
    now = time.time()
    cutoff = now - ADAPTER_RATE_LIMIT_WINDOW_SECONDS
    with REQUEST_TRACKING_LOCK:
        while RATE_GLOBAL_WINDOW and RATE_GLOBAL_WINDOW[0] < cutoff:
            RATE_GLOBAL_WINDOW.popleft()
        if len(RATE_GLOBAL_WINDOW) >= ADAPTER_RATE_LIMIT_GLOBAL:
            return True

        ip_window = RATE_IP_WINDOWS.setdefault(source_ip, deque())
        while ip_window and ip_window[0] < cutoff:
            ip_window.popleft()
        if len(ip_window) >= ADAPTER_RATE_LIMIT_PER_IP:
            return True

        RATE_GLOBAL_WINDOW.append(now)
        ip_window.append(now)
    return False


def _check_and_track_nonce(kid: str, nonce: str, request_time: datetime) -> bool:
    cache_key = f"{kid}:{nonce}"
    now_epoch = time.time()
    expiry_epoch = max(now_epoch, request_time.timestamp()) + ADAPTER_REQUEST_NONCE_TTL_SECONDS
    with REQUEST_TRACKING_LOCK:
        expired_keys = [key for key, expires_at in NONCE_REPLAY_CACHE.items() if expires_at < now_epoch]
        for key in expired_keys:
            NONCE_REPLAY_CACHE.pop(key, None)
        if cache_key in NONCE_REPLAY_CACHE:
            return False
        NONCE_REPLAY_CACHE[cache_key] = expiry_epoch
    return True


def _source_ip(handler: BaseHTTPRequestHandler) -> str:
    direct_ip = str(handler.client_address[0] if handler.client_address else "")
    forwarded_for = handler.headers.get("X-Forwarded-For", "")
    if direct_ip in {"127.0.0.1", "::1"} and forwarded_for:
        candidate = forwarded_for.split(",")[0].strip()
        if candidate:
            return candidate
    return direct_ip or "unknown"


class AdapterHandler(BaseHTTPRequestHandler):
    server_version = "FAXP-FMCSA-Adapter/0.2"

    def _write_json(self, status_code: int, body: dict, request_id: str = "") -> None:
        response_bytes = json.dumps(body, sort_keys=True).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Pragma", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Length", str(len(response_bytes)))
        if request_id:
            self.send_header("X-FAXP-Request-Id", request_id)
        self.end_headers()
        self.wfile.write(response_bytes)

    def _read_json_body(self) -> tuple[dict, bytes]:
        content_type = str(self.headers.get("Content-Type", "")).lower()
        if "application/json" not in content_type:
            raise ValueError("Content-Type must be application/json.")

        content_length_header = self.headers.get("Content-Length", "0")
        try:
            content_length = int(content_length_header)
        except ValueError:
            raise ValueError("Invalid Content-Length.")
        if content_length <= 0:
            raise ValueError("Request body is required.")
        if content_length > ADAPTER_MAX_BODY_BYTES:
            raise ValueError("Request body too large.")

        raw_body = self.rfile.read(content_length)
        if len(raw_body) > ADAPTER_MAX_BODY_BYTES:
            raise ValueError("Request body too large.")

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Request body must be valid JSON.") from exc
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")
        return payload, raw_body

    def _is_authorized(self) -> bool:
        if not ADAPTER_REQUIRE_AUTH:
            return True
        if not ADAPTER_AUTH_TOKEN:
            return False
        incoming_token = _extract_bearer_token(self.headers.get("Authorization", ""))
        return bool(incoming_token) and secrets.compare_digest(incoming_token, ADAPTER_AUTH_TOKEN)

    def _verify_signed_request(self, raw_body: bytes) -> tuple[bool, str]:
        if not ADAPTER_REQUIRE_SIGNED_REQUESTS:
            return True, "disabled"
        if not ADAPTER_REQUEST_SIGNING_KEYS:
            return False, "request-signing-key-ring-missing"

        kid = str(self.headers.get("X-FAXP-Key-Id", "")).strip()
        timestamp_text = str(self.headers.get("X-FAXP-Timestamp", "")).strip()
        nonce = str(self.headers.get("X-FAXP-Nonce", "")).strip()
        signature = str(self.headers.get("X-FAXP-Signature", "")).strip()

        if not kid or not timestamp_text or not nonce or not signature:
            return False, "missing-signed-request-headers"
        if kid not in ADAPTER_REQUEST_SIGNING_KEYS:
            return False, "untrusted-request-signing-kid"
        if not NONCE_PATTERN.match(nonce):
            return False, "invalid-nonce-format"

        try:
            request_time = _parse_timestamp(timestamp_text)
        except Exception:
            return False, "invalid-timestamp"
        now = datetime.now(timezone.utc)
        skew_seconds = abs((now - request_time).total_seconds())
        if skew_seconds > ADAPTER_REQUEST_MAX_CLOCK_SKEW_SECONDS:
            return False, "timestamp-skew-exceeded"

        if not _check_and_track_nonce(kid, nonce, request_time):
            return False, "nonce-replay-detected"

        expected_signature = _build_adapter_request_signature(
            method=self.command,
            path=self.path,
            timestamp_text=timestamp_text,
            nonce=nonce,
            body_bytes=raw_body,
            key=ADAPTER_REQUEST_SIGNING_KEYS[kid],
        )
        if not hmac.compare_digest(expected_signature, signature):
            return False, "request-signature-mismatch"
        return True, "verified"

    def do_GET(self) -> None:  # noqa: N802
        request_id = self.headers.get("X-FAXP-Request-Id", str(uuid4()))
        source_ip = _source_ip(self)
        if self.path == ADAPTER_HEALTH_ENDPOINT:
            if ADAPTER_HEALTH_REQUIRE_AUTH and not self._is_authorized():
                _sleep_auth_penalty()
                _write_audit_event("health", request_id, source_ip, "deny", "unauthorized")
                self._write_json(401, {"error": "Unauthorized."}, request_id=request_id)
                return
            _write_audit_event("health", request_id, source_ip, "allow", "ok")
            self._write_json(
                200,
                {
                    "status": "ok",
                    "service": "faxp-fmcsa-adapter",
                    "timestamp": _now_utc(),
                },
                request_id=request_id,
            )
            return
        self._write_json(404, {"error": "Not found."}, request_id=request_id)

    def do_POST(self) -> None:  # noqa: N802
        request_id = self.headers.get("X-FAXP-Request-Id", str(uuid4()))
        source_ip = _source_ip(self)

        if self.path != ADAPTER_ENDPOINT:
            self._write_json(404, {"error": "Not found."}, request_id=request_id)
            return

        if _is_rate_limited(source_ip):
            _write_audit_event("verify", request_id, source_ip, "deny", "rate-limited")
            self._write_json(429, {"error": "Rate limit exceeded."}, request_id=request_id)
            return

        if not self._is_authorized():
            _sleep_auth_penalty()
            _write_audit_event("verify", request_id, source_ip, "deny", "unauthorized")
            self._write_json(401, {"error": "Unauthorized."}, request_id=request_id)
            return

        try:
            request_body, raw_body = self._read_json_body()
        except ValueError as exc:
            _write_audit_event("verify", request_id, source_ip, "deny", str(exc))
            self._write_json(400, {"error": str(exc)}, request_id=request_id)
            return

        signed_ok, signed_reason = self._verify_signed_request(raw_body)
        if not signed_ok:
            _sleep_auth_penalty()
            _write_audit_event("verify", request_id, source_ip, "deny", signed_reason)
            self._write_json(401, {"error": "Signed request verification failed."}, request_id=request_id)
            return

        mc_number = _normalize_mc(request_body.get("mcNumber"))
        if not mc_number:
            payload = {"ok": False, "error": "mcNumber is required."}
            wrapper = _build_signed_wrapper(payload)
            _write_audit_event("verify", request_id, source_ip, "deny", "missing-mc")
            self._write_json(400, wrapper, request_id=request_id)
            return

        result = lookup_fmcsa_live_api(mc_number=mc_number)
        payload = dict(result)
        payload["mc_number"] = mc_number

        try:
            wrapper = _build_signed_wrapper(payload)
        except Exception as exc:
            _write_audit_event("verify", request_id, source_ip, "error", "signing-failure")
            if ADAPTER_DEBUG:
                self._write_json(
                    500,
                    {"error": f"Signing failure: {type(exc).__name__}"},
                    request_id=request_id,
                )
            else:
                self._write_json(500, {"error": "Signing failure."}, request_id=request_id)
            return

        if result.get("ok"):
            _write_audit_event("verify", request_id, source_ip, "allow", "verified")
            self._write_json(200, wrapper, request_id=request_id)
            return

        _write_audit_event("verify", request_id, source_ip, "deny", "upstream-unavailable")
        self._write_json(502, wrapper, request_id=request_id)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        if ADAPTER_DEBUG:
            super().log_message(format, *args)


def _validate_startup_config() -> None:
    if ADAPTER_REQUIRE_AUTH and not ADAPTER_AUTH_TOKEN:
        raise RuntimeError(
            "FAXP_ADAPTER_REQUIRE_AUTH=1 but FAXP_FMCSA_ADAPTER_AUTH_TOKEN is empty."
        )
    if ADAPTER_REQUIRE_SIGNED_REQUESTS and not ADAPTER_REQUEST_SIGNING_KEYS:
        raise RuntimeError(
            "FAXP_ADAPTER_REQUIRE_SIGNED_REQUESTS=1 but FAXP_ADAPTER_REQUEST_SIGNING_KEYS is empty."
        )
    if VERIFIER_SIGNATURE_SCHEME not in {"HMAC_SHA256", "ED25519"}:
        raise RuntimeError("Unsupported verifier signature scheme.")
    if VERIFIER_SIGNATURE_SCHEME == "ED25519":
        if not VERIFIER_ED25519_ACTIVE_KEY_ID:
            raise RuntimeError("Missing VERIFIER_ED25519_ACTIVE_KEY_ID.")
        if VERIFIER_ED25519_ACTIVE_KEY_ID not in VERIFIER_ED25519_PRIVATE_KEYS:
            raise RuntimeError("Missing active ED25519 private key path.")
    if VERIFIER_SIGNATURE_SCHEME == "HMAC_SHA256":
        if not VERIFIER_SIGNING_ACTIVE_KEY_ID:
            raise RuntimeError("Missing VERIFIER_SIGNING_ACTIVE_KEY_ID.")
        if VERIFIER_SIGNING_ACTIVE_KEY_ID not in VERIFIER_SIGNING_KEYS:
            raise RuntimeError("Missing active verifier HMAC key.")


def main() -> int:
    _validate_startup_config()
    server = ThreadingHTTPServer((ADAPTER_HOST, ADAPTER_PORT), AdapterHandler)
    print(
        json.dumps(
            {
                "event": "adapter_started",
                "host": ADAPTER_HOST,
                "port": ADAPTER_PORT,
                "endpoint": ADAPTER_ENDPOINT,
                "health": ADAPTER_HEALTH_ENDPOINT,
                "authRequired": ADAPTER_REQUIRE_AUTH,
                "signedRequestsRequired": ADAPTER_REQUIRE_SIGNED_REQUESTS,
                "verifierSignatureScheme": VERIFIER_SIGNATURE_SCHEME,
                "maxBodyBytes": ADAPTER_MAX_BODY_BYTES,
                "rateLimitPerIp": ADAPTER_RATE_LIMIT_PER_IP,
                "rateLimitGlobal": ADAPTER_RATE_LIMIT_GLOBAL,
            },
            sort_keys=True,
        )
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    except Exception:
        if ADAPTER_DEBUG:
            traceback.print_exc()
        raise
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
