#!/usr/bin/env python3
"""Hosted FMCSA adapter service for FAXP (Vultr-ready minimal server)."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime, timezone
import base64
import json
import os
import secrets
import traceback

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
ADAPTER_AUTH_TOKEN = os.getenv("FAXP_FMCSA_ADAPTER_AUTH_TOKEN", "").strip()
ADAPTER_DEBUG = os.getenv("FAXP_ADAPTER_DEBUG", "0").strip() == "1"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize_mc(value: object) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if not digits:
        return ""
    return digits.lstrip("0") or "0"


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


class AdapterHandler(BaseHTTPRequestHandler):
    server_version = "FAXP-FMCSA-Adapter/0.1"

    def _write_json(self, status_code: int, body: dict) -> None:
        response_bytes = json.dumps(body, sort_keys=True).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

    def _read_json_body(self) -> dict:
        content_length_header = self.headers.get("Content-Length", "0")
        try:
            content_length = int(content_length_header)
        except ValueError:
            raise ValueError("Invalid Content-Length.")
        if content_length <= 0:
            raise ValueError("Request body is required.")
        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Request body must be valid JSON.") from exc
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")
        return payload

    def _check_auth(self) -> bool:
        if not ADAPTER_REQUIRE_AUTH:
            return True
        if not ADAPTER_AUTH_TOKEN:
            return False
        incoming_token = _extract_bearer_token(self.headers.get("Authorization", ""))
        return bool(incoming_token) and secrets.compare_digest(incoming_token, ADAPTER_AUTH_TOKEN)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == ADAPTER_HEALTH_ENDPOINT:
            self._write_json(
                200,
                {
                    "status": "ok",
                    "service": "faxp-fmcsa-adapter",
                    "timestamp": _now_utc(),
                },
            )
            return
        self._write_json(404, {"error": "Not found."})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != ADAPTER_ENDPOINT:
            self._write_json(404, {"error": "Not found."})
            return

        if not self._check_auth():
            self._write_json(401, {"error": "Unauthorized."})
            return

        try:
            request_body = self._read_json_body()
        except ValueError as exc:
            self._write_json(400, {"error": str(exc)})
            return

        mc_number = _normalize_mc(request_body.get("mcNumber"))
        if not mc_number:
            unsigned_payload = {
                "ok": False,
                "error": "mcNumber is required.",
            }
            self._write_json(400, _build_signed_wrapper(unsigned_payload))
            return

        result = lookup_fmcsa_live_api(mc_number=mc_number)
        payload = dict(result)
        payload["mc_number"] = mc_number

        try:
            wrapper = _build_signed_wrapper(payload)
        except Exception as exc:  # fail closed
            if ADAPTER_DEBUG:
                self._write_json(500, {"error": f"Signing failure: {exc}"})
            else:
                self._write_json(500, {"error": "Signing failure."})
            return

        status_code = 200 if result.get("ok") else 502
        self._write_json(status_code, wrapper)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        if ADAPTER_DEBUG:
            super().log_message(format, *args)


def main() -> int:
    if ADAPTER_REQUIRE_AUTH and not ADAPTER_AUTH_TOKEN:
        raise RuntimeError(
            "FAXP_ADAPTER_REQUIRE_AUTH=1 but FAXP_FMCSA_ADAPTER_AUTH_TOKEN is empty."
        )
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
                "signatureScheme": VERIFIER_SIGNATURE_SCHEME,
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
