#!/usr/bin/env python3
"""
FAXP v0.1 MVP simulation

Minimal, self-contained simulation of autonomous freight booking between:
- Broker Agent
- Carrier Agent
"""

from datetime import date, datetime, timedelta, timezone
from uuid import uuid4
import argparse
import base64
import hashlib
import hmac
import json
import os
import random
import re
import shlex
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_CARRIER_FINDER_PATH = "/Users/zglitch009/projects/logistics-ai/carrier-finder"
DEBUG_MODE = os.getenv("FAXP_DEBUG", "0") == "1"
SENSITIVE_KEYS = {"token", "stderr", "Signature"}
APP_MODE = os.getenv("FAXP_APP_MODE", "local").strip().lower()
NON_LOCAL_MODE = APP_MODE not in {"local", "dev", "development"}
FMCSA_WEBKEY = os.getenv("FAXP_FMCSA_WEBKEY", "").strip()
FMCSA_CLIENT_SECRET = os.getenv("FAXP_FMCSA_CLIENT_SECRET", "").strip()
FMCSA_API_BASE_URL = os.getenv(
    "FAXP_FMCSA_API_BASE_URL", "https://mobile.fmcsa.dot.gov/qc/services"
).strip()
FMCSA_API_TIMEOUT_SECONDS_RAW = os.getenv("FAXP_FMCSA_API_TIMEOUT_SECONDS", "12").strip()
FMCSA_LOG_UNKNOWN_KEYS_RAW = os.getenv("FAXP_FMCSA_LOG_UNKNOWN_KEYS", "1").strip()
FMCSA_EXPECTED_TOP_LEVEL_KEYS_RAW = os.getenv(
    "FAXP_FMCSA_EXPECTED_TOP_LEVEL_KEYS",
    "content,result,data,error,errors",
).strip()
VERIFICATION_POLICY_PROFILE_ID = os.getenv(
    "FAXP_VERIFICATION_POLICY_PROFILE_ID",
    "US_FMCSA_BALANCED_V1",
).strip()
DEFAULT_RISK_TIER_RAW = os.getenv("FAXP_DEFAULT_RISK_TIER", "1").strip()
try:
    DEFAULT_RISK_TIER = int(DEFAULT_RISK_TIER_RAW)
except ValueError:
    DEFAULT_RISK_TIER = 1
FMCSA_ADAPTER_BASE_URL = os.getenv("FAXP_FMCSA_ADAPTER_BASE_URL", "").strip()
FMCSA_ADAPTER_AUTH_TOKEN = os.getenv("FAXP_FMCSA_ADAPTER_AUTH_TOKEN", "").strip()
FMCSA_ADAPTER_TIMEOUT_SECONDS_RAW = os.getenv("FAXP_FMCSA_ADAPTER_TIMEOUT_SECONDS", "10").strip()
FMCSA_ADAPTER_REQUIRE_SIGNED_WRAPPER_RAW = os.getenv(
    "FAXP_FMCSA_ADAPTER_REQUIRE_SIGNED_WRAPPER",
    "1",
).strip()
FMCSA_ADAPTER_SIGN_REQUESTS_RAW = os.getenv("FAXP_FMCSA_ADAPTER_SIGN_REQUESTS", "1").strip()
FMCSA_ADAPTER_REQUEST_SIGNING_KEYS_RAW = os.getenv(
    "FAXP_FMCSA_ADAPTER_REQUEST_SIGNING_KEYS",
    "",
).strip()
FMCSA_ADAPTER_REQUEST_SIGNING_ACTIVE_KEY_ID = os.getenv(
    "FAXP_FMCSA_ADAPTER_REQUEST_SIGNING_ACTIVE_KEY_ID",
    "",
).strip()

LEGACY_MESSAGE_SIGNING_KEY = os.getenv("FAXP_MESSAGE_SIGNING_KEY", "").encode("utf-8")
LEGACY_VERIFIER_SIGNING_KEY = os.getenv("FAXP_VERIFIER_SIGNING_KEY", "").encode("utf-8")
MESSAGE_SIGNING_KEYS_RAW = os.getenv("FAXP_MESSAGE_SIGNING_KEYS", "").strip()
VERIFIER_SIGNING_KEYS_RAW = os.getenv("FAXP_VERIFIER_SIGNING_KEYS", "").strip()
MESSAGE_SIGNING_ACTIVE_KEY_ID = os.getenv("FAXP_MESSAGE_SIGNING_ACTIVE_KEY_ID", "").strip()
VERIFIER_SIGNING_ACTIVE_KEY_ID = os.getenv("FAXP_VERIFIER_SIGNING_ACTIVE_KEY_ID", "").strip()
VERIFIER_SIGNATURE_SCHEME = (
    os.getenv("FAXP_VERIFIER_SIGNATURE_SCHEME", "HMAC_SHA256").strip().upper()
)
VERIFIER_ED25519_PRIVATE_KEYS_RAW = os.getenv(
    "FAXP_VERIFIER_ED25519_PRIVATE_KEYS", ""
).strip()
VERIFIER_ED25519_PUBLIC_KEYS_RAW = os.getenv(
    "FAXP_VERIFIER_ED25519_PUBLIC_KEYS", ""
).strip()
VERIFIER_ED25519_ACTIVE_KEY_ID = os.getenv(
    "FAXP_VERIFIER_ED25519_ACTIVE_KEY_ID", ""
).strip()
REQUIRE_SIGNED_VERIFIER = os.getenv("FAXP_REQUIRE_SIGNED_VERIFIER", "1") == "1"
MESSAGE_TTL_SECONDS = int(os.getenv("FAXP_MESSAGE_TTL_SECONDS", "300"))
MAX_CLOCK_SKEW_SECONDS = int(os.getenv("FAXP_MAX_CLOCK_SKEW_SECONDS", "30"))
SIGNATURE_SCHEME = os.getenv("FAXP_SIGNATURE_SCHEME", "HMAC_SHA256").strip().upper()
REPLAY_DB_PATH = os.getenv(
    "FAXP_REPLAY_DB_PATH",
    os.path.join(tempfile.gettempdir(), "faxp_replay.db"),
)
REPLAY_RETENTION_SECONDS = int(os.getenv("FAXP_REPLAY_RETENTION_SECONDS", "86400"))
MAX_TRACKED_ENTITY_STATES = int(os.getenv("FAXP_MAX_TRACKED_ENTITY_STATES", "50000"))
IMMUTABLE_AUDIT_PATH = os.getenv("FAXP_IMMUTABLE_AUDIT_PATH", "").strip()
IMMUTABLE_AUDIT_URL = os.getenv("FAXP_IMMUTABLE_AUDIT_URL", "").strip()
REQUIRE_IMMUTABLE_AUDIT = os.getenv("FAXP_REQUIRE_IMMUTABLE_AUDIT", "0") == "1"
REQUIRE_EXTERNAL_SECRET_MANAGER = (
    os.getenv("FAXP_REQUIRE_EXTERNAL_SECRET_MANAGER", "0") == "1"
)
SECRET_SOURCE = os.getenv("FAXP_SECRET_SOURCE", "env").strip().lower()
ENFORCE_DUAL_CONTROL = os.getenv("FAXP_ENFORCE_DUAL_CONTROL", "0") == "1"
KEY_CHANGE_APPROVALS_RAW = os.getenv("FAXP_KEY_CHANGE_APPROVALS", "").strip()
MAX_ACTIVE_KEY_AGE_DAYS = int(os.getenv("FAXP_MAX_ACTIVE_KEY_AGE_DAYS", "30"))
MESSAGE_ACTIVE_KEY_ISSUED_AT = os.getenv("FAXP_MESSAGE_ACTIVE_KEY_ISSUED_AT", "").strip()
VERIFIER_ACTIVE_KEY_ISSUED_AT = os.getenv("FAXP_VERIFIER_ACTIVE_KEY_ISSUED_AT", "").strip()
AGENT_KEY_REGISTRY_RAW = os.getenv("FAXP_AGENT_KEY_REGISTRY", "").strip()
AGENT_KEY_REGISTRY_FILE = os.getenv("FAXP_AGENT_KEY_REGISTRY_FILE", "").strip()
EXTERNAL_SECRET_BUNDLE_FILE = os.getenv("FAXP_EXTERNAL_SECRET_BUNDLE_FILE", "").strip()
EXTERNAL_SECRET_BUNDLE_COMMAND = os.getenv("FAXP_EXTERNAL_SECRET_BUNDLE_COMMAND", "").strip()
EXTERNAL_SECRET_BUNDLE_TIMEOUT_SECONDS = int(
    os.getenv("FAXP_EXTERNAL_SECRET_BUNDLE_TIMEOUT_SECONDS", "8")
)
MAX_STRING_LENGTH = int(os.getenv("FAXP_MAX_STRING_LENGTH", "256"))
MAX_AUDIT_ENTRIES = int(os.getenv("FAXP_MAX_AUDIT_ENTRIES", "20000"))
AUDIT_LOG_PATH = os.getenv(
    "FAXP_AUDIT_LOG_PATH",
    os.path.join(tempfile.gettempdir(), "faxp_audit.log"),
)
VERIFIER_REPOSITORIES_FILE = os.path.join(
    DEFAULT_CARRIER_FINDER_PATH, "backend", "app", "repositories.py"
)
EXPECTED_REPO_HASH = os.getenv("FAXP_CARRIER_FINDER_REPOSITORIES_SHA256", "").strip().lower()


def _build_allowed_carrier_finder_paths():
    configured = os.getenv("FAXP_ALLOWED_CARRIER_FINDER_PATHS", "")
    paths = set()
    for raw in configured.split(":"):
        candidate = raw.strip()
        if candidate:
            paths.add(os.path.realpath(candidate))
    paths.add(os.path.realpath(DEFAULT_CARRIER_FINDER_PATH))
    return paths


ALLOWED_CARRIER_FINDER_PATHS = _build_allowed_carrier_finder_paths()
SUPPORTED_SIGNATURE_SCHEMES = {"HMAC_SHA256", "ED25519"}
ALLOWED_EXTERNAL_SECRET_KEYS = {
    "FAXP_SIGNATURE_SCHEME",
    "FAXP_MESSAGE_SIGNING_KEY",
    "FAXP_MESSAGE_SIGNING_KEYS",
    "FAXP_MESSAGE_SIGNING_ACTIVE_KEY_ID",
    "FAXP_MESSAGE_ACTIVE_KEY_ISSUED_AT",
    "FAXP_VERIFIER_SIGNATURE_SCHEME",
    "FAXP_VERIFIER_SIGNING_KEY",
    "FAXP_VERIFIER_SIGNING_KEYS",
    "FAXP_VERIFIER_SIGNING_ACTIVE_KEY_ID",
    "FAXP_VERIFIER_ACTIVE_KEY_ISSUED_AT",
    "FAXP_VERIFIER_ED25519_PRIVATE_KEYS",
    "FAXP_VERIFIER_ED25519_PUBLIC_KEYS",
    "FAXP_VERIFIER_ED25519_ACTIVE_KEY_ID",
    "FAXP_AGENT_KEY_REGISTRY",
    "FAXP_AGENT_KEY_REGISTRY_FILE",
    "FAXP_FMCSA_WEBKEY",
    "FAXP_FMCSA_CLIENT_SECRET",
    "FAXP_FMCSA_API_BASE_URL",
    "FAXP_FMCSA_API_TIMEOUT_SECONDS",
    "FAXP_FMCSA_LOG_UNKNOWN_KEYS",
    "FAXP_FMCSA_EXPECTED_TOP_LEVEL_KEYS",
    "FAXP_FMCSA_ADAPTER_BASE_URL",
    "FAXP_FMCSA_ADAPTER_AUTH_TOKEN",
    "FAXP_FMCSA_ADAPTER_TIMEOUT_SECONDS",
    "FAXP_FMCSA_ADAPTER_REQUIRE_SIGNED_WRAPPER",
    "FAXP_FMCSA_ADAPTER_SIGN_REQUESTS",
    "FAXP_FMCSA_ADAPTER_REQUEST_SIGNING_KEYS",
    "FAXP_FMCSA_ADAPTER_REQUEST_SIGNING_ACTIVE_KEY_ID",
}
ROUTE_POLICY = {
    "NewLoad": {("Broker", "Carrier")},
    "LoadSearch": {("Carrier", "Broker")},
    "NewTruck": {("Carrier", "Broker")},
    "TruckSearch": {("Broker", "Carrier")},
    "BidRequest": {("Carrier", "Broker"), ("Broker", "Carrier")},
    "BidResponse": {("Broker", "Carrier"), ("Carrier", "Broker")},
    "ExecutionReport": {("Broker", "Carrier")},
    "AmendRequest": {("Broker", "Carrier")},
}
SEEN_MESSAGE_IDS = set()
SEEN_NONCES = set()
LAST_AUDIT_HASH = ""
REPLAY_DB_LOCK = threading.Lock()
STATE_LOCK = threading.Lock()
FLOW_STATE = {"load": "START", "truck": "START"}
FMCSA_DRIFT_WARNED_SIGNATURES = set()
CURRENT_RUN_ID = ""


def _normalize_external_secret_bundle(raw_bundle):
    if not isinstance(raw_bundle, dict):
        raise RuntimeError("External secret bundle must be a JSON object.")
    normalized = {}
    for key, value in raw_bundle.items():
        key_name = str(key).strip()
        if key_name not in ALLOWED_EXTERNAL_SECRET_KEYS:
            continue
        if value is None:
            continue
        if isinstance(value, (dict, list)):
            normalized[key_name] = json.dumps(value, sort_keys=True, separators=(",", ":"))
        else:
            normalized[key_name] = str(value)
    return normalized


def _load_external_secret_bundle():
    if SECRET_SOURCE not in {"kms", "hsm"}:
        return {}

    if EXTERNAL_SECRET_BUNDLE_FILE:
        with open(EXTERNAL_SECRET_BUNDLE_FILE, "r", encoding="utf-8") as handle:
            return _normalize_external_secret_bundle(json.load(handle))

    if EXTERNAL_SECRET_BUNDLE_COMMAND:
        command = shlex.split(EXTERNAL_SECRET_BUNDLE_COMMAND)
        if not command:
            raise RuntimeError("FAXP_EXTERNAL_SECRET_BUNDLE_COMMAND is empty.")
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=EXTERNAL_SECRET_BUNDLE_TIMEOUT_SECONDS,
        )
        if completed.returncode != 0:
            raise RuntimeError("External secret bundle command failed.")
        output_lines = [line for line in (completed.stdout or "").splitlines() if line.strip()]
        if not output_lines:
            raise RuntimeError("External secret bundle command returned no output.")
        try:
            bundle = json.loads(output_lines[-1])
        except json.JSONDecodeError as exc:
            raise RuntimeError("External secret bundle output is not valid JSON.") from exc
        return _normalize_external_secret_bundle(bundle)

    if REQUIRE_EXTERNAL_SECRET_MANAGER:
        has_preloaded_material = any(
            [
                bool(MESSAGE_SIGNING_KEYS_RAW),
                bool(VERIFIER_SIGNING_KEYS_RAW),
                bool(VERIFIER_ED25519_PRIVATE_KEYS_RAW),
                bool(VERIFIER_ED25519_PUBLIC_KEYS_RAW),
                bool(AGENT_KEY_REGISTRY_RAW),
                bool(AGENT_KEY_REGISTRY_FILE),
                bool(LEGACY_MESSAGE_SIGNING_KEY),
                bool(LEGACY_VERIFIER_SIGNING_KEY),
            ]
        )
        if not has_preloaded_material:
            raise RuntimeError(
                "FAXP_SECRET_SOURCE is kms/hsm but no external bundle source or preloaded key material is configured."
            )
    return {}


EXTERNAL_SECRET_OVERRIDES = _load_external_secret_bundle()


def _override_secret_value(key_name, current_value):
    if key_name in EXTERNAL_SECRET_OVERRIDES and EXTERNAL_SECRET_OVERRIDES[key_name] != "":
        return EXTERNAL_SECRET_OVERRIDES[key_name]
    return current_value


LEGACY_MESSAGE_SIGNING_KEY = _override_secret_value(
    "FAXP_MESSAGE_SIGNING_KEY",
    LEGACY_MESSAGE_SIGNING_KEY.decode("utf-8"),
).encode("utf-8")
LEGACY_VERIFIER_SIGNING_KEY = _override_secret_value(
    "FAXP_VERIFIER_SIGNING_KEY",
    LEGACY_VERIFIER_SIGNING_KEY.decode("utf-8"),
).encode("utf-8")
MESSAGE_SIGNING_KEYS_RAW = _override_secret_value(
    "FAXP_MESSAGE_SIGNING_KEYS", MESSAGE_SIGNING_KEYS_RAW
)
VERIFIER_SIGNING_KEYS_RAW = _override_secret_value(
    "FAXP_VERIFIER_SIGNING_KEYS", VERIFIER_SIGNING_KEYS_RAW
)
MESSAGE_SIGNING_ACTIVE_KEY_ID = _override_secret_value(
    "FAXP_MESSAGE_SIGNING_ACTIVE_KEY_ID", MESSAGE_SIGNING_ACTIVE_KEY_ID
)
VERIFIER_SIGNING_ACTIVE_KEY_ID = _override_secret_value(
    "FAXP_VERIFIER_SIGNING_ACTIVE_KEY_ID", VERIFIER_SIGNING_ACTIVE_KEY_ID
)
VERIFIER_SIGNATURE_SCHEME = _override_secret_value(
    "FAXP_VERIFIER_SIGNATURE_SCHEME", VERIFIER_SIGNATURE_SCHEME
).upper()
VERIFIER_ED25519_PRIVATE_KEYS_RAW = _override_secret_value(
    "FAXP_VERIFIER_ED25519_PRIVATE_KEYS", VERIFIER_ED25519_PRIVATE_KEYS_RAW
)
VERIFIER_ED25519_PUBLIC_KEYS_RAW = _override_secret_value(
    "FAXP_VERIFIER_ED25519_PUBLIC_KEYS", VERIFIER_ED25519_PUBLIC_KEYS_RAW
)
VERIFIER_ED25519_ACTIVE_KEY_ID = _override_secret_value(
    "FAXP_VERIFIER_ED25519_ACTIVE_KEY_ID", VERIFIER_ED25519_ACTIVE_KEY_ID
)
SIGNATURE_SCHEME = _override_secret_value(
    "FAXP_SIGNATURE_SCHEME", SIGNATURE_SCHEME
).upper()
MESSAGE_ACTIVE_KEY_ISSUED_AT = _override_secret_value(
    "FAXP_MESSAGE_ACTIVE_KEY_ISSUED_AT", MESSAGE_ACTIVE_KEY_ISSUED_AT
)
VERIFIER_ACTIVE_KEY_ISSUED_AT = _override_secret_value(
    "FAXP_VERIFIER_ACTIVE_KEY_ISSUED_AT", VERIFIER_ACTIVE_KEY_ISSUED_AT
)
AGENT_KEY_REGISTRY_RAW = _override_secret_value("FAXP_AGENT_KEY_REGISTRY", AGENT_KEY_REGISTRY_RAW)
AGENT_KEY_REGISTRY_FILE = _override_secret_value(
    "FAXP_AGENT_KEY_REGISTRY_FILE", AGENT_KEY_REGISTRY_FILE
)
FMCSA_WEBKEY = _override_secret_value("FAXP_FMCSA_WEBKEY", FMCSA_WEBKEY).strip()
FMCSA_CLIENT_SECRET = _override_secret_value(
    "FAXP_FMCSA_CLIENT_SECRET", FMCSA_CLIENT_SECRET
).strip()
FMCSA_API_BASE_URL = _override_secret_value(
    "FAXP_FMCSA_API_BASE_URL", FMCSA_API_BASE_URL
).strip()
try:
    FMCSA_API_TIMEOUT_SECONDS = int(
        _override_secret_value(
            "FAXP_FMCSA_API_TIMEOUT_SECONDS",
            FMCSA_API_TIMEOUT_SECONDS_RAW,
        )
    )
except ValueError:
    FMCSA_API_TIMEOUT_SECONDS = 12
FMCSA_API_TIMEOUT_SECONDS = max(3, min(30, FMCSA_API_TIMEOUT_SECONDS))
FMCSA_LOG_UNKNOWN_KEYS_RAW = _override_secret_value(
    "FAXP_FMCSA_LOG_UNKNOWN_KEYS",
    FMCSA_LOG_UNKNOWN_KEYS_RAW,
).strip()
FMCSA_EXPECTED_TOP_LEVEL_KEYS_RAW = _override_secret_value(
    "FAXP_FMCSA_EXPECTED_TOP_LEVEL_KEYS",
    FMCSA_EXPECTED_TOP_LEVEL_KEYS_RAW,
).strip()
FMCSA_ADAPTER_BASE_URL = _override_secret_value(
    "FAXP_FMCSA_ADAPTER_BASE_URL",
    FMCSA_ADAPTER_BASE_URL,
).strip()
FMCSA_ADAPTER_AUTH_TOKEN = _override_secret_value(
    "FAXP_FMCSA_ADAPTER_AUTH_TOKEN",
    FMCSA_ADAPTER_AUTH_TOKEN,
).strip()
FMCSA_ADAPTER_REQUIRE_SIGNED_WRAPPER_RAW = _override_secret_value(
    "FAXP_FMCSA_ADAPTER_REQUIRE_SIGNED_WRAPPER",
    FMCSA_ADAPTER_REQUIRE_SIGNED_WRAPPER_RAW,
).strip()
FMCSA_ADAPTER_SIGN_REQUESTS_RAW = _override_secret_value(
    "FAXP_FMCSA_ADAPTER_SIGN_REQUESTS",
    FMCSA_ADAPTER_SIGN_REQUESTS_RAW,
).strip()
FMCSA_ADAPTER_REQUEST_SIGNING_KEYS_RAW = _override_secret_value(
    "FAXP_FMCSA_ADAPTER_REQUEST_SIGNING_KEYS",
    FMCSA_ADAPTER_REQUEST_SIGNING_KEYS_RAW,
).strip()
FMCSA_ADAPTER_REQUEST_SIGNING_ACTIVE_KEY_ID = _override_secret_value(
    "FAXP_FMCSA_ADAPTER_REQUEST_SIGNING_ACTIVE_KEY_ID",
    FMCSA_ADAPTER_REQUEST_SIGNING_ACTIVE_KEY_ID,
).strip()
try:
    FMCSA_ADAPTER_TIMEOUT_SECONDS = int(
        _override_secret_value(
            "FAXP_FMCSA_ADAPTER_TIMEOUT_SECONDS",
            FMCSA_ADAPTER_TIMEOUT_SECONDS_RAW,
        )
    )
except ValueError:
    FMCSA_ADAPTER_TIMEOUT_SECONDS = 10
FMCSA_ADAPTER_TIMEOUT_SECONDS = max(3, min(30, FMCSA_ADAPTER_TIMEOUT_SECONDS))


def _is_truthy(value):
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "y"}


def _parse_expected_fmcsa_top_level_keys(raw_value):
    keys = {
        str(part).strip().lower()
        for part in str(raw_value or "").split(",")
        if str(part).strip()
    }
    return keys or {"content", "result", "data", "error", "errors"}


FMCSA_LOG_UNKNOWN_KEYS = _is_truthy(FMCSA_LOG_UNKNOWN_KEYS_RAW)
FMCSA_EXPECTED_TOP_LEVEL_KEYS = _parse_expected_fmcsa_top_level_keys(
    FMCSA_EXPECTED_TOP_LEVEL_KEYS_RAW
)
FMCSA_ADAPTER_REQUIRE_SIGNED_WRAPPER = _is_truthy(
    FMCSA_ADAPTER_REQUIRE_SIGNED_WRAPPER_RAW
)
FMCSA_ADAPTER_SIGN_REQUESTS = _is_truthy(FMCSA_ADAPTER_SIGN_REQUESTS_RAW)


def _load_agent_key_registry():
    registry_text = AGENT_KEY_REGISTRY_RAW
    if not registry_text and AGENT_KEY_REGISTRY_FILE:
        with open(AGENT_KEY_REGISTRY_FILE, "r", encoding="utf-8") as handle:
            registry_text = handle.read()
    if not registry_text:
        return {}
    try:
        raw_registry = json.loads(registry_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("FAXP agent key registry is not valid JSON.") from exc
    if not isinstance(raw_registry, dict):
        raise RuntimeError("FAXP agent key registry must be a JSON object.")

    normalized = {}
    for agent_name, config in raw_registry.items():
        if not isinstance(config, dict):
            raise RuntimeError(f"Agent key registry entry for '{agent_name}' must be an object.")
        active_kid = str(config.get("active_kid") or "").strip()
        private_keys = {}
        public_keys = {}
        metadata = {}

        if isinstance(config.get("private_keys"), dict):
            for kid, path in config["private_keys"].items():
                private_keys[str(kid).strip()] = os.path.realpath(str(path))
        if isinstance(config.get("public_keys"), dict):
            for kid, path in config["public_keys"].items():
                public_keys[str(kid).strip()] = os.path.realpath(str(path))
        if isinstance(config.get("key_metadata"), dict):
            for kid, details in config["key_metadata"].items():
                if isinstance(details, dict):
                    metadata[str(kid).strip()] = details

        # Alternative compact format:
        # {"keys": {"kid1": {"private_key_path": "...", "public_key_path": "...", "issued_at": "..."}}}
        if isinstance(config.get("keys"), dict):
            for kid, details in config["keys"].items():
                key_id = str(kid).strip()
                if not isinstance(details, dict):
                    continue
                priv_path = details.get("private_key_path")
                pub_path = details.get("public_key_path")
                if priv_path:
                    private_keys[key_id] = os.path.realpath(str(priv_path))
                if pub_path:
                    public_keys[key_id] = os.path.realpath(str(pub_path))
                metadata[key_id] = details

        normalized[agent_name] = {
            "active_kid": active_kid,
            "private_keys": private_keys,
            "public_keys": public_keys,
            "key_metadata": metadata,
        }
    return normalized


AGENT_KEY_REGISTRY = _load_agent_key_registry()


class FaxpProtocol:
    """Lightweight protocol constants and examples."""

    NAME = "FAXP"
    VERSION = "0.1.1"

    MESSAGE_TYPES = [
        "NewLoad",
        "LoadSearch",
        "NewTruck",
        "TruckSearch",
        "BidRequest",
        "BidResponse",
        "ExecutionReport",
        "AmendRequest",
    ]

    @staticmethod
    def amend_request_example(load_id):
        # This message type exists in the protocol but is not used in this happy path.
        return {
            "LoadID": load_id,
            "AmendmentType": "UpdateRate",
            "ReasonCode": "MarketShift",
            "NewRate": 2.75,
            "AmendmentNotes": "Example only for MVP visibility",
        }


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def sign_payload(payload, key):
    if not key:
        return None
    return hmac.new(key, canonical_json(payload).encode("utf-8"), hashlib.sha256).hexdigest()


def verify_signature(payload, signature, key):
    if not key or not signature:
        return False
    expected = sign_payload(payload, key)
    return bool(expected) and hmac.compare_digest(expected, signature)


def _build_adapter_request_signature(method, path, timestamp_text, nonce, body_bytes, key):
    body_hash = hashlib.sha256(body_bytes).hexdigest()
    signing_payload = "\n".join(
        [
            str(method or "").upper(),
            str(path or "/"),
            str(timestamp_text or ""),
            str(nonce or ""),
            body_hash,
        ]
    )
    return hmac.new(key, signing_payload.encode("utf-8"), hashlib.sha256).hexdigest()


def _run_openssl(command):
    completed = subprocess.run(
        command,
        capture_output=True,
        text=False,
        check=False,
        timeout=10,
    )
    return completed


def _ed25519_sign_bytes(message_bytes, private_key_path):
    msg_path = ""
    sig_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False) as msg_file:
            msg_file.write(message_bytes)
            msg_path = msg_file.name
        with tempfile.NamedTemporaryFile(delete=False) as sig_file:
            sig_path = sig_file.name
        sign_commands = [
            [
                "openssl",
                "pkeyutl",
                "-sign",
                "-inkey",
                private_key_path,
                "-in",
                msg_path,
                "-out",
                sig_path,
            ],
            [
                "openssl",
                "pkeyutl",
                "-sign",
                "-rawin",
                "-inkey",
                private_key_path,
                "-in",
                msg_path,
                "-out",
                sig_path,
            ],
        ]
        completed = None
        for command in sign_commands:
            completed = _run_openssl(command)
            if completed.returncode == 0:
                break
        if not completed or completed.returncode != 0:
            return None
        with open(sig_path, "rb") as handle:
            return handle.read()
    finally:
        for path in [msg_path, sig_path]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass


def _ed25519_verify_bytes(message_bytes, signature_bytes, public_key_path):
    msg_path = ""
    sig_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False) as msg_file:
            msg_file.write(message_bytes)
            msg_path = msg_file.name
        with tempfile.NamedTemporaryFile(delete=False) as sig_file:
            sig_file.write(signature_bytes)
            sig_path = sig_file.name
        verify_commands = [
            [
                "openssl",
                "pkeyutl",
                "-verify",
                "-pubin",
                "-inkey",
                public_key_path,
                "-sigfile",
                sig_path,
                "-in",
                msg_path,
            ],
            [
                "openssl",
                "pkeyutl",
                "-verify",
                "-rawin",
                "-pubin",
                "-inkey",
                public_key_path,
                "-sigfile",
                sig_path,
                "-in",
                msg_path,
            ],
        ]
        for command in verify_commands:
            completed = _run_openssl(command)
            if completed.returncode == 0:
                return True
        return False
    finally:
        for path in [msg_path, sig_path]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass


def _load_key_material_for_agent(agent_name):
    config = AGENT_KEY_REGISTRY.get(agent_name, {})
    if not isinstance(config, dict):
        return {"active_kid": "", "private_keys": {}, "public_keys": {}, "key_metadata": {}}
    return {
        "active_kid": str(config.get("active_kid", "")).strip(),
        "private_keys": dict(config.get("private_keys", {})),
        "public_keys": dict(config.get("public_keys", {})),
        "key_metadata": dict(config.get("key_metadata", {})),
    }


def _sign_asymmetric(envelope):
    signer = envelope.get("From")
    material = _load_key_material_for_agent(signer)
    kid = material["active_kid"]
    private_key_path = material["private_keys"].get(kid)
    if not kid or not private_key_path:
        if NON_LOCAL_MODE:
            raise RuntimeError(f"Missing active ED25519 private key for sender '{signer}'.")
        return envelope
    envelope["SignatureAlgorithm"] = "ED25519"
    envelope["SignatureKeyID"] = kid
    payload = {k: v for k, v in envelope.items() if k != "Signature"}
    signature_bytes = _ed25519_sign_bytes(
        canonical_json(payload).encode("utf-8"),
        private_key_path,
    )
    if not signature_bytes:
        raise RuntimeError("Failed to sign envelope with ED25519 key.")
    envelope["Signature"] = base64.b64encode(signature_bytes).decode("ascii")
    return envelope


def _verify_asymmetric(envelope):
    signer = envelope.get("From")
    material = _load_key_material_for_agent(signer)
    signature_key_id = envelope.get("SignatureKeyID")
    if not signature_key_id:
        return False
    public_key_path = material["public_keys"].get(signature_key_id)
    if not public_key_path:
        return False
    signature = envelope.get("Signature")
    if not signature or not isinstance(signature, str):
        return False
    try:
        signature_bytes = base64.b64decode(signature.encode("ascii"), validate=True)
    except Exception:
        return False
    payload = {k: v for k, v in envelope.items() if k != "Signature"}
    return _ed25519_verify_bytes(
        canonical_json(payload).encode("utf-8"),
        signature_bytes,
        public_key_path,
    )


def _ship_immutable_audit_event(event):
    sent = False
    payload = canonical_json(event).encode("utf-8")
    if IMMUTABLE_AUDIT_PATH:
        with open(IMMUTABLE_AUDIT_PATH, "a", encoding="utf-8") as handle:
            handle.write(canonical_json(event) + "\n")
        sent = True
    if IMMUTABLE_AUDIT_URL:
        request = urllib.request.Request(
            IMMUTABLE_AUDIT_URL,
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=5):
            pass
        sent = True
    return sent


def _parse_key_ring(raw_pairs, legacy_key, legacy_kid):
    key_ring = {}
    if raw_pairs:
        for raw_entry in raw_pairs.split(","):
            entry = raw_entry.strip()
            if not entry:
                continue
            if ":" in entry:
                kid, key_value = entry.split(":", 1)
            elif "=" in entry:
                kid, key_value = entry.split("=", 1)
            else:
                raise RuntimeError(
                    "Key ring entries must use 'kid:key' or 'kid=key' format."
                )
            kid = kid.strip()
            key_value = key_value.strip()
            if not kid or not key_value:
                raise RuntimeError("Key ring contains an empty key ID or key value.")
            key_ring[kid] = key_value.encode("utf-8")
    if legacy_key:
        key_ring.setdefault(legacy_kid, legacy_key)
    return key_ring


def _parse_path_key_ring(raw_pairs, context):
    key_ring = {}
    if not raw_pairs:
        return key_ring
    for raw_entry in raw_pairs.split(","):
        entry = raw_entry.strip()
        if not entry:
            continue
        if ":" in entry:
            kid, path_value = entry.split(":", 1)
        elif "=" in entry:
            kid, path_value = entry.split("=", 1)
        else:
            raise RuntimeError(
                f"{context} entries must use 'kid:path' or 'kid=path' format."
            )
        kid = kid.strip()
        path_value = path_value.strip()
        if not kid or not path_value:
            raise RuntimeError(f"{context} contains an empty key ID or path.")
        key_ring[kid] = os.path.realpath(path_value)
    return key_ring


def _resolve_active_key_id(key_ring, configured_key_id, context_name):
    if configured_key_id:
        if configured_key_id not in key_ring:
            raise RuntimeError(
                f"{context_name} active key ID '{configured_key_id}' not found in configured key ring."
            )
        return configured_key_id
    if not key_ring:
        return ""
    return next(iter(key_ring))


def _verify_with_key_ring(payload, signature, signature_key_id, key_ring):
    if not signature or not key_ring:
        return False
    if signature_key_id:
        return verify_signature(payload, signature, key_ring.get(signature_key_id))
    for key in key_ring.values():
        if verify_signature(payload, signature, key):
            return True
    return False


def _verify_ed25519_with_public_key_ring(payload, signature, signature_key_id, public_key_ring):
    if not signature_key_id or signature_key_id not in public_key_ring:
        return False
    if not isinstance(signature, str):
        return False
    try:
        signature_bytes = base64.b64decode(signature.encode("ascii"), validate=True)
    except Exception:
        return False
    return _ed25519_verify_bytes(
        canonical_json(payload).encode("utf-8"),
        signature_bytes,
        public_key_ring[signature_key_id],
    )


def _build_verifier_attestation(payload):
    """Sign a verification payload and return attestation metadata."""
    if VERIFIER_SIGNATURE_SCHEME == "HMAC_SHA256":
        key_id = VERIFIER_SIGNING_ACTIVE_KEY_ID
        key = VERIFIER_SIGNING_KEYS.get(key_id, b"")
        if not key_id:
            raise RuntimeError("Missing verifier HMAC key ID.")
        if not key:
            raise RuntimeError("Missing verifier HMAC key material.")
        signature = sign_payload(payload, key)
        if not signature:
            raise RuntimeError("Failed to produce verifier HMAC signature.")
        return {"alg": "HMAC_SHA256", "kid": key_id, "sig": signature}

    if VERIFIER_SIGNATURE_SCHEME == "ED25519":
        key_id = VERIFIER_ED25519_ACTIVE_KEY_ID
        private_key_path = VERIFIER_ED25519_PRIVATE_KEYS.get(key_id, "")
        if not key_id:
            raise RuntimeError("Missing verifier ED25519 key ID.")
        if not private_key_path:
            raise RuntimeError("Missing verifier ED25519 private key path.")
        signature_bytes = _ed25519_sign_bytes(
            canonical_json(payload).encode("utf-8"),
            private_key_path,
        )
        if not signature_bytes:
            raise RuntimeError("Failed to produce verifier ED25519 signature.")
        return {
            "alg": "ED25519",
            "kid": key_id,
            "sig": base64.b64encode(signature_bytes).decode("ascii"),
        }

    raise RuntimeError(
        f"Unsupported verifier signature scheme for attestation: {VERIFIER_SIGNATURE_SCHEME}."
    )


MESSAGE_SIGNING_KEYS = _parse_key_ring(
    MESSAGE_SIGNING_KEYS_RAW, LEGACY_MESSAGE_SIGNING_KEY, "legacy-msg"
)
VERIFIER_SIGNING_KEYS = _parse_key_ring(
    VERIFIER_SIGNING_KEYS_RAW, LEGACY_VERIFIER_SIGNING_KEY, "legacy-verifier"
)
FMCSA_ADAPTER_REQUEST_SIGNING_KEYS = _parse_key_ring(
    FMCSA_ADAPTER_REQUEST_SIGNING_KEYS_RAW,
    b"",
    "legacy-adapter-request",
)
VERIFIER_ED25519_PRIVATE_KEYS = _parse_path_key_ring(
    VERIFIER_ED25519_PRIVATE_KEYS_RAW,
    "FAXP_VERIFIER_ED25519_PRIVATE_KEYS",
)
VERIFIER_ED25519_PUBLIC_KEYS = _parse_path_key_ring(
    VERIFIER_ED25519_PUBLIC_KEYS_RAW,
    "FAXP_VERIFIER_ED25519_PUBLIC_KEYS",
)
MESSAGE_SIGNING_ACTIVE_KEY_ID = _resolve_active_key_id(
    MESSAGE_SIGNING_KEYS, MESSAGE_SIGNING_ACTIVE_KEY_ID, "message signing"
)
VERIFIER_SIGNING_ACTIVE_KEY_ID = _resolve_active_key_id(
    VERIFIER_SIGNING_KEYS, VERIFIER_SIGNING_ACTIVE_KEY_ID, "verifier signing"
)
FMCSA_ADAPTER_REQUEST_SIGNING_ACTIVE_KEY_ID = _resolve_active_key_id(
    FMCSA_ADAPTER_REQUEST_SIGNING_KEYS,
    FMCSA_ADAPTER_REQUEST_SIGNING_ACTIVE_KEY_ID,
    "FMCSA adapter request signing",
)
VERIFIER_ED25519_ACTIVE_KEY_ID = _resolve_active_key_id(
    VERIFIER_ED25519_PUBLIC_KEYS or VERIFIER_ED25519_PRIVATE_KEYS,
    VERIFIER_ED25519_ACTIVE_KEY_ID,
    "verifier ED25519 signing",
)
MESSAGE_SIGNING_KEY = MESSAGE_SIGNING_KEYS.get(MESSAGE_SIGNING_ACTIVE_KEY_ID, b"")
VERIFIER_SIGNING_KEY = VERIFIER_SIGNING_KEYS.get(VERIFIER_SIGNING_ACTIVE_KEY_ID, b"")
FMCSA_ADAPTER_REQUEST_SIGNING_KEY = FMCSA_ADAPTER_REQUEST_SIGNING_KEYS.get(
    FMCSA_ADAPTER_REQUEST_SIGNING_ACTIVE_KEY_ID,
    b"",
)
VERIFIER_ED25519_PRIVATE_KEY_PATH = VERIFIER_ED25519_PRIVATE_KEYS.get(
    VERIFIER_ED25519_ACTIVE_KEY_ID,
    "",
)


def _init_replay_db():
    with sqlite3.connect(REPLAY_DB_PATH, timeout=5) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS replay_cache (
                kind TEXT NOT NULL,
                value TEXT NOT NULL,
                seen_at INTEGER NOT NULL,
                PRIMARY KEY(kind, value)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_replay_seen_at ON replay_cache(seen_at)"
        )
        conn.commit()


def _cleanup_replay_db(conn, now_epoch):
    cutoff = now_epoch - REPLAY_RETENTION_SECONDS
    if cutoff > 0:
        conn.execute("DELETE FROM replay_cache WHERE seen_at < ?", (cutoff,))


def _infer_role(agent_name):
    lowered = str(agent_name).lower()
    if "broker" in lowered:
        return "Broker"
    if "carrier" in lowered:
        return "Carrier"
    if "shipper" in lowered:
        return "Shipper"
    return "Unknown"


def _message_domain(message_type, body):
    if message_type in {"NewLoad", "LoadSearch", "AmendRequest"}:
        return "load"
    if message_type in {"NewTruck", "TruckSearch"}:
        return "truck"
    if message_type in {"BidRequest", "BidResponse", "ExecutionReport"}:
        if isinstance(body, dict) and "LoadID" in body:
            return "load"
        if isinstance(body, dict) and "TruckID" in body:
            return "truck"
    return None


def _validate_route_policy(envelope):
    sender_role = _infer_role(envelope.get("From"))
    receiver_role = _infer_role(envelope.get("To"))
    allowed = ROUTE_POLICY.get(envelope.get("MessageType"), set())
    if (sender_role, receiver_role) not in allowed:
        raise ValueError(
            f"Unauthorized route for {envelope.get('MessageType')}: {sender_role} -> {receiver_role}"
        )


def _trim_flow_state():
    if len(FLOW_STATE) > MAX_TRACKED_ENTITY_STATES:
        # Keep fixed domains used by MVP.
        FLOW_STATE.clear()
        FLOW_STATE.update({"load": "START", "truck": "START"})


def _enforce_state_transition(envelope):
    message_type = envelope.get("MessageType")
    body = envelope.get("Body", {})
    domain = _message_domain(message_type, body)
    if domain not in {"load", "truck"}:
        return

    allowed_previous = {
        "load": {
            "NewLoad": {"START", "NEWLOAD", "LOADSEARCH", "BIDREQUEST", "BIDRESPONSE", "BOOKED"},
            "LoadSearch": {"NEWLOAD"},
            "BidRequest": {"LOADSEARCH"},
            "BidResponse": {"BIDREQUEST"},
            "ExecutionReport": {"BIDRESPONSE"},
            "AmendRequest": {"BOOKED"},
        },
        "truck": {
            "NewTruck": {"START", "NEWTRUCK", "TRUCKSEARCH", "BIDREQUEST", "BIDRESPONSE", "BOOKED"},
            "TruckSearch": {"NEWTRUCK"},
            "BidRequest": {"TRUCKSEARCH"},
            "BidResponse": {"BIDREQUEST"},
            "ExecutionReport": {"BIDRESPONSE"},
        },
    }
    next_state = {
        "NewLoad": "NEWLOAD",
        "LoadSearch": "LOADSEARCH",
        "NewTruck": "NEWTRUCK",
        "TruckSearch": "TRUCKSEARCH",
        "BidRequest": "BIDREQUEST",
        "BidResponse": "BIDRESPONSE",
        "ExecutionReport": "BOOKED",
        "AmendRequest": "BOOKED",
    }
    current_state = FLOW_STATE.get(domain, "START")
    allowed_for_message = allowed_previous.get(domain, {}).get(message_type)
    if allowed_for_message and current_state not in allowed_for_message:
        raise ValueError(
            f"Invalid state transition for {domain} flow: {current_state} -> {message_type}"
        )
    FLOW_STATE[domain] = next_state.get(message_type, current_state)
    _trim_flow_state()


def reset_protocol_runtime_state():
    global CURRENT_RUN_ID
    with STATE_LOCK:
        FLOW_STATE.clear()
        FLOW_STATE.update({"load": "START", "truck": "START"})
        CURRENT_RUN_ID = ""


def set_protocol_run_id(run_id=None):
    global CURRENT_RUN_ID
    candidate = str(run_id or "").strip() or str(uuid4())
    with STATE_LOCK:
        CURRENT_RUN_ID = candidate
    return CURRENT_RUN_ID


def get_protocol_run_id():
    if CURRENT_RUN_ID:
        return CURRENT_RUN_ID
    return set_protocol_run_id()


def _bounded_string(value, context):
    if not isinstance(value, str):
        raise ValueError(f"{context} must be a string.")
    if len(value) > MAX_STRING_LENGTH:
        raise ValueError(f"{context} exceeds max length ({MAX_STRING_LENGTH}).")


def _validate_iso_date(value, context):
    _bounded_string(value, context)
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{context} must be ISO date (YYYY-MM-DD).") from exc


def _validate_iso_datetime(value, context):
    _bounded_string(value, context)
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{context} must be ISO datetime.") from exc


def _validate_state_code(value, context):
    _bounded_string(value, context)
    if not re.fullmatch(r"[A-Z]{2}", value):
        raise ValueError(f"{context} must be a 2-letter uppercase state code.")


def _validate_zip_code(value, context):
    _bounded_string(value, context)
    if not re.fullmatch(r"\d{5}", value):
        raise ValueError(f"{context} must be a 5-digit ZIP code.")


def _validate_location_obj(location, context):
    if not isinstance(location, dict):
        raise ValueError(f"{context} must be an object.")
    _require_fields(location, ["city", "state", "zip"], context)
    _bounded_string(location["city"], f"{context}.city")
    _validate_state_code(location["state"], f"{context}.state")
    _validate_zip_code(location["zip"], f"{context}.zip")


def _validate_verifier_dependency_integrity():
    if not NON_LOCAL_MODE:
        return
    if not EXPECTED_REPO_HASH:
        raise RuntimeError(
            "Missing FAXP_CARRIER_FINDER_REPOSITORIES_SHA256 in non-local mode."
        )
    try:
        with open(VERIFIER_REPOSITORIES_FILE, "rb") as handle:
            digest = hashlib.sha256(handle.read()).hexdigest().lower()
    except FileNotFoundError as exc:
        raise RuntimeError("Verifier dependency file not found.") from exc
    if digest != EXPECTED_REPO_HASH:
        raise RuntimeError("Verifier dependency hash mismatch.")


def _append_audit_event(envelope, validation_status="pass"):
    global LAST_AUDIT_HASH
    event = {
        "timestamp": now_utc(),
        "run_id": envelope.get("RunID"),
        "protocol": envelope.get("Protocol"),
        "version": envelope.get("ProtocolVersion"),
        "message_id": envelope.get("MessageID"),
        "message_type": envelope.get("MessageType"),
        "from": envelope.get("From"),
        "to": envelope.get("To"),
        "validation_status": validation_status,
        "body_hash": hashlib.sha256(
            canonical_json(envelope.get("Body", {})).encode("utf-8")
        ).hexdigest(),
        "prev_hash": LAST_AUDIT_HASH,
    }
    event_hash = hashlib.sha256(canonical_json(event).encode("utf-8")).hexdigest()
    event["event_hash"] = event_hash
    LAST_AUDIT_HASH = event_hash
    with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as handle:
        handle.write(canonical_json(event) + "\n")

    try:
        _ship_immutable_audit_event(event)
    except Exception:
        if NON_LOCAL_MODE and REQUIRE_IMMUTABLE_AUDIT:
            raise

    # Keep audit log bounded for demo environments.
    if MAX_AUDIT_ENTRIES > 0:
        try:
            with open(AUDIT_LOG_PATH, "r", encoding="utf-8") as handle:
                lines = handle.readlines()
            if len(lines) > MAX_AUDIT_ENTRIES:
                with open(AUDIT_LOG_PATH, "w", encoding="utf-8") as handle:
                    handle.writelines(lines[-MAX_AUDIT_ENTRIES:])
        except OSError:
            pass


def parse_args():
    parser = argparse.ArgumentParser(
        description=f"Run {FaxpProtocol.NAME} v{FaxpProtocol.VERSION} MVP simulation."
    )
    parser.add_argument(
        "--provider",
        choices=["FMCSA", "MockComplianceProvider", "MockBiometricProvider", "iDenfy"],
        default="MockBiometricProvider",
        help="Verification provider ID to simulate (legacy alias: iDenfy).",
    )
    parser.add_argument(
        "--response",
        choices=["Accept", "Counter", "Reject"],
        default="Accept",
        help="Broker response to the bid.",
    )
    parser.add_argument(
        "--verification-status",
        choices=["Success", "Fail"],
        default="Success",
        help="Verification result status to simulate when response is Accept.",
    )
    parser.add_argument(
        "--no-match",
        action="store_true",
        help="Force a no-load-match search branch.",
    )
    parser.add_argument(
        "--mc-number",
        default=None,
        help="MC number used for FMCSA verification (example: 498282).",
    )
    parser.add_argument(
        "--carrier-finder-path",
        default=DEFAULT_CARRIER_FINDER_PATH,
        help="Path to the allowlisted carrier-finder project root.",
    )
    parser.add_argument(
        "--fmcsa-source",
        choices=["carrier-finder", "live-fmcsa", "hosted-adapter"],
        default="carrier-finder",
        help="FMCSA verification source. 'hosted-adapter' calls a hosted FMCSA wrapper API.",
    )
    parser.add_argument(
        "--rate-model",
        choices=["PerMile", "Flat"],
        default="PerMile",
        help="Base pricing method for this simulation run.",
    )
    parser.add_argument(
        "--bid-amount",
        type=float,
        default=None,
        help="Optional bid amount override for the selected rate model.",
    )
    parser.add_argument(
        "--security-self-test",
        action="store_true",
        help="Run randomized parser/validation security tests before protocol flows.",
    )
    parser.add_argument(
        "--self-test-iterations",
        type=int,
        default=50,
        help="Number of randomized security self-test iterations.",
    )
    parser.add_argument(
        "--force-capability-mismatch",
        action="store_true",
        help="Force verification capability mismatch to exercise fail-closed negotiation path.",
    )
    parser.add_argument(
        "--policy-profile-id",
        default=VERIFICATION_POLICY_PROFILE_ID,
        help="Verification policy profile ID (for example: US_FMCSA_BALANCED_V1).",
    )
    parser.add_argument(
        "--risk-tier",
        choices=[0, 1, 2, 3],
        type=int,
        default=max(0, min(DEFAULT_RISK_TIER, 3)),
        help="Risk tier used for degraded verification policy decisions (0=Low, 3=Critical).",
    )
    parser.add_argument(
        "--exception-approved",
        action="store_true",
        help="Mark an explicit human exception approval for degraded verification decisions.",
    )
    parser.add_argument(
        "--exception-approval-ref",
        default="",
        help="Reference ID for the approving human exception (used for auditability).",
    )
    return parser.parse_args()


def _validate_key_age(issued_at_text, context):
    if not issued_at_text:
        return
    _validate_iso_datetime(issued_at_text, context)
    issued_at = datetime.fromisoformat(issued_at_text.replace("Z", "+00:00"))
    age_days = (datetime.now(timezone.utc) - issued_at.astimezone(timezone.utc)).days
    if age_days > MAX_ACTIVE_KEY_AGE_DAYS:
        raise RuntimeError(
            f"{context} is older than MAX_ACTIVE_KEY_AGE_DAYS ({MAX_ACTIVE_KEY_AGE_DAYS})."
        )


def _enforce_dual_control():
    if not ENFORCE_DUAL_CONTROL:
        return
    approvals = sorted(
        {item.strip() for item in KEY_CHANGE_APPROVALS_RAW.split(",") if item.strip()}
    )
    if len(approvals) < 2:
        raise RuntimeError(
            "Dual control policy requires at least two approval IDs in FAXP_KEY_CHANGE_APPROVALS."
        )


def _enforce_external_secret_source():
    if REQUIRE_EXTERNAL_SECRET_MANAGER and SECRET_SOURCE not in {"kms", "hsm"}:
        raise RuntimeError(
            "External secret manager policy enabled but FAXP_SECRET_SOURCE is not 'kms' or 'hsm'."
        )


def _validate_agent_key_registry():
    if SIGNATURE_SCHEME != "ED25519":
        return
    if not AGENT_KEY_REGISTRY:
        if NON_LOCAL_MODE:
            raise RuntimeError(
                "ED25519 signature scheme requires FAXP_AGENT_KEY_REGISTRY or FAXP_AGENT_KEY_REGISTRY_FILE."
            )
        return
    for agent_name, material in AGENT_KEY_REGISTRY.items():
        active_kid = material.get("active_kid", "")
        private_keys = material.get("private_keys", {})
        public_keys = material.get("public_keys", {})
        key_metadata = material.get("key_metadata", {})
        if not active_kid:
            raise RuntimeError(f"Agent '{agent_name}' missing active_kid.")
        if active_kid not in public_keys:
            raise RuntimeError(
                f"Agent '{agent_name}' missing public key for active_kid '{active_kid}'."
            )
        if not os.path.exists(public_keys[active_kid]):
            raise RuntimeError(
                f"Agent '{agent_name}' public key path does not exist for active_kid '{active_kid}'."
            )
        if NON_LOCAL_MODE and active_kid not in private_keys:
            raise RuntimeError(
                f"Agent '{agent_name}' missing private key for active_kid '{active_kid}'."
            )
        if active_kid in private_keys and not os.path.exists(private_keys[active_kid]):
            raise RuntimeError(
                f"Agent '{agent_name}' private key path does not exist for active_kid '{active_kid}'."
            )
        meta = key_metadata.get(active_kid, {})
        if isinstance(meta, dict):
            issued_at = str(meta.get("issued_at") or meta.get("activated_at") or "").strip()
            if issued_at:
                _validate_key_age(issued_at, f"{agent_name}:{active_kid}.issued_at")


def enforce_security_baseline():
    if SIGNATURE_SCHEME not in SUPPORTED_SIGNATURE_SCHEMES:
        raise RuntimeError(
            f"Unsupported FAXP_SIGNATURE_SCHEME '{SIGNATURE_SCHEME}'."
        )
    if VERIFIER_SIGNATURE_SCHEME not in SUPPORTED_SIGNATURE_SCHEMES:
        raise RuntimeError(
            f"Unsupported FAXP_VERIFIER_SIGNATURE_SCHEME '{VERIFIER_SIGNATURE_SCHEME}'."
        )
    if (
        SIGNATURE_SCHEME == "ED25519" or VERIFIER_SIGNATURE_SCHEME == "ED25519"
    ) and not shutil.which("openssl"):
        raise RuntimeError("ED25519 signature scheme requires openssl binary.")
    _init_replay_db()
    _enforce_external_secret_source()
    _enforce_dual_control()
    if MESSAGE_TTL_SECONDS <= 0:
        raise RuntimeError("FAXP_MESSAGE_TTL_SECONDS must be greater than zero.")
    if MAX_CLOCK_SKEW_SECONDS < 0:
        raise RuntimeError("FAXP_MAX_CLOCK_SKEW_SECONDS must be zero or greater.")
    _validate_key_age(MESSAGE_ACTIVE_KEY_ISSUED_AT, "FAXP_MESSAGE_ACTIVE_KEY_ISSUED_AT")
    _validate_key_age(VERIFIER_ACTIVE_KEY_ISSUED_AT, "FAXP_VERIFIER_ACTIVE_KEY_ISSUED_AT")
    _validate_agent_key_registry()
    if NON_LOCAL_MODE:
        if SIGNATURE_SCHEME == "HMAC_SHA256" and not MESSAGE_SIGNING_KEYS:
            raise RuntimeError(
                "Missing message signing key material in non-local mode."
            )
        if REQUIRE_SIGNED_VERIFIER:
            if VERIFIER_SIGNATURE_SCHEME == "HMAC_SHA256" and not VERIFIER_SIGNING_KEYS:
                raise RuntimeError(
                    "Missing verifier HMAC signing key material with REQUIRE_SIGNED_VERIFIER enabled."
                )
            if VERIFIER_SIGNATURE_SCHEME == "ED25519":
                if not VERIFIER_ED25519_ACTIVE_KEY_ID:
                    raise RuntimeError(
                        "Missing FAXP_VERIFIER_ED25519_ACTIVE_KEY_ID with ED25519 verifier signatures."
                    )
                if VERIFIER_ED25519_ACTIVE_KEY_ID not in VERIFIER_ED25519_PUBLIC_KEYS:
                    raise RuntimeError(
                        "Verifier ED25519 active key ID is not present in trusted public key ring."
                    )
                if not VERIFIER_ED25519_PRIVATE_KEY_PATH:
                    raise RuntimeError(
                        "Verifier ED25519 private key path missing for active key ID."
                    )
                if not os.path.exists(VERIFIER_ED25519_PRIVATE_KEY_PATH):
                    raise RuntimeError("Verifier ED25519 private key path does not exist.")
                if not os.path.exists(
                    VERIFIER_ED25519_PUBLIC_KEYS[VERIFIER_ED25519_ACTIVE_KEY_ID]
                ):
                    raise RuntimeError("Verifier ED25519 public key path does not exist.")
        if REQUIRE_IMMUTABLE_AUDIT and not (IMMUTABLE_AUDIT_PATH or IMMUTABLE_AUDIT_URL):
            raise RuntimeError(
                "Immutable audit required in non-local mode but no immutable sink configured."
            )
        _validate_verifier_dependency_integrity()


def now_utc():
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def default_floor_amount(rate_model):
    if rate_model == "Flat":
        return 1850.0
    return 2.35


def default_bid_amount(rate_model):
    if rate_model == "Flat":
        return 1950.0
    return 2.62


def default_search_max(rate_model):
    if rate_model == "Flat":
        return 2200.0
    return 2.80


def counter_amount(rate_model, floor_amount):
    if rate_model == "Flat":
        return round(floor_amount + 150.0, 2)
    return round(floor_amount + 0.16, 2)


def build_rate(rate_model, amount):
    return {
        "RateModel": rate_model,
        "Amount": round(float(amount), 2),
        "Currency": "USD",
    }


def format_rate(rate):
    if rate["RateModel"] == "Flat":
        return f"${rate['Amount']:.2f} flat"
    return f"${rate['Amount']:.2f}/mile"


def redact_sensitive(value):
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            if key in SENSITIVE_KEYS:
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = redact_sensitive(item)
        return redacted
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    return value


def resolve_allowed_carrier_finder_path(candidate_path):
    resolved = os.path.realpath(candidate_path or DEFAULT_CARRIER_FINDER_PATH)
    if resolved not in ALLOWED_CARRIER_FINDER_PATHS:
        raise ValueError("carrier-finder path is not allowlisted.")
    return resolved


VALID_RATE_MODELS = {"PerMile", "Flat"}
VALID_BID_RESPONSE_TYPES = {"Accept", "Counter", "Reject"}
VALID_EXECUTION_STATUSES = {"Booked"}
VALID_VERIFIED_BADGES = {"None", "Basic", "Premium"}
VALID_VERIFICATION_STATUSES = {"Success", "Fail", "Pending"}
VALID_VERIFICATION_MODES = {"Live", "Cached", "Fallback"}
VALID_DISPATCH_AUTHORIZATIONS = {"Allowed", "Hold", "Blocked"}
FORBIDDEN_BIOMETRIC_FIELDS = {
    "faceimage",
    "selfieimage",
    "documentimage",
    "biometrictemplate",
    "rawbiometric",
    "fingerprintimage",
    "irisimage",
    "face_template",
    "fingerprint_template",
    "iris_template",
}
PROVIDER_VERIFICATION_REQUIREMENTS = {
    "FMCSA": {
        "category": "Compliance",
        "method": "AuthorityRecordCheck",
        "minAssuranceLevel": "AAL1",
    },
    "MockBiometricProvider": {
        "category": "Biometric",
        "method": "LivenessPlusDocument",
        "minAssuranceLevel": "AAL2",
    },
}
KNOWN_VERIFICATION_CATEGORIES = {
    "Identity",
    *(cfg["category"] for cfg in PROVIDER_VERIFICATION_REQUIREMENTS.values()),
}
KNOWN_VERIFICATION_METHODS = {
    "DocumentOnly",
    *(cfg["method"] for cfg in PROVIDER_VERIFICATION_REQUIREMENTS.values()),
}
KNOWN_VERIFICATION_CATEGORY_METHOD_PAIRS = {
    (cfg["category"], cfg["method"]) for cfg in PROVIDER_VERIFICATION_REQUIREMENTS.values()
}
KNOWN_VERIFICATION_CATEGORY_METHOD_PAIRS.add(("Identity", "DocumentOnly"))
NEUTRAL_VERIFICATION_PROVIDER_IDS = {
    "fmcsa_live": "compliance.authority-record.live",
    "fmcsa_hosted_adapter": "compliance.authority-record.adapter",
    "fmcsa_registry": "compliance.authority-record.registry",
    "compliance_mock": "compliance.authority-record.mock",
    "biometric_mock": "identity.liveness-document.mock",
}
PROVIDER_ALIASES = {
    "FMCSA": "FMCSA",
    "MockComplianceProvider": "FMCSA",
    "iDenfy": "MockBiometricProvider",
    "MockBiometricProvider": "MockBiometricProvider",
}
ASSURANCE_LEVEL_RANK = {"AAL0": 0, "AAL1": 1, "AAL2": 2, "AAL3": 3}


def _require_fields(payload, required_fields, context):
    missing = [field for field in required_fields if field not in payload]
    if missing:
        raise ValueError(f"{context} missing required fields: {missing}")


def _validate_rate_object(rate, context):
    if not isinstance(rate, dict):
        raise ValueError(f"{context} must be an object.")
    _require_fields(rate, ["RateModel", "Amount", "Currency"], context)
    if rate["RateModel"] not in VALID_RATE_MODELS:
        raise ValueError(f"{context}.RateModel must be one of {sorted(VALID_RATE_MODELS)}.")
    if not isinstance(rate["Amount"], (int, float)) or rate["Amount"] < 0:
        raise ValueError(f"{context}.Amount must be a non-negative number.")
    if rate["Currency"] != "USD":
        raise ValueError(f"{context}.Currency must be USD for v0.1.1.")


def _contains_forbidden_biometric_field(value):
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).strip().lower()
            if normalized in FORBIDDEN_BIOMETRIC_FIELDS:
                return True
            if _contains_forbidden_biometric_field(item):
                return True
        return False
    if isinstance(value, list):
        return any(_contains_forbidden_biometric_field(item) for item in value)
    return False


def _validate_verification_result(result, context):
    if not isinstance(result, dict):
        raise ValueError(f"{context} must be an object.")
    _require_fields(result, ["status"], context)
    if result["status"] not in VALID_VERIFICATION_STATUSES:
        raise ValueError(
            f"{context}.status must be one of {sorted(VALID_VERIFICATION_STATUSES)}."
        )
    _bounded_string(result["status"], f"{context}.status")

    optional_string_fields = [
        "category",
        "method",
        "provider",
        "providerAlias",
        "assuranceLevel",
        "token",
        "evidenceRef",
        "source",
        "sourceAuthority",
        "mcNumber",
        "error",
    ]
    for field in optional_string_fields:
        if field in result:
            _bounded_string(result[field], f"{context}.{field}")

    if "category" in result and result["category"] not in KNOWN_VERIFICATION_CATEGORIES:
        raise ValueError(f"{context}.category is not recognized.")

    if "method" in result and result["method"] not in KNOWN_VERIFICATION_METHODS:
        raise ValueError(f"{context}.method is not recognized.")

    if "category" in result and "method" in result:
        category_method = (result["category"], result["method"])
        if category_method not in KNOWN_VERIFICATION_CATEGORY_METHOD_PAIRS:
            raise ValueError(f"{context}.category/method combination is not recognized.")

    if "score" in result:
        score = result["score"]
        if not isinstance(score, (int, float)) or not (0 <= score <= 100):
            raise ValueError(f"{context}.score must be between 0 and 100.")

    if "verifiedAt" in result:
        _validate_iso_datetime(result["verifiedAt"], f"{context}.verifiedAt")
    if "expiresAt" in result:
        _validate_iso_datetime(result["expiresAt"], f"{context}.expiresAt")

    if "carrier" in result:
        carrier = result["carrier"]
        if not isinstance(carrier, dict):
            raise ValueError(f"{context}.carrier must be an object.")
        for field in ["mc", "name", "operatingStatus"]:
            if field in carrier and carrier[field] is not None:
                _bounded_string(str(carrier[field]), f"{context}.carrier.{field}")
        for field in ["hasCurrentInsurance", "interstateAuthorityOk"]:
            if field in carrier and not isinstance(carrier[field], bool):
                raise ValueError(f"{context}.carrier.{field} must be boolean.")
        if "usdot" in carrier and carrier["usdot"] is not None:
            if not isinstance(carrier["usdot"], (int, str)):
                raise ValueError(f"{context}.carrier.usdot must be int/string.")

    if _contains_forbidden_biometric_field(result):
        raise ValueError(f"{context} must not include raw biometric artifacts.")

    if REQUIRE_SIGNED_VERIFIER and "attestation" not in result:
        raise ValueError(
            f"{context}.attestation is required when signed verifier mode is enabled."
        )

    if "attestation" in result:
        attestation = result["attestation"]
        if not isinstance(attestation, dict):
            raise ValueError(f"{context}.attestation must be an object.")
        _require_fields(attestation, ["alg", "kid", "sig"], f"{context}.attestation")
        _bounded_string(attestation["alg"], f"{context}.attestation.alg")
        _bounded_string(attestation["kid"], f"{context}.attestation.kid")
        _bounded_string(attestation["sig"], f"{context}.attestation.sig")

        attestation_alg = str(attestation["alg"]).upper()
        attestation_kid = str(attestation["kid"])
        attestation_sig = attestation["sig"]
        signed_payload = {k: v for k, v in result.items() if k != "attestation"}

        if attestation_alg not in SUPPORTED_SIGNATURE_SCHEMES:
            raise ValueError(f"{context}.attestation.alg is not supported.")

        if REQUIRE_SIGNED_VERIFIER and attestation_alg != VERIFIER_SIGNATURE_SCHEME:
            raise ValueError(
                f"{context}.attestation.alg must match configured verifier signature scheme."
            )

        if attestation_alg == "HMAC_SHA256":
            if REQUIRE_SIGNED_VERIFIER and attestation_kid not in VERIFIER_SIGNING_KEYS:
                raise ValueError(f"{context}.attestation.kid is not trusted for HMAC verifier mode.")
            if not _verify_with_key_ring(
                signed_payload,
                attestation_sig,
                attestation_kid,
                VERIFIER_SIGNING_KEYS,
            ):
                raise ValueError(f"{context}.attestation signature verification failed.")
        elif attestation_alg == "ED25519":
            if REQUIRE_SIGNED_VERIFIER and attestation_kid not in VERIFIER_ED25519_PUBLIC_KEYS:
                raise ValueError(f"{context}.attestation.kid is not trusted for ED25519 verifier mode.")
            if not _verify_ed25519_with_public_key_ring(
                signed_payload,
                attestation_sig,
                attestation_kid,
                VERIFIER_ED25519_PUBLIC_KEYS,
            ):
                raise ValueError(f"{context}.attestation signature verification failed.")


def _validate_string_array(values, context):
    if not isinstance(values, list):
        raise ValueError(f"{context} must be an array.")
    if not values:
        raise ValueError(f"{context} must include at least one value.")
    if len(values) > 20:
        raise ValueError(f"{context} exceeds max list length (20).")
    for idx, item in enumerate(values):
        _bounded_string(item, f"{context}[{idx}]")


def _derive_verification_mode(verification_result):
    source = str((verification_result or {}).get("source") or "").strip().lower()
    if source in {"live-fmcsa", "hosted-adapter"}:
        return "Live"
    if source in {"cache", "cached-fmcsa", "fmcsa-cache"}:
        return "Cached"
    return "Fallback"


def _derive_policy_rule_id(verification_mode, status_value):
    normalized_mode = str(verification_mode or "").strip().lower()
    normalized_status = str(status_value or "").strip().lower()
    if normalized_status == "success":
        return f"policy.{normalized_mode or 'unknown'}.success.v1"
    return f"policy.{normalized_mode or 'unknown'}.degraded.v1"


def _coerce_risk_tier(risk_tier):
    try:
        value = int(risk_tier)
    except (TypeError, ValueError):
        return max(0, min(DEFAULT_RISK_TIER, 3))
    return max(0, min(value, 3))


def _policy_profiles_dir():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "profiles", "verification")


def _load_policy_profile(profile_id):
    normalized_profile_id = str(profile_id or VERIFICATION_POLICY_PROFILE_ID).strip()
    if not normalized_profile_id:
        normalized_profile_id = VERIFICATION_POLICY_PROFILE_ID
    profile_path = os.path.join(_policy_profiles_dir(), f"{normalized_profile_id}.json")
    with open(profile_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _risk_tier_policy(profile, risk_tier):
    tiers = profile.get("riskTiers", [])
    for tier in tiers:
        if int(tier.get("tier", -1)) == int(risk_tier):
            return tier
    raise ValueError(f"Risk tier {risk_tier} is not defined in profile {profile.get('profileId')}.")


def evaluate_verification_policy_decision(
    verification_result,
    *,
    profile_id,
    risk_tier,
    exception_approved=False,
    exception_approval_ref="",
):
    """
    Derive booking/dispatch behavior from verification status and policy profile.

    Notes:
    - Verification failures with no infrastructure error are treated as true compliance fails.
    - Verification failures with an error are treated as degraded/outage mode and use profile policy.
    """
    profile = _load_policy_profile(profile_id)
    policy_profile_id = str(profile.get("profileId") or profile_id or VERIFICATION_POLICY_PROFILE_ID)
    normalized_risk_tier = _coerce_risk_tier(risk_tier)
    tier_policy = _risk_tier_policy(profile, normalized_risk_tier)

    verification_status = str((verification_result or {}).get("status") or "Fail").strip()
    verification_error = str((verification_result or {}).get("error") or "").strip()
    verification_mode = _derive_verification_mode(verification_result)
    evidence_refs = []
    if (verification_result or {}).get("evidenceRef"):
        evidence_refs.append(verification_result["evidenceRef"])

    reverify_window_seconds = int(
        (profile.get("dispatchRules") or {}).get("reverifyWindowSeconds", 86400)
    )
    fallback_window_seconds = int(
        (profile.get("policyDefaults") or {}).get("maxFallbackDurationSeconds", 0)
    )
    decision_window_seconds = reverify_window_seconds

    dispatch_authorization = "Allowed"
    decision_reason_code = "VerificationSuccess"
    should_book = True

    if verification_status != "Success":
        if not verification_error:
            dispatch_authorization = "Blocked"
            decision_reason_code = "VerificationNegativeResult"
            should_book = False
        else:
            decision_window_seconds = max(1, reverify_window_seconds)
            degraded_mode = str(
                (profile.get("policyDefaults") or {}).get("degradedMode") or "HardBlock"
            ).strip()
            outage_decision = str(tier_policy.get("decisionOnOutage") or "Block").strip()
            tier_dispatch = str(tier_policy.get("dispatchAuthorization") or "Hold").strip()

            if degraded_mode == "HardBlock":
                dispatch_authorization = "Blocked"
                decision_reason_code = "VerificationUnavailableHardBlock"
            elif degraded_mode == "SoftHold":
                dispatch_authorization = "Hold"
                decision_reason_code = "VerificationUnavailableSoftHold"
            else:
                # GraceCache uses per-tier outage handling rules.
                if outage_decision == "AllowProvisional":
                    dispatch_authorization = tier_dispatch if tier_dispatch in VALID_DISPATCH_AUTHORIZATIONS else "Hold"
                    decision_reason_code = "VerificationUnavailableGraceCache"
                elif outage_decision == "HoldDispatch":
                    dispatch_authorization = "Hold"
                    decision_reason_code = "VerificationUnavailableHoldDispatch"
                else:
                    dispatch_authorization = "Blocked"
                    decision_reason_code = "VerificationUnavailableBlock"

                if fallback_window_seconds > 0:
                    decision_window_seconds = min(decision_window_seconds, fallback_window_seconds)

            require_manual_escalation_tier = int(
                (profile.get("policyDefaults") or {}).get("requireManualEscalationForTier", 3)
            )
            tier_requires_human = bool(tier_policy.get("requiresHumanApproval", False))
            requires_human = tier_requires_human or normalized_risk_tier >= require_manual_escalation_tier

            if requires_human:
                if exception_approved:
                    if outage_decision == "Block":
                        dispatch_authorization = "Blocked"
                        decision_reason_code = "HumanExceptionDeniedByTierPolicy"
                    elif dispatch_authorization != "Blocked":
                        dispatch_authorization = "Allowed"
                        decision_reason_code = "HumanExceptionApproved"
                else:
                    if dispatch_authorization == "Allowed":
                        dispatch_authorization = "Hold"
                    decision_reason_code = "PendingHumanApproval"

            should_book = dispatch_authorization != "Blocked"

    decision = {
        "VerificationMode": verification_mode,
        "VerificationPolicyProfileID": policy_profile_id,
        "DispatchAuthorization": dispatch_authorization,
        "DecisionReasonCode": decision_reason_code,
        "PolicyRuleID": _derive_policy_rule_id(verification_mode, verification_status),
        "ReverifyBy": (
            datetime.now(timezone.utc) + timedelta(seconds=max(1, decision_window_seconds))
        )
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "EvidenceRefs": evidence_refs,
        "RiskTier": normalized_risk_tier,
        "ShouldBook": should_book,
    }
    normalized_exception_ref = str(exception_approval_ref or "").strip()
    if exception_approved and normalized_exception_ref:
        decision["ExceptionApprovalRef"] = normalized_exception_ref
    return decision


def default_verification_capabilities():
    return {
        "supportedCategories": ["Compliance", "Biometric", "Identity"],
        "supportedMethods": ["AuthorityRecordCheck", "LivenessPlusDocument"],
        "minAssuranceLevel": "AAL1",
        "requiresSignedAttestation": bool(REQUIRE_SIGNED_VERIFIER),
    }


def _assurance_rank(value):
    return ASSURANCE_LEVEL_RANK.get(str(value or "").upper(), -1)


def normalize_verification_provider(provider):
    normalized = PROVIDER_ALIASES.get(str(provider or "").strip())
    if normalized:
        return normalized
    return str(provider or "").strip()


def negotiate_verification_capability(provider, *agents):
    normalized_provider = normalize_verification_provider(provider)
    requirement = PROVIDER_VERIFICATION_REQUIREMENTS.get(normalized_provider)
    if not requirement:
        return (
            False,
            f"Unsupported verification provider for capability negotiation: {provider}.",
        )

    required_category = requirement["category"]
    required_method = requirement["method"]
    required_aal = requirement["minAssuranceLevel"]
    required_aal_rank = _assurance_rank(required_aal)

    for agent in agents:
        agent_name = getattr(agent, "name", "Unknown Agent")
        capabilities = getattr(agent, "verification_capabilities", {}) or {}

        categories = capabilities.get("supportedCategories") or []
        methods = capabilities.get("supportedMethods") or []
        min_aal = str(capabilities.get("minAssuranceLevel") or "AAL0").upper()
        min_aal_rank = _assurance_rank(min_aal)

        if required_category not in categories:
            return (
                False,
                f"Capability mismatch: {agent_name} does not support category '{required_category}'.",
            )
        if required_method not in methods:
            return (
                False,
                f"Capability mismatch: {agent_name} does not support method '{required_method}'.",
            )
        # Agent minAssuranceLevel is a requirement floor; provider assurance must meet/exceed it.
        if required_aal_rank < min_aal_rank:
            return (
                False,
                f"Capability mismatch: provider assurance '{required_aal}' below {agent_name} minimum '{min_aal}'.",
            )

    return True, ""


def validate_message_body(message_type, body):
    """Minimal provider-agnostic validation for FAXP message bodies."""
    if message_type not in FaxpProtocol.MESSAGE_TYPES:
        raise ValueError(f"Unknown message type: {message_type}")
    if not isinstance(body, dict):
        raise ValueError(f"{message_type} body must be an object.")

    if message_type == "NewLoad":
        _require_fields(
            body,
            [
                "LoadID",
                "Origin",
                "Destination",
                "PickupEarliest",
                "PickupLatest",
                "LoadType",
                "EquipmentType",
                "TrailerLength",
                "Weight",
                "Commodity",
                "Rate",
                "RequireTracking",
            ],
            "NewLoad",
        )
        _validate_rate_object(body["Rate"], "NewLoad.Rate")
        _bounded_string(body["LoadID"], "NewLoad.LoadID")
        _validate_location_obj(body["Origin"], "NewLoad.Origin")
        _validate_location_obj(body["Destination"], "NewLoad.Destination")
        _validate_iso_date(body["PickupEarliest"], "NewLoad.PickupEarliest")
        _validate_iso_date(body["PickupLatest"], "NewLoad.PickupLatest")
        _bounded_string(body["LoadType"], "NewLoad.LoadType")
        _bounded_string(body["EquipmentType"], "NewLoad.EquipmentType")
        _bounded_string(body["Commodity"], "NewLoad.Commodity")
        if not isinstance(body["TrailerLength"], (int, float)) or body["TrailerLength"] <= 0:
            raise ValueError("NewLoad.TrailerLength must be a positive number.")
        if not isinstance(body["Weight"], (int, float)) or body["Weight"] <= 0:
            raise ValueError("NewLoad.Weight must be a positive number.")
        if not isinstance(body["RequireTracking"], bool):
            raise ValueError("NewLoad.RequireTracking must be boolean.")
        return

    if message_type == "LoadSearch":
        _require_fields(
            body,
            ["OriginState", "DestinationState", "EquipmentType", "PickupDate", "RateModel", "MaxRate"],
            "LoadSearch",
        )
        if body["RateModel"] not in VALID_RATE_MODELS:
            raise ValueError(f"LoadSearch.RateModel must be one of {sorted(VALID_RATE_MODELS)}.")
        _validate_state_code(body["OriginState"], "LoadSearch.OriginState")
        _validate_state_code(body["DestinationState"], "LoadSearch.DestinationState")
        _bounded_string(body["EquipmentType"], "LoadSearch.EquipmentType")
        _validate_iso_date(body["PickupDate"], "LoadSearch.PickupDate")
        if not isinstance(body["MaxRate"], (int, float)) or body["MaxRate"] < 0:
            raise ValueError("LoadSearch.MaxRate must be a non-negative number.")
        return

    if message_type == "NewTruck":
        _require_fields(
            body,
            [
                "TruckID",
                "Location",
                "AvailabilityDate",
                "EquipmentType",
                "TrailerLength",
                "MaxWeight",
                "RateMin",
                "Notes",
            ],
            "NewTruck",
        )
        _validate_rate_object(body["RateMin"], "NewTruck.RateMin")
        _bounded_string(body["TruckID"], "NewTruck.TruckID")
        _validate_location_obj(body["Location"], "NewTruck.Location")
        _validate_iso_date(body["AvailabilityDate"], "NewTruck.AvailabilityDate")
        _bounded_string(body["EquipmentType"], "NewTruck.EquipmentType")
        _bounded_string(body["Notes"], "NewTruck.Notes")
        if not isinstance(body["TrailerLength"], (int, float)) or body["TrailerLength"] <= 0:
            raise ValueError("NewTruck.TrailerLength must be a positive number.")
        if not isinstance(body["MaxWeight"], (int, float)) or body["MaxWeight"] <= 0:
            raise ValueError("NewTruck.MaxWeight must be a positive number.")
        return

    if message_type == "TruckSearch":
        _require_fields(
            body,
            [
                "LocationRadiusMiles",
                "OriginState",
                "EquipmentType",
                "AvailableFrom",
                "AvailableTo",
                "RateModel",
                "MinRate",
                "MaxRate",
            ],
            "TruckSearch",
        )
        if body["RateModel"] not in VALID_RATE_MODELS:
            raise ValueError(f"TruckSearch.RateModel must be one of {sorted(VALID_RATE_MODELS)}.")
        _validate_state_code(body["OriginState"], "TruckSearch.OriginState")
        _bounded_string(body["EquipmentType"], "TruckSearch.EquipmentType")
        _validate_iso_date(body["AvailableFrom"], "TruckSearch.AvailableFrom")
        _validate_iso_date(body["AvailableTo"], "TruckSearch.AvailableTo")
        for field in ["LocationRadiusMiles", "MinRate", "MaxRate"]:
            if not isinstance(body[field], (int, float)) or body[field] < 0:
                raise ValueError(f"TruckSearch.{field} must be a non-negative number.")
        return

    if message_type == "BidRequest":
        has_load_id = "LoadID" in body
        has_truck_id = "TruckID" in body
        if has_load_id == has_truck_id:
            raise ValueError("BidRequest must include exactly one of LoadID or TruckID.")
        _require_fields(body, ["Rate"], "BidRequest")
        _validate_rate_object(body["Rate"], "BidRequest.Rate")
        if has_load_id:
            _bounded_string(body["LoadID"], "BidRequest.LoadID")
        if has_truck_id:
            _bounded_string(body["TruckID"], "BidRequest.TruckID")
        return

    if message_type == "BidResponse":
        has_load_id = "LoadID" in body
        has_truck_id = "TruckID" in body
        if has_load_id == has_truck_id:
            raise ValueError("BidResponse must include exactly one of LoadID or TruckID.")
        _require_fields(body, ["ResponseType"], "BidResponse")
        if body["ResponseType"] not in VALID_BID_RESPONSE_TYPES:
            raise ValueError(
                f"BidResponse.ResponseType must be one of {sorted(VALID_BID_RESPONSE_TYPES)}."
            )
        if body["ResponseType"] == "Counter":
            _require_fields(body, ["ProposedRate"], "BidResponse")
            _validate_rate_object(body["ProposedRate"], "BidResponse.ProposedRate")
        if has_load_id:
            _bounded_string(body["LoadID"], "BidResponse.LoadID")
        if has_truck_id:
            _bounded_string(body["TruckID"], "BidResponse.TruckID")
        if "VerifiedBadge" in body and body["VerifiedBadge"] not in VALID_VERIFIED_BADGES:
            raise ValueError(
                f"BidResponse.VerifiedBadge must be one of {sorted(VALID_VERIFIED_BADGES)}."
            )
        return

    if message_type == "ExecutionReport":
        has_load_id = "LoadID" in body
        has_truck_id = "TruckID" in body
        if has_load_id == has_truck_id:
            raise ValueError("ExecutionReport must include exactly one of LoadID or TruckID.")
        _require_fields(
            body,
            ["ContractID", "Status", "Timestamp", "VerifiedBadge", "VerificationResult"],
            "ExecutionReport",
        )
        if body["Status"] not in VALID_EXECUTION_STATUSES:
            raise ValueError(
                f"ExecutionReport.Status must be one of {sorted(VALID_EXECUTION_STATUSES)}."
            )
        if body["VerifiedBadge"] not in VALID_VERIFIED_BADGES:
            raise ValueError(
                f"ExecutionReport.VerifiedBadge must be one of {sorted(VALID_VERIFIED_BADGES)}."
            )
        if "AgreedRate" in body:
            _validate_rate_object(body["AgreedRate"], "ExecutionReport.AgreedRate")
        _bounded_string(body["ContractID"], "ExecutionReport.ContractID")
        _validate_iso_datetime(body["Timestamp"], "ExecutionReport.Timestamp")
        _validate_verification_result(body["VerificationResult"], "ExecutionReport.VerificationResult")
        if has_load_id:
            _bounded_string(body["LoadID"], "ExecutionReport.LoadID")
        if has_truck_id:
            _bounded_string(body["TruckID"], "ExecutionReport.TruckID")

        policy_fields = [
            "VerificationMode",
            "VerificationPolicyProfileID",
            "DispatchAuthorization",
            "DecisionReasonCode",
            "PolicyRuleID",
        ]
        if any(field in body for field in policy_fields):
            _require_fields(body, policy_fields, "ExecutionReport")
            if body["VerificationMode"] not in VALID_VERIFICATION_MODES:
                raise ValueError(
                    f"ExecutionReport.VerificationMode must be one of {sorted(VALID_VERIFICATION_MODES)}."
                )
            if body["DispatchAuthorization"] not in VALID_DISPATCH_AUTHORIZATIONS:
                raise ValueError(
                    "ExecutionReport.DispatchAuthorization must be one of "
                    f"{sorted(VALID_DISPATCH_AUTHORIZATIONS)}."
                )
            _bounded_string(
                body["VerificationPolicyProfileID"],
                "ExecutionReport.VerificationPolicyProfileID",
            )
            _bounded_string(body["DecisionReasonCode"], "ExecutionReport.DecisionReasonCode")
            _bounded_string(body["PolicyRuleID"], "ExecutionReport.PolicyRuleID")

            if "ReverifyBy" in body:
                _validate_iso_datetime(body["ReverifyBy"], "ExecutionReport.ReverifyBy")
            if "EvidenceRefs" in body:
                _validate_string_array(body["EvidenceRefs"], "ExecutionReport.EvidenceRefs")
            if "ExceptionApprovalRef" in body:
                _bounded_string(
                    body["ExceptionApprovalRef"],
                    "ExecutionReport.ExceptionApprovalRef",
                )
        return

    if message_type == "AmendRequest":
        _require_fields(body, ["LoadID", "AmendmentType", "ReasonCode"], "AmendRequest")
        _bounded_string(body["LoadID"], "AmendRequest.LoadID")
        _bounded_string(body["AmendmentType"], "AmendRequest.AmendmentType")
        _bounded_string(body["ReasonCode"], "AmendRequest.ReasonCode")
        return


def _track_unique_value(seen_set, value, label):
    if value in seen_set:
        raise ValueError(f"Replay detected for {label}: {value}")
    now_epoch = int(datetime.now(timezone.utc).timestamp())
    attempts = 0
    last_error = None
    while attempts < 2:
        attempts += 1
        with REPLAY_DB_LOCK:
            try:
                with sqlite3.connect(REPLAY_DB_PATH, timeout=5) as conn:
                    try:
                        conn.execute(
                            "INSERT INTO replay_cache(kind, value, seen_at) VALUES (?, ?, ?)",
                            (label, value, now_epoch),
                        )
                    except sqlite3.IntegrityError as exc:
                        raise ValueError(f"Replay detected for {label}: {value}") from exc
                    _cleanup_replay_db(conn, now_epoch)
                    conn.commit()
                last_error = None
                break
            except sqlite3.OperationalError as exc:
                last_error = exc
                # Recover from cold-start race where replay table/index is not initialized yet.
                if "no such table" in str(exc).lower():
                    _init_replay_db()
                    continue
                # Retry once for transient sqlite lock contention.
                if "database is locked" in str(exc).lower() and attempts < 2:
                    continue
                raise
    if last_error is not None:
        raise last_error
    seen_set.add(value)
    # Keep in-memory cache bounded while sqlite handles durability.
    if len(seen_set) > 200000:
        seen_set.pop()


def _parse_utc_timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _enforce_message_ttl(value):
    message_time = _parse_utc_timestamp(value)
    current_time = datetime.now(timezone.utc)
    delta_seconds = (current_time - message_time).total_seconds()
    if delta_seconds > MESSAGE_TTL_SECONDS:
        raise ValueError(
            f"Envelope.Timestamp exceeded TTL ({MESSAGE_TTL_SECONDS}s)."
        )
    if delta_seconds < -MAX_CLOCK_SKEW_SECONDS:
        raise ValueError(
            f"Envelope.Timestamp exceeds future clock skew allowance ({MAX_CLOCK_SKEW_SECONDS}s)."
        )


def validate_envelope(envelope, track_replay=True, track_state=True):
    _require_fields(
        envelope,
        [
            "Protocol",
            "ProtocolVersion",
            "MessageType",
            "From",
            "To",
            "Timestamp",
            "Body",
            "MessageID",
            "Nonce",
        ],
        "Envelope",
    )
    if envelope["Protocol"] != FaxpProtocol.NAME:
        raise ValueError("Envelope.Protocol mismatch.")
    if envelope["ProtocolVersion"] != FaxpProtocol.VERSION:
        raise ValueError("Envelope.ProtocolVersion mismatch.")
    _bounded_string(envelope["From"], "Envelope.From")
    _bounded_string(envelope["To"], "Envelope.To")
    if "RunID" in envelope:
        _bounded_string(envelope["RunID"], "Envelope.RunID")
    _bounded_string(envelope["MessageID"], "Envelope.MessageID")
    _bounded_string(envelope["Nonce"], "Envelope.Nonce")
    _validate_iso_datetime(envelope["Timestamp"], "Envelope.Timestamp")
    _enforce_message_ttl(envelope["Timestamp"])
    validate_message_body(envelope["MessageType"], envelope["Body"])
    _validate_route_policy(envelope)
    signature = envelope.get("Signature")
    signature_algorithm = envelope.get("SignatureAlgorithm")
    signature_key_id = envelope.get("SignatureKeyID")
    if signature is not None:
        _bounded_string(signature, "Envelope.Signature")
    if signature_algorithm is not None:
        _bounded_string(signature_algorithm, "Envelope.SignatureAlgorithm")
    if "SignatureKeyID" in envelope:
        _bounded_string(envelope["SignatureKeyID"], "Envelope.SignatureKeyID")
    if NON_LOCAL_MODE:
        if not signature:
            raise ValueError("Envelope signature is required in non-local mode.")
        if not signature_key_id:
            raise ValueError("Envelope.SignatureKeyID is required in non-local mode.")
        if not signature_algorithm:
            raise ValueError("Envelope.SignatureAlgorithm is required in non-local mode.")
        if signature_algorithm != SIGNATURE_SCHEME:
            raise ValueError("Envelope.SignatureAlgorithm does not match configured scheme.")
    if signature:
        if signature_algorithm == "HMAC_SHA256":
            if signature_key_id not in MESSAGE_SIGNING_KEYS:
                raise ValueError("Envelope.SignatureKeyID is not trusted.")
            payload = {k: v for k, v in envelope.items() if k != "Signature"}
            if not _verify_with_key_ring(
                payload,
                signature,
                signature_key_id,
                MESSAGE_SIGNING_KEYS,
            ):
                raise ValueError("Envelope signature verification failed.")
        elif signature_algorithm == "ED25519":
            if not _verify_asymmetric(envelope):
                raise ValueError("Envelope ED25519 signature verification failed.")
        else:
            raise ValueError("Unsupported Envelope.SignatureAlgorithm.")
    if track_replay:
        _track_unique_value(SEEN_MESSAGE_IDS, envelope["MessageID"], "MessageID")
        _track_unique_value(SEEN_NONCES, envelope["Nonce"], "Nonce")
    if track_state:
        with STATE_LOCK:
            _enforce_state_transition(envelope)


def apply_message_signature(envelope):
    if SIGNATURE_SCHEME == "ED25519":
        return _sign_asymmetric(envelope)
    if SIGNATURE_SCHEME == "HMAC_SHA256":
        if not MESSAGE_SIGNING_KEY:
            return envelope
        envelope["SignatureAlgorithm"] = "HMAC_SHA256"
        envelope["SignatureKeyID"] = MESSAGE_SIGNING_ACTIVE_KEY_ID
        payload = {k: v for k, v in envelope.items() if k != "Signature"}
        envelope["Signature"] = sign_payload(payload, MESSAGE_SIGNING_KEY)
        return envelope
    return envelope


def build_envelope(sender, receiver, message_type, body):
    run_id = get_protocol_run_id()
    envelope = {
        "Protocol": FaxpProtocol.NAME,
        "ProtocolVersion": FaxpProtocol.VERSION,
        "RunID": run_id,
        "MessageType": message_type,
        "From": sender,
        "To": receiver,
        "Timestamp": now_utc(),
        "MessageID": str(uuid4()),
        "Nonce": uuid4().hex,
        "Body": body,
    }
    return apply_message_signature(envelope)


def log_message(sender, receiver, message_type, body):
    """Print a clear message envelope and body."""
    envelope = build_envelope(sender, receiver, message_type, body)
    try:
        validate_envelope(envelope)
        _append_audit_event(envelope, validation_status="pass")
    except Exception:
        _append_audit_event(envelope, validation_status="fail")
        raise
    print(f"\n[{sender} -> {receiver}] {message_type}")
    print(json.dumps(redact_sensitive(envelope), indent=2))
    return envelope


def _normalize_digits(value):
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _normalize_mc(value):
    digits = _normalize_digits(value)
    if not digits:
        return ""
    return digits.lstrip("0") or "0"


def _unknown_fmcsa_top_level_keys(payload):
    if not isinstance(payload, dict):
        return []
    unknown = []
    for key in payload.keys():
        normalized = str(key).strip().lower()
        if normalized and normalized not in FMCSA_EXPECTED_TOP_LEVEL_KEYS:
            unknown.append(str(key))
    return sorted(unknown)


def _log_fmcsa_contract_drift(endpoint, payload):
    if not FMCSA_LOG_UNKNOWN_KEYS:
        return
    unknown = _unknown_fmcsa_top_level_keys(payload)
    if not unknown:
        return

    signature = f"{endpoint}|{','.join(unknown)}"
    with STATE_LOCK:
        if signature in FMCSA_DRIFT_WARNED_SIGNATURES:
            return
        FMCSA_DRIFT_WARNED_SIGNATURES.add(signature)

    print(
        f"[WARN] FMCSA response contract drift detected from {endpoint}. "
        f"Unknown top-level keys: {unknown}",
        file=sys.stderr,
    )


def _status_is_active(value):
    text = str(value or "").strip().upper()
    if not text:
        return False
    if "INACTIVE" in text or "NOT AUTH" in text or "OUT OF SERVICE" in text:
        return False
    if text in {"A", "ACT", "ACTIVE", "AUTHORIZED"}:
        return True
    if text.startswith("ACTIVE") or text.startswith("AUTH"):
        return True
    return False


def _value_indicates_present(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value > 0
    text = str(value or "").strip()
    if not text:
        return False
    normalized = text.upper().replace(",", "").replace("$", "")
    if normalized in {"NO", "N", "NONE", "FALSE", "0", "0.0", "0.00", "N/A", "NA"}:
        return False
    if normalized in {"YES", "Y", "TRUE", "ACTIVE", "AUTHORIZED"}:
        return True
    numeric_match = re.search(r"[-+]?\d*\.?\d+", normalized)
    if numeric_match:
        try:
            return float(numeric_match.group(0)) > 0
        except ValueError:
            return False
    return True


def _parse_bool_flag(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    text = str(value or "").strip().lower()
    if not text:
        return None
    if text in {"1", "true", "t", "yes", "y", "on", "active", "authorized"}:
        return True
    if text in {"0", "false", "f", "no", "n", "off", "inactive"}:
        return False
    return None


def _extract_first_value(mapping, keys):
    for key in keys:
        if key in mapping:
            value = mapping[key]
            if value is not None and value != "":
                return value
    return None


def _iter_dicts(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _iter_dicts(child)
        return
    if isinstance(value, list):
        for item in value:
            yield from _iter_dicts(item)


def _score_fmcsa_candidate(record, target_mc):
    if not isinstance(record, dict):
        return -1

    mc_value = _extract_first_value(
        record,
        ["docketNumber", "mcNumber", "mc_number", "docket_number", "docket", "mc"],
    )
    mc_digits = _normalize_mc(mc_value)
    score = 0
    if target_mc and mc_digits == target_mc:
        score += 100
    elif mc_digits:
        score += 20

    if _extract_first_value(record, ["legalName", "carrierName", "name"]):
        score += 10
    if _extract_first_value(record, ["dotNumber", "usdotNumber", "usdot_number"]):
        score += 10
    if _extract_first_value(
        record,
        [
            "operatingStatus",
            "commonAuthorityStatus",
            "contractAuthorityStatus",
            "brokerAuthorityStatus",
            "authorityStatus",
            "allowedToOperate",
            "interstateAuthority",
            "interstateAuthorityOk",
        ],
    ):
        score += 10
    return score


def _record_looks_like_carrier_profile(record):
    keys = {
        "legalName",
        "carrierName",
        "name",
        "dotNumber",
        "usdotNumber",
        "usdot_number",
        "operatingStatus",
        "commonAuthorityStatus",
        "contractAuthorityStatus",
        "brokerAuthorityStatus",
        "bipdInsuranceOnFile",
        "bipdOnFile",
        "insuranceOnFile",
    }
    return any(key in record for key in keys)


def _select_fmcsa_candidate(payload, target_mc):
    best_score = -1
    best_record = None
    for record in _iter_dicts(payload):
        if not _record_looks_like_carrier_profile(record):
            continue
        score = _score_fmcsa_candidate(record, target_mc)
        if score > best_score:
            best_score = score
            best_record = record
    return best_record if best_score >= 20 else None


def _normalize_fmcsa_live_payload(payload, requested_mc):
    target_mc = _normalize_mc(requested_mc)
    record = _select_fmcsa_candidate(payload, target_mc)
    if not record:
        return {
            "found": False,
            "status": "Fail",
            "score": 10,
            "usdot_number": None,
            "mc_number": target_mc or None,
            "carrier_name": None,
            "operating_status": None,
            "has_current_insurance": False,
            "interstate_authority_ok": False,
        }

    mc_value = _extract_first_value(
        record,
        ["docketNumber", "mcNumber", "mc_number", "docket_number", "docket", "mc"],
    )
    mc_digits = _normalize_mc(mc_value) or target_mc
    if target_mc and mc_digits != target_mc:
        return {
            "found": False,
            "status": "Fail",
            "score": 10,
            "usdot_number": None,
            "mc_number": target_mc,
            "carrier_name": None,
            "operating_status": None,
            "has_current_insurance": False,
            "interstate_authority_ok": False,
        }

    common_status = _extract_first_value(
        record,
        ["commonAuthorityStatus", "common_authority_status", "commonAuthority"],
    )
    contract_status = _extract_first_value(
        record,
        ["contractAuthorityStatus", "contract_authority_status", "contractAuthority"],
    )
    broker_status = _extract_first_value(
        record,
        ["brokerAuthorityStatus", "broker_authority_status", "brokerAuthority"],
    )
    operating_status_raw = _extract_first_value(
        record,
        ["operatingStatus", "authorityStatus", "status"],
    )

    authority_signals = [
        common_status,
        contract_status,
        broker_status,
        _extract_first_value(record, ["allowedToOperate", "interstateAuthority"]),
        operating_status_raw,
    ]
    active = any(_status_is_active(signal) for signal in authority_signals if signal is not None)

    status_parts = []
    if common_status is not None:
        status_parts.append(f"Common={common_status}")
    if contract_status is not None:
        status_parts.append(f"Contract={contract_status}")
    if broker_status is not None:
        status_parts.append(f"Broker={broker_status}")
    if not status_parts and operating_status_raw is not None:
        status_parts.append(str(operating_status_raw))
    operating_status = "; ".join(status_parts) if status_parts else None

    insurance_flags = []
    for key in [
        "bipdInsuranceOnFile",
        "bipdOnFile",
        "bipd_on_file",
        "bipdInsuranceAmountOnFile",
        "bipdAmountOnFile",
        "insuranceOnFileAmount",
        "cargoInsuranceOnFile",
        "insuranceOnFile",
        "hasCurrentInsurance",
        "has_current_insurance",
    ]:
        if key in record:
            value = record.get(key)
            parsed = _parse_bool_flag(value)
            if parsed is not None:
                insurance_flags.append(parsed)
            else:
                insurance_flags.append(_value_indicates_present(value))
    insurance_text = _extract_first_value(
        record,
        ["insuranceStatus", "bipdInsuranceStatus", "cargoInsuranceStatus"],
    )
    if not insurance_flags and insurance_text is not None:
        insurance_flags.append(_status_is_active(insurance_text))
    has_current_insurance = any(insurance_flags) if insurance_flags else False

    interstate_signals = []
    for key in [
        "interstateAuthorityOk",
        "interstate_authority_ok",
        "allowedToOperate",
        "commonAuthorityActive",
        "commonAuthority",
    ]:
        if key in record:
            parsed = _parse_bool_flag(record.get(key))
            if parsed is not None:
                interstate_signals.append(parsed)
    if not interstate_signals:
        interstate_signals.extend(
            _status_is_active(signal) for signal in authority_signals if signal is not None
        )
    interstate_authority_ok = any(interstate_signals) if interstate_signals else False

    score = 50
    if active:
        score += 20
    if has_current_insurance:
        score += 15
    if interstate_authority_ok:
        score += 15
    status = "Success" if (active and has_current_insurance and interstate_authority_ok) else "Fail"

    return {
        "found": True,
        "status": status,
        "score": int(score),
        "usdot_number": _extract_first_value(
            record,
            ["dotNumber", "usdotNumber", "usdot_number", "dot_number"],
        ),
        "mc_number": mc_digits,
        "carrier_name": _extract_first_value(record, ["legalName", "carrierName", "name"]),
        "operating_status": operating_status,
        "has_current_insurance": has_current_insurance,
        "interstate_authority_ok": interstate_authority_ok,
    }


def lookup_fmcsa_live_api(mc_number):
    """Query FMCSA QCMobile API for MC compliance signals."""
    target_mc = _normalize_mc(mc_number)
    if not target_mc:
        return {"ok": False, "error": "No MC number provided for live FMCSA verification."}
    if not FMCSA_WEBKEY:
        return {"ok": False, "error": "Missing FAXP_FMCSA_WEBKEY for live FMCSA verification."}

    base_url = (FMCSA_API_BASE_URL or "").strip().rstrip("/")
    if not base_url:
        return {"ok": False, "error": "FAXP_FMCSA_API_BASE_URL is not configured."}

    endpoints = [
        f"{base_url}/carriers/docket-number/{urllib.parse.quote(target_mc)}",
        f"{base_url}/carriers/{urllib.parse.quote(target_mc)}",
    ]
    errors = []
    for endpoint in endpoints:
        url = endpoint + "?webKey=" + urllib.parse.quote(FMCSA_WEBKEY)
        request = urllib.request.Request(
            url,
            headers={"Accept": "application/json"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=FMCSA_API_TIMEOUT_SECONDS) as response:
                raw_text = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            errors.append(f"{endpoint} -> HTTP {exc.code}: {body[:180]}")
            continue
        except urllib.error.URLError as exc:
            errors.append(f"{endpoint} -> {exc.reason}")
            continue
        except Exception as exc:
            errors.append(f"{endpoint} -> {exc}")
            continue

        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError:
            errors.append(f"{endpoint} -> non-JSON response.")
            continue

        _log_fmcsa_contract_drift(endpoint, payload)
        normalized = _normalize_fmcsa_live_payload(payload, target_mc)
        try:
            _validate_carrier_finder_payload(normalized, requested_mc=target_mc)
        except ValueError as exc:
            errors.append(f"{endpoint} -> response validation error: {exc}")
            continue

        normalized["ok"] = True
        return normalized

    joined = "; ".join(errors) if errors else "Unknown FMCSA response error."
    return {"ok": False, "error": f"live-fmcsa query failed: {joined}"}


def _validate_carrier_finder_payload(payload, requested_mc):
    if not isinstance(payload, dict):
        raise ValueError("carrier-finder response must be a JSON object.")

    required = {
        "found",
        "status",
        "score",
        "usdot_number",
        "mc_number",
        "carrier_name",
        "operating_status",
        "has_current_insurance",
        "interstate_authority_ok",
    }
    extras = set(payload.keys()) - required
    if extras:
        raise ValueError(f"carrier-finder returned unexpected fields: {sorted(extras)}")

    missing = [field for field in required if field not in payload]
    if missing:
        raise ValueError(f"carrier-finder response missing fields: {missing}")

    if not isinstance(payload["found"], bool):
        raise ValueError("carrier-finder 'found' must be boolean.")
    if payload["status"] not in {"Success", "Fail"}:
        raise ValueError("carrier-finder 'status' must be Success or Fail.")
    if not isinstance(payload["score"], (int, float)) or not (0 <= payload["score"] <= 100):
        raise ValueError("carrier-finder 'score' must be between 0 and 100.")
    if not isinstance(payload["has_current_insurance"], bool):
        raise ValueError("carrier-finder 'has_current_insurance' must be boolean.")
    if not isinstance(payload["interstate_authority_ok"], bool):
        raise ValueError("carrier-finder 'interstate_authority_ok' must be boolean.")

    target_mc = _normalize_mc(requested_mc)
    returned_mc = _normalize_mc(payload.get("mc_number"))
    if target_mc and returned_mc != target_mc:
        raise ValueError("carrier-finder returned an MC number that does not match the request.")

    if payload["status"] == "Success" and not payload["found"]:
        raise ValueError("carrier-finder returned Success with found=false.")


def _normalize_hosted_adapter_payload(payload, requested_mc):
    """
    Accept both legacy carrier-finder style and neutral translator style payloads.

    Returns a normalized compatibility dict with fields consumed by run_verification().
    """
    if not isinstance(payload, dict):
        raise ValueError("hosted adapter payload must be a JSON object.")

    if "VerificationResult" not in payload:
        legacy_payload = dict(payload)
        legacy_payload.pop("ok", None)
        legacy_payload.pop("error", None)
        _validate_carrier_finder_payload(legacy_payload, requested_mc=requested_mc)
        return legacy_payload

    verification_result = payload.get("VerificationResult")
    if not isinstance(verification_result, dict):
        raise ValueError("hosted adapter VerificationResult must be an object.")
    _require_fields(
        verification_result,
        [
            "status",
            "category",
            "method",
            "provider",
            "assuranceLevel",
            "score",
            "token",
            "evidenceRef",
            "verifiedAt",
        ],
        "hosted adapter VerificationResult",
    )
    if verification_result["status"] not in VALID_VERIFICATION_STATUSES:
        raise ValueError(
            "hosted adapter VerificationResult.status must be one of "
            f"{sorted(VALID_VERIFICATION_STATUSES)}."
        )
    if verification_result["category"] not in KNOWN_VERIFICATION_CATEGORIES:
        raise ValueError("hosted adapter VerificationResult.category is not recognized.")
    if verification_result["method"] not in KNOWN_VERIFICATION_METHODS:
        raise ValueError("hosted adapter VerificationResult.method is not recognized.")
    if (
        verification_result["category"],
        verification_result["method"],
    ) not in KNOWN_VERIFICATION_CATEGORY_METHOD_PAIRS:
        raise ValueError("hosted adapter VerificationResult.category/method combination is not recognized.")
    if not isinstance(verification_result["score"], (int, float)) or not (
        0 <= verification_result["score"] <= 100
    ):
        raise ValueError("hosted adapter VerificationResult.score must be between 0 and 100.")
    _bounded_string(verification_result["provider"], "hosted adapter VerificationResult.provider")
    _bounded_string(
        verification_result["assuranceLevel"],
        "hosted adapter VerificationResult.assuranceLevel",
    )
    _bounded_string(verification_result["token"], "hosted adapter VerificationResult.token")
    _bounded_string(
        verification_result["evidenceRef"],
        "hosted adapter VerificationResult.evidenceRef",
    )
    _validate_iso_datetime(
        verification_result["verifiedAt"],
        "hosted adapter VerificationResult.verifiedAt",
    )
    if _contains_forbidden_biometric_field(verification_result):
        raise ValueError("hosted adapter VerificationResult must not include raw biometric artifacts.")

    provider_extensions = payload.get("ProviderExtensions")
    if provider_extensions is None:
        provider_extensions = {}
    if not isinstance(provider_extensions, dict):
        raise ValueError("hosted adapter ProviderExtensions must be an object.")

    carrier = provider_extensions.get("carrier")
    if carrier is None:
        carrier = {}
    if not isinstance(carrier, dict):
        raise ValueError("hosted adapter ProviderExtensions.carrier must be an object.")

    target_mc = _normalize_mc(requested_mc)
    mc_number = _normalize_mc(
        provider_extensions.get("mcNumber")
        or carrier.get("mc")
        or target_mc
    )
    if target_mc and mc_number and mc_number != target_mc:
        raise ValueError("hosted adapter returned an MC number that does not match the request.")

    status_value = str(verification_result.get("status") or "Fail")
    if status_value not in VALID_VERIFICATION_STATUSES:
        status_value = "Fail"

    score_value = verification_result.get("score", 0)
    if not isinstance(score_value, (int, float)):
        raise ValueError("hosted adapter VerificationResult.score must be numeric.")
    score = int(round(float(score_value)))
    score = max(0, min(100, score))

    has_current_insurance = bool(carrier.get("hasCurrentInsurance"))
    interstate_authority_ok = bool(carrier.get("interstateAuthorityOk"))
    normalized_payload = {
        "found": bool(mc_number),
        "status": status_value,
        "score": score,
        "usdot_number": carrier.get("usdot"),
        "mc_number": mc_number or target_mc or None,
        "carrier_name": carrier.get("name"),
        "operating_status": carrier.get("operatingStatus"),
        "has_current_insurance": has_current_insurance,
        "interstate_authority_ok": interstate_authority_ok,
    }
    return normalized_payload


def _unwrap_verifier_payload_wrapper(
    wrapper,
    source_name,
    require_payload_wrapper,
    require_signature,
):
    if not isinstance(wrapper, dict):
        raise ValueError(f"{source_name} output must be a JSON object.")
    if require_payload_wrapper and "payload" not in wrapper:
        raise ValueError(f"{source_name} output missing payload wrapper.")
    if "payload" not in wrapper:
        return wrapper

    payload = wrapper.get("payload")
    signature = wrapper.get("signature")
    signature_key_id = wrapper.get("signature_key_id")
    signature_algorithm = str(wrapper.get("signature_algorithm") or "").upper()

    if require_signature:
        if signature_algorithm != VERIFIER_SIGNATURE_SCHEME:
            raise ValueError("Verifier signature algorithm mismatch.")
        if not signature_key_id:
            raise ValueError("Verifier signature key ID missing.")
        if signature_algorithm == "HMAC_SHA256":
            if not VERIFIER_SIGNING_KEYS:
                raise ValueError(
                    "Missing verifier HMAC signing key material for signed verifier mode."
                )
            if signature_key_id not in VERIFIER_SIGNING_KEYS:
                raise ValueError("Verifier signature key ID is not trusted.")
            if not _verify_with_key_ring(
                payload,
                signature,
                signature_key_id,
                VERIFIER_SIGNING_KEYS,
            ):
                raise ValueError("Verifier signature validation failed.")
        elif signature_algorithm == "ED25519":
            if signature_key_id not in VERIFIER_ED25519_PUBLIC_KEYS:
                raise ValueError("Verifier ED25519 signature key ID is not trusted.")
            if not _verify_ed25519_with_public_key_ring(
                payload,
                signature,
                signature_key_id,
                VERIFIER_ED25519_PUBLIC_KEYS,
            ):
                raise ValueError("Verifier ED25519 signature validation failed.")
        else:
            raise ValueError("Unsupported verifier signature algorithm.")

    return payload


def lookup_fmcsa_with_carrier_finder(mc_number, carrier_finder_path):
    """Query carrier-finder for MC compliance signals."""
    if not mc_number:
        return {"ok": False, "error": "No MC number provided."}

    try:
        allowed_path = resolve_allowed_carrier_finder_path(carrier_finder_path)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}

    venv_python = os.path.join(allowed_path, ".venv", "bin", "python")
    inline_code = (
        "import base64,hashlib,hmac,json,os,subprocess,sys,tempfile\n"
        "from backend.app.repositories import search_carriers\n"
        "def d(v):\n"
        "    digits = ''.join(ch for ch in str(v or '') if ch.isdigit())\n"
        "    return (digits.lstrip('0') or '0') if digits else ''\n"
        "def cj(v):\n"
        "    return json.dumps(v, sort_keys=True, separators=(',', ':'))\n"
        "mc = sys.argv[1].strip()\n"
        "payload = search_carriers(\n"
        "    query=mc,\n"
        "    state=None,\n"
        "    min_power_units=None,\n"
        "    cargo_type=None,\n"
        "    interstate_authority_only=False,\n"
        "    valid_insurance_only=False,\n"
        "    min_auto_liability_limit=None,\n"
        "    requires_cargo_coverage=False,\n"
        "    min_cargo_limit=None,\n"
        "    insurance_source_mode='authoritative_only',\n"
        "    risk_band=None,\n"
        "    quality_band=None,\n"
        "    safety_rating_status=None,\n"
        "    safety_freshness=None,\n"
        "    sort_by='power_units',\n"
        "    sort_dir='desc',\n"
        "    limit=50,\n"
        "    offset=0,\n"
        ")\n"
        "items = payload.get('items') or []\n"
        "target = d(mc)\n"
        "exact = None\n"
        "for row in items:\n"
        "    if d(row.get('mc_number')) == target:\n"
        "        exact = row\n"
        "        break\n"
        "if exact:\n"
        "    operating = str(exact.get('operating_status') or '')\n"
        "    active = operating.upper().startswith('ACTIVE') or operating.upper() in {'A','ACT','ACTIVE','AUTHORIZED'}\n"
        "    has_ins = bool(exact.get('has_current_insurance'))\n"
        "    interstate = bool(exact.get('interstate_authority_ok'))\n"
        "    score = 50 + (20 if active else 0) + (15 if has_ins else 0) + (15 if interstate else 0)\n"
        "    status = 'Success' if (active and has_ins and interstate) else 'Fail'\n"
        "    out = {\n"
        "        'found': True,\n"
        "        'status': status,\n"
        "        'score': int(score),\n"
        "        'usdot_number': exact.get('usdot_number'),\n"
        "        'mc_number': exact.get('mc_number'),\n"
        "        'carrier_name': exact.get('legal_name'),\n"
        "        'operating_status': operating,\n"
        "        'has_current_insurance': has_ins,\n"
        "        'interstate_authority_ok': interstate,\n"
        "    }\n"
        "else:\n"
        "    out = {\n"
        "        'found': False,\n"
        "        'status': 'Fail',\n"
        "        'score': 10,\n"
        "        'usdot_number': None,\n"
        "        'mc_number': mc,\n"
        "        'carrier_name': None,\n"
        "        'operating_status': None,\n"
        "        'has_current_insurance': False,\n"
        "        'interstate_authority_ok': False,\n"
        "    }\n"
        "scheme = (os.getenv('FAXP_VERIFIER_SIGNATURE_SCHEME', 'HMAC_SHA256') or 'HMAC_SHA256').upper()\n"
        "kid = os.getenv('FAXP_VERIFIER_SIGNING_KEY_ID', '')\n"
        "sig = ''\n"
        "if scheme == 'ED25519':\n"
        "    key_path = os.getenv('FAXP_VERIFIER_ED25519_PRIVATE_KEY_PATH', '').strip()\n"
        "    if key_path:\n"
        "        msg = tempfile.NamedTemporaryFile(delete=False)\n"
        "        sigf = tempfile.NamedTemporaryFile(delete=False)\n"
        "        try:\n"
        "            msg.write(cj(out).encode('utf-8'))\n"
        "            msg.flush(); msg.close(); sigf.close()\n"
        "            proc = subprocess.run(['openssl', 'pkeyutl', '-sign', '-inkey', key_path, '-in', msg.name, '-out', sigf.name], capture_output=True, check=False)\n"
        "            if proc.returncode == 0:\n"
        "                with open(sigf.name, 'rb') as h:\n"
        "                    sig = base64.b64encode(h.read()).decode('ascii')\n"
        "        finally:\n"
        "            for p in (msg.name, sigf.name):\n"
        "                try:\n"
        "                    os.remove(p)\n"
        "                except OSError:\n"
        "                    pass\n"
        "elif scheme == 'HMAC_SHA256':\n"
        "    key = os.getenv('FAXP_VERIFIER_SIGNING_KEY', '')\n"
        "    if key:\n"
        "        sig = hmac.new(key.encode('utf-8'), cj(out).encode('utf-8'), hashlib.sha256).hexdigest()\n"
        "print(json.dumps({'payload': out, 'signature': sig, 'signature_key_id': kid, 'signature_algorithm': scheme}))\n"
    )

    try:
        verifier_signing_key_id = VERIFIER_SIGNING_ACTIVE_KEY_ID
        if VERIFIER_SIGNATURE_SCHEME == "ED25519":
            verifier_signing_key_id = VERIFIER_ED25519_ACTIVE_KEY_ID
        subprocess_env = {
            "PATH": os.environ.get("PATH", ""),
            "LANG": os.environ.get("LANG", "C"),
            "LC_ALL": os.environ.get("LC_ALL", "C"),
            "FAXP_VERIFIER_SIGNATURE_SCHEME": VERIFIER_SIGNATURE_SCHEME,
            "FAXP_VERIFIER_SIGNING_KEY": VERIFIER_SIGNING_KEY.decode("utf-8"),
            "FAXP_VERIFIER_SIGNING_KEY_ID": verifier_signing_key_id,
            "FAXP_VERIFIER_ED25519_PRIVATE_KEY_PATH": VERIFIER_ED25519_PRIVATE_KEY_PATH,
        }
        completed = subprocess.run(
            [venv_python, "-c", inline_code, str(mc_number)],
            cwd=allowed_path,
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
            env=subprocess_env,
        )
    except Exception as exc:
        return {"ok": False, "error": f"carrier-finder call failed: {exc}"}

    if completed.returncode != 0:
        error = {"ok": False, "error": "carrier-finder verification failed."}
        if DEBUG_MODE:
            error["debug"] = (completed.stderr or "").strip()[:500]
        return error

    lines = [line.strip() for line in (completed.stdout or "").splitlines() if line.strip()]
    if not lines:
        return {"ok": False, "error": "carrier-finder returned no output."}

    try:
        wrapper = json.loads(lines[-1])
    except json.JSONDecodeError:
        return {
            "ok": False,
            "error": "carrier-finder output was not valid JSON.",
        }

    try:
        payload = _unwrap_verifier_payload_wrapper(
            wrapper=wrapper,
            source_name="carrier-finder",
            require_payload_wrapper=True,
            require_signature=REQUIRE_SIGNED_VERIFIER,
        )
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}

    try:
        _validate_carrier_finder_payload(payload, requested_mc=mc_number)
    except ValueError as exc:
        return {"ok": False, "error": f"carrier-finder validation error: {exc}"}

    payload["ok"] = True
    return payload


def lookup_fmcsa_with_hosted_adapter(mc_number):
    """Query a hosted FMCSA adapter service for normalized compliance signals."""
    target_mc = _normalize_mc(mc_number)
    if not target_mc:
        return {"ok": False, "error": "No MC number provided for hosted FMCSA verification."}

    base_url = (FMCSA_ADAPTER_BASE_URL or "").strip()
    if not base_url:
        return {"ok": False, "error": "Missing FAXP_FMCSA_ADAPTER_BASE_URL for hosted adapter."}

    endpoint = base_url.rstrip("/")
    parsed_endpoint = urllib.parse.urlsplit(endpoint)
    if parsed_endpoint.scheme not in {"http", "https"}:
        return {"ok": False, "error": "Invalid hosted adapter URL scheme."}
    if NON_LOCAL_MODE and parsed_endpoint.scheme != "https":
        return {"ok": False, "error": "Hosted adapter URL must use HTTPS in non-local mode."}
    if not parsed_endpoint.netloc:
        return {"ok": False, "error": "Hosted adapter URL is missing host information."}

    canonical_path = parsed_endpoint.path or "/"
    if parsed_endpoint.query:
        canonical_path = canonical_path + "?" + parsed_endpoint.query

    request_body = json.dumps({"mcNumber": target_mc}).encode("utf-8")
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "FAXP-AdapterClient/0.2",
        "X-FAXP-Request-Id": str(uuid4()),
    }
    if FMCSA_ADAPTER_AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {FMCSA_ADAPTER_AUTH_TOKEN}"
    if FMCSA_ADAPTER_SIGN_REQUESTS:
        if not FMCSA_ADAPTER_REQUEST_SIGNING_ACTIVE_KEY_ID or not FMCSA_ADAPTER_REQUEST_SIGNING_KEY:
            return {
                "ok": False,
                "error": "Hosted adapter request signing is enabled but request key material is missing.",
            }
        timestamp_text = now_utc()
        nonce = uuid4().hex
        signature = _build_adapter_request_signature(
            method="POST",
            path=canonical_path,
            timestamp_text=timestamp_text,
            nonce=nonce,
            body_bytes=request_body,
            key=FMCSA_ADAPTER_REQUEST_SIGNING_KEY,
        )
        headers["X-FAXP-Key-Id"] = FMCSA_ADAPTER_REQUEST_SIGNING_ACTIVE_KEY_ID
        headers["X-FAXP-Timestamp"] = timestamp_text
        headers["X-FAXP-Nonce"] = nonce
        headers["X-FAXP-Signature"] = signature

    request = urllib.request.Request(
        endpoint,
        data=request_body,
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=FMCSA_ADAPTER_TIMEOUT_SECONDS) as response:
            raw_text = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        if exc.code in {401, 403}:
            return {"ok": False, "error": "Hosted adapter authentication rejected."}
        if exc.code == 429:
            return {"ok": False, "error": "Hosted adapter rate limit exceeded."}
        if 500 <= exc.code < 600:
            return {"ok": False, "error": "Hosted adapter upstream error."}
        return {"ok": False, "error": f"Hosted adapter HTTP error ({exc.code})."}
    except urllib.error.URLError as exc:
        return {"ok": False, "error": "Hosted adapter network error."}
    except Exception:
        return {"ok": False, "error": "Hosted adapter call failed."}

    try:
        wrapper = json.loads(raw_text)
    except json.JSONDecodeError:
        return {"ok": False, "error": "hosted adapter returned non-JSON response."}

    require_signed_wrapper = FMCSA_ADAPTER_REQUIRE_SIGNED_WRAPPER or REQUIRE_SIGNED_VERIFIER
    try:
        payload = _unwrap_verifier_payload_wrapper(
            wrapper=wrapper,
            source_name="hosted adapter",
            require_payload_wrapper=require_signed_wrapper,
            require_signature=require_signed_wrapper,
        )
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}

    if not isinstance(payload, dict):
        return {"ok": False, "error": "hosted adapter payload must be a JSON object."}
    if payload.get("ok") is False:
        return {
            "ok": False,
            "error": str(
                payload.get("error")
                or (payload.get("ProviderExtensions") or {}).get("error")
                or "Hosted adapter returned failure."
            ),
        }

    try:
        normalized_payload = _normalize_hosted_adapter_payload(payload, requested_mc=target_mc)
    except ValueError as exc:
        return {"ok": False, "error": f"hosted adapter validation error: {exc}"}

    normalized_payload["ok"] = True
    return normalized_payload


def run_verification(
    provider,
    status,
    mc_number=None,
    carrier_finder_path=None,
    fmcsa_source="carrier-finder",
):
    """
    Verification providers:
    - FMCSA / MockComplianceProvider: compliance check -> Basic badge (on success)
    - MockBiometricProvider / iDenfy alias: biometric check -> Premium badge (on success)
    """
    requested_provider = str(provider or "").strip()
    normalized_provider = normalize_verification_provider(requested_provider)

    def build_result(
        status_value,
        provider_value,
        category,
        method,
        assurance_level,
        score_value,
        token_value,
        source_value,
        source_authority=None,
        extra=None,
    ):
        result = {
            "status": status_value,
            "provider": provider_value,
            "category": category,
            "method": method,
            "assuranceLevel": assurance_level,
            "score": int(score_value),
            "token": token_value,
            "source": source_value,
            "verifiedAt": now_utc(),
            "evidenceRef": f"sha256:{hashlib.sha256(token_value.encode('utf-8')).hexdigest()[:24]}",
        }
        if source_authority:
            result["sourceAuthority"] = source_authority
        if requested_provider and requested_provider != provider_value:
            result["providerAlias"] = requested_provider
        if extra:
            result.update(extra)
        if REQUIRE_SIGNED_VERIFIER:
            attestation_payload = {k: v for k, v in result.items() if k != "attestation"}
            result["attestation"] = _build_verifier_attestation(attestation_payload)
        return result

    if normalized_provider == "FMCSA":
        fm_token = f"fmcsa-{uuid4().hex[:14]}"
        if fmcsa_source == "hosted-adapter":
            live = lookup_fmcsa_with_hosted_adapter(mc_number=mc_number)
            if live.get("ok"):
                live_status = live.get("status", "Fail")
                score = int(live.get("score", 0))
                badge = "Basic" if live_status == "Success" else "None"
                verification_result = build_result(
                    status_value=live_status,
                    provider_value=NEUTRAL_VERIFICATION_PROVIDER_IDS["fmcsa_hosted_adapter"],
                    category="Compliance",
                    method="AuthorityRecordCheck",
                    assurance_level="AAL1",
                    score_value=score,
                    token_value=fm_token,
                    source_value="hosted-adapter",
                    source_authority="FMCSA",
                    extra={
                        "mcNumber": _normalize_mc(mc_number),
                        "carrier": {
                            "usdot": live.get("usdot_number"),
                            "mc": live.get("mc_number"),
                            "name": live.get("carrier_name"),
                            "operatingStatus": live.get("operating_status"),
                            "hasCurrentInsurance": live.get("has_current_insurance"),
                            "interstateAuthorityOk": live.get("interstate_authority_ok"),
                        },
                    },
                )
                return verification_result, badge

            verification_result = build_result(
                status_value="Fail",
                provider_value=NEUTRAL_VERIFICATION_PROVIDER_IDS["fmcsa_hosted_adapter"],
                category="Compliance",
                method="AuthorityRecordCheck",
                assurance_level="AAL1",
                score_value=0,
                token_value=fm_token,
                source_value="hosted-adapter",
                source_authority="FMCSA",
                extra={
                    "mcNumber": _normalize_mc(mc_number),
                    "error": live.get("error", "Unknown hosted FMCSA adapter error."),
                },
            )
            return verification_result, "None"

        if fmcsa_source == "live-fmcsa":
            live = lookup_fmcsa_live_api(mc_number=mc_number)
            if live.get("ok"):
                live_status = live.get("status", "Fail")
                score = int(live.get("score", 0))
                badge = "Basic" if live_status == "Success" else "None"
                verification_result = build_result(
                    status_value=live_status,
                    provider_value=NEUTRAL_VERIFICATION_PROVIDER_IDS["fmcsa_live"],
                    category="Compliance",
                    method="AuthorityRecordCheck",
                    assurance_level="AAL1",
                    score_value=score,
                    token_value=fm_token,
                    source_value="live-fmcsa",
                    source_authority="FMCSA",
                    extra={
                        "mcNumber": _normalize_mc(mc_number),
                        "carrier": {
                            "usdot": live.get("usdot_number"),
                            "mc": live.get("mc_number"),
                            "name": live.get("carrier_name"),
                            "operatingStatus": live.get("operating_status"),
                            "hasCurrentInsurance": live.get("has_current_insurance"),
                            "interstateAuthorityOk": live.get("interstate_authority_ok"),
                        },
                    },
                )
                return verification_result, badge

            verification_result = build_result(
                status_value="Fail",
                provider_value=NEUTRAL_VERIFICATION_PROVIDER_IDS["fmcsa_live"],
                category="Compliance",
                method="AuthorityRecordCheck",
                assurance_level="AAL1",
                score_value=0,
                token_value=fm_token,
                source_value="live-fmcsa",
                source_authority="FMCSA",
                extra={
                    "mcNumber": _normalize_mc(mc_number),
                    "error": live.get("error", "Unknown FMCSA API error."),
                },
            )
            return verification_result, "None"

        if fmcsa_source == "carrier-finder" and mc_number:
            live = lookup_fmcsa_with_carrier_finder(
                mc_number=mc_number,
                carrier_finder_path=carrier_finder_path
                or DEFAULT_CARRIER_FINDER_PATH,
            )
            if live.get("ok"):
                live_status = live.get("status", "Fail")
                score = int(live.get("score", 0))
                badge = "Basic" if live_status == "Success" else "None"
                verification_result = build_result(
                    status_value=live_status,
                    provider_value=NEUTRAL_VERIFICATION_PROVIDER_IDS["fmcsa_registry"],
                    category="Compliance",
                    method="AuthorityRecordCheck",
                    assurance_level="AAL1",
                    score_value=score,
                    token_value=fm_token,
                    source_value="carrier-finder",
                    source_authority="FMCSA",
                    extra={
                        "mcNumber": _normalize_mc(mc_number),
                        "carrier": {
                            "usdot": live.get("usdot_number"),
                            "mc": live.get("mc_number"),
                            "name": live.get("carrier_name"),
                            "operatingStatus": live.get("operating_status"),
                            "hasCurrentInsurance": live.get("has_current_insurance"),
                            "interstateAuthorityOk": live.get("interstate_authority_ok"),
                        },
                    },
                )
                return verification_result, badge

            verification_result = build_result(
                status_value="Fail",
                provider_value=NEUTRAL_VERIFICATION_PROVIDER_IDS["fmcsa_registry"],
                category="Compliance",
                method="AuthorityRecordCheck",
                assurance_level="AAL1",
                score_value=0,
                token_value=fm_token,
                source_value="carrier-finder",
                source_authority="FMCSA",
                extra={
                    "mcNumber": _normalize_mc(mc_number),
                    "error": live.get("error", "Unknown carrier-finder error."),
                },
            )
            return verification_result, "None"

        if fmcsa_source not in {"carrier-finder", "live-fmcsa", "hosted-adapter"}:
            verification_result = build_result(
                status_value="Fail",
                provider_value=NEUTRAL_VERIFICATION_PROVIDER_IDS["compliance_mock"],
                category="Compliance",
                method="AuthorityRecordCheck",
                assurance_level="AAL1",
                score_value=0,
                token_value=fm_token,
                source_value="mock-compliance",
                source_authority="FMCSA",
                extra={"error": f"Unsupported FMCSA source: {fmcsa_source}"},
            )
            return verification_result, "None"

        success_score = 86
        badge = "Basic"
    elif normalized_provider == "MockBiometricProvider":
        success_score = 94
        badge = "Premium"
        id_token = f"biometric-{uuid4().hex[:14]}"
    else:
        raise ValueError(f"Unsupported verification provider: {provider!r}")

    score = success_score if status == "Success" else 42
    badge = badge if status == "Success" else "None"

    if normalized_provider == "FMCSA":
        token = fm_token
        verification_result = build_result(
            status_value=status,
            provider_value=NEUTRAL_VERIFICATION_PROVIDER_IDS["compliance_mock"],
            category="Compliance",
            method="AuthorityRecordCheck",
            assurance_level="AAL1",
            score_value=score,
            token_value=token,
            source_value="mock-compliance",
            source_authority="FMCSA",
        )
    else:
        token = id_token
        verification_result = build_result(
            status_value=status,
            provider_value=NEUTRAL_VERIFICATION_PROVIDER_IDS["biometric_mock"],
            category="Biometric",
            method="LivenessPlusDocument",
            assurance_level="AAL2",
            score_value=score,
            token_value=token,
            source_value="mock-biometric",
        )
    return verification_result, badge


class BrokerAgent:
    def __init__(self, name):
        self.name = name
        self.loads = {}
        self.completed_bookings = {}
        self.verification_capabilities = default_verification_capabilities()

    def post_new_load(self, rate_model="PerMile"):
        load_id = str(uuid4())
        pickup_earliest = date.today() + timedelta(days=2)
        pickup_latest = pickup_earliest + timedelta(days=1)
        floor_amount = default_floor_amount(rate_model)

        new_load = {
            "LoadID": load_id,
            "Origin": {"city": "Dallas", "state": "TX", "zip": "75201"},
            "Destination": {"city": "Atlanta", "state": "GA", "zip": "30301"},
            "PickupEarliest": pickup_earliest.isoformat(),
            "PickupLatest": pickup_latest.isoformat(),
            "LoadType": "Full",
            "EquipmentType": "Reefer",
            "TrailerLength": 53,
            "Weight": 42000,
            "Commodity": "Frozen Poultry",
            "Rate": build_rate(rate_model, floor_amount),
            "AccessorialPolicy": {
                "AllowedTypes": ["UnloadingFee"],
                "RequiresApproval": True,
                "MaxTotal": 300.0,
                "Currency": "USD",
            },
            # Charges are intentionally empty at booking time; they can be approved later.
            "Accessorials": [],
            "RequireTracking": True,
        }
        self.loads[load_id] = new_load
        return new_load

    def search_loads(self, filters):
        matches = []
        for load in self.loads.values():
            pickup_date = filters.get("PickupDate")
            in_pickup_window = (
                load["PickupEarliest"] <= pickup_date <= load["PickupLatest"]
                if pickup_date
                else True
            )
            if (
                load["Origin"]["state"] == filters.get("OriginState")
                and load["Destination"]["state"] == filters.get("DestinationState")
                and load["EquipmentType"] == filters.get("EquipmentType")
                and load["Rate"]["RateModel"] == filters.get("RateModel")
                and in_pickup_window
                and load["Rate"]["Amount"] <= filters.get("MaxRate", 9999)
                and (not filters.get("RequireTracking") or load["RequireTracking"] is True)
            ):
                matches.append(load)
        return matches

    def respond_to_bid(self, bid_request, forced_response):
        load_id = bid_request["LoadID"]
        load_rate = self.loads[load_id]["Rate"]
        bid_rate = bid_request["Rate"]

        if bid_rate["RateModel"] != load_rate["RateModel"]:
            return {
                "LoadID": load_id,
                "ResponseType": "Reject",
                "VerifiedBadge": "None",
                "ReasonCode": "RateModelMismatch",
            }

        rate_floor = load_rate["Amount"]
        rate_model = load_rate["RateModel"]

        if forced_response == "Counter":
            return {
                "LoadID": load_id,
                "ResponseType": "Counter",
                "ProposedRate": build_rate(rate_model, counter_amount(rate_model, rate_floor)),
                "VerifiedBadge": "None",
            }

        if forced_response == "Reject":
            return {
                "LoadID": load_id,
                "ResponseType": "Reject",
                "VerifiedBadge": "None",
            }

        if bid_rate["Amount"] < rate_floor:
            return {
                "LoadID": load_id,
                "ResponseType": "Reject",
                "VerifiedBadge": "None",
            }

        return {
            "LoadID": load_id,
            "ResponseType": "Accept",
            "VerifiedBadge": "None",
        }

    def create_execution_report(
        self,
        load_id,
        bid_request,
        verified_badge,
        verification_result,
        policy_decision=None,
    ):
        load = self.loads[load_id]
        if policy_decision is None:
            policy_decision = evaluate_verification_policy_decision(
                verification_result,
                profile_id=VERIFICATION_POLICY_PROFILE_ID,
                risk_tier=DEFAULT_RISK_TIER,
            )
        report = {
            "LoadID": load_id,
            "ContractID": f"FAXP-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid4().hex[:8]}",
            "Status": "Booked",
            "Timestamp": now_utc(),
            "AgreedRate": bid_request["Rate"],
            "AccessorialPolicy": load["AccessorialPolicy"],
            "Accessorials": [],
            "VerifiedBadge": verified_badge,
            "VerificationResult": verification_result,
            "VerificationMode": policy_decision["VerificationMode"],
            "VerificationPolicyProfileID": policy_decision["VerificationPolicyProfileID"],
            "DispatchAuthorization": policy_decision["DispatchAuthorization"],
            "DecisionReasonCode": policy_decision["DecisionReasonCode"],
            "PolicyRuleID": policy_decision["PolicyRuleID"],
            "ReverifyBy": policy_decision["ReverifyBy"],
            "EvidenceRefs": policy_decision.get("EvidenceRefs", []),
        }
        if policy_decision.get("ExceptionApprovalRef"):
            report["ExceptionApprovalRef"] = policy_decision["ExceptionApprovalRef"]
        self.completed_bookings[load_id] = report
        return report

    def create_truck_search(self, rate_model="PerMile"):
        target_date = (date.today() + timedelta(days=2)).isoformat()
        return {
            "LocationRadiusMiles": 120,
            "OriginState": "TX",
            "EquipmentType": "Reefer",
            "AvailableFrom": target_date,
            "AvailableTo": (date.today() + timedelta(days=3)).isoformat(),
            "RateModel": rate_model,
            "MinRate": default_floor_amount(rate_model),
            "MaxRate": default_search_max(rate_model),
        }

    def create_truck_bid_request(self, truck, bid_amount=None):
        rate_model = truck["RateMin"]["RateModel"]
        amount = default_bid_amount(rate_model) if bid_amount is None else bid_amount
        return {
            "TruckID": truck["TruckID"],
            "Rate": build_rate(rate_model, amount),
            "AvailabilityDate": truck["AvailabilityDate"],
            "MatchType": "TruckCapacity",
        }

    def create_truck_execution_report(
        self,
        truck_id,
        bid_request,
        verified_badge,
        verification_result,
        policy_decision=None,
    ):
        if policy_decision is None:
            policy_decision = evaluate_verification_policy_decision(
                verification_result,
                profile_id=VERIFICATION_POLICY_PROFILE_ID,
                risk_tier=DEFAULT_RISK_TIER,
            )
        report = {
            "TruckID": truck_id,
            "ContractID": f"FAXP-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid4().hex[:8]}",
            "Status": "Booked",
            "Timestamp": now_utc(),
            "AgreedRate": bid_request["Rate"],
            "VerifiedBadge": verified_badge,
            "VerificationResult": verification_result,
            "VerificationMode": policy_decision["VerificationMode"],
            "VerificationPolicyProfileID": policy_decision["VerificationPolicyProfileID"],
            "DispatchAuthorization": policy_decision["DispatchAuthorization"],
            "DecisionReasonCode": policy_decision["DecisionReasonCode"],
            "PolicyRuleID": policy_decision["PolicyRuleID"],
            "ReverifyBy": policy_decision["ReverifyBy"],
            "EvidenceRefs": policy_decision.get("EvidenceRefs", []),
        }
        if policy_decision.get("ExceptionApprovalRef"):
            report["ExceptionApprovalRef"] = policy_decision["ExceptionApprovalRef"]
        self.completed_bookings[truck_id] = report
        return report


class CarrierAgent:
    def __init__(self, name):
        self.name = name
        self.completed_bookings = {}
        self.trucks = {}
        self.verification_capabilities = default_verification_capabilities()

    def create_load_search(self, force_no_match, rate_model):
        target_pickup = (date.today() + timedelta(days=2)).isoformat()
        destination_state = "FL" if force_no_match else "GA"
        return {
            "OriginState": "TX",
            "DestinationState": destination_state,
            "EquipmentType": "Reefer",
            "PickupDate": target_pickup,
            "RateModel": rate_model,
            "MaxRate": default_search_max(rate_model),
            "RequireTracking": True,
        }

    def create_bid_request(self, load, bid_amount=None):
        rate_model = load["Rate"]["RateModel"]
        amount = default_bid_amount(rate_model) if bid_amount is None else bid_amount
        return {
            "LoadID": load["LoadID"],
            "Rate": build_rate(rate_model, amount),
            "AvailabilityDate": (date.today() + timedelta(days=2)).isoformat(),
            "AccessorialPolicyAcceptance": {
                "Accepted": True,
                "AllowedTypes": ["UnloadingFee"],
            },
        }

    def mark_booking_complete(self, execution_report):
        self.completed_bookings[execution_report["LoadID"]] = execution_report

    def post_new_truck(self, rate_model="PerMile"):
        truck_id = str(uuid4())
        availability = (date.today() + timedelta(days=2)).isoformat()
        truck = {
            "TruckID": truck_id,
            "Location": {"city": "Fort Worth", "state": "TX", "zip": "76102"},
            "AvailabilityDate": availability,
            "EquipmentType": "Reefer",
            "TrailerLength": 53,
            "MaxWeight": 44000,
            "RateMin": build_rate(rate_model, default_floor_amount(rate_model)),
            "Notes": "Team driver available, same-day pickup preferred.",
        }
        self.trucks[truck_id] = truck
        return truck

    def search_trucks(self, filters):
        matches = []
        for truck in self.trucks.values():
            available_from = filters.get("AvailableFrom")
            available_to = filters.get("AvailableTo")
            date_ok = True
            if available_from and available_to:
                date_ok = available_from <= truck["AvailabilityDate"] <= available_to

            # MVP approximation: if searching within radius, match by state to keep logic simple.
            location_ok = truck["Location"]["state"] == filters.get("OriginState")
            rate_model_ok = truck["RateMin"]["RateModel"] == filters.get("RateModel")
            rate_ok = (
                filters.get("MinRate", 0.0)
                <= truck["RateMin"]["Amount"]
                <= filters.get("MaxRate", 9999.0)
            )
            if (
                location_ok
                and date_ok
                and rate_model_ok
                and rate_ok
                and truck["EquipmentType"] == filters.get("EquipmentType")
            ):
                matches.append(truck)
        return matches

    def respond_to_truck_bid(self, bid_request, forced_response="Accept"):
        truck_id = bid_request["TruckID"]
        truck = self.trucks[truck_id]
        min_rate = truck["RateMin"]
        bid_rate = bid_request["Rate"]

        if bid_rate["RateModel"] != min_rate["RateModel"]:
            return {
                "TruckID": truck_id,
                "ResponseType": "Reject",
                "VerifiedBadge": "None",
                "ReasonCode": "RateModelMismatch",
            }

        if forced_response == "Counter":
            return {
                "TruckID": truck_id,
                "ResponseType": "Counter",
                "ProposedRate": build_rate(
                    min_rate["RateModel"],
                    counter_amount(min_rate["RateModel"], min_rate["Amount"]),
                ),
                "VerifiedBadge": "None",
            }

        if forced_response == "Reject":
            return {
                "TruckID": truck_id,
                "ResponseType": "Reject",
                "VerifiedBadge": "None",
            }

        if bid_rate["Amount"] < min_rate["Amount"]:
            return {
                "TruckID": truck_id,
                "ResponseType": "Reject",
                "VerifiedBadge": "None",
            }

        return {
            "TruckID": truck_id,
            "ResponseType": "Accept",
            "VerifiedBadge": "None",
        }

    def mark_truck_booking_complete(self, execution_report):
        self.completed_bookings[execution_report["TruckID"]] = execution_report


# ShipperAgent stub — to be connected in v0.2 for full shipper-broker-carrier flow
class ShipperAgent:
    def __init__(self, name):
        self.name = name

    def post_tender(self):
        pickup_earliest = date.today() + timedelta(days=3)
        pickup_latest = pickup_earliest + timedelta(days=1)
        return {
            "LoadID": str(uuid4()),
            "Origin": {"city": "Chicago", "state": "IL", "zip": "60601"},
            "Destination": {"city": "Nashville", "state": "TN", "zip": "37201"},
            "PickupEarliest": pickup_earliest.isoformat(),
            "PickupLatest": pickup_latest.isoformat(),
            "LoadType": "Full",
            "EquipmentType": "DryVan",
            "TrailerLength": 53,
            "Weight": 38000,
            "Commodity": "Packaged Foods",
            "Rate": build_rate("PerMile", 2.15),
            "AccessorialPolicy": {
                "AllowedTypes": ["UnloadingFee"],
                "RequiresApproval": True,
                "MaxTotal": 300.0,
                "Currency": "USD",
            },
            "Accessorials": [],
            "RequireTracking": True,
        }


def run_security_self_tests(iterations=50):
    """Lightweight fuzz-style checks for envelope parser and auth/state rules."""
    if iterations <= 0:
        return True

    random.seed(1337)
    passed = 0
    failed = 0

    base_body = BrokerAgent("Broker Agent").post_new_load(rate_model="PerMile")

    for _ in range(iterations):
        # Ensure each test case is isolated; mutations must not leak across iterations.
        message_body = json.loads(json.dumps(base_body))
        message = build_envelope("Broker Agent", "Carrier Agent", "NewLoad", message_body)
        mutation = random.choice(
            [
                "valid",
                "drop_protocol",
                "bad_timestamp",
                "unknown_type",
                "bad_route",
                "tamper_body",
            ]
        )
        expect_valid = mutation == "valid"

        if mutation == "drop_protocol":
            message.pop("Protocol", None)
        elif mutation == "bad_timestamp":
            message["Timestamp"] = "not-a-date"
        elif mutation == "unknown_type":
            message["MessageType"] = "UnknownMessageType"
        elif mutation == "bad_route":
            message["From"] = "Carrier Agent"
            message["To"] = "Broker Agent"
        elif mutation == "tamper_body":
            # Always change value so tamper is effective even after prior iterations.
            message["Body"]["Commodity"] = f"TamperedCommodity-{uuid4().hex[:8]}"
            # Tamper is only detectable when the envelope is signed.
            expect_valid = "Signature" not in message

        try:
            validate_envelope(message, track_replay=False, track_state=False)
            outcome_valid = True
        except Exception:
            outcome_valid = False

        if outcome_valid == expect_valid:
            passed += 1
        else:
            failed += 1

    print(
        f"\n[SecuritySelfTest] iterations={iterations}, passed={passed}, failed={failed}"
    )
    return failed == 0


def run_load_flow(args, broker, carrier):
    """Existing load-centric happy path (kept intact)."""
    print("\n=== Load-Centric Flow ===")

    # 1) Broker posts a NewLoad message.
    new_load = broker.post_new_load(rate_model=args.rate_model)
    log_message(broker.name, carrier.name, "NewLoad", new_load)

    # 2) Carrier searches for loads using LoadSearch filters.
    load_search = carrier.create_load_search(
        force_no_match=args.no_match,
        rate_model=args.rate_model,
    )
    log_message(carrier.name, broker.name, "LoadSearch", load_search)
    matched_loads = broker.search_loads(load_search)
    print("\n[System] Load search results:")
    print(json.dumps(matched_loads, indent=2))

    if not matched_loads:
        print("\n[System] No matching loads found. Ending load flow.")
        return

    selected_load = matched_loads[0]

    # 3) Carrier submits BidRequest for the found load.
    bid_request = carrier.create_bid_request(
        selected_load,
        bid_amount=args.bid_amount,
    )
    log_message(carrier.name, broker.name, "BidRequest", bid_request)

    # 4) Broker receives bid and sends BidResponse.
    bid_response = broker.respond_to_bid(bid_request, forced_response=args.response)
    log_message(broker.name, carrier.name, "BidResponse", bid_response)

    if bid_response["ResponseType"] == "Counter":
        print(
            "\n[System] Counter received. Negotiation pending; load booking not complete in this run."
        )
        return

    if bid_response["ResponseType"] == "Reject":
        print("\n[System] Bid rejected. Load booking not complete in this run.")
        return

    capabilities_ok, capability_reason = negotiate_verification_capability(
        args.provider, broker, carrier
    )
    if not capabilities_ok:
        print(f"\n[System] {capability_reason}")
        print("[System] Verification not attempted due to capability mismatch.")
        return

    # 5) Verification step (success/fail configurable).
    print(f"\n[System] Verification requested via provider: {args.provider}")
    verification_result, verified_badge = run_verification(
        provider=args.provider,
        status=args.verification_status,
        mc_number=args.mc_number,
        carrier_finder_path=args.carrier_finder_path,
        fmcsa_source=args.fmcsa_source,
    )
    print("[System] Verification result:")
    print(json.dumps(redact_sensitive(verification_result), indent=2))
    print(f"[System] VerifiedBadge assigned: {verified_badge}")

    policy_decision = evaluate_verification_policy_decision(
        verification_result,
        profile_id=args.policy_profile_id,
        risk_tier=args.risk_tier,
        exception_approved=args.exception_approved,
        exception_approval_ref=args.exception_approval_ref,
    )
    print("[System] Policy decision:")
    print(
        json.dumps(
            {
                "profile": policy_decision["VerificationPolicyProfileID"],
                "riskTier": policy_decision["RiskTier"],
                "dispatchAuthorization": policy_decision["DispatchAuthorization"],
                "decisionReasonCode": policy_decision["DecisionReasonCode"],
                "policyRuleID": policy_decision["PolicyRuleID"],
                "shouldBook": policy_decision["ShouldBook"],
                "exceptionApprovalRef": policy_decision.get("ExceptionApprovalRef", ""),
            },
            indent=2,
        )
    )

    if not policy_decision["ShouldBook"]:
        print("\n[System] Policy blocked booking. Load booking not completed.")
        return

    # 6) Broker sends ExecutionReport confirming the booking.
    execution_report = broker.create_execution_report(
        load_id=bid_request["LoadID"],
        bid_request=bid_request,
        verified_badge=verified_badge,
        verification_result=verification_result,
        policy_decision=policy_decision,
    )
    log_message(broker.name, carrier.name, "ExecutionReport", execution_report)

    # 7) Booking is marked complete for both parties.
    carrier.mark_booking_complete(execution_report)
    broker_complete = bid_request["LoadID"] in broker.completed_bookings
    carrier_complete = bid_request["LoadID"] in carrier.completed_bookings
    print(
        f"\n[System] Booking completion state -> Broker: {broker_complete}, Carrier: {carrier_complete}"
    )

    if execution_report["DispatchAuthorization"] == "Hold":
        print(
            "Booking provisionally completed - "
            f"RunID: {get_protocol_run_id()}, "
            f"LoadID: {bid_request['LoadID']}, "
            f"Verified: {verified_badge}, "
            f"DispatchAuthorization: Hold, "
            f"Rate: {format_rate(bid_request['Rate'])}"
        )
    else:
        print(
            "Booking completed successfully - "
            f"RunID: {get_protocol_run_id()}, "
            f"LoadID: {bid_request['LoadID']}, "
            f"Verified: {verified_badge}, "
            f"Rate: {format_rate(bid_request['Rate'])}"
        )


def run_truck_flow(args, broker, carrier):
    """
    Alternative happy path:
    Carrier posts truck capacity, broker searches trucks, matches via bid, verifies, and books.
    """
    print("\n=== Truck-Capacity Flow ===")

    # 1) Carrier posts a NewTruck message.
    new_truck = carrier.post_new_truck(rate_model=args.rate_model)
    log_message(carrier.name, broker.name, "NewTruck", new_truck)

    # 2) Broker searches for available trucks via TruckSearch filters.
    truck_search = broker.create_truck_search(rate_model=args.rate_model)
    log_message(broker.name, carrier.name, "TruckSearch", truck_search)
    matched_trucks = carrier.search_trucks(truck_search)
    print("\n[System] Truck search results:")
    print(json.dumps(matched_trucks, indent=2))

    if not matched_trucks:
        print("\n[System] No matching trucks found. Ending truck flow.")
        return

    selected_truck = matched_trucks[0]

    # 3) Broker submits BidRequest on truck capacity.
    truck_bid_request = broker.create_truck_bid_request(
        selected_truck,
        bid_amount=args.bid_amount,
    )
    log_message(broker.name, carrier.name, "BidRequest", truck_bid_request)

    # 4) Carrier responds with BidResponse (Accept in this minimal happy path).
    truck_bid_response = carrier.respond_to_truck_bid(
        truck_bid_request,
        forced_response="Accept",
    )
    log_message(carrier.name, broker.name, "BidResponse", truck_bid_response)

    if truck_bid_response["ResponseType"] != "Accept":
        print("\n[System] Truck bid was not accepted. Truck booking not complete.")
        return

    capabilities_ok, capability_reason = negotiate_verification_capability(
        "FMCSA", broker, carrier
    )
    if not capabilities_ok:
        print(f"\n[System] {capability_reason}")
        print("[System] Truck flow verification not attempted due to capability mismatch.")
        return

    # 5) Verification uses configured FMCSA source.
    verification_mc = args.mc_number or "498282"
    print(
        f"\n[System] Truck flow verification requested via provider: FMCSA "
        f"(source: {args.fmcsa_source}, MC: {verification_mc})"
    )
    verification_result, verified_badge = run_verification(
        provider="FMCSA",
        status="Success",
        mc_number=verification_mc,
        carrier_finder_path=args.carrier_finder_path,
        fmcsa_source=args.fmcsa_source,
    )
    print("[System] Truck flow verification result:")
    print(json.dumps(redact_sensitive(verification_result), indent=2))
    print(f"[System] Truck flow VerifiedBadge assigned: {verified_badge}")

    policy_decision = evaluate_verification_policy_decision(
        verification_result,
        profile_id=args.policy_profile_id,
        risk_tier=args.risk_tier,
        exception_approved=args.exception_approved,
        exception_approval_ref=args.exception_approval_ref,
    )
    print("[System] Truck flow policy decision:")
    print(
        json.dumps(
            {
                "profile": policy_decision["VerificationPolicyProfileID"],
                "riskTier": policy_decision["RiskTier"],
                "dispatchAuthorization": policy_decision["DispatchAuthorization"],
                "decisionReasonCode": policy_decision["DecisionReasonCode"],
                "policyRuleID": policy_decision["PolicyRuleID"],
                "shouldBook": policy_decision["ShouldBook"],
                "exceptionApprovalRef": policy_decision.get("ExceptionApprovalRef", ""),
            },
            indent=2,
        )
    )

    if not policy_decision["ShouldBook"]:
        print("\n[System] Truck flow policy blocked booking. Truck booking not completed.")
        return

    # 6) Broker sends ExecutionReport confirming truck capacity booking.
    truck_execution_report = broker.create_truck_execution_report(
        truck_id=selected_truck["TruckID"],
        bid_request=truck_bid_request,
        verified_badge=verified_badge,
        verification_result=verification_result,
        policy_decision=policy_decision,
    )
    log_message(broker.name, carrier.name, "ExecutionReport", truck_execution_report)

    # 7) Mark completion for both parties.
    carrier.mark_truck_booking_complete(truck_execution_report)
    broker_complete = selected_truck["TruckID"] in broker.completed_bookings
    carrier_complete = selected_truck["TruckID"] in carrier.completed_bookings
    print(
        f"\n[System] Truck booking completion state -> Broker: {broker_complete}, Carrier: {carrier_complete}"
    )
    if truck_execution_report["DispatchAuthorization"] == "Hold":
        print(
            "Truck capacity booking provisionally completed - "
            f"RunID: {get_protocol_run_id()}, "
            f"TruckID: {selected_truck['TruckID']}, "
            f"Verified: {verified_badge}, "
            f"DispatchAuthorization: Hold, "
            f"Rate: {format_rate(truck_bid_request['Rate'])}"
        )
    else:
        print(
            "Truck capacity booking complete - "
            f"RunID: {get_protocol_run_id()}, "
            f"TruckID: {selected_truck['TruckID']}, "
            f"Verified: {verified_badge}, "
            f"Rate: {format_rate(truck_bid_request['Rate'])}"
        )


def main():
    args = parse_args()
    enforce_security_baseline()
    reset_protocol_runtime_state()
    run_id = set_protocol_run_id()

    if args.security_self_test:
        if not run_security_self_tests(args.self_test_iterations):
            raise RuntimeError("Security self-tests failed.")

    print(
        f"{FaxpProtocol.NAME} v{FaxpProtocol.VERSION} MVP - Autonomous Freight Booking Happy-Path Simulation"
    )
    print(f"[System] RunID: {run_id}")
    print("\nSupported message types:")
    print(json.dumps(FaxpProtocol.MESSAGE_TYPES, indent=2))

    broker = BrokerAgent("Broker Agent")
    carrier = CarrierAgent("Carrier Agent")
    if args.force_capability_mismatch:
        carrier.verification_capabilities = {
            "supportedCategories": ["Identity"],
            "supportedMethods": ["DocumentOnly"],
            "minAssuranceLevel": "AAL1",
            "requiresSignedAttestation": bool(REQUIRE_SIGNED_VERIFIER),
        }
        print("\n[System] Forced capability mismatch is enabled for this run.")
    print("\nVerificationCapabilities (Broker):")
    print(json.dumps(broker.verification_capabilities, indent=2))
    print("VerificationCapabilities (Carrier):")
    print(json.dumps(carrier.verification_capabilities, indent=2))
    print(
        "\n[System] Policy controls: "
        f"profile={args.policy_profile_id}, "
        f"riskTier={args.risk_tier}, "
        f"exceptionApproved={args.exception_approved}, "
        f"exceptionApprovalRef={args.exception_approval_ref or '[none]'}"
    )

    # Show AmendRequest exists in protocol but do not execute it in these happy paths.
    amend_preview = FaxpProtocol.amend_request_example("example-load-id")
    print("\nAmendRequest (exists, not executed in this run):")
    print(json.dumps(amend_preview, indent=2))

    # Existing load-centric flow.
    run_load_flow(args, broker, carrier)

    # Additional reverse flow: carrier truck posting -> broker truck search.
    run_truck_flow(args, broker, carrier)


if __name__ == "__main__":
    main()
