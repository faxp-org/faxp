#!/usr/bin/env python3
"""Regression checks for hosted FMCSA adapter integration."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import json
import threading
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import faxp_mvp_simulation as sim  # noqa: E402


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _build_payload(mc_number: str) -> dict[str, object]:
    return {
        "found": True,
        "status": "Success",
        "score": 93,
        "usdot_number": 1292301,
        "mc_number": mc_number,
        "carrier_name": "CA FREIGHT XPRESS INC",
        "operating_status": "ACTIVE",
        "has_current_insurance": True,
        "interstate_authority_ok": True,
    }


def _signed_wrapper(
    payload: dict[str, object],
    key_id: str,
    key: bytes,
    signature_suffix: str = "",
) -> dict[str, object]:
    signature = sim.sign_payload(payload, key)
    if signature_suffix:
        signature = f"{signature}{signature_suffix}"
    return {
        "payload": payload,
        "signature_algorithm": "HMAC_SHA256",
        "signature_key_id": key_id,
        "signature": signature,
    }


class _HostedAdapterHandler(BaseHTTPRequestHandler):
    good_wrapper: dict[str, object] = {}
    bad_wrapper: dict[str, object] = {}
    request_key_id: str = ""
    request_key: bytes = b""

    def do_POST(self) -> None:
        raw_length = self.headers.get("Content-Length", "0")
        try:
            body_length = int(raw_length)
        except ValueError:
            body_length = 0
        payload = self.rfile.read(body_length)
        try:
            request_json = json.loads(payload.decode("utf-8"))
        except Exception:
            self._write_json(400, {"error": "invalid-json"})
            return

        key_id = self.headers.get("X-FAXP-Key-Id", "")
        timestamp_text = self.headers.get("X-FAXP-Timestamp", "")
        nonce = self.headers.get("X-FAXP-Nonce", "")
        signature = self.headers.get("X-FAXP-Signature", "")
        if (
            key_id != self.request_key_id
            or not timestamp_text
            or not nonce
            or not signature
        ):
            self._write_json(401, {"error": "missing-signed-request-headers"})
            return
        expected_signature = sim._build_adapter_request_signature(  # noqa: SLF001
            method="POST",
            path=self.path,
            timestamp_text=timestamp_text,
            nonce=nonce,
            body_bytes=payload,
            key=self.request_key,
        )
        if signature != expected_signature:
            self._write_json(401, {"error": "invalid-request-signature"})
            return

        if request_json.get("mcNumber") != "498282":
            self._write_json(422, {"error": "unexpected-mc"})
            return

        if self.path == "/verify":
            self._write_json(200, self.good_wrapper)
            return
        if self.path == "/verify-bad":
            self._write_json(200, self.bad_wrapper)
            return

        self._write_json(404, {"error": "not-found"})

    def _write_json(self, status_code: int, body: dict[str, object]) -> None:
        data = json.dumps(body).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args: object) -> None:  # noqa: D401
        return


def main() -> int:
    original_values = {
        "REQUIRE_SIGNED_VERIFIER": sim.REQUIRE_SIGNED_VERIFIER,
        "VERIFIER_SIGNATURE_SCHEME": sim.VERIFIER_SIGNATURE_SCHEME,
        "VERIFIER_SIGNING_KEYS": sim.VERIFIER_SIGNING_KEYS,
        "VERIFIER_SIGNING_ACTIVE_KEY_ID": sim.VERIFIER_SIGNING_ACTIVE_KEY_ID,
        "VERIFIER_ED25519_PUBLIC_KEYS": sim.VERIFIER_ED25519_PUBLIC_KEYS,
        "FMCSA_ADAPTER_REQUIRE_SIGNED_WRAPPER": sim.FMCSA_ADAPTER_REQUIRE_SIGNED_WRAPPER,
        "FMCSA_ADAPTER_TIMEOUT_SECONDS": sim.FMCSA_ADAPTER_TIMEOUT_SECONDS,
        "FMCSA_ADAPTER_BASE_URL": sim.FMCSA_ADAPTER_BASE_URL,
        "FMCSA_ADAPTER_SIGN_REQUESTS": sim.FMCSA_ADAPTER_SIGN_REQUESTS,
        "FMCSA_ADAPTER_REQUEST_SIGNING_KEYS": sim.FMCSA_ADAPTER_REQUEST_SIGNING_KEYS,
        "FMCSA_ADAPTER_REQUEST_SIGNING_ACTIVE_KEY_ID": sim.FMCSA_ADAPTER_REQUEST_SIGNING_ACTIVE_KEY_ID,
        "FMCSA_ADAPTER_REQUEST_SIGNING_KEY": sim.FMCSA_ADAPTER_REQUEST_SIGNING_KEY,
    }
    server = HTTPServer(("127.0.0.1", 0), _HostedAdapterHandler)
    port = server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)

    try:
        verifier_key_id = "adapter-test-kid"
        verifier_key = b"adapter-test-secret"
        request_signing_key_id = "adapter-request-kid"
        request_signing_key = b"adapter-request-secret"
        payload = _build_payload("498282")
        _HostedAdapterHandler.request_key_id = request_signing_key_id
        _HostedAdapterHandler.request_key = request_signing_key
        _HostedAdapterHandler.good_wrapper = _signed_wrapper(
            payload,
            verifier_key_id,
            verifier_key,
        )
        _HostedAdapterHandler.bad_wrapper = _signed_wrapper(
            payload,
            verifier_key_id,
            verifier_key,
            signature_suffix="tampered",
        )

        sim.REQUIRE_SIGNED_VERIFIER = True
        sim.VERIFIER_SIGNATURE_SCHEME = "HMAC_SHA256"
        sim.VERIFIER_SIGNING_KEYS = {verifier_key_id: verifier_key}
        sim.VERIFIER_SIGNING_ACTIVE_KEY_ID = verifier_key_id
        sim.VERIFIER_ED25519_PUBLIC_KEYS = {}
        sim.FMCSA_ADAPTER_REQUIRE_SIGNED_WRAPPER = True
        sim.FMCSA_ADAPTER_TIMEOUT_SECONDS = 5
        sim.FMCSA_ADAPTER_SIGN_REQUESTS = True
        sim.FMCSA_ADAPTER_REQUEST_SIGNING_KEYS = {request_signing_key_id: request_signing_key}
        sim.FMCSA_ADAPTER_REQUEST_SIGNING_ACTIVE_KEY_ID = request_signing_key_id
        sim.FMCSA_ADAPTER_REQUEST_SIGNING_KEY = request_signing_key

        thread.start()

        sim.FMCSA_ADAPTER_BASE_URL = f"http://127.0.0.1:{port}/verify"
        success_result, success_badge = sim.run_verification(
            provider="FMCSA",
            status="Success",
            mc_number="498282",
            fmcsa_source="hosted-adapter",
        )
        _assert(success_result["status"] == "Success", "hosted adapter success status mismatch")
        _assert(success_badge == "Basic", "hosted adapter badge mismatch")
        _assert(success_result["source"] == "hosted-adapter", "hosted adapter source mismatch")
        _assert(
            success_result["provider"]
            == sim.NEUTRAL_VERIFICATION_PROVIDER_IDS["fmcsa_hosted_adapter"],
            "hosted adapter provider ID mismatch",
        )

        sim.FMCSA_ADAPTER_BASE_URL = f"http://127.0.0.1:{port}/verify-bad"
        fail_result, fail_badge = sim.run_verification(
            provider="FMCSA",
            status="Success",
            mc_number="498282",
            fmcsa_source="hosted-adapter",
        )
        _assert(fail_result["status"] == "Fail", "tampered signature should fail verification")
        _assert(fail_badge == "None", "tampered signature should not assign badge")
        _assert(
            "signature" in str(fail_result.get("error", "")).lower(),
            "tampered signature failure should mention signature validation",
        )

        print("Hosted FMCSA adapter regression checks passed.")
        return 0
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        sim.REQUIRE_SIGNED_VERIFIER = original_values["REQUIRE_SIGNED_VERIFIER"]
        sim.VERIFIER_SIGNATURE_SCHEME = original_values["VERIFIER_SIGNATURE_SCHEME"]
        sim.VERIFIER_SIGNING_KEYS = original_values["VERIFIER_SIGNING_KEYS"]
        sim.VERIFIER_SIGNING_ACTIVE_KEY_ID = original_values["VERIFIER_SIGNING_ACTIVE_KEY_ID"]
        sim.VERIFIER_ED25519_PUBLIC_KEYS = original_values["VERIFIER_ED25519_PUBLIC_KEYS"]
        sim.FMCSA_ADAPTER_REQUIRE_SIGNED_WRAPPER = original_values[
            "FMCSA_ADAPTER_REQUIRE_SIGNED_WRAPPER"
        ]
        sim.FMCSA_ADAPTER_TIMEOUT_SECONDS = original_values["FMCSA_ADAPTER_TIMEOUT_SECONDS"]
        sim.FMCSA_ADAPTER_BASE_URL = original_values["FMCSA_ADAPTER_BASE_URL"]
        sim.FMCSA_ADAPTER_SIGN_REQUESTS = original_values["FMCSA_ADAPTER_SIGN_REQUESTS"]
        sim.FMCSA_ADAPTER_REQUEST_SIGNING_KEYS = original_values[
            "FMCSA_ADAPTER_REQUEST_SIGNING_KEYS"
        ]
        sim.FMCSA_ADAPTER_REQUEST_SIGNING_ACTIVE_KEY_ID = original_values[
            "FMCSA_ADAPTER_REQUEST_SIGNING_ACTIVE_KEY_ID"
        ]
        sim.FMCSA_ADAPTER_REQUEST_SIGNING_KEY = original_values[
            "FMCSA_ADAPTER_REQUEST_SIGNING_KEY"
        ]


if __name__ == "__main__":
    raise SystemExit(main())
