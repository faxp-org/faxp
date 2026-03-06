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


def _env_non_negative_float(name, default):
    raw_value = os.getenv(name, str(default)).strip()
    try:
        parsed = float(raw_value)
    except ValueError:
        return float(default)
    if parsed < 0:
        return float(default)
    return parsed


def _normalize_mileage_dispute_policy(value):
    normalized = str(value or "").strip().lower()
    if normalized in {"strict", "balanced"}:
        return normalized
    return "balanced"


DEBUG_MODE = os.getenv("FAXP_DEBUG", "0") == "1"
SENSITIVE_KEYS = {"token", "stderr", "Signature"}
APP_MODE = os.getenv("FAXP_APP_MODE", "local").strip().lower()
NON_LOCAL_MODE = APP_MODE not in {"local", "dev", "development"}
VERIFICATION_POLICY_PROFILE_ID = os.getenv(
    "FAXP_VERIFICATION_POLICY_PROFILE_ID",
    "US_VERIFICATION_BALANCED_V1",
).strip()
MILEAGE_DISPUTE_POLICY = _normalize_mileage_dispute_policy(
    os.getenv("FAXP_MILEAGE_DISPUTE_POLICY", "balanced")
)
MILEAGE_DISPUTE_ABS_TOLERANCE_MILES = _env_non_negative_float(
    "FAXP_MILEAGE_DISPUTE_ABS_TOLERANCE_MILES",
    25.0,
)
MILEAGE_DISPUTE_REL_TOLERANCE_RATIO = _env_non_negative_float(
    "FAXP_MILEAGE_DISPUTE_REL_TOLERANCE_RATIO",
    0.02,
)
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
TRUSTED_VERIFIER_REGISTRY_RAW = os.getenv("FAXP_TRUSTED_VERIFIER_REGISTRY", "").strip()
TRUSTED_VERIFIER_REGISTRY_FILE = os.getenv(
    "FAXP_TRUSTED_VERIFIER_REGISTRY_FILE", ""
).strip()
ENFORCE_TRUSTED_VERIFIER_REGISTRY_RAW = os.getenv(
    "FAXP_ENFORCE_TRUSTED_VERIFIER_REGISTRY",
    "1",
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
VERIFIER_COMPONENT_FILE = os.getenv("FAXP_VERIFIER_COMPONENT_FILE", "").strip()
EXPECTED_VERIFIER_COMPONENT_SHA256 = os.getenv(
    "FAXP_VERIFIER_COMPONENT_SHA256",
    "",
).strip().lower()
SUPPORTED_SIGNATURE_SCHEMES = {"HMAC_SHA256", "ED25519"}
AGENT_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._:-]{1,127}$")
TIME_ZONE_PATTERN = re.compile(r"^[A-Za-z_]+(?:/[A-Za-z0-9_+-]+)+$")
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
    "FAXP_TRUSTED_VERIFIER_REGISTRY",
    "FAXP_TRUSTED_VERIFIER_REGISTRY_FILE",
    "FAXP_ENFORCE_TRUSTED_VERIFIER_REGISTRY",
    "FAXP_FMCSA_ADAPTER_BASE_URL",
    "FAXP_FMCSA_ADAPTER_AUTH_TOKEN",
    "FAXP_FMCSA_ADAPTER_TIMEOUT_SECONDS",
    "FAXP_FMCSA_ADAPTER_REQUIRE_SIGNED_WRAPPER",
    "FAXP_FMCSA_ADAPTER_SIGN_REQUESTS",
    "FAXP_FMCSA_ADAPTER_REQUEST_SIGNING_KEYS",
    "FAXP_FMCSA_ADAPTER_REQUEST_SIGNING_ACTIVE_KEY_ID",
}
ROLE_CAPABILITIES = {
    # User-facing posting/booking capability policy.
    "Shipper": {"post_load": True, "post_truck": False, "book_load": False, "book_truck": True},
    "Broker": {"post_load": True, "post_truck": True, "book_load": True, "book_truck": True},
    "Carrier": {"post_load": False, "post_truck": True, "book_load": True, "book_truck": False},
}


def _default_agent_id(agent_name):
    normalized_name = str(agent_name or "").strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized_name).strip("-")
    if not slug:
        digest = hashlib.sha256(normalized_name.encode("utf-8")).hexdigest()[:10]
        slug = f"agent-{digest}"
    return slug[:128]


def _normalize_agent_id(value):
    candidate = str(value or "").strip().lower()
    if not candidate:
        return ""
    if not AGENT_ID_PATTERN.fullmatch(candidate):
        return ""
    return candidate
SEEN_MESSAGE_IDS = set()
SEEN_NONCES = set()
LAST_AUDIT_HASH = ""
REPLAY_DB_LOCK = threading.Lock()
STATE_LOCK = threading.Lock()
FLOW_STATE = {"load": "START", "truck": "START"}
CURRENT_RUN_ID = ""
RUNTIME_MILEAGE_POLICY = {
    "policy": MILEAGE_DISPUTE_POLICY,
    "absToleranceMiles": float(MILEAGE_DISPUTE_ABS_TOLERANCE_MILES),
    "relToleranceRatio": float(MILEAGE_DISPUTE_REL_TOLERANCE_RATIO),
}


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
TRUSTED_VERIFIER_REGISTRY_RAW = _override_secret_value(
    "FAXP_TRUSTED_VERIFIER_REGISTRY",
    TRUSTED_VERIFIER_REGISTRY_RAW,
).strip()
TRUSTED_VERIFIER_REGISTRY_FILE = _override_secret_value(
    "FAXP_TRUSTED_VERIFIER_REGISTRY_FILE",
    TRUSTED_VERIFIER_REGISTRY_FILE,
).strip()
ENFORCE_TRUSTED_VERIFIER_REGISTRY_RAW = _override_secret_value(
    "FAXP_ENFORCE_TRUSTED_VERIFIER_REGISTRY",
    ENFORCE_TRUSTED_VERIFIER_REGISTRY_RAW,
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


FMCSA_ADAPTER_REQUIRE_SIGNED_WRAPPER = _is_truthy(
    FMCSA_ADAPTER_REQUIRE_SIGNED_WRAPPER_RAW
)
FMCSA_ADAPTER_SIGN_REQUESTS = _is_truthy(FMCSA_ADAPTER_SIGN_REQUESTS_RAW)
ENFORCE_TRUSTED_VERIFIER_REGISTRY = _is_truthy(
    ENFORCE_TRUSTED_VERIFIER_REGISTRY_RAW
)


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
        agent_id = _normalize_agent_id(config.get("agent_id")) or _default_agent_id(agent_name)
        private_keys = {}
        public_keys = {}
        metadata = {}
        allowed_kids = set()

        if isinstance(config.get("private_keys"), dict):
            for kid, path in config["private_keys"].items():
                kid_text = str(kid).strip()
                private_keys[kid_text] = os.path.realpath(str(path))
                if kid_text:
                    allowed_kids.add(kid_text)
        if isinstance(config.get("public_keys"), dict):
            for kid, path in config["public_keys"].items():
                kid_text = str(kid).strip()
                public_keys[kid_text] = os.path.realpath(str(path))
                if kid_text:
                    allowed_kids.add(kid_text)
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
                if key_id:
                    allowed_kids.add(key_id)

        raw_allowed_kids = config.get("allowed_kids")
        if isinstance(raw_allowed_kids, list):
            parsed_allowed = {
                str(item).strip()
                for item in raw_allowed_kids
                if str(item).strip()
            }
            if parsed_allowed:
                allowed_kids = parsed_allowed
        if active_kid:
            allowed_kids.add(active_kid)

        normalized[agent_name] = {
            "agent_id": agent_id,
            "active_kid": active_kid,
            "private_keys": private_keys,
            "public_keys": public_keys,
            "key_metadata": metadata,
            "allowed_kids": sorted(allowed_kids),
        }
    return normalized


AGENT_KEY_REGISTRY = _load_agent_key_registry()


def _build_agent_identity_bindings(registry):
    by_name = {}
    by_id = {}

    for agent_name, material in registry.items():
        if not isinstance(material, dict):
            continue
        agent_id = (
            _normalize_agent_id(material.get("agent_id")) or _default_agent_id(agent_name)
        )
        allowed_kids = {
            str(item).strip()
            for item in (material.get("allowed_kids") or [])
            if str(item).strip()
        }
        if not allowed_kids:
            allowed_kids.update(str(key).strip() for key in (material.get("public_keys") or {}).keys())
            allowed_kids.update(str(key).strip() for key in (material.get("private_keys") or {}).keys())
        active_kid = str(material.get("active_kid") or "").strip()
        if active_kid:
            allowed_kids.add(active_kid)

        binding = {
            "agent_name": str(agent_name),
            "agent_id": agent_id,
            "allowed_kids": sorted(item for item in allowed_kids if item),
        }
        by_name[str(agent_name)] = binding
        existing = by_id.get(agent_id)
        if existing and existing["agent_name"] != binding["agent_name"] and NON_LOCAL_MODE:
            raise RuntimeError(
                f"Duplicate agent_id '{agent_id}' in FAXP_AGENT_KEY_REGISTRY for "
                f"'{existing['agent_name']}' and '{binding['agent_name']}'."
            )
        by_id.setdefault(agent_id, binding)

    return {"by_name": by_name, "by_id": by_id}


AGENT_ID_BINDINGS = _build_agent_identity_bindings(AGENT_KEY_REGISTRY)


def resolve_agent_id(agent_name):
    binding = AGENT_ID_BINDINGS["by_name"].get(str(agent_name))
    if binding:
        return binding["agent_id"]
    return _default_agent_id(agent_name)
FALLBACK_TRUSTED_VERIFIER_REGISTRY_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "conformance",
    "trusted_verifier_registry.sample.json",
)


def _load_trusted_verifier_registry():
    registry_text = TRUSTED_VERIFIER_REGISTRY_RAW
    registry_file = TRUSTED_VERIFIER_REGISTRY_FILE
    if not registry_text and not registry_file and os.path.exists(
        FALLBACK_TRUSTED_VERIFIER_REGISTRY_FILE
    ):
        registry_file = FALLBACK_TRUSTED_VERIFIER_REGISTRY_FILE

    if not registry_text and registry_file:
        with open(registry_file, "r", encoding="utf-8") as handle:
            registry_text = handle.read()
    if not registry_text:
        return {}

    try:
        payload = json.loads(registry_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Trusted verifier registry is not valid JSON.") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Trusted verifier registry must be a JSON object.")
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise RuntimeError("Trusted verifier registry must include an entries array.")

    index = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise RuntimeError("Trusted verifier registry entries must be objects.")
        provider_id = str(entry.get("providerId") or "").strip()
        if not provider_id:
            raise RuntimeError("Trusted verifier registry entry missing providerId.")
        status = str(entry.get("status") or "").strip() or "Unknown"
        provider_type = str(entry.get("providerType") or "").strip() or "Unknown"

        allowed_sources = []
        raw_sources = entry.get("allowedSources")
        if isinstance(raw_sources, list):
            allowed_sources = [str(item).strip().lower() for item in raw_sources if str(item).strip()]

        allowed_assurance_levels = []
        raw_aals = entry.get("allowedAssuranceLevels")
        if isinstance(raw_aals, list):
            allowed_assurance_levels = [str(item).strip().upper() for item in raw_aals if str(item).strip()]

        allowed_attestation_kids = []
        raw_kids = entry.get("allowedAttestationKids")
        if isinstance(raw_kids, list):
            allowed_attestation_kids = [str(item).strip() for item in raw_kids if str(item).strip()]

        index[provider_id] = {
            "providerId": provider_id,
            "providerType": provider_type,
            "status": status,
            "allowedSources": allowed_sources,
            "allowedAssuranceLevels": allowed_assurance_levels,
            "allowedAttestationKids": allowed_attestation_kids,
        }
    return index


TRUSTED_VERIFIER_REGISTRY = _load_trusted_verifier_registry()


class FaxpProtocol:
    """Lightweight protocol constants and examples."""

    NAME = "FAXP"
    VERSION = "0.1.1"
    SUPPORTED_PROTOCOL_VERSIONS = ("0.1.1", "0.2.0")
    VERSION_COMPATIBILITY_MATRIX = {
        # Runtime version -> incoming version -> compatibility class.
        "0.1.1": {
            "0.1.1": "Compatible",
            "0.2.0": "Degradable",
        },
        "0.2.0": {
            "0.2.0": "Compatible",
            "0.1.1": "Degradable",
        },
    }

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


PROTOCOL_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


def negotiate_protocol_version(incoming_version, runtime_version=None):
    """
    Evaluate protocol-version compatibility for incoming envelopes.

    Returns:
      {
        "status": "Compatible" | "Degradable" | "Incompatible",
        "reasonCode": "...",
        "incomingVersion": "...",
        "runtimeVersion": "...",
      }
    """
    runtime = str(runtime_version or FaxpProtocol.VERSION).strip()
    incoming = str(incoming_version or "").strip()

    if not runtime:
        return {
            "status": "Incompatible",
            "reasonCode": "RuntimeProtocolVersionMissing",
            "incomingVersion": incoming,
            "runtimeVersion": runtime,
        }
    if not PROTOCOL_VERSION_PATTERN.fullmatch(runtime):
        return {
            "status": "Incompatible",
            "reasonCode": "RuntimeProtocolVersionInvalid",
            "incomingVersion": incoming,
            "runtimeVersion": runtime,
        }
    if not incoming:
        return {
            "status": "Incompatible",
            "reasonCode": "ProtocolVersionMissing",
            "incomingVersion": incoming,
            "runtimeVersion": runtime,
        }
    if not PROTOCOL_VERSION_PATTERN.fullmatch(incoming):
        return {
            "status": "Incompatible",
            "reasonCode": "ProtocolVersionInvalidFormat",
            "incomingVersion": incoming,
            "runtimeVersion": runtime,
        }

    if incoming not in FaxpProtocol.SUPPORTED_PROTOCOL_VERSIONS:
        return {
            "status": "Incompatible",
            "reasonCode": "ProtocolVersionUnsupported",
            "incomingVersion": incoming,
            "runtimeVersion": runtime,
        }

    matrix = FaxpProtocol.VERSION_COMPATIBILITY_MATRIX.get(runtime, {})
    compatibility = matrix.get(incoming)
    if compatibility in {"Compatible", "Degradable"}:
        return {
            "status": compatibility,
            "reasonCode": (
                "ProtocolVersionCompatible"
                if compatibility == "Compatible"
                else "ProtocolVersionDegradable"
            ),
            "incomingVersion": incoming,
            "runtimeVersion": runtime,
        }

    # Fallback path for runtimes without explicit matrix entry.
    if incoming == runtime:
        return {
            "status": "Compatible",
            "reasonCode": "ProtocolVersionCompatible",
            "incomingVersion": incoming,
            "runtimeVersion": runtime,
        }

    return {
        "status": "Incompatible",
        "reasonCode": "ProtocolVersionIncompatiblePair",
        "incomingVersion": incoming,
        "runtimeVersion": runtime,
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
    binding = AGENT_ID_BINDINGS["by_name"].get(str(agent_name), {})
    if not isinstance(config, dict):
        return {
            "agent_id": resolve_agent_id(agent_name),
            "allowed_kids": [],
            "active_kid": "",
            "private_keys": {},
            "public_keys": {},
            "key_metadata": {},
        }
    return {
        "agent_id": str(binding.get("agent_id") or resolve_agent_id(agent_name)),
        "allowed_kids": list(binding.get("allowed_kids") or []),
        "active_kid": str(config.get("active_kid", "")).strip(),
        "private_keys": dict(config.get("private_keys", {})),
        "public_keys": dict(config.get("public_keys", {})),
        "key_metadata": dict(config.get("key_metadata", {})),
    }


def _sign_asymmetric(envelope):
    signer = envelope.get("From")
    material = _load_key_material_for_agent(signer)
    expected_agent_id = str(material.get("agent_id") or resolve_agent_id(signer))
    current_agent_id = str(envelope.get("FromAgentID") or "").strip().lower()
    if current_agent_id and current_agent_id != expected_agent_id:
        if NON_LOCAL_MODE:
            raise RuntimeError(
                f"FromAgentID '{current_agent_id}' does not match expected agent identity "
                f"'{expected_agent_id}' for sender '{signer}'."
            )
    envelope["FromAgentID"] = expected_agent_id
    kid = material["active_kid"]
    allowed_kids = set(str(item).strip() for item in material.get("allowed_kids", []))
    if NON_LOCAL_MODE and allowed_kids and kid and kid not in allowed_kids:
        raise RuntimeError(
            f"Active SignatureKeyID '{kid}' is not allowed for sender '{signer}' "
            f"(AgentID: {expected_agent_id})."
        )
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
    if sender_role not in ROLE_CAPABILITIES:
        raise ValueError(f"Unknown sender role inferred from envelope From: {sender_role}")
    if receiver_role not in ROLE_CAPABILITIES:
        raise ValueError(f"Unknown receiver role inferred from envelope To: {receiver_role}")
    _validate_role_capability_policy(envelope, sender_role)
    _validate_receiver_capability_policy(envelope, receiver_role)


def _validate_role_capability_policy(envelope, sender_role):
    capabilities = ROLE_CAPABILITIES.get(sender_role) or {}
    message_type = envelope.get("MessageType")
    body = envelope.get("Body") or {}

    if message_type == "NewLoad" and not capabilities.get("post_load", False):
        raise ValueError(f"Sender role '{sender_role}' is not allowed to post loads.")
    if message_type == "NewTruck" and not capabilities.get("post_truck", False):
        raise ValueError(f"Sender role '{sender_role}' is not allowed to post trucks.")

    if message_type == "LoadSearch" and not capabilities.get("book_load", False):
        raise ValueError(f"Sender role '{sender_role}' is not allowed to search/book loads.")
    if message_type == "TruckSearch" and not capabilities.get("book_truck", False):
        raise ValueError(f"Sender role '{sender_role}' is not allowed to search/book trucks.")

    if message_type == "BidRequest":
        if isinstance(body, dict) and "LoadID" in body and not capabilities.get("book_load", False):
            raise ValueError(f"Sender role '{sender_role}' is not allowed to book loads.")
        if isinstance(body, dict) and "TruckID" in body and not capabilities.get("book_truck", False):
            raise ValueError(f"Sender role '{sender_role}' is not allowed to book trucks.")


def _validate_receiver_capability_policy(envelope, receiver_role):
    receiver_capabilities = ROLE_CAPABILITIES.get(receiver_role) or {}
    message_type = envelope.get("MessageType")
    body = envelope.get("Body") or {}

    if message_type == "NewLoad" and not receiver_capabilities.get("book_load", False):
        raise ValueError(f"Receiver role '{receiver_role}' is not allowed to receive posted loads.")
    if message_type == "NewTruck" and not receiver_capabilities.get("book_truck", False):
        raise ValueError(f"Receiver role '{receiver_role}' is not allowed to receive posted trucks.")

    if message_type == "LoadSearch" and not receiver_capabilities.get("post_load", False):
        raise ValueError(f"Receiver role '{receiver_role}' is not allowed to respond to load searches.")
    if message_type == "TruckSearch" and not receiver_capabilities.get("post_truck", False):
        raise ValueError(f"Receiver role '{receiver_role}' is not allowed to respond to truck searches.")

    if message_type == "BidRequest":
        if isinstance(body, dict) and "LoadID" in body and not receiver_capabilities.get("post_load", False):
            raise ValueError(f"Receiver role '{receiver_role}' is not allowed to receive load bids.")
        if isinstance(body, dict) and "TruckID" in body and not receiver_capabilities.get("post_truck", False):
            raise ValueError(f"Receiver role '{receiver_role}' is not allowed to receive truck bids.")

    if message_type == "BidResponse":
        if isinstance(body, dict) and "LoadID" in body and not receiver_capabilities.get("book_load", False):
            raise ValueError(f"Receiver role '{receiver_role}' is not allowed to receive load bid responses.")
        if isinstance(body, dict) and "TruckID" in body and not receiver_capabilities.get("book_truck", False):
            raise ValueError(f"Receiver role '{receiver_role}' is not allowed to receive truck bid responses.")

    if message_type == "ExecutionReport":
        if isinstance(body, dict) and "LoadID" in body and not receiver_capabilities.get("book_load", False):
            raise ValueError(f"Receiver role '{receiver_role}' is not allowed to receive load execution reports.")
        if isinstance(body, dict) and "TruckID" in body and not receiver_capabilities.get("book_truck", False):
            raise ValueError(f"Receiver role '{receiver_role}' is not allowed to receive truck execution reports.")

    if message_type == "AmendRequest" and not receiver_capabilities.get("book_load", False):
        raise ValueError(f"Receiver role '{receiver_role}' is not allowed to receive load amendments.")


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


def configure_mileage_dispute_policy(
    *,
    policy=None,
    abs_tolerance_miles=None,
    rel_tolerance_ratio=None,
):
    with STATE_LOCK:
        if policy is not None:
            RUNTIME_MILEAGE_POLICY["policy"] = _normalize_mileage_dispute_policy(policy)
        if abs_tolerance_miles is not None:
            try:
                parsed_abs = float(abs_tolerance_miles)
            except (TypeError, ValueError):
                parsed_abs = float(MILEAGE_DISPUTE_ABS_TOLERANCE_MILES)
            RUNTIME_MILEAGE_POLICY["absToleranceMiles"] = max(0.0, parsed_abs)
        if rel_tolerance_ratio is not None:
            try:
                parsed_rel = float(rel_tolerance_ratio)
            except (TypeError, ValueError):
                parsed_rel = float(MILEAGE_DISPUTE_REL_TOLERANCE_RATIO)
            RUNTIME_MILEAGE_POLICY["relToleranceRatio"] = max(0.0, parsed_rel)
    return dict(RUNTIME_MILEAGE_POLICY)


def get_mileage_dispute_policy():
    with STATE_LOCK:
        return dict(RUNTIME_MILEAGE_POLICY)


def _bounded_string(value, context):
    if not isinstance(value, str):
        raise ValueError(f"{context} must be a string.")
    if len(value) > MAX_STRING_LENGTH:
        raise ValueError(f"{context} exceeds max length ({MAX_STRING_LENGTH}).")


def _validate_agent_id(value, context):
    _bounded_string(value, context)
    normalized = str(value).strip().lower()
    if not AGENT_ID_PATTERN.fullmatch(normalized):
        raise ValueError(
            f"{context} must match pattern '{AGENT_ID_PATTERN.pattern}' and be lowercase."
        )


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


def _parse_iso_datetime(value, context):
    _bounded_string(value, context)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
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


def _normalize_location_key(location):
    return (
        str(location.get("city") or "").strip().lower(),
        str(location.get("state") or "").strip().upper(),
        str(location.get("zip") or "").strip(),
    )


def _validate_stop_plan(stops, context, origin=None, destination=None):
    if not isinstance(stops, list) or len(stops) < 2:
        raise ValueError(f"{context} must be an array with at least two stops.")

    sequences = []
    stop_types = []
    for idx, stop in enumerate(stops):
        item_context = f"{context}[{idx}]"
        if not isinstance(stop, dict):
            raise ValueError(f"{item_context} must be an object.")
        _require_fields(stop, ["StopSequence", "StopType", "Location"], item_context)
        sequence = stop["StopSequence"]
        if not isinstance(sequence, int) or sequence <= 0:
            raise ValueError(f"{item_context}.StopSequence must be a positive integer.")
        _bounded_string(stop["StopType"], f"{item_context}.StopType")
        if stop["StopType"] not in VALID_STOP_TYPES:
            raise ValueError(f"{item_context}.StopType must be one of {sorted(VALID_STOP_TYPES)}.")
        _validate_location_obj(stop["Location"], f"{item_context}.Location")
        if "WindowOpen" in stop:
            _validate_iso_date(stop["WindowOpen"], f"{item_context}.WindowOpen")
        if "WindowClose" in stop:
            _validate_iso_date(stop["WindowClose"], f"{item_context}.WindowClose")
        if "WindowOpen" in stop and "WindowClose" in stop and stop["WindowOpen"] > stop["WindowClose"]:
            raise ValueError(f"{item_context}.WindowOpen must be <= WindowClose.")
        if "Notes" in stop:
            _bounded_string(stop["Notes"], f"{item_context}.Notes")
        sequences.append(sequence)
        stop_types.append(stop["StopType"])

    ordered = sorted(sequences)
    expected = list(range(1, len(stops) + 1))
    if ordered != expected:
        raise ValueError(f"{context}.StopSequence values must be contiguous starting at 1.")
    if stop_types[0] != "Pickup":
        raise ValueError(f"{context}[0].StopType must be 'Pickup'.")
    if stop_types[-1] != "Drop":
        raise ValueError(f"{context}[{len(stops) - 1}].StopType must be 'Drop'.")
    if "Pickup" not in stop_types or "Drop" not in stop_types:
        raise ValueError(f"{context} must include at least one Pickup and one Drop stop.")

    if isinstance(origin, dict):
        first_location = stops[0]["Location"]
        if _normalize_location_key(first_location) != _normalize_location_key(origin):
            raise ValueError(f"{context}[0].Location must match NewLoad.Origin.")
    if isinstance(destination, dict):
        last_location = stops[-1]["Location"]
        if _normalize_location_key(last_location) != _normalize_location_key(destination):
            raise ValueError(f"{context}[{len(stops) - 1}].Location must match NewLoad.Destination.")


def _derive_stop_plan_summary(load_like):
    stops = load_like.get("Stops")
    if isinstance(stops, list) and stops:
        stop_types = [str(item.get("StopType") or "").strip() for item in stops if isinstance(item, dict)]
        return {
            "stopCount": len(stops),
            "stopTypes": sorted({item for item in stop_types if item}),
            "isMultiStop": len(stops) > 2,
        }
    return {
        "stopCount": 2,
        "stopTypes": ["Drop", "Pickup"],
        "isMultiStop": False,
    }


def _validate_stop_search_filters(filters, context):
    if "RequireMultiStop" in filters and not isinstance(filters["RequireMultiStop"], bool):
        raise ValueError(f"{context}.RequireMultiStop must be boolean.")
    for field in ["StopCountMin", "StopCountMax"]:
        if field in filters:
            value = filters[field]
            if not isinstance(value, int) or value < 2:
                raise ValueError(f"{context}.{field} must be an integer >= 2.")
    if "StopCountMin" in filters and "StopCountMax" in filters:
        if filters["StopCountMin"] > filters["StopCountMax"]:
            raise ValueError(f"{context}.StopCountMin must be <= StopCountMax.")
    if "RequiredStopTypes" in filters:
        required_types = filters["RequiredStopTypes"]
        if not isinstance(required_types, list) or not required_types:
            raise ValueError(f"{context}.RequiredStopTypes must be a non-empty array.")
        seen = set()
        for idx, value in enumerate(required_types):
            _bounded_string(value, f"{context}.RequiredStopTypes[{idx}]")
            if value not in VALID_STOP_TYPES:
                raise ValueError(
                    f"{context}.RequiredStopTypes[{idx}] must be one of {sorted(VALID_STOP_TYPES)}."
                )
            if value in seen:
                raise ValueError(f"{context}.RequiredStopTypes must not contain duplicates.")
            seen.add(value)


def _validate_stop_plan_acceptance(acceptance, context):
    if not isinstance(acceptance, dict):
        raise ValueError(f"{context} must be an object.")
    _require_fields(acceptance, ["Accepted"], context)
    if not isinstance(acceptance["Accepted"], bool):
        raise ValueError(f"{context}.Accepted must be boolean.")
    if "StopCount" in acceptance:
        value = acceptance["StopCount"]
        if not isinstance(value, int) or value < 2:
            raise ValueError(f"{context}.StopCount must be an integer >= 2.")
    if "StopTypes" in acceptance:
        stop_types = acceptance["StopTypes"]
        if not isinstance(stop_types, list) or not stop_types:
            raise ValueError(f"{context}.StopTypes must be a non-empty array.")
        seen = set()
        for idx, value in enumerate(stop_types):
            _bounded_string(value, f"{context}.StopTypes[{idx}]")
            if value not in VALID_STOP_TYPES:
                raise ValueError(f"{context}.StopTypes[{idx}] must be one of {sorted(VALID_STOP_TYPES)}.")
            if value in seen:
                raise ValueError(f"{context}.StopTypes must not contain duplicates.")
            seen.add(value)
    if "Notes" in acceptance:
        _bounded_string(acceptance["Notes"], f"{context}.Notes")


def _validate_special_instructions(instructions, context):
    if not isinstance(instructions, list) or not instructions:
        raise ValueError(f"{context} must be a non-empty array.")
    seen = set()
    for idx, value in enumerate(instructions):
        _bounded_string(value, f"{context}[{idx}]")
        normalized = str(value).strip().lower()
        if normalized in seen:
            raise ValueError(f"{context} must not contain duplicates.")
        seen.add(normalized)


def _validate_special_instructions_acceptance(acceptance, context):
    if not isinstance(acceptance, dict):
        raise ValueError(f"{context} must be an object.")
    _require_fields(acceptance, ["Accepted"], context)
    if not isinstance(acceptance["Accepted"], bool):
        raise ValueError(f"{context}.Accepted must be boolean.")
    if "Exceptions" in acceptance:
        exceptions = acceptance["Exceptions"]
        if not isinstance(exceptions, list):
            raise ValueError(f"{context}.Exceptions must be an array.")
        seen = set()
        for idx, value in enumerate(exceptions):
            _bounded_string(value, f"{context}.Exceptions[{idx}]")
            normalized = str(value).strip().lower()
            if normalized in seen:
                raise ValueError(f"{context}.Exceptions must not contain duplicates.")
            seen.add(normalized)
    if "Notes" in acceptance:
        _bounded_string(acceptance["Notes"], f"{context}.Notes")


def _normalize_equipment_token(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").strip().lower())


def _canonical_equipment_class(value):
    token = _normalize_equipment_token(value)
    if not token:
        return ""
    return EQUIPMENT_CLASS_ALIASES.get(token, "")


def _canonical_equipment_subclass(value):
    token = _normalize_equipment_token(value)
    if not token:
        return ""
    return EQUIPMENT_SUBCLASS_ALIASES.get(token, "")


def _canonical_equipment_tag(value):
    token = _normalize_equipment_token(value)
    if not token:
        return ""
    return EQUIPMENT_TAG_ALIASES.get(token, "")


def _infer_equipment_class_from_type(equipment_type):
    source = str(equipment_type or "").strip().lower()
    if not source:
        return ""
    normalized_source = _normalize_equipment_token(source)
    aliased_class = EQUIPMENT_TYPE_CLASS_ALIASES.get(normalized_source, "")
    if aliased_class:
        return aliased_class
    direct_alias = _canonical_equipment_class(equipment_type)
    if direct_alias:
        return direct_alias
    if "sprinter van" in source:
        return "SprinterVan"
    if "straight box truck" in source:
        return "StraightBoxTruck"
    if "moving van" in source:
        return "MovingVan"
    if "b-train" in source or "b train" in source:
        return "BTrain"
    if "power only" in source:
        return "PowerOnly"
    if "double drop" in source:
        return "DoubleDrop"
    if "stepdeck" in source or "step deck" in source or "drop deck" in source:
        return "StepDeck"
    if "lowboy" in source:
        return "Lowboy"
    if "removeable gooseneck" in source or "removable gooseneck" in source or " rgn" in source:
        return "RGN"
    if "flabtbed" in source:
        return "Flatbed"
    if "flatbed" in source:
        return "Flatbed"
    if "reefer" in source:
        return "Reefer"
    if "dry van" in source or source.startswith("van") or " van -" in source:
        return "Van"
    if "container" in source:
        return "Container"
    if "tanker" in source:
        return "Tanker"
    if "auto carrier" in source:
        return "AutoCarrier"
    if "dump trailer" in source:
        return "DumpTrailer"
    if "hopper" in source:
        return "HopperBottom"
    if "pneumatic" in source:
        return "Pneumatic"
    if "conveyor" in source:
        return "Conveyor"
    return "Special"


def _infer_equipment_subclass_from_type(equipment_type):
    source = str(equipment_type or "").strip().lower()
    normalized_source = _normalize_equipment_token(source)
    aliased_subclass = EQUIPMENT_TYPE_SUBCLASS_ALIASES.get(normalized_source, "")
    if aliased_subclass:
        return aliased_subclass
    candidates = [
        ("conestoga", "Conestoga"),
        ("contestoga", "Conestoga"),
        ("hotshot", "Hotshot"),
        ("landoll", "Landoll"),
        ("stretch", "Stretch"),
        ("maxi", "Maxi"),
        ("open top", "OpenTop"),
        ("lift gate", "LiftGate"),
        ("roller bed", "RollerBed"),
        ("vented", "Vented"),
        ("insulated", "Insulated"),
        ("insultated", "Insulated"),
        ("intermodal", "Intermodal"),
        ("air ride", "AirRide"),
        ("hazmat", "Hazmat"),
        ("over dimension", "OverDimension"),
        ("double", "Double"),
        ("triple", "Triple"),
        ("aluminum", "Aluminum"),
        ("steel", "Steel"),
    ]
    for marker, canonical in candidates:
        if marker in source:
            return canonical
    return ""


def _infer_equipment_tags_from_type(equipment_type):
    source = str(equipment_type or "").strip().lower()
    normalized_source = _normalize_equipment_token(source)
    tags = set()

    subclass_value = _infer_equipment_subclass_from_type(equipment_type)
    subclass_tag = EQUIPMENT_TAGS_BY_SUBCLASS.get(subclass_value, "")
    if subclass_tag:
        tags.add(subclass_tag)

    if "airride" in normalized_source:
        tags.add("AirRide")
    if "hazmat" in normalized_source:
        tags.add("HazmatCapable")
    if "intermodal" in normalized_source:
        tags.add("Intermodal")
    if "overdimension" in normalized_source:
        tags.add("OverDimensionCapable")
    if "double" in normalized_source:
        tags.add("DoubleTrailer")
    if "triple" in normalized_source:
        tags.add("TripleTrailer")
    return sorted(tags)


def _validate_equipment_contract(payload, context):
    _bounded_string(payload["EquipmentType"], f"{context}.EquipmentType")

    raw_class = payload.get("EquipmentClass")
    class_value = _canonical_equipment_class(raw_class) if raw_class else ""
    if raw_class and not class_value:
        raise ValueError(f"{context}.EquipmentClass must be one of {sorted(VALID_EQUIPMENT_CLASSES)}.")
    if not class_value:
        class_value = _infer_equipment_class_from_type(payload.get("EquipmentType"))
    if class_value not in VALID_EQUIPMENT_CLASSES:
        raise ValueError(f"{context}.EquipmentClass must be one of {sorted(VALID_EQUIPMENT_CLASSES)}.")
    payload["EquipmentClass"] = class_value

    raw_subclass = payload.get("EquipmentSubClass")
    subclass_value = _canonical_equipment_subclass(raw_subclass) if raw_subclass else ""
    if raw_subclass and not subclass_value:
        raise ValueError(
            f"{context}.EquipmentSubClass must be one of {sorted(VALID_EQUIPMENT_SUBCLASSES)}."
        )
    if not subclass_value:
        subclass_value = _infer_equipment_subclass_from_type(payload.get("EquipmentType"))
    if subclass_value:
        payload["EquipmentSubClass"] = subclass_value

    tags = payload.get("EquipmentTags")
    if tags is None:
        inferred_tags = _infer_equipment_tags_from_type(payload.get("EquipmentType"))
        if inferred_tags:
            payload["EquipmentTags"] = inferred_tags
    else:
        if not isinstance(tags, list):
            raise ValueError(f"{context}.EquipmentTags must be an array.")
        normalized = []
        seen = set()
        for idx, item in enumerate(tags):
            _bounded_string(item, f"{context}.EquipmentTags[{idx}]")
            canonical_tag = _canonical_equipment_tag(item)
            if not canonical_tag:
                raise ValueError(f"{context}.EquipmentTags[{idx}] must be one of {sorted(VALID_EQUIPMENT_TAGS)}.")
            if canonical_tag in seen:
                raise ValueError(f"{context}.EquipmentTags must not contain duplicates.")
            seen.add(canonical_tag)
            normalized.append(canonical_tag)
        payload["EquipmentTags"] = normalized

    if "TrailerCount" in payload:
        trailer_count = payload["TrailerCount"]
        if not isinstance(trailer_count, int) or trailer_count <= 0:
            raise ValueError(f"{context}.TrailerCount must be a positive integer.")

    if class_value == "Special":
        description = payload.get("EquipmentSpecialDescription")
        if not description:
            raise ValueError(
                f"{context}.EquipmentSpecialDescription is required when EquipmentClass is 'Special'."
            )
        _bounded_string(description, f"{context}.EquipmentSpecialDescription")


def _validate_equipment_search_filters(payload, context):
    if "EquipmentClass" in payload:
        class_value = _canonical_equipment_class(payload["EquipmentClass"])
        if not class_value:
            raise ValueError(f"{context}.EquipmentClass must be one of {sorted(VALID_EQUIPMENT_CLASSES)}.")
        payload["EquipmentClass"] = class_value
    if "EquipmentSubClass" in payload:
        subclass_value = _canonical_equipment_subclass(payload["EquipmentSubClass"])
        if not subclass_value:
            raise ValueError(
                f"{context}.EquipmentSubClass must be one of {sorted(VALID_EQUIPMENT_SUBCLASSES)}."
            )
        payload["EquipmentSubClass"] = subclass_value
    if "RequiredEquipmentTags" in payload:
        tags = payload["RequiredEquipmentTags"]
        if not isinstance(tags, list) or not tags:
            raise ValueError(f"{context}.RequiredEquipmentTags must be a non-empty array.")
        seen = set()
        normalized = []
        for idx, item in enumerate(tags):
            _bounded_string(item, f"{context}.RequiredEquipmentTags[{idx}]")
            canonical_tag = _canonical_equipment_tag(item)
            if not canonical_tag:
                raise ValueError(
                    f"{context}.RequiredEquipmentTags[{idx}] must be one of {sorted(VALID_EQUIPMENT_TAGS)}."
                )
            if canonical_tag in seen:
                raise ValueError(f"{context}.RequiredEquipmentTags must not contain duplicates.")
            seen.add(canonical_tag)
            normalized.append(canonical_tag)
        payload["RequiredEquipmentTags"] = normalized
    for field in ["TrailerLengthMin", "TrailerLengthMax"]:
        if field in payload:
            value = payload[field]
            if not isinstance(value, (int, float)) or value <= 0:
                raise ValueError(f"{context}.{field} must be a positive number.")
    if "TrailerLengthMin" in payload and "TrailerLengthMax" in payload:
        if float(payload["TrailerLengthMin"]) > float(payload["TrailerLengthMax"]):
            raise ValueError(f"{context}.TrailerLengthMin must be <= TrailerLengthMax.")


def _validate_equipment_acceptance(acceptance, context):
    if not isinstance(acceptance, dict):
        raise ValueError(f"{context} must be an object.")
    _require_fields(acceptance, ["Accepted"], context)
    if not isinstance(acceptance["Accepted"], bool):
        raise ValueError(f"{context}.Accepted must be boolean.")
    if "EquipmentClass" in acceptance:
        class_value = _canonical_equipment_class(acceptance["EquipmentClass"])
        if not class_value:
            raise ValueError(f"{context}.EquipmentClass must be one of {sorted(VALID_EQUIPMENT_CLASSES)}.")
        acceptance["EquipmentClass"] = class_value
    if "EquipmentSubClass" in acceptance:
        subclass_value = _canonical_equipment_subclass(acceptance["EquipmentSubClass"])
        if not subclass_value:
            raise ValueError(
                f"{context}.EquipmentSubClass must be one of {sorted(VALID_EQUIPMENT_SUBCLASSES)}."
            )
        acceptance["EquipmentSubClass"] = subclass_value
    if "EquipmentTags" in acceptance:
        tags = acceptance["EquipmentTags"]
        if not isinstance(tags, list):
            raise ValueError(f"{context}.EquipmentTags must be an array.")
        seen = set()
        normalized = []
        for idx, item in enumerate(tags):
            _bounded_string(item, f"{context}.EquipmentTags[{idx}]")
            canonical_tag = _canonical_equipment_tag(item)
            if not canonical_tag:
                raise ValueError(f"{context}.EquipmentTags[{idx}] must be one of {sorted(VALID_EQUIPMENT_TAGS)}.")
            if canonical_tag in seen:
                raise ValueError(f"{context}.EquipmentTags must not contain duplicates.")
            seen.add(canonical_tag)
            normalized.append(canonical_tag)
        acceptance["EquipmentTags"] = normalized
    for field in ["TrailerLength", "TrailerLengthMin", "TrailerLengthMax"]:
        if field in acceptance:
            value = acceptance[field]
            if not isinstance(value, (int, float)) or value <= 0:
                raise ValueError(f"{context}.{field} must be a positive number.")
    if "TrailerLengthMin" in acceptance and "TrailerLengthMax" in acceptance:
        if float(acceptance["TrailerLengthMin"]) > float(acceptance["TrailerLengthMax"]):
            raise ValueError(f"{context}.TrailerLengthMin must be <= TrailerLengthMax.")
    if "TrailerLength" in acceptance and "TrailerLengthMin" in acceptance:
        if float(acceptance["TrailerLength"]) < float(acceptance["TrailerLengthMin"]):
            raise ValueError(f"{context}.TrailerLength must be >= TrailerLengthMin when both are present.")
    if "TrailerLength" in acceptance and "TrailerLengthMax" in acceptance:
        if float(acceptance["TrailerLength"]) > float(acceptance["TrailerLengthMax"]):
            raise ValueError(f"{context}.TrailerLength must be <= TrailerLengthMax when both are present.")
    if "TrailerCount" in acceptance:
        value = acceptance["TrailerCount"]
        if not isinstance(value, int) or value <= 0:
            raise ValueError(f"{context}.TrailerCount must be a positive integer.")
    if "Notes" in acceptance:
        _bounded_string(acceptance["Notes"], f"{context}.Notes")


def _extract_equipment_terms(payload):
    class_value = _canonical_equipment_class(payload.get("EquipmentClass")) or _infer_equipment_class_from_type(
        payload.get("EquipmentType")
    )
    subclass_value = _canonical_equipment_subclass(payload.get("EquipmentSubClass")) or _infer_equipment_subclass_from_type(
        payload.get("EquipmentType")
    )
    tags = set()
    for item in payload.get("EquipmentTags") or []:
        canonical_tag = _canonical_equipment_tag(item)
        if canonical_tag:
            tags.add(canonical_tag)
    if not tags:
        tags.update(_infer_equipment_tags_from_type(payload.get("EquipmentType")))
    trailer_length = payload.get("TrailerLength")
    trailer_count = payload.get("TrailerCount", 1)
    return {
        "EquipmentClass": class_value,
        "EquipmentSubClass": subclass_value,
        "EquipmentTags": sorted(tags),
        "TrailerLength": trailer_length,
        "TrailerCount": trailer_count,
    }


def _equipment_matches_search_terms(resource_payload, filters):
    resource_terms = _extract_equipment_terms(resource_payload)
    filter_class = _canonical_equipment_class(filters.get("EquipmentClass")) if filters.get("EquipmentClass") else ""
    filter_subclass = (
        _canonical_equipment_subclass(filters.get("EquipmentSubClass"))
        if filters.get("EquipmentSubClass")
        else ""
    )
    required_tags = set(filters.get("RequiredEquipmentTags") or [])
    trailer_length_min = filters.get("TrailerLengthMin")
    trailer_length_max = filters.get("TrailerLengthMax")

    if filter_class and resource_terms["EquipmentClass"] != filter_class:
        return False
    if filter_subclass and resource_terms["EquipmentSubClass"] != filter_subclass:
        return False
    if required_tags and not required_tags.issubset(set(resource_terms["EquipmentTags"])):
        return False
    trailer_length = resource_terms.get("TrailerLength")
    if trailer_length_min is not None and trailer_length is not None:
        if float(trailer_length) < float(trailer_length_min):
            return False
    if trailer_length_max is not None and trailer_length is not None:
        if float(trailer_length) > float(trailer_length_max):
            return False
    return True


def _equipment_acceptance_mismatch(reference_terms, acceptance):
    if not acceptance:
        return True
    if acceptance.get("Accepted") is not True:
        return True

    accepted_class = _canonical_equipment_class(acceptance.get("EquipmentClass"))
    accepted_subclass = _canonical_equipment_subclass(acceptance.get("EquipmentSubClass"))
    accepted_tags = set(acceptance.get("EquipmentTags") or [])
    accepted_trailer_length = acceptance.get("TrailerLength")
    accepted_trailer_length_min = acceptance.get("TrailerLengthMin")
    accepted_trailer_length_max = acceptance.get("TrailerLengthMax")
    accepted_trailer_count = acceptance.get("TrailerCount")

    if accepted_class and accepted_class != reference_terms["EquipmentClass"]:
        return True
    if accepted_subclass and reference_terms.get("EquipmentSubClass"):
        if accepted_subclass != reference_terms["EquipmentSubClass"]:
            return True
    if accepted_tags and not set(reference_terms["EquipmentTags"]).issubset(accepted_tags):
        return True
    reference_trailer_length = reference_terms.get("TrailerLength")
    if reference_trailer_length is not None:
        has_range = accepted_trailer_length_min is not None or accepted_trailer_length_max is not None
        if has_range:
            if accepted_trailer_length_min is not None:
                if float(reference_trailer_length) < (float(accepted_trailer_length_min) - 0.01):
                    return True
            if accepted_trailer_length_max is not None:
                if float(reference_trailer_length) > (float(accepted_trailer_length_max) + 0.01):
                    return True
        elif accepted_trailer_length is not None:
            if abs(float(accepted_trailer_length) - float(reference_trailer_length)) > 0.01:
                return True
    if accepted_trailer_count is not None and reference_terms.get("TrailerCount") is not None:
        if int(accepted_trailer_count) != int(reference_terms["TrailerCount"]):
            return True
    return False


def _canonical_driver_configuration(value):
    token = _normalize_equipment_token(value)
    if not token:
        return ""
    return DRIVER_CONFIGURATION_ALIASES.get(token, "")


def _validate_driver_configuration_terms(payload, context):
    if "DriverConfiguration" not in payload:
        return
    canonical = _canonical_driver_configuration(payload.get("DriverConfiguration"))
    if not canonical:
        raise ValueError(
            f"{context}.DriverConfiguration must be one of {sorted(VALID_DRIVER_CONFIGURATIONS)}."
        )
    payload["DriverConfiguration"] = canonical


def _validate_driver_configuration_filters(payload, context):
    if "RequiredDriverConfiguration" not in payload:
        return
    canonical = _canonical_driver_configuration(payload.get("RequiredDriverConfiguration"))
    if not canonical:
        raise ValueError(
            f"{context}.RequiredDriverConfiguration must be one of {sorted(VALID_DRIVER_CONFIGURATIONS)}."
        )
    payload["RequiredDriverConfiguration"] = canonical


def _validate_driver_configuration_acceptance(acceptance, context):
    if not isinstance(acceptance, dict):
        raise ValueError(f"{context} must be an object.")
    _require_fields(acceptance, ["Accepted"], context)
    if not isinstance(acceptance["Accepted"], bool):
        raise ValueError(f"{context}.Accepted must be boolean.")
    if "DriverConfiguration" in acceptance:
        canonical = _canonical_driver_configuration(acceptance.get("DriverConfiguration"))
        if not canonical:
            raise ValueError(
                f"{context}.DriverConfiguration must be one of {sorted(VALID_DRIVER_CONFIGURATIONS)}."
            )
        acceptance["DriverConfiguration"] = canonical
    if "Notes" in acceptance:
        _bounded_string(acceptance["Notes"], f"{context}.Notes")


def _driver_configuration_matches(resource_payload, filters):
    required = _canonical_driver_configuration(filters.get("RequiredDriverConfiguration"))
    if not required:
        return True
    resource = _canonical_driver_configuration(resource_payload.get("DriverConfiguration"))
    return bool(resource) and resource == required


def _driver_configuration_acceptance_mismatch(reference_configuration, acceptance):
    canonical_reference = _canonical_driver_configuration(reference_configuration)
    if not canonical_reference:
        return False
    if not acceptance:
        return True
    if acceptance.get("Accepted") is not True:
        return True
    accepted_configuration = _canonical_driver_configuration(acceptance.get("DriverConfiguration"))
    if not accepted_configuration:
        return True
    return accepted_configuration != canonical_reference


def _validate_schedule_time_window(window, context):
    if not isinstance(window, dict):
        raise ValueError(f"{context} must be an object.")
    _require_fields(window, ["Start", "End", "TimeZone"], context)
    start_dt = _parse_iso_datetime(window["Start"], f"{context}.Start")
    end_dt = _parse_iso_datetime(window["End"], f"{context}.End")
    if start_dt > end_dt:
        raise ValueError(f"{context}.Start must be <= End.")
    _bounded_string(window["TimeZone"], f"{context}.TimeZone")
    timezone_value = str(window["TimeZone"]).strip()
    if timezone_value and not TIME_ZONE_PATTERN.fullmatch(timezone_value):
        raise ValueError(f"{context}.TimeZone must be an IANA timezone (e.g., America/Chicago).")


def _validate_schedule_terms_fields(payload, context):
    has_pickup_earliest = "PickupEarliest" in payload
    has_pickup_latest = "PickupLatest" in payload
    if has_pickup_earliest != has_pickup_latest:
        raise ValueError(f"{context} must include both PickupEarliest and PickupLatest when either is present.")
    if has_pickup_earliest:
        _validate_iso_date(payload["PickupEarliest"], f"{context}.PickupEarliest")
        _validate_iso_date(payload["PickupLatest"], f"{context}.PickupLatest")
        if payload["PickupEarliest"] > payload["PickupLatest"]:
            raise ValueError(f"{context}.PickupEarliest must be <= PickupLatest.")

    has_delivery_earliest = "DeliveryEarliest" in payload
    has_delivery_latest = "DeliveryLatest" in payload
    if has_delivery_earliest != has_delivery_latest:
        raise ValueError(f"{context} must include both DeliveryEarliest and DeliveryLatest when either is present.")
    if has_delivery_earliest:
        _validate_iso_date(payload["DeliveryEarliest"], f"{context}.DeliveryEarliest")
        _validate_iso_date(payload["DeliveryLatest"], f"{context}.DeliveryLatest")
        if payload["DeliveryEarliest"] > payload["DeliveryLatest"]:
            raise ValueError(f"{context}.DeliveryEarliest must be <= DeliveryLatest.")
        if has_pickup_earliest and payload["DeliveryLatest"] < payload["PickupEarliest"]:
            raise ValueError(f"{context}.DeliveryLatest must be on/after PickupEarliest.")

    if "PickupTimeWindow" in payload:
        _validate_schedule_time_window(payload["PickupTimeWindow"], f"{context}.PickupTimeWindow")
    if "DeliveryTimeWindow" in payload:
        _validate_schedule_time_window(payload["DeliveryTimeWindow"], f"{context}.DeliveryTimeWindow")

    if "DeliveryTimeWindow" in payload and not has_delivery_earliest:
        raise ValueError(f"{context}.DeliveryEarliest/DeliveryLatest are required when DeliveryTimeWindow is present.")


def _validate_schedule_acceptance(acceptance, context):
    if not isinstance(acceptance, dict):
        raise ValueError(f"{context} must be an object.")
    _require_fields(acceptance, ["Accepted"], context)
    if not isinstance(acceptance["Accepted"], bool):
        raise ValueError(f"{context}.Accepted must be boolean.")
    if "Exceptions" in acceptance:
        if not isinstance(acceptance["Exceptions"], list):
            raise ValueError(f"{context}.Exceptions must be an array.")
        seen = set()
        for idx, value in enumerate(acceptance["Exceptions"]):
            _bounded_string(value, f"{context}.Exceptions[{idx}]")
            normalized = str(value).strip().lower()
            if normalized in seen:
                raise ValueError(f"{context}.Exceptions must not contain duplicates.")
            seen.add(normalized)
    for field in ["PickupTimeWindow", "DeliveryTimeWindow"]:
        if field in acceptance:
            _validate_schedule_time_window(acceptance[field], f"{context}.{field}")
    if "Notes" in acceptance:
        _bounded_string(acceptance["Notes"], f"{context}.Notes")


def _validate_load_reference_numbers(reference_numbers, context):
    if not isinstance(reference_numbers, dict):
        raise ValueError(f"{context} must be an object.")

    allowed_fields = {
        "PrimaryReferenceNumber",
        "SecondaryReferenceNumber",
        "Additional",
    }
    unknown_fields = sorted(set(reference_numbers.keys()) - allowed_fields)
    if unknown_fields:
        raise ValueError(f"{context} contains unsupported fields: {unknown_fields}.")

    has_reference = False
    for field in ["PrimaryReferenceNumber", "SecondaryReferenceNumber"]:
        if field in reference_numbers:
            _bounded_string(reference_numbers[field], f"{context}.{field}")
            has_reference = True

    if "Additional" in reference_numbers:
        additional = reference_numbers["Additional"]
        if not isinstance(additional, list):
            raise ValueError(f"{context}.Additional must be an array.")
        for idx, entry in enumerate(additional):
            item_context = f"{context}.Additional[{idx}]"
            if not isinstance(entry, dict):
                raise ValueError(f"{item_context} must be an object.")
            _require_fields(entry, ["ReferenceType", "ReferenceValue"], item_context)
            _bounded_string(entry["ReferenceType"], f"{item_context}.ReferenceType")
            _bounded_string(entry["ReferenceValue"], f"{item_context}.ReferenceValue")
            if "IssuerParty" in entry:
                _bounded_string(entry["IssuerParty"], f"{item_context}.IssuerParty")
                if entry["IssuerParty"] not in VALID_ACCESSORIAL_PARTIES:
                    raise ValueError(
                        f"{item_context}.IssuerParty must be one of {sorted(VALID_ACCESSORIAL_PARTIES)}."
                    )
            has_reference = True

    if not has_reference:
        raise ValueError(f"{context} must include at least one reference number.")


def _validate_operational_handoff(handoff, context):
    if not isinstance(handoff, dict):
        raise ValueError(f"{context} must be an object.")

    allowed_fields = {
        "OperationalReference",
        "SystemOfRecordType",
        "SystemOfRecordRef",
        "HandoffEndpointType",
        "HandoffEndpointRef",
        "SupportedHandoffActions",
        "SetupStatus",
    }
    unknown_fields = sorted(set(handoff.keys()) - allowed_fields)
    if unknown_fields:
        raise ValueError(f"{context} contains unsupported fields: {unknown_fields}.")

    _require_fields(
        handoff,
        ["OperationalReference", "SystemOfRecordType", "SystemOfRecordRef", "SetupStatus"],
        context,
    )
    _bounded_string(handoff["OperationalReference"], f"{context}.OperationalReference")
    _bounded_string(handoff["SystemOfRecordType"], f"{context}.SystemOfRecordType")
    if handoff["SystemOfRecordType"] not in VALID_HANDOFF_SYSTEM_OF_RECORD_TYPES:
        raise ValueError(
            f"{context}.SystemOfRecordType must be one of {sorted(VALID_HANDOFF_SYSTEM_OF_RECORD_TYPES)}."
        )
    _bounded_string(handoff["SystemOfRecordRef"], f"{context}.SystemOfRecordRef")
    _bounded_string(handoff["SetupStatus"], f"{context}.SetupStatus")
    if handoff["SetupStatus"] not in VALID_HANDOFF_SETUP_STATUSES:
        raise ValueError(
            f"{context}.SetupStatus must be one of {sorted(VALID_HANDOFF_SETUP_STATUSES)}."
        )

    has_endpoint_type = "HandoffEndpointType" in handoff
    has_endpoint_ref = "HandoffEndpointRef" in handoff
    if has_endpoint_type != has_endpoint_ref:
        raise ValueError(
            f"{context} must include both HandoffEndpointType and HandoffEndpointRef when either is present."
        )
    if has_endpoint_type:
        _bounded_string(handoff["HandoffEndpointType"], f"{context}.HandoffEndpointType")
        if handoff["HandoffEndpointType"] not in VALID_HANDOFF_ENDPOINT_TYPES:
            raise ValueError(
                f"{context}.HandoffEndpointType must be one of {sorted(VALID_HANDOFF_ENDPOINT_TYPES)}."
            )
        _bounded_string(handoff["HandoffEndpointRef"], f"{context}.HandoffEndpointRef")

    if "SupportedHandoffActions" in handoff:
        actions = handoff["SupportedHandoffActions"]
        if not isinstance(actions, list) or not actions:
            raise ValueError(f"{context}.SupportedHandoffActions must be a non-empty array.")
        seen = set()
        for idx, action in enumerate(actions):
            _bounded_string(action, f"{context}.SupportedHandoffActions[{idx}]")
            if action not in VALID_HANDOFF_ACTIONS:
                raise ValueError(
                    f"{context}.SupportedHandoffActions[{idx}] must be one of {sorted(VALID_HANDOFF_ACTIONS)}."
                )
            if action in seen:
                raise ValueError(f"{context}.SupportedHandoffActions must not contain duplicates.")
            seen.add(action)


def _validate_verifier_dependency_integrity():
    if not NON_LOCAL_MODE:
        return
    if not (VERIFIER_COMPONENT_FILE and EXPECTED_VERIFIER_COMPONENT_SHA256):
        return
    try:
        with open(VERIFIER_COMPONENT_FILE, "rb") as handle:
            digest = hashlib.sha256(handle.read()).hexdigest().lower()
    except FileNotFoundError as exc:
        raise RuntimeError("Verifier dependency file not found.") from exc
    if digest != EXPECTED_VERIFIER_COMPONENT_SHA256:
        raise RuntimeError("Verifier dependency hash mismatch.")


def _default_operational_handoff(agent_name, load_id, load):
    slug = re.sub(r"[^a-z0-9]+", "-", str(agent_name).strip().lower()).strip("-") or "ops"
    reference_numbers = load.get("LoadReferenceNumbers") or {}
    operational_reference = (
        reference_numbers.get("PrimaryReferenceNumber")
        or reference_numbers.get("SecondaryReferenceNumber")
        or f"OPS-{load_id[:8].upper()}"
    )
    return {
        "OperationalReference": operational_reference,
        "SystemOfRecordType": "TMS",
        "SystemOfRecordRef": f"{slug}-load-{load_id[:8]}",
        "HandoffEndpointType": "InternalQueue",
        "HandoffEndpointRef": f"{slug}:booking-confirmed",
        "SupportedHandoffActions": [
            "GenerateRateConfirmation",
            "RequestCarrierSetup",
            "RetrieveDispatchInstructions",
        ],
        "SetupStatus": "Unknown",
    }


def _validate_agent_identity_binding(envelope):
    sender_name = str(envelope.get("From") or "")
    receiver_name = str(envelope.get("To") or "")
    sender_agent_id = str(envelope.get("FromAgentID") or "").strip().lower()
    receiver_agent_id = str(envelope.get("ToAgentID") or "").strip().lower()
    expected_sender_id = resolve_agent_id(sender_name)
    expected_receiver_id = resolve_agent_id(receiver_name)

    if sender_agent_id and sender_agent_id != expected_sender_id:
        raise ValueError(
            f"Envelope.FromAgentID '{sender_agent_id}' does not match expected sender AgentID "
            f"'{expected_sender_id}'."
        )
    if receiver_agent_id and receiver_agent_id != expected_receiver_id:
        raise ValueError(
            f"Envelope.ToAgentID '{receiver_agent_id}' does not match expected receiver AgentID "
            f"'{expected_receiver_id}'."
        )

    if NON_LOCAL_MODE:
        if not sender_agent_id:
            raise ValueError("Envelope.FromAgentID is required in non-local mode.")
        if not receiver_agent_id:
            raise ValueError("Envelope.ToAgentID is required in non-local mode.")
        if AGENT_KEY_REGISTRY and sender_name not in AGENT_ID_BINDINGS["by_name"]:
            raise ValueError(
                f"Envelope.From '{sender_name}' is not present in configured AGENT_KEY_REGISTRY."
            )
        if AGENT_KEY_REGISTRY and receiver_name not in AGENT_ID_BINDINGS["by_name"]:
            raise ValueError(
                f"Envelope.To '{receiver_name}' is not present in configured AGENT_KEY_REGISTRY."
            )

    signature_key_id = str(envelope.get("SignatureKeyID") or "").strip()
    sender_binding = AGENT_ID_BINDINGS["by_name"].get(sender_name)
    if signature_key_id and sender_binding:
        allowed_kids = set(sender_binding.get("allowed_kids") or [])
        if allowed_kids and signature_key_id not in allowed_kids:
            raise ValueError(
                f"Envelope.SignatureKeyID '{signature_key_id}' is not allowed for "
                f"Envelope.FromAgentID '{expected_sender_id}'."
            )


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
        "--shipper-flow",
        action="store_true",
        help=(
            "Run optional shipper -> broker -> carrier load orchestration path "
            "(existing broker-originated load flow remains default)."
        ),
    )
    parser.add_argument(
        "--mc-number",
        default=None,
        help="MC number used for FMCSA verification (example: 498282).",
    )
    parser.add_argument(
        "--fmcsa-source",
        choices=["authority-mock", "hosted-adapter", "implementer-adapter", "vendor-direct"],
        default="authority-mock",
        help=(
            "FMCSA verification source. 'implementer-adapter' and 'vendor-direct' are preferred labels; "
            "'hosted-adapter' is retained as a backward-compatible alias."
        ),
    )
    parser.add_argument(
        "--rate-model",
        choices=["PerMile", "Flat", "PerPallet", "CWT", "PerHour", "LaneMinimum"],
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
        help="Verification policy profile ID (for example: US_VERIFICATION_BALANCED_V1).",
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
    parser.add_argument(
        "--mileage-dispute-policy",
        choices=["strict", "balanced"],
        default=MILEAGE_DISPUTE_POLICY,
        help=(
            "PerMile disagreement behavior. "
            "'strict' counters on any mismatch; 'balanced' uses tolerance before countering."
        ),
    )
    parser.add_argument(
        "--mileage-abs-tolerance-miles",
        type=float,
        default=MILEAGE_DISPUTE_ABS_TOLERANCE_MILES,
        help="Absolute miles tolerance for balanced mileage dispute handling.",
    )
    parser.add_argument(
        "--mileage-rel-tolerance-ratio",
        type=float,
        default=MILEAGE_DISPUTE_REL_TOLERANCE_RATIO,
        help="Relative miles tolerance ratio (for example 0.02 = 2%%) for balanced handling.",
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
        agent_id = str(material.get("agent_id") or resolve_agent_id(agent_name)).strip().lower()
        if not AGENT_ID_PATTERN.fullmatch(agent_id):
            raise RuntimeError(
                f"Agent '{agent_name}' has invalid agent_id '{agent_id}' in FAXP_AGENT_KEY_REGISTRY."
            )
        active_kid = material.get("active_kid", "")
        private_keys = material.get("private_keys", {})
        public_keys = material.get("public_keys", {})
        key_metadata = material.get("key_metadata", {})
        allowed_kids = {
            str(item).strip()
            for item in (material.get("allowed_kids") or [])
            if str(item).strip()
        }
        if allowed_kids and active_kid and active_kid not in allowed_kids:
            raise RuntimeError(
                f"Agent '{agent_name}' active_kid '{active_kid}' is not listed in allowed_kids."
            )
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
        if ENFORCE_TRUSTED_VERIFIER_REGISTRY and not TRUSTED_VERIFIER_REGISTRY:
            raise RuntimeError(
                "Trusted verifier registry enforcement is enabled in non-local mode but no registry entries are configured."
            )
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
    if rate_model == "LaneMinimum":
        return 1850.0
    if rate_model == "PerHour":
        return 95.0
    if rate_model == "PerPallet":
        return 74.0
    if rate_model == "CWT":
        return 4.75
    return 2.35


def default_bid_amount(rate_model):
    if rate_model == "Flat":
        return 1950.0
    if rate_model == "LaneMinimum":
        return 1950.0
    if rate_model == "PerHour":
        return 110.0
    if rate_model == "PerPallet":
        return 79.0
    if rate_model == "CWT":
        return 5.10
    return 2.62


def default_search_max(rate_model):
    if rate_model == "Flat":
        return 2200.0
    if rate_model == "LaneMinimum":
        return 2200.0
    if rate_model == "PerHour":
        return 140.0
    if rate_model == "PerPallet":
        return 90.0
    if rate_model == "CWT":
        return 6.0
    return 2.80


def counter_amount(rate_model, floor_amount):
    if rate_model == "Flat":
        return round(floor_amount + 150.0, 2)
    if rate_model == "LaneMinimum":
        return round(floor_amount + 150.0, 2)
    if rate_model == "PerHour":
        return round(floor_amount + 8.0, 2)
    if rate_model == "PerPallet":
        return round(floor_amount + 4.0, 2)
    if rate_model == "CWT":
        return round(floor_amount + 0.35, 2)
    return round(floor_amount + 0.16, 2)


def default_rate_quantity(rate_model):
    if rate_model == "PerPallet":
        return 26
    if rate_model == "CWT":
        return 420
    if rate_model == "PerHour":
        return 6
    return 1


def default_agreed_miles():
    return 925.5


def _normalize_rate_components(rate):
    if "LineHaulAmount" not in rate:
        return

    linehaul = float(rate["LineHaulAmount"])
    has_fuel_amount = "FuelSurchargeAmount" in rate
    has_fuel_percent = "FuelSurchargePercent" in rate

    if has_fuel_percent and not has_fuel_amount:
        rate["FuelSurchargeAmount"] = round(linehaul * float(rate["FuelSurchargePercent"]) / 100.0, 2)
    elif has_fuel_amount and not has_fuel_percent:
        if linehaul > 0:
            rate["FuelSurchargePercent"] = round(float(rate["FuelSurchargeAmount"]) / linehaul * 100.0, 2)
        else:
            rate["FuelSurchargePercent"] = 0.0


def default_unit_basis(rate_model):
    return str((RATE_MODEL_CATALOG.get(rate_model) or {}).get("unitBasis") or "")


def build_rate(rate_model, amount, **metadata):
    rate = {
        "RateModel": rate_model,
        "Amount": round(float(amount), 2),
        "Currency": "USD",
    }
    fallback_unit_basis = default_unit_basis(rate_model)
    if fallback_unit_basis and "UnitBasis" not in metadata:
        rate["UnitBasis"] = fallback_unit_basis
    if rate_model == "PerMile":
        if "AgreedMiles" not in metadata:
            rate["AgreedMiles"] = default_agreed_miles()
        if "MilesSource" not in metadata:
            rate["MilesSource"] = "BrokerRouteGuide"
    if rate_model in {"PerPallet", "CWT", "PerHour"} and "Quantity" not in metadata:
        rate["Quantity"] = default_rate_quantity(rate_model)
    for key, value in metadata.items():
        if value is not None:
            rate[key] = value
    _normalize_rate_components(rate)
    return rate


def format_rate(rate):
    if rate["RateModel"] == "Flat":
        return f"${rate['Amount']:.2f} flat"
    if rate["RateModel"] == "LaneMinimum":
        return f"${rate['Amount']:.2f} lane minimum"
    if rate["RateModel"] == "PerHour":
        return f"${rate['Amount']:.2f}/hour"
    if rate["RateModel"] == "PerPallet":
        return f"${rate['Amount']:.2f}/pallet"
    if rate["RateModel"] == "CWT":
        return f"${rate['Amount']:.2f}/cwt"
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


RATE_MODEL_CATALOG = {
    # Active models supported by executable v0.3 negotiation flows.
    "PerMile": {"status": "active", "unitBasis": "mile"},
    "Flat": {"status": "active", "unitBasis": "load"},
    "PerPallet": {"status": "active", "unitBasis": "pallet"},
    "CWT": {"status": "active", "unitBasis": "cwt"},
    "PerHour": {"status": "active", "unitBasis": "hour"},
    "LaneMinimum": {"status": "active", "unitBasis": "lane"},
    # Planned models for post-v0.3 profile expansion.
    "Tiered": {"status": "planned", "unitBasis": "lane"},
}
VALID_RATE_MODELS = {
    name for name, details in RATE_MODEL_CATALOG.items() if details.get("status") == "active"
}
PLANNED_RATE_MODELS = {
    name for name, details in RATE_MODEL_CATALOG.items() if details.get("status") == "planned"
}
RATE_MODEL_REQUIREMENTS = {
    # Active models are enforced in runtime validation.
    "PerMile": {
        "requiredFields": ["UnitBasis", "AgreedMiles", "MilesSource"],
        "allowedUnitBasis": ["mile"],
        "status": "active",
    },
    "Flat": {
        "requiredFields": ["UnitBasis"],
        "allowedUnitBasis": ["load"],
        "status": "active",
    },
    "PerPallet": {
        "requiredFields": ["UnitBasis", "Quantity"],
        "allowedUnitBasis": ["pallet"],
        "status": "active",
    },
    "CWT": {
        "requiredFields": ["UnitBasis", "Quantity"],
        "allowedUnitBasis": ["cwt"],
        "status": "active",
    },
    "PerHour": {
        "requiredFields": ["UnitBasis", "Quantity"],
        "allowedUnitBasis": ["hour"],
        "status": "active",
    },
    "LaneMinimum": {
        "requiredFields": ["UnitBasis"],
        "allowedUnitBasis": ["lane"],
        "status": "active",
    },
    "Tiered": {
        "requiredFields": ["UnitBasis"],
        "allowedUnitBasis": ["lane"],
        "status": "planned",
    },
}
VALID_BID_RESPONSE_TYPES = {"Accept", "Counter", "Reject"}
VALID_EXECUTION_STATUSES = {"Booked"}
VALID_VERIFIED_BADGES = {"None", "Basic", "Premium"}
VALID_VERIFICATION_STATUSES = {"Success", "Fail", "Pending"}
VALID_VERIFICATION_MODES = {"Live", "Cached", "Fallback"}
VALID_DISPATCH_AUTHORIZATIONS = {"Allowed", "Hold", "Blocked"}
VALID_HANDOFF_SYSTEM_OF_RECORD_TYPES = {
    "TMS",
    "LoadBoard",
    "BrokerPortal",
    "CarrierPortal",
    "ShipperPortal",
    "InternalQueue",
    "ManualWorkflow",
}
VALID_HANDOFF_ENDPOINT_TYPES = {
    "A2A",
    "Webhook",
    "Portal",
    "Email",
    "InternalQueue",
    "ManualWorkflow",
}
VALID_HANDOFF_SETUP_STATUSES = {"Known", "Required", "Expired", "Unknown"}
VALID_HANDOFF_ACTIONS = {
    "GenerateRateConfirmation",
    "SendRateConfirmation",
    "RequestCarrierSetup",
    "RetrieveDispatchInstructions",
    "AcknowledgeBooking",
    "ManualFollowUp",
}
VALID_ACCESSORIAL_PRICING_MODES = {
    "IncludedInBaseRate",
    "Reimbursable",
    "PassThrough",
    "TBD",
}
ACCESSORIAL_TYPE_CATALOG = {
    # Active booking-plane accessorial types in v0.1.1/v0.3 baseline.
    "UnloadingFee": {"status": "active"},
    "OverweightPermit": {"status": "active"},
    "EscortVehicle": {"status": "active"},
    "Detention": {"status": "active"},
    # Planned types are declared for roadmap visibility and future RFC-governed expansion.
    "Layover": {"status": "planned"},
    "LumperFee": {"status": "planned"},
}
ACTIVE_ACCESSORIAL_TYPES = tuple(
    name for name, details in ACCESSORIAL_TYPE_CATALOG.items() if details.get("status") == "active"
)
PLANNED_ACCESSORIAL_TYPES = tuple(
    name for name, details in ACCESSORIAL_TYPE_CATALOG.items() if details.get("status") == "planned"
)
VALID_ACCESSORIAL_PARTIES = {"Broker", "Carrier", "Shipper", "Vendor", "Unknown"}
VALID_ACCESSORIAL_EVIDENCE_TYPES = {"Receipt", "Permit", "EscortInvoice", "Other"}
VALID_ACCESSORIAL_STATUSES = {"Proposed", "Approved", "Rejected"}
VALID_DETENTION_RATE_UNITS = {"Hour"}
VALID_DETENTION_LOCATION_EVIDENCE_TYPES = {"GPS", "ELDPosition", "GeofenceCheckIn", "Other"}
VALID_STOP_TYPES = {"Pickup", "Drop"}
VALID_EQUIPMENT_CLASSES = {
    "Van",
    "Reefer",
    "Flatbed",
    "StepDeck",
    "DoubleDrop",
    "Lowboy",
    "RGN",
    "Tanker",
    "Container",
    "AutoCarrier",
    "DumpTrailer",
    "HopperBottom",
    "Pneumatic",
    "StraightBoxTruck",
    "SprinterVan",
    "PowerOnly",
    "BTrain",
    "Conveyor",
    "MovingVan",
    "Special",
}
VALID_EQUIPMENT_SUBCLASSES = {
    "Hotshot",
    "Conestoga",
    "Landoll",
    "Stretch",
    "Maxi",
    "OpenTop",
    "LiftGate",
    "RollerBed",
    "Vented",
    "Insulated",
    "Intermodal",
    "AirRide",
    "Hazmat",
    "Double",
    "Triple",
    "OverDimension",
    "Aluminum",
    "Steel",
}
VALID_EQUIPMENT_TAGS = {
    "AirRide",
    "HazmatCapable",
    "Intermodal",
    "OverDimensionCapable",
    "DoubleTrailer",
    "TripleTrailer",
}
VALID_DRIVER_CONFIGURATIONS = {"Single", "Team"}
DRIVER_CONFIGURATION_ALIASES = {
    "single": "Single",
    "singledriver": "Single",
    "solo": "Single",
    "team": "Team",
    "teamdriver": "Team",
    "teamdrivers": "Team",
    "dual": "Team",
}
EQUIPMENT_CLASS_ALIASES = {
    "dryvan": "Van",
    "van": "Van",
    "reefer": "Reefer",
    "flatbed": "Flatbed",
    "stepdeck": "StepDeck",
    "doubledrop": "DoubleDrop",
    "lowboy": "Lowboy",
    "rgn": "RGN",
    "removeablegooseneck": "RGN",
    "removablegooseneck": "RGN",
    "tanker": "Tanker",
    "container": "Container",
    "autocarrier": "AutoCarrier",
    "dumptrailer": "DumpTrailer",
    "hopperbottom": "HopperBottom",
    "pneumatic": "Pneumatic",
    "straightboxtruck": "StraightBoxTruck",
    "sprintervan": "SprinterVan",
    "poweronly": "PowerOnly",
    "btrain": "BTrain",
    "conveyor": "Conveyor",
    "movingvan": "MovingVan",
    "special": "Special",
}
EQUIPMENT_SUBCLASS_ALIASES = {
    "hotshot": "Hotshot",
    "conestoga": "Conestoga",
    "contestoga": "Conestoga",
    "landoll": "Landoll",
    "stretch": "Stretch",
    "maxi": "Maxi",
    "opentop": "OpenTop",
    "liftgate": "LiftGate",
    "rollerbed": "RollerBed",
    "vented": "Vented",
    "insulated": "Insulated",
    "intermodal": "Intermodal",
    "airride": "AirRide",
    "hazmat": "Hazmat",
    "double": "Double",
    "triple": "Triple",
    "overdimension": "OverDimension",
    "aluminum": "Aluminum",
    "steel": "Steel",
}
EQUIPMENT_TAG_ALIASES = {
    "airride": "AirRide",
    "hazmat": "HazmatCapable",
    "hazmatcapable": "HazmatCapable",
    "intermodal": "Intermodal",
    "overdimension": "OverDimensionCapable",
    "overdimensioncapable": "OverDimensionCapable",
    "double": "DoubleTrailer",
    "doubletrailer": "DoubleTrailer",
    "triple": "TripleTrailer",
    "tripletrailer": "TripleTrailer",
}
EQUIPMENT_TAGS_BY_SUBCLASS = {
    "AirRide": "AirRide",
    "Hazmat": "HazmatCapable",
    "Intermodal": "Intermodal",
    "OverDimension": "OverDimensionCapable",
    "Double": "DoubleTrailer",
    "Triple": "TripleTrailer",
}
EQUIPMENT_TYPE_CLASS_ALIASES = {
    "dryvan": "Van",
    "reefer": "Reefer",
    "flatbed": "Flatbed",
    "autocarrier": "AutoCarrier",
    "btrain": "BTrain",
    "conestoga": "Flatbed",
    "container": "Container",
    "containerinsulated": "Container",
    "containerinsultated": "Container",
    "containerrefrigerated": "Container",
    "conveyor": "Conveyor",
    "doubledrop": "DoubleDrop",
    "dropdecklandoll": "StepDeck",
    "dumptrailer": "DumpTrailer",
    "flatbedairride": "Flatbed",
    "flatbedconestoga": "Flatbed",
    "flatbedcontestoga": "Flatbed",
    "flatbeddouble": "Flatbed",
    "flatbedhazmat": "Flatbed",
    "flatbedhotshot": "Flatbed",
    "flatbedmaxi": "Flatbed",
    "flatbedoverdimension": "Flatbed",
    "flabtbedoverdimension": "Flatbed",
    "hopperbottom": "HopperBottom",
    "lowboy": "Lowboy",
    "lowboyoverdimension": "Lowboy",
    "movingvan": "MovingVan",
    "pneumatic": "Pneumatic",
    "poweronly": "PowerOnly",
    "reeferairride": "Reefer",
    "reeferdouble": "Reefer",
    "reeferhazmat": "Reefer",
    "reeferintermodal": "Reefer",
    "removeablegooseneck": "RGN",
    "removablegooseneck": "RGN",
    "stepdeck": "StepDeck",
    "stepdeckconestoga": "StepDeck",
    "straightboxtruck": "StraightBoxTruck",
    "stretchtrailer": "Flatbed",
    "tankeraluminum": "Tanker",
    "tankerintermodal": "Tanker",
    "tankersteel": "Tanker",
    "vanairride": "Van",
    "vanconestoga": "Van",
    "vanhazmat": "Van",
    "vanhotshot": "Van",
    "vaninsulated": "Van",
    "vanintermodal": "Van",
    "vanliftgate": "Van",
    "vanopentop": "Van",
    "vanrollerbed": "Van",
    "vantriple": "Van",
    "vanvented": "Van",
    "sprintervan": "SprinterVan",
    "sprintervanhazmat": "SprinterVan",
}
EQUIPMENT_TYPE_SUBCLASS_ALIASES = {
    "conestoga": "Conestoga",
    "containerinsulated": "Insulated",
    "containerinsultated": "Insulated",
    "containerrefrigerated": "Insulated",
    "dropdecklandoll": "Landoll",
    "flatbedairride": "AirRide",
    "flatbedconestoga": "Conestoga",
    "flatbedcontestoga": "Conestoga",
    "flatbeddouble": "Double",
    "flatbedhazmat": "Hazmat",
    "flatbedhotshot": "Hotshot",
    "flatbedmaxi": "Maxi",
    "flatbedoverdimension": "OverDimension",
    "flabtbedoverdimension": "OverDimension",
    "lowboyoverdimension": "OverDimension",
    "reeferairride": "AirRide",
    "reeferdouble": "Double",
    "reeferhazmat": "Hazmat",
    "reeferintermodal": "Intermodal",
    "stepdeckconestoga": "Conestoga",
    "stretchtrailer": "Stretch",
    "tankeraluminum": "Aluminum",
    "tankerintermodal": "Intermodal",
    "tankersteel": "Steel",
    "vanairride": "AirRide",
    "vanconestoga": "Conestoga",
    "vanhazmat": "Hazmat",
    "vanhotshot": "Hotshot",
    "vaninsulated": "Insulated",
    "vanintermodal": "Intermodal",
    "vanliftgate": "LiftGate",
    "vanopentop": "OpenTop",
    "vanrollerbed": "RollerBed",
    "vantriple": "Triple",
    "vanvented": "Vented",
    "sprintervanhazmat": "Hazmat",
}
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


def _validate_rate_model(rate_model, context):
    _bounded_string(rate_model, context)
    if rate_model not in VALID_RATE_MODELS:
        raise ValueError(f"{context} must be one of {sorted(VALID_RATE_MODELS)}.")


def _validate_rate_extensions(rate, context):
    string_fields = ["UnitBasis", "ReferenceID", "Notes", "MilesSource", "MilesSourceVersion"]
    numeric_fields = [
        "DistanceMiles",
        "Quantity",
        "LineHaulAmount",
        "FuelSurchargeAmount",
        "AgreedMiles",
    ]
    percent_fields = ["FuelSurchargePercent"]

    for field in string_fields:
        if field in rate:
            _bounded_string(rate[field], f"{context}.{field}")

    for field in numeric_fields:
        if field in rate:
            value = rate[field]
            if not isinstance(value, (int, float)) or value < 0:
                raise ValueError(f"{context}.{field} must be a non-negative number.")

    for field in percent_fields:
        if field in rate:
            value = rate[field]
            if not isinstance(value, (int, float)) or not (0 <= value <= 100):
                raise ValueError(f"{context}.{field} must be between 0 and 100.")

    if "MilesCalculatedAt" in rate:
        _validate_iso_datetime(rate["MilesCalculatedAt"], f"{context}.MilesCalculatedAt")

    if "Extensions" in rate:
        extensions = rate["Extensions"]
        if not isinstance(extensions, dict):
            raise ValueError(f"{context}.Extensions must be an object.")
        for key, value in extensions.items():
            _bounded_string(str(key), f"{context}.Extensions key")
            if isinstance(value, str):
                _bounded_string(value, f"{context}.Extensions.{key}")


def _validate_rate_component_normalization(rate, context):
    has_linehaul = "LineHaulAmount" in rate
    has_fuel_amount = "FuelSurchargeAmount" in rate
    has_fuel_percent = "FuelSurchargePercent" in rate

    if (has_fuel_amount or has_fuel_percent) and not has_linehaul:
        raise ValueError(
            f"{context}.LineHaulAmount is required when FuelSurchargeAmount/FuelSurchargePercent is provided."
        )

    if not has_linehaul:
        return

    linehaul = float(rate["LineHaulAmount"])
    fuel_amount = float(rate.get("FuelSurchargeAmount", 0.0))
    fuel_percent = float(rate.get("FuelSurchargePercent", 0.0))

    if linehaul == 0 and fuel_amount > 0:
        raise ValueError(f"{context}.FuelSurchargeAmount must be zero when LineHaulAmount is zero.")

    if linehaul > 0 and has_fuel_amount and has_fuel_percent:
        expected_percent = round(fuel_amount / linehaul * 100.0, 2)
        if abs(expected_percent - fuel_percent) > 0.05:
            raise ValueError(
                f"{context}.FuelSurchargePercent must match FuelSurchargeAmount/LineHaulAmount."
            )


def _validate_rate_model_requirements(rate, context):
    model = rate["RateModel"]
    requirements = RATE_MODEL_REQUIREMENTS.get(model) or {}
    if requirements.get("status") != "active":
        return

    for field in requirements.get("requiredFields", []):
        if field not in rate:
            raise ValueError(f"{context}.{field} is required for RateModel '{model}'.")

    allowed_unit_basis = [str(item) for item in requirements.get("allowedUnitBasis", [])]
    if allowed_unit_basis:
        unit_basis = rate.get("UnitBasis")
        if unit_basis not in allowed_unit_basis:
            raise ValueError(
                f"{context}.UnitBasis must be one of {allowed_unit_basis} for RateModel '{model}'."
            )

    if model == "PerMile":
        agreed_miles = rate.get("AgreedMiles")
        if not isinstance(agreed_miles, (int, float)) or agreed_miles <= 0:
            raise ValueError(f"{context}.AgreedMiles must be a positive number for RateModel '{model}'.")
        if "DistanceMiles" in rate:
            distance = float(rate["DistanceMiles"])
            if abs(distance - float(agreed_miles)) > 0.01:
                raise ValueError(f"{context}.DistanceMiles must equal AgreedMiles for RateModel '{model}'.")
    elif model in {"PerPallet", "CWT", "PerHour"}:
        quantity = rate.get("Quantity")
        if not isinstance(quantity, (int, float)) or quantity <= 0:
            raise ValueError(f"{context}.Quantity must be a positive number for RateModel '{model}'.")


def _validate_rate_search_requirements(search_body, context):
    model = search_body["RateModel"]
    rate_stub = {"RateModel": model}
    if "UnitBasis" in search_body:
        rate_stub["UnitBasis"] = search_body["UnitBasis"]
    # Search filters should enforce model/basis semantics without requiring full bid/load rate fields.
    if model == "PerMile":
        rate_stub.setdefault("AgreedMiles", default_agreed_miles())
        rate_stub.setdefault("MilesSource", "SearchRouteBasis")
    if model in {"PerPallet", "CWT", "PerHour"}:
        rate_stub.setdefault("Quantity", 1)
    _validate_rate_model_requirements(
        rate_stub,
        context,
    )


def _validate_rate_object(rate, context):
    if not isinstance(rate, dict):
        raise ValueError(f"{context} must be an object.")
    _require_fields(rate, ["RateModel", "Amount", "Currency"], context)
    _validate_rate_model(rate["RateModel"], f"{context}.RateModel")
    if not isinstance(rate["Amount"], (int, float)) or rate["Amount"] < 0:
        raise ValueError(f"{context}.Amount must be a non-negative number.")
    if rate["Currency"] != "USD":
        raise ValueError(f"{context}.Currency must be USD for v0.1.1.")
    _validate_rate_extensions(rate, context)
    _validate_rate_component_normalization(rate, context)
    _validate_rate_model_requirements(rate, context)


def _per_mile_mileage_decision(reference_rate, candidate_rate):
    default_result = {
        "hasMismatch": False,
        "requiresCounter": False,
        "reasonCode": "Accepted",
        "deltaMiles": 0.0,
        "toleranceMiles": 0.0,
        "policy": get_mileage_dispute_policy().get("policy", "balanced"),
    }
    if (reference_rate or {}).get("RateModel") != "PerMile":
        return default_result
    if (candidate_rate or {}).get("RateModel") != "PerMile":
        result = dict(default_result)
        result.update(
            {
                "hasMismatch": True,
                "requiresCounter": True,
                "reasonCode": "MileageBasisMissing",
            }
        )
        return result

    policy = get_mileage_dispute_policy()
    policy_mode = str(policy.get("policy", "balanced"))
    abs_tolerance_miles = float(policy.get("absToleranceMiles", MILEAGE_DISPUTE_ABS_TOLERANCE_MILES))
    rel_tolerance_ratio = float(policy.get("relToleranceRatio", MILEAGE_DISPUTE_REL_TOLERANCE_RATIO))

    try:
        reference_miles = float(reference_rate.get("AgreedMiles"))
        candidate_miles = float(candidate_rate.get("AgreedMiles"))
    except (TypeError, ValueError):
        result = dict(default_result)
        result.update(
            {
                "hasMismatch": True,
                "requiresCounter": True,
                "reasonCode": "MileageBasisMissing",
                "policy": policy_mode,
            }
        )
        return result

    delta_miles = abs(reference_miles - candidate_miles)
    has_mismatch = delta_miles > 0.01
    tolerance_miles = 0.01
    requires_counter = has_mismatch
    reason_code = "Accepted"

    if has_mismatch:
        if policy_mode == "balanced":
            tolerance_miles = max(abs_tolerance_miles, reference_miles * rel_tolerance_ratio)
            requires_counter = delta_miles > tolerance_miles
            reason_code = (
                "MileageDispute" if requires_counter else "AcceptedWithinMileageTolerance"
            )
        else:
            tolerance_miles = 0.01
            requires_counter = True
            reason_code = "MileageDispute"

    return {
        "hasMismatch": has_mismatch,
        "requiresCounter": requires_counter,
        "reasonCode": reason_code,
        "deltaMiles": round(delta_miles, 2),
        "toleranceMiles": round(tolerance_miles, 2),
        "policy": policy_mode,
    }


def _per_mile_miles_mismatch(reference_rate, candidate_rate):
    return _per_mile_mileage_decision(reference_rate, candidate_rate)["hasMismatch"]


def _validate_accessorial_term(term, context):
    if not isinstance(term, dict):
        raise ValueError(f"{context} must be an object.")
    _require_fields(term, ["Type", "PricingMode"], context)
    _bounded_string(term["Type"], f"{context}.Type")
    _bounded_string(term["PricingMode"], f"{context}.PricingMode")
    if term["PricingMode"] not in VALID_ACCESSORIAL_PRICING_MODES:
        raise ValueError(
            f"{context}.PricingMode must be one of {sorted(VALID_ACCESSORIAL_PRICING_MODES)}."
        )

    for field in ["PayerParty", "PayeeParty"]:
        if field in term:
            _bounded_string(term[field], f"{context}.{field}")
            if term[field] not in VALID_ACCESSORIAL_PARTIES:
                raise ValueError(
                    f"{context}.{field} must be one of {sorted(VALID_ACCESSORIAL_PARTIES)}."
                )

    if term["PricingMode"] in {"Reimbursable", "PassThrough", "TBD"}:
        _require_fields(term, ["PayerParty", "PayeeParty"], context)

    for field in ["ApprovalRequired", "EvidenceRequired"]:
        if field in term and not isinstance(term[field], bool):
            raise ValueError(f"{context}.{field} must be boolean.")

    if "EvidenceType" in term:
        _bounded_string(term["EvidenceType"], f"{context}.EvidenceType")
        if term["EvidenceType"] not in VALID_ACCESSORIAL_EVIDENCE_TYPES:
            raise ValueError(
                f"{context}.EvidenceType must be one of {sorted(VALID_ACCESSORIAL_EVIDENCE_TYPES)}."
            )

    if term.get("EvidenceRequired") is True and "EvidenceType" not in term:
        raise ValueError(f"{context}.EvidenceType is required when EvidenceRequired is true.")

    if term["Type"] == "Detention":
        _require_fields(term, ["DetentionTerms"], context)
        _validate_detention_terms(term["DetentionTerms"], f"{context}.DetentionTerms")
    elif "DetentionTerms" in term:
        raise ValueError(f"{context}.DetentionTerms is only allowed when Type is 'Detention'.")

    if "CapAmount" in term:
        value = term["CapAmount"]
        if not isinstance(value, (int, float)) or value < 0:
            raise ValueError(f"{context}.CapAmount must be a non-negative number.")
    if "Currency" in term:
        _bounded_string(term["Currency"], f"{context}.Currency")
        if term["Currency"] != "USD":
            raise ValueError(f"{context}.Currency must be USD for v0.1.1.")
    if "SettlementReference" in term:
        _bounded_string(term["SettlementReference"], f"{context}.SettlementReference")
    if "Notes" in term:
        _bounded_string(term["Notes"], f"{context}.Notes")


def _validate_detention_terms(terms, context):
    if not isinstance(terms, dict):
        raise ValueError(f"{context} must be an object.")
    _require_fields(terms, ["GracePeriodMinutes", "RateAmount", "RateUnit"], context)

    grace_period = terms["GracePeriodMinutes"]
    if not isinstance(grace_period, int) or grace_period < 0:
        raise ValueError(f"{context}.GracePeriodMinutes must be a non-negative integer.")

    rate_amount = terms["RateAmount"]
    if not isinstance(rate_amount, (int, float)) or rate_amount <= 0:
        raise ValueError(f"{context}.RateAmount must be a positive number.")

    _bounded_string(terms["RateUnit"], f"{context}.RateUnit")
    if terms["RateUnit"] not in VALID_DETENTION_RATE_UNITS:
        raise ValueError(f"{context}.RateUnit must be one of {sorted(VALID_DETENTION_RATE_UNITS)}.")

    if "BillingIncrementMinutes" in terms:
        billing_increment = terms["BillingIncrementMinutes"]
        if not isinstance(billing_increment, int) or billing_increment <= 0:
            raise ValueError(f"{context}.BillingIncrementMinutes must be a positive integer.")

    for field in ["RequiresDelayNotice", "RequiresLocationEvidence"]:
        if field in terms and not isinstance(terms[field], bool):
            raise ValueError(f"{context}.{field} must be boolean.")

    if "LocationEvidenceType" in terms:
        _bounded_string(terms["LocationEvidenceType"], f"{context}.LocationEvidenceType")
        if terms["LocationEvidenceType"] not in VALID_DETENTION_LOCATION_EVIDENCE_TYPES:
            raise ValueError(
                f"{context}.LocationEvidenceType must be one of "
                f"{sorted(VALID_DETENTION_LOCATION_EVIDENCE_TYPES)}."
            )

    if terms.get("RequiresLocationEvidence") is True and "LocationEvidenceType" not in terms:
        raise ValueError(
            f"{context}.LocationEvidenceType is required when RequiresLocationEvidence is true."
        )

    if "Notes" in terms:
        _bounded_string(terms["Notes"], f"{context}.Notes")


def _validate_accessorial_policy(policy, context):
    if not isinstance(policy, dict):
        raise ValueError(f"{context} must be an object.")
    _require_fields(policy, ["AllowedTypes", "RequiresApproval", "Currency"], context)
    if not isinstance(policy["AllowedTypes"], list) or not policy["AllowedTypes"]:
        raise ValueError(f"{context}.AllowedTypes must be a non-empty array.")
    allowed_types = []
    for idx, item in enumerate(policy["AllowedTypes"]):
        _bounded_string(item, f"{context}.AllowedTypes[{idx}]")
        allowed_types.append(item)
    if len(allowed_types) != len(set(allowed_types)):
        raise ValueError(f"{context}.AllowedTypes must not contain duplicates.")
    unknown_types = [item for item in allowed_types if item not in ACCESSORIAL_TYPE_CATALOG]
    if unknown_types:
        raise ValueError(
            f"{context}.AllowedTypes includes unknown type(s): {unknown_types}. "
            "Update accessorial type registry/profile before use."
        )
    if not isinstance(policy["RequiresApproval"], bool):
        raise ValueError(f"{context}.RequiresApproval must be boolean.")
    _bounded_string(policy["Currency"], f"{context}.Currency")
    if policy["Currency"] != "USD":
        raise ValueError(f"{context}.Currency must be USD for v0.1.1.")

    if "MaxTotal" in policy:
        value = policy["MaxTotal"]
        if not isinstance(value, (int, float)) or value < 0:
            raise ValueError(f"{context}.MaxTotal must be a non-negative number.")

    terms = policy.get("Terms")
    if terms is None:
        return
    if not isinstance(terms, list):
        raise ValueError(f"{context}.Terms must be an array.")
    for idx, term in enumerate(terms):
        item_context = f"{context}.Terms[{idx}]"
        _validate_accessorial_term(term, item_context)
        if term["Type"] not in allowed_types:
            raise ValueError(f"{item_context}.Type must be present in {context}.AllowedTypes.")


def _validate_accessorial_policy_acceptance(acceptance, context):
    if not isinstance(acceptance, dict):
        raise ValueError(f"{context} must be an object.")
    _require_fields(acceptance, ["Accepted"], context)
    if not isinstance(acceptance["Accepted"], bool):
        raise ValueError(f"{context}.Accepted must be boolean.")

    if "AllowedTypes" in acceptance:
        if not isinstance(acceptance["AllowedTypes"], list):
            raise ValueError(f"{context}.AllowedTypes must be an array.")
        for idx, item in enumerate(acceptance["AllowedTypes"]):
            _bounded_string(item, f"{context}.AllowedTypes[{idx}]")

    if "AcceptedTerms" in acceptance:
        if not isinstance(acceptance["AcceptedTerms"], list):
            raise ValueError(f"{context}.AcceptedTerms must be an array.")
        for idx, term in enumerate(acceptance["AcceptedTerms"]):
            _validate_accessorial_term(term, f"{context}.AcceptedTerms[{idx}]")


def _validate_accessorial_entries(accessorials, context, allowed_types=None):
    if not isinstance(accessorials, list):
        raise ValueError(f"{context} must be an array.")
    allowed = set(allowed_types or [])
    for idx, item in enumerate(accessorials):
        item_context = f"{context}[{idx}]"
        if not isinstance(item, dict):
            raise ValueError(f"{item_context} must be an object.")
        _require_fields(item, ["Type"], item_context)
        _bounded_string(item["Type"], f"{item_context}.Type")
        if allowed and item["Type"] not in allowed:
            raise ValueError(f"{item_context}.Type must be present in AccessorialPolicy.AllowedTypes.")
        if "Amount" in item:
            value = item["Amount"]
            if not isinstance(value, (int, float)) or value < 0:
                raise ValueError(f"{item_context}.Amount must be a non-negative number.")
        if "Currency" in item:
            _bounded_string(item["Currency"], f"{item_context}.Currency")
            if item["Currency"] != "USD":
                raise ValueError(f"{item_context}.Currency must be USD for v0.1.1.")
        if "Status" in item:
            _bounded_string(item["Status"], f"{item_context}.Status")
            if item["Status"] not in VALID_ACCESSORIAL_STATUSES:
                raise ValueError(
                    f"{item_context}.Status must be one of {sorted(VALID_ACCESSORIAL_STATUSES)}."
                )
        status = item.get("Status")
        if status == "Proposed":
            _require_fields(item, ["ClaimID"], item_context)
            _bounded_string(item["ClaimID"], f"{item_context}.ClaimID")
            if "ProposedAt" in item:
                _validate_iso_datetime(item["ProposedAt"], f"{item_context}.ProposedAt")
            if "ApprovedAt" in item:
                raise ValueError(f"{item_context}.ApprovedAt is not allowed for Status 'Proposed'.")
            if "RejectedAt" in item:
                raise ValueError(f"{item_context}.RejectedAt is not allowed for Status 'Proposed'.")
        elif status == "Approved":
            _require_fields(item, ["ApprovedAt"], item_context)
        elif status == "Rejected":
            _require_fields(item, ["RejectedAt"], item_context)
        if "ApprovedAt" in item:
            _validate_iso_datetime(item["ApprovedAt"], f"{item_context}.ApprovedAt")
        if "RejectedAt" in item:
            _validate_iso_datetime(item["RejectedAt"], f"{item_context}.RejectedAt")
        if "EvidenceRef" in item:
            _bounded_string(item["EvidenceRef"], f"{item_context}.EvidenceRef")
        if "EvidenceRefs" in item:
            _validate_string_array(item["EvidenceRefs"], f"{item_context}.EvidenceRefs")
        if "SettlementReference" in item:
            _bounded_string(item["SettlementReference"], f"{item_context}.SettlementReference")
        if "Note" in item:
            _bounded_string(item["Note"], f"{item_context}.Note")


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

    _enforce_trusted_verifier_registry_result(result, context)


def _enforce_trusted_verifier_registry_result(result, context):
    if not (NON_LOCAL_MODE and ENFORCE_TRUSTED_VERIFIER_REGISTRY):
        return
    if not isinstance(result, dict):
        raise ValueError(f"{context} must be an object.")
    provider_id = str(result.get("provider") or "").strip()
    if not provider_id:
        raise ValueError(f"{context}.provider is required in non-local mode.")
    if provider_id not in TRUSTED_VERIFIER_REGISTRY:
        raise ValueError(
            f"{context}.provider is not in trusted verifier registry: {provider_id}."
        )
    registry_entry = TRUSTED_VERIFIER_REGISTRY[provider_id]
    status = str(registry_entry.get("status") or "").strip().lower()
    if status not in {"active", "approved"}:
        raise ValueError(
            f"{context}.provider is not active in trusted verifier registry."
        )

    source = str(result.get("source") or "").strip().lower()
    source_normalized = _normalize_verifier_source(source)
    allowed_sources = registry_entry.get("allowedSources") or []
    allowed_sources_normalized = {
        _normalize_verifier_source(item) for item in allowed_sources if str(item or "").strip()
    }
    if (
        allowed_sources
        and source not in allowed_sources
        and source_normalized not in allowed_sources_normalized
    ):
        raise ValueError(
            f"{context}.source '{source}' is not allowed for trusted provider '{provider_id}'."
        )

    assurance_level = str(result.get("assuranceLevel") or "").strip().upper()
    allowed_assurance_levels = registry_entry.get("allowedAssuranceLevels") or []
    if allowed_assurance_levels and assurance_level not in allowed_assurance_levels:
        raise ValueError(
            f"{context}.assuranceLevel '{assurance_level}' is not allowed for trusted provider '{provider_id}'."
        )

    allowed_attestation_kids = registry_entry.get("allowedAttestationKids") or []
    if allowed_attestation_kids:
        attestation = result.get("attestation")
        if not isinstance(attestation, dict):
            raise ValueError(
                f"{context}.attestation is required for trusted verifier registry enforcement."
            )
        attestation_kid = str(attestation.get("kid") or "").strip()
        if attestation_kid not in allowed_attestation_kids:
            raise ValueError(
                f"{context}.attestation.kid '{attestation_kid}' is not approved for trusted provider '{provider_id}'."
            )


def _validate_string_array(values, context):
    if not isinstance(values, list):
        raise ValueError(f"{context} must be an array.")
    if not values:
        raise ValueError(f"{context} must include at least one value.")
    if len(values) > 20:
        raise ValueError(f"{context} exceeds max list length (20).")
    for idx, item in enumerate(values):
        _bounded_string(item, f"{context}[{idx}]")


def _normalize_verifier_source(source_value):
    source = str(source_value or "").strip().lower()
    if source in {"hosted-adapter", "implementer-adapter", "builder-hosted-adapter"}:
        return "implementer-adapter"
    if source in {"vendor-direct", "vendor-attestation"}:
        return "vendor-direct"
    if source in {"authority-mock", "mock-compliance", "authority-only", "live-fmcsa", "fmcsa-api"}:
        return "authority-only"
    if source in {"self-attested", "self-attest"}:
        return "self-attested"
    if source in {"cache", "cached-fmcsa", "fmcsa-cache"}:
        return "cached-authority"
    if source in {"mock-biometric", "simulated", "simulation"}:
        return "simulated"
    return source


def _normalize_fmcsa_source(fmcsa_source):
    source = str(fmcsa_source or "").strip().lower()
    if source in {"hosted-adapter", "implementer-adapter", "vendor-direct"}:
        return source
    if source == "authority-mock":
        return source
    return source


def _derive_verification_mode(verification_result):
    source = str((verification_result or {}).get("source") or "").strip().lower()
    source_normalized = _normalize_verifier_source(source)
    if source_normalized in {"implementer-adapter", "vendor-direct", "authority-only"}:
        return "Live"
    if source_normalized in {"cached-authority"}:
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
        _validate_schedule_terms_fields(body, "NewLoad")
        _bounded_string(body["LoadType"], "NewLoad.LoadType")
        _bounded_string(body["EquipmentType"], "NewLoad.EquipmentType")
        _validate_equipment_contract(body, "NewLoad")
        _validate_driver_configuration_terms(body, "NewLoad")
        _bounded_string(body["Commodity"], "NewLoad.Commodity")
        if not isinstance(body["TrailerLength"], (int, float)) or body["TrailerLength"] <= 0:
            raise ValueError("NewLoad.TrailerLength must be a positive number.")
        if not isinstance(body["Weight"], (int, float)) or body["Weight"] <= 0:
            raise ValueError("NewLoad.Weight must be a positive number.")
        if not isinstance(body["RequireTracking"], bool):
            raise ValueError("NewLoad.RequireTracking must be boolean.")
        if "AccessorialPolicy" in body:
            _validate_accessorial_policy(body["AccessorialPolicy"], "NewLoad.AccessorialPolicy")
        if "Stops" in body:
            _validate_stop_plan(
                body["Stops"],
                "NewLoad.Stops",
                origin=body.get("Origin"),
                destination=body.get("Destination"),
            )
        if "SpecialInstructions" in body:
            _validate_special_instructions(body["SpecialInstructions"], "NewLoad.SpecialInstructions")
        if "LoadReferenceNumbers" in body:
            _validate_load_reference_numbers(body["LoadReferenceNumbers"], "NewLoad.LoadReferenceNumbers")
        if "Accessorials" in body:
            allowed_types = []
            policy = body.get("AccessorialPolicy")
            if isinstance(policy, dict):
                allowed_types = policy.get("AllowedTypes") or []
            _validate_accessorial_entries(body["Accessorials"], "NewLoad.Accessorials", allowed_types)
        return

    if message_type == "LoadSearch":
        _require_fields(
            body,
            ["OriginState", "DestinationState", "EquipmentType", "PickupDate", "RateModel", "MaxRate"],
            "LoadSearch",
        )
        _validate_rate_model(body["RateModel"], "LoadSearch.RateModel")
        _validate_state_code(body["OriginState"], "LoadSearch.OriginState")
        _validate_state_code(body["DestinationState"], "LoadSearch.DestinationState")
        _bounded_string(body["EquipmentType"], "LoadSearch.EquipmentType")
        _validate_equipment_search_filters(body, "LoadSearch")
        _validate_driver_configuration_filters(body, "LoadSearch")
        _validate_iso_date(body["PickupDate"], "LoadSearch.PickupDate")
        if not isinstance(body["MaxRate"], (int, float)) or body["MaxRate"] < 0:
            raise ValueError("LoadSearch.MaxRate must be a non-negative number.")
        _validate_stop_search_filters(body, "LoadSearch")
        _validate_rate_search_requirements(body, "LoadSearch")
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
        _validate_equipment_contract(body, "NewTruck")
        _validate_driver_configuration_terms(body, "NewTruck")
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
        _validate_rate_model(body["RateModel"], "TruckSearch.RateModel")
        _validate_state_code(body["OriginState"], "TruckSearch.OriginState")
        _bounded_string(body["EquipmentType"], "TruckSearch.EquipmentType")
        _validate_equipment_search_filters(body, "TruckSearch")
        _validate_driver_configuration_filters(body, "TruckSearch")
        _validate_iso_date(body["AvailableFrom"], "TruckSearch.AvailableFrom")
        _validate_iso_date(body["AvailableTo"], "TruckSearch.AvailableTo")
        for field in ["LocationRadiusMiles", "MinRate", "MaxRate"]:
            if not isinstance(body[field], (int, float)) or body[field] < 0:
                raise ValueError(f"TruckSearch.{field} must be a non-negative number.")
        _validate_rate_search_requirements(body, "TruckSearch")
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
        if "EquipmentAcceptance" in body:
            _validate_equipment_acceptance(body["EquipmentAcceptance"], "BidRequest.EquipmentAcceptance")
        if "StopPlanAcceptance" in body:
            _validate_stop_plan_acceptance(body["StopPlanAcceptance"], "BidRequest.StopPlanAcceptance")
        if "SpecialInstructionsAcceptance" in body:
            _validate_special_instructions_acceptance(
                body["SpecialInstructionsAcceptance"],
                "BidRequest.SpecialInstructionsAcceptance",
            )
        if "ScheduleAcceptance" in body:
            _validate_schedule_acceptance(body["ScheduleAcceptance"], "BidRequest.ScheduleAcceptance")
        if "DriverConfigurationAcceptance" in body:
            _validate_driver_configuration_acceptance(
                body["DriverConfigurationAcceptance"],
                "BidRequest.DriverConfigurationAcceptance",
            )
        if "AccessorialPolicyAcceptance" in body:
            _validate_accessorial_policy_acceptance(
                body["AccessorialPolicyAcceptance"],
                "BidRequest.AccessorialPolicyAcceptance",
            )
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
        if "ReasonCode" in body:
            _bounded_string(body["ReasonCode"], "BidResponse.ReasonCode")
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
        if "AccessorialPolicy" in body:
            _validate_accessorial_policy(body["AccessorialPolicy"], "ExecutionReport.AccessorialPolicy")
        if "Accessorials" in body:
            allowed_types = []
            policy = body.get("AccessorialPolicy")
            if isinstance(policy, dict):
                allowed_types = policy.get("AllowedTypes") or []
            _validate_accessorial_entries(
                body["Accessorials"],
                "ExecutionReport.Accessorials",
                allowed_types,
            )
        if "SpecialInstructions" in body:
            _validate_special_instructions(body["SpecialInstructions"], "ExecutionReport.SpecialInstructions")
        if "ScheduleTerms" in body:
            _validate_schedule_terms_fields(body["ScheduleTerms"], "ExecutionReport.ScheduleTerms")
        if "DriverTerms" in body:
            if not isinstance(body["DriverTerms"], dict):
                raise ValueError("ExecutionReport.DriverTerms must be an object.")
            _require_fields(body["DriverTerms"], ["DriverConfiguration"], "ExecutionReport.DriverTerms")
            _validate_driver_configuration_terms(body["DriverTerms"], "ExecutionReport.DriverTerms")
        if "LoadReferenceNumbers" in body:
            _validate_load_reference_numbers(
                body["LoadReferenceNumbers"],
                "ExecutionReport.LoadReferenceNumbers",
            )
        if "EquipmentTerms" in body:
            equipment_terms = dict(body["EquipmentTerms"])
            if "EquipmentType" not in equipment_terms:
                equipment_terms["EquipmentType"] = "Special"
            _validate_equipment_contract(equipment_terms, "ExecutionReport.EquipmentTerms")
        if "OperationalHandoff" in body:
            _validate_operational_handoff(body["OperationalHandoff"], "ExecutionReport.OperationalHandoff")
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
    version_decision = negotiate_protocol_version(envelope.get("ProtocolVersion"))
    if version_decision["status"] == "Incompatible":
        raise ValueError(
            "Envelope.ProtocolVersion rejected. "
            f"ReasonCode={version_decision['reasonCode']}. "
            f"Incoming={version_decision['incomingVersion']!r}. "
            f"Runtime={version_decision['runtimeVersion']!r}."
        )
    _bounded_string(envelope["From"], "Envelope.From")
    _bounded_string(envelope["To"], "Envelope.To")
    if "FromAgentID" in envelope:
        _validate_agent_id(envelope["FromAgentID"], "Envelope.FromAgentID")
    if "ToAgentID" in envelope:
        _validate_agent_id(envelope["ToAgentID"], "Envelope.ToAgentID")
    _validate_agent_identity_binding(envelope)
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
        "FromAgentID": resolve_agent_id(sender),
        "ToAgentID": resolve_agent_id(receiver),
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


def _validate_fmcsa_normalized_payload(payload, requested_mc):
    if not isinstance(payload, dict):
        raise ValueError("FMCSA payload must be a JSON object.")

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
        raise ValueError(f"FMCSA payload returned unexpected fields: {sorted(extras)}")

    missing = [field for field in required if field not in payload]
    if missing:
        raise ValueError(f"FMCSA payload missing fields: {missing}")

    if not isinstance(payload["found"], bool):
        raise ValueError("FMCSA payload 'found' must be boolean.")
    if payload["status"] not in {"Success", "Fail"}:
        raise ValueError("FMCSA payload 'status' must be Success or Fail.")
    if not isinstance(payload["score"], (int, float)) or not (0 <= payload["score"] <= 100):
        raise ValueError("FMCSA payload 'score' must be between 0 and 100.")
    if not isinstance(payload["has_current_insurance"], bool):
        raise ValueError("FMCSA payload 'has_current_insurance' must be boolean.")
    if not isinstance(payload["interstate_authority_ok"], bool):
        raise ValueError("FMCSA payload 'interstate_authority_ok' must be boolean.")

    target_mc = _normalize_mc(requested_mc)
    returned_mc = _normalize_mc(payload.get("mc_number"))
    if target_mc and returned_mc != target_mc:
        raise ValueError("FMCSA payload returned an MC number that does not match the request.")

    if payload["status"] == "Success" and not payload["found"]:
        raise ValueError("FMCSA payload returned Success with found=false.")


def _normalize_hosted_adapter_payload(payload, requested_mc):
    """
    Accept both legacy compact style and neutral translator style payloads.

    Returns a normalized compatibility dict with fields consumed by run_verification().
    """
    if not isinstance(payload, dict):
        raise ValueError("hosted adapter payload must be a JSON object.")

    if "VerificationResult" not in payload:
        legacy_payload = dict(payload)
        legacy_payload.pop("ok", None)
        legacy_payload.pop("error", None)
        _validate_fmcsa_normalized_payload(legacy_payload, requested_mc=requested_mc)
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
    fmcsa_source="authority-mock",
):
    """
    Verification providers:
    - FMCSA / MockComplianceProvider: compliance check -> Basic badge (on success)
    - MockBiometricProvider / iDenfy alias: biometric check -> Premium badge (on success)
    """
    requested_provider = str(provider or "").strip()
    normalized_provider = normalize_verification_provider(requested_provider)
    normalized_fmcsa_source = _normalize_fmcsa_source(fmcsa_source)

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
            "provenance": _normalize_verifier_source(source_value),
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

    if NON_LOCAL_MODE and normalized_provider == "FMCSA" and normalized_fmcsa_source not in {
        "hosted-adapter",
        "implementer-adapter",
        "vendor-direct",
    }:
        verification_result = build_result(
            status_value="Fail",
            provider_value=NEUTRAL_VERIFICATION_PROVIDER_IDS["compliance_mock"],
            category="Compliance",
            method="AuthorityRecordCheck",
            assurance_level="AAL1",
            score_value=0,
            token_value=f"fmcsa-{uuid4().hex[:14]}",
            source_value="policy-enforcement",
            source_authority="FMCSA",
            extra={
                "mcNumber": _normalize_mc(mc_number),
                "error": (
                    "Non-local mode requires implementer-adapter or vendor-direct compliance "
                    "verification source."
                ),
            },
        )
        return verification_result, "None"

    if NON_LOCAL_MODE and normalized_provider == "MockBiometricProvider":
        verification_result = build_result(
            status_value="Fail",
            provider_value=NEUTRAL_VERIFICATION_PROVIDER_IDS["biometric_mock"],
            category="Biometric",
            method="LivenessPlusDocument",
            assurance_level="AAL2",
            score_value=0,
            token_value=f"biometric-{uuid4().hex[:14]}",
            source_value="policy-enforcement",
            extra={"error": "Non-local mode requires trusted external identity verifier attestations."},
        )
        return verification_result, "None"

    if normalized_provider == "FMCSA":
        fm_token = f"fmcsa-{uuid4().hex[:14]}"
        if normalized_fmcsa_source in {"hosted-adapter", "implementer-adapter", "vendor-direct"}:
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
                    source_value=normalized_fmcsa_source,
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
                source_value=normalized_fmcsa_source,
                source_authority="FMCSA",
                extra={
                    "mcNumber": _normalize_mc(mc_number),
                    "error": live.get("error", "Unknown hosted FMCSA adapter error."),
                },
            )
            return verification_result, "None"

        if normalized_fmcsa_source not in {
            "authority-mock",
            "hosted-adapter",
            "implementer-adapter",
            "vendor-direct",
        }:
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
        delivery_earliest = pickup_latest + timedelta(days=1)
        delivery_latest = delivery_earliest + timedelta(days=1)
        floor_amount = default_floor_amount(rate_model)

        new_load = {
            "LoadID": load_id,
            "Origin": {"city": "Dallas", "state": "TX", "zip": "75201"},
            "Destination": {"city": "Atlanta", "state": "GA", "zip": "30301"},
            "PickupEarliest": pickup_earliest.isoformat(),
            "PickupLatest": pickup_latest.isoformat(),
            "DeliveryEarliest": delivery_earliest.isoformat(),
            "DeliveryLatest": delivery_latest.isoformat(),
            "PickupTimeWindow": {
                "Start": f"{pickup_earliest.isoformat()}T08:00:00-05:00",
                "End": f"{pickup_earliest.isoformat()}T12:00:00-05:00",
                "TimeZone": "America/Chicago",
            },
            "DeliveryTimeWindow": {
                "Start": f"{delivery_earliest.isoformat()}T09:00:00-05:00",
                "End": f"{delivery_earliest.isoformat()}T15:00:00-05:00",
                "TimeZone": "America/New_York",
            },
            "LoadType": "Full",
            "EquipmentType": "Reefer",
            "EquipmentClass": "Reefer",
            "EquipmentSubClass": "AirRide",
            "EquipmentTags": ["AirRide"],
            "DriverConfiguration": "Single",
            "TrailerLength": 53,
            "Weight": 42000,
            "Commodity": "Frozen Poultry",
            "Rate": build_rate(rate_model, floor_amount),
            "SpecialInstructions": [
                "Reefer must be pre-cooled to 34F before pickup.",
                "Driver must notify broker at each stop arrival/departure.",
            ],
            "LoadReferenceNumbers": {
                "PrimaryReferenceNumber": "BRK-2026-000421",
                "SecondaryReferenceNumber": "SHIP-2026-18411",
                "Additional": [
                    {
                        "ReferenceType": "PartnerReference",
                        "ReferenceValue": "REF-772991",
                        "IssuerParty": "Shipper",
                    }
                ],
            },
            "Stops": [
                {
                    "StopSequence": 1,
                    "StopType": "Pickup",
                    "Location": {"city": "Dallas", "state": "TX", "zip": "75201"},
                    "WindowOpen": pickup_earliest.isoformat(),
                    "WindowClose": pickup_latest.isoformat(),
                },
                {
                    "StopSequence": 2,
                    "StopType": "Pickup",
                    "Location": {"city": "Little Rock", "state": "AR", "zip": "72201"},
                    "WindowOpen": pickup_earliest.isoformat(),
                    "WindowClose": pickup_latest.isoformat(),
                    "Notes": "Secondary pallet pickup.",
                },
                {
                    "StopSequence": 3,
                    "StopType": "Drop",
                    "Location": {"city": "Atlanta", "state": "GA", "zip": "30301"},
                    "WindowOpen": (pickup_latest + timedelta(days=1)).isoformat(),
                    "WindowClose": (pickup_latest + timedelta(days=2)).isoformat(),
                },
            ],
            "AccessorialPolicy": {
                "AllowedTypes": list(ACTIVE_ACCESSORIAL_TYPES),
                "RequiresApproval": True,
                "MaxTotal": 300.0,
                "Currency": "USD",
                "Terms": [
                    {
                        "Type": "UnloadingFee",
                        "PricingMode": "Reimbursable",
                        "PayerParty": "Broker",
                        "PayeeParty": "Carrier",
                        "ApprovalRequired": True,
                        "EvidenceRequired": True,
                        "EvidenceType": "Receipt",
                        "CapAmount": 300.0,
                        "Currency": "USD",
                    },
                    {
                        "Type": "OverweightPermit",
                        "PricingMode": "PassThrough",
                        "PayerParty": "Broker",
                        "PayeeParty": "Carrier",
                        "ApprovalRequired": True,
                        "EvidenceRequired": True,
                        "EvidenceType": "Permit",
                        "Currency": "USD",
                    },
                    {
                        "Type": "EscortVehicle",
                        "PricingMode": "TBD",
                        "PayerParty": "Broker",
                        "PayeeParty": "Vendor",
                        "ApprovalRequired": True,
                        "EvidenceRequired": True,
                        "EvidenceType": "EscortInvoice",
                        "Currency": "USD",
                    },
                    {
                        "Type": "Detention",
                        "PricingMode": "Reimbursable",
                        "PayerParty": "Broker",
                        "PayeeParty": "Carrier",
                        "ApprovalRequired": True,
                        "EvidenceRequired": False,
                        "Currency": "USD",
                        "DetentionTerms": {
                            "GracePeriodMinutes": 120,
                            "RateAmount": 25.0,
                            "RateUnit": "Hour",
                            "BillingIncrementMinutes": 60,
                            "RequiresDelayNotice": True,
                            "RequiresLocationEvidence": True,
                            "LocationEvidenceType": "GPS",
                            "Notes": "Delay notice and location evidence are commercial preconditions only.",
                        },
                    },
                ],
            },
            # Charges are intentionally empty at booking time; they can be approved later.
            "Accessorials": [],
            "RequireTracking": True,
        }
        self.loads[load_id] = new_load
        return new_load

    def ingest_shipper_tender(self, tender):
        if not isinstance(tender, dict):
            raise ValueError("Shipper tender must be an object.")
        normalized = json.loads(json.dumps(tender))
        validate_message_body("NewLoad", normalized)
        load_id = normalized.get("LoadID")
        if load_id in self.loads:
            raise ValueError(f"LoadID already exists in broker load book: {load_id}")
        normalized.setdefault("TenderSource", "Shipper")
        normalized.setdefault("InitiatorRole", "Shipper")
        self.loads[load_id] = normalized
        return normalized

    def search_loads(self, filters):
        matches = []
        for load in self.loads.values():
            stop_summary = _derive_stop_plan_summary(load)
            pickup_date = filters.get("PickupDate")
            in_pickup_window = (
                load["PickupEarliest"] <= pickup_date <= load["PickupLatest"]
                if pickup_date
                else True
            )
            stop_count_min = int(filters.get("StopCountMin", 2))
            stop_count_max = int(filters.get("StopCountMax", 9999))
            required_stop_types = set(filters.get("RequiredStopTypes") or [])
            stop_count_ok = stop_count_min <= stop_summary["stopCount"] <= stop_count_max
            stop_type_ok = not required_stop_types or required_stop_types.issubset(
                set(stop_summary["stopTypes"])
            )
            multi_stop_ok = (
                not filters.get("RequireMultiStop", False)
                or stop_summary["isMultiStop"]
            )
            if (
                load["Origin"]["state"] == filters.get("OriginState")
                and load["Destination"]["state"] == filters.get("DestinationState")
                and load["EquipmentType"] == filters.get("EquipmentType")
                and _equipment_matches_search_terms(load, filters)
                and _driver_configuration_matches(load, filters)
                and load["Rate"]["RateModel"] == filters.get("RateModel")
                and in_pickup_window
                and load["Rate"]["Amount"] <= filters.get("MaxRate", 9999)
                and (not filters.get("RequireTracking") or load["RequireTracking"] is True)
                and stop_count_ok
                and stop_type_ok
                and multi_stop_ok
            ):
                matches.append(load)
        return matches

    def respond_to_bid(self, bid_request, forced_response):
        load_id = bid_request["LoadID"]
        load = self.loads[load_id]
        load_rate = load["Rate"]
        bid_rate = bid_request["Rate"]
        load_equipment_terms = _extract_equipment_terms(load)
        equipment_acceptance = bid_request.get("EquipmentAcceptance") or {}
        driver_acceptance = bid_request.get("DriverConfigurationAcceptance") or {}
        stop_summary = _derive_stop_plan_summary(load)
        stop_plan_acceptance = bid_request.get("StopPlanAcceptance") or {}
        special_instructions = list(load.get("SpecialInstructions") or [])
        special_acceptance = bid_request.get("SpecialInstructionsAcceptance") or {}
        schedule_acceptance = bid_request.get("ScheduleAcceptance") or {}
        stop_plan_mismatch = False
        if stop_plan_acceptance:
            accepted = bool(stop_plan_acceptance.get("Accepted"))
            accepted_stop_count = stop_plan_acceptance.get("StopCount")
            accepted_stop_types = set(stop_plan_acceptance.get("StopTypes") or [])
            if not accepted:
                stop_plan_mismatch = True
            if accepted_stop_count is not None and int(accepted_stop_count) != stop_summary["stopCount"]:
                stop_plan_mismatch = True
            if accepted_stop_types and accepted_stop_types != set(stop_summary["stopTypes"]):
                stop_plan_mismatch = True
        special_instructions_mismatch = False
        if special_instructions:
            if not special_acceptance:
                special_instructions_mismatch = True
            elif special_acceptance.get("Accepted") is not True:
                special_instructions_mismatch = True
            elif special_acceptance.get("Exceptions"):
                special_instructions_mismatch = True
        schedule_terms_present = any(
            key in load
            for key in ["DeliveryEarliest", "DeliveryLatest", "PickupTimeWindow", "DeliveryTimeWindow"]
        )
        schedule_mismatch = False
        if schedule_terms_present:
            if not schedule_acceptance or schedule_acceptance.get("Accepted") is not True:
                schedule_mismatch = True
            elif schedule_acceptance.get("Exceptions"):
                schedule_mismatch = True
            else:
                for window_field in ["PickupTimeWindow", "DeliveryTimeWindow"]:
                    expected_window = load.get(window_field)
                    accepted_window = schedule_acceptance.get(window_field)
                    if expected_window and accepted_window and accepted_window != expected_window:
                        schedule_mismatch = True

        if bid_rate["RateModel"] != load_rate["RateModel"]:
            return {
                "LoadID": load_id,
                "ResponseType": "Reject",
                "VerifiedBadge": "None",
                "ReasonCode": "RateModelMismatch",
            }

        rate_floor = load_rate["Amount"]
        rate_model = load_rate["RateModel"]
        mileage_decision = _per_mile_mileage_decision(load_rate, bid_rate)

        if forced_response == "Counter":
            counter_metadata = {}
            if rate_model == "PerMile":
                for field in ["AgreedMiles", "MilesSource", "MilesSourceVersion", "MilesCalculatedAt"]:
                    if field in load_rate:
                        counter_metadata[field] = load_rate[field]
            return {
                "LoadID": load_id,
                "ResponseType": "Counter",
                "ProposedRate": build_rate(
                    rate_model,
                    counter_amount(rate_model, rate_floor),
                    **counter_metadata,
                ),
                "ReasonCode": (
                    "MileageDispute" if mileage_decision["requiresCounter"] else "MarketCounter"
                ),
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

        if _equipment_acceptance_mismatch(load_equipment_terms, equipment_acceptance):
            counter_metadata = {}
            if rate_model == "PerMile":
                for field in ["AgreedMiles", "MilesSource", "MilesSourceVersion", "MilesCalculatedAt"]:
                    if field in load_rate:
                        counter_metadata[field] = load_rate[field]
            return {
                "LoadID": load_id,
                "ResponseType": "Counter",
                "ProposedRate": build_rate(
                    rate_model,
                    counter_amount(rate_model, rate_floor),
                    **counter_metadata,
                ),
                "ReasonCode": "EquipmentCompatibilityDispute",
                "VerifiedBadge": "None",
            }

        if _driver_configuration_acceptance_mismatch(load.get("DriverConfiguration"), driver_acceptance):
            counter_metadata = {}
            if rate_model == "PerMile":
                for field in ["AgreedMiles", "MilesSource", "MilesSourceVersion", "MilesCalculatedAt"]:
                    if field in load_rate:
                        counter_metadata[field] = load_rate[field]
            return {
                "LoadID": load_id,
                "ResponseType": "Counter",
                "ProposedRate": build_rate(
                    rate_model,
                    counter_amount(rate_model, rate_floor),
                    **counter_metadata,
                ),
                "ReasonCode": "DriverConfigurationDispute",
                "VerifiedBadge": "None",
            }

        if stop_plan_mismatch:
            counter_metadata = {}
            if rate_model == "PerMile":
                for field in ["AgreedMiles", "MilesSource", "MilesSourceVersion", "MilesCalculatedAt"]:
                    if field in load_rate:
                        counter_metadata[field] = load_rate[field]
            return {
                "LoadID": load_id,
                "ResponseType": "Counter",
                "ProposedRate": build_rate(
                    rate_model,
                    counter_amount(rate_model, rate_floor),
                    **counter_metadata,
                ),
                "ReasonCode": "StopPlanDispute",
                "VerifiedBadge": "None",
            }

        if special_instructions_mismatch:
            counter_metadata = {}
            if rate_model == "PerMile":
                for field in ["AgreedMiles", "MilesSource", "MilesSourceVersion", "MilesCalculatedAt"]:
                    if field in load_rate:
                        counter_metadata[field] = load_rate[field]
            return {
                "LoadID": load_id,
                "ResponseType": "Counter",
                "ProposedRate": build_rate(
                    rate_model,
                    counter_amount(rate_model, rate_floor),
                    **counter_metadata,
                ),
                "ReasonCode": "SpecialInstructionsDispute",
                "VerifiedBadge": "None",
            }

        if schedule_mismatch:
            counter_metadata = {}
            if rate_model == "PerMile":
                for field in ["AgreedMiles", "MilesSource", "MilesSourceVersion", "MilesCalculatedAt"]:
                    if field in load_rate:
                        counter_metadata[field] = load_rate[field]
            return {
                "LoadID": load_id,
                "ResponseType": "Counter",
                "ProposedRate": build_rate(
                    rate_model,
                    counter_amount(rate_model, rate_floor),
                    **counter_metadata,
                ),
                "ReasonCode": "ScheduleWindowDispute",
                "VerifiedBadge": "None",
            }

        if mileage_decision["requiresCounter"]:
            counter_metadata = {}
            for field in ["AgreedMiles", "MilesSource", "MilesSourceVersion", "MilesCalculatedAt"]:
                if field in load_rate:
                    counter_metadata[field] = load_rate[field]
            return {
                "LoadID": load_id,
                "ResponseType": "Counter",
                "ProposedRate": build_rate(
                    rate_model,
                    counter_amount(rate_model, rate_floor),
                    **counter_metadata,
                ),
                "ReasonCode": mileage_decision["reasonCode"],
                "VerifiedBadge": "None",
            }

        return {
            "LoadID": load_id,
            "ResponseType": "Accept",
            "ReasonCode": mileage_decision["reasonCode"],
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
        load_equipment_terms = _extract_equipment_terms(load)
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
            "SpecialInstructions": list(load.get("SpecialInstructions") or []),
            "ScheduleTerms": {
                key: value
                for key, value in {
                    "PickupEarliest": load.get("PickupEarliest"),
                    "PickupLatest": load.get("PickupLatest"),
                    "DeliveryEarliest": load.get("DeliveryEarliest"),
                    "DeliveryLatest": load.get("DeliveryLatest"),
                    "PickupTimeWindow": load.get("PickupTimeWindow"),
                    "DeliveryTimeWindow": load.get("DeliveryTimeWindow"),
                }.items()
                if value is not None
            },
            "EquipmentTerms": {
                "EquipmentType": load["EquipmentType"],
                "EquipmentClass": load_equipment_terms["EquipmentClass"],
                "EquipmentSubClass": load_equipment_terms["EquipmentSubClass"],
                "EquipmentTags": list(load_equipment_terms["EquipmentTags"]),
                "TrailerLength": load.get("TrailerLength"),
                "TrailerCount": load.get("TrailerCount", 1),
            },
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
            "OperationalHandoff": _default_operational_handoff(self.name, load_id, load),
        }
        if load.get("DriverConfiguration"):
            report["DriverTerms"] = {"DriverConfiguration": load.get("DriverConfiguration")}
        if isinstance(load.get("LoadReferenceNumbers"), dict):
            report["LoadReferenceNumbers"] = dict(load["LoadReferenceNumbers"])
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
            "EquipmentClass": "Reefer",
            "EquipmentSubClass": "AirRide",
            "RequiredEquipmentTags": ["AirRide"],
            "RequiredDriverConfiguration": "Team",
            "TrailerLengthMin": 53,
            "TrailerLengthMax": 53,
            "AvailableFrom": target_date,
            "AvailableTo": (date.today() + timedelta(days=3)).isoformat(),
            "RateModel": rate_model,
            "UnitBasis": default_unit_basis(rate_model),
            "MinRate": default_floor_amount(rate_model),
            "MaxRate": default_search_max(rate_model),
        }

    def create_truck_bid_request(self, truck, bid_amount=None):
        rate_model = truck["RateMin"]["RateModel"]
        amount = default_bid_amount(rate_model) if bid_amount is None else bid_amount
        metadata = {}
        if rate_model == "PerMile":
            for field in ["AgreedMiles", "MilesSource", "MilesSourceVersion", "MilesCalculatedAt"]:
                if field in truck["RateMin"]:
                    metadata[field] = truck["RateMin"][field]
        if rate_model in {"PerPallet", "CWT", "PerHour"} and "Quantity" in truck["RateMin"]:
            metadata["Quantity"] = truck["RateMin"]["Quantity"]
        truck_equipment_terms = _extract_equipment_terms(truck)
        return {
            "TruckID": truck["TruckID"],
            "Rate": build_rate(rate_model, amount, **metadata),
            "AvailabilityDate": truck["AvailabilityDate"],
            "EquipmentAcceptance": {
                "Accepted": True,
                "EquipmentClass": truck_equipment_terms["EquipmentClass"],
                "EquipmentSubClass": truck_equipment_terms["EquipmentSubClass"],
                "EquipmentTags": list(truck_equipment_terms["EquipmentTags"]),
                "TrailerLength": truck.get("TrailerLength"),
                "TrailerLengthMin": truck.get("TrailerLength"),
                "TrailerLengthMax": truck.get("TrailerLength"),
                "TrailerCount": truck.get("TrailerCount", 1),
            },
            "DriverConfigurationAcceptance": {
                "Accepted": True,
                "DriverConfiguration": truck.get("DriverConfiguration"),
            },
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
        truck = self.trucks.get(truck_id, {})
        truck_equipment_terms = _extract_equipment_terms(truck) if truck else {}
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
            "EquipmentTerms": {
                key: value
                for key, value in {
                    "EquipmentType": truck.get("EquipmentType"),
                    "EquipmentClass": truck_equipment_terms.get("EquipmentClass"),
                    "EquipmentSubClass": truck_equipment_terms.get("EquipmentSubClass"),
                    "EquipmentTags": list(truck_equipment_terms.get("EquipmentTags") or []),
                    "TrailerLength": truck.get("TrailerLength"),
                    "TrailerCount": truck.get("TrailerCount"),
                }.items()
                if value not in (None, "", [])
            },
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
        if truck.get("DriverConfiguration"):
            report["DriverTerms"] = {"DriverConfiguration": truck.get("DriverConfiguration")}
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
            "EquipmentClass": "Reefer",
            "EquipmentSubClass": "AirRide",
            "RequiredEquipmentTags": ["AirRide"],
            "RequiredDriverConfiguration": "Single",
            "TrailerLengthMin": 53,
            "TrailerLengthMax": 53,
            "PickupDate": target_pickup,
            "RateModel": rate_model,
            "UnitBasis": default_unit_basis(rate_model),
            "MaxRate": default_search_max(rate_model),
            "RequireMultiStop": True,
            "StopCountMin": 3,
            "StopCountMax": 6,
            "RequiredStopTypes": ["Pickup", "Drop"],
            "RequireTracking": True,
        }

    def create_load_search_for_load(self, load, force_no_match=False):
        rate_model = str((load.get("Rate") or {}).get("RateModel") or "PerMile")
        equipment_terms = _extract_equipment_terms(load)
        stop_summary = _derive_stop_plan_summary(load)
        destination_state = "FL" if force_no_match else load["Destination"]["state"]
        search = {
            "OriginState": load["Origin"]["state"],
            "DestinationState": destination_state,
            "EquipmentType": load["EquipmentType"],
            "EquipmentClass": equipment_terms["EquipmentClass"],
            "EquipmentSubClass": equipment_terms["EquipmentSubClass"],
            "RequiredEquipmentTags": list(equipment_terms["EquipmentTags"]),
            "RequiredDriverConfiguration": load.get("DriverConfiguration", "Single"),
            "TrailerLengthMin": int(load.get("TrailerLength", 53)),
            "TrailerLengthMax": int(load.get("TrailerLength", 53)),
            "PickupDate": load.get("PickupEarliest"),
            "RateModel": rate_model,
            "UnitBasis": default_unit_basis(rate_model),
            "MaxRate": default_search_max(rate_model),
            "RequireMultiStop": bool(stop_summary["isMultiStop"]),
            "StopCountMin": int(stop_summary["stopCount"]),
            "StopCountMax": int(stop_summary["stopCount"]),
            "RequiredStopTypes": list(stop_summary["stopTypes"]),
            "RequireTracking": bool(load.get("RequireTracking", True)),
        }
        return search

    def create_bid_request(self, load, bid_amount=None):
        rate_model = load["Rate"]["RateModel"]
        amount = default_bid_amount(rate_model) if bid_amount is None else bid_amount
        stop_summary = _derive_stop_plan_summary(load)
        load_equipment_terms = _extract_equipment_terms(load)
        metadata = {}
        if rate_model == "PerMile":
            for field in ["AgreedMiles", "MilesSource", "MilesSourceVersion", "MilesCalculatedAt"]:
                if field in load["Rate"]:
                    metadata[field] = load["Rate"][field]
        if rate_model in {"PerPallet", "CWT", "PerHour"} and "Quantity" in load["Rate"]:
            metadata["Quantity"] = load["Rate"]["Quantity"]
        schedule_acceptance = {"Accepted": True, "Exceptions": []}
        for field in ["PickupTimeWindow", "DeliveryTimeWindow"]:
            if field in load:
                schedule_acceptance[field] = load[field]
        return {
            "LoadID": load["LoadID"],
            "Rate": build_rate(rate_model, amount, **metadata),
            "AvailabilityDate": (date.today() + timedelta(days=2)).isoformat(),
            "EquipmentAcceptance": {
                "Accepted": True,
                "EquipmentClass": load_equipment_terms["EquipmentClass"],
                "EquipmentSubClass": load_equipment_terms["EquipmentSubClass"],
                "EquipmentTags": list(load_equipment_terms["EquipmentTags"]),
                "TrailerLength": load.get("TrailerLength"),
                "TrailerLengthMin": load.get("TrailerLength"),
                "TrailerLengthMax": load.get("TrailerLength"),
                "TrailerCount": load.get("TrailerCount", 1),
            },
            "DriverConfigurationAcceptance": {
                "Accepted": True,
                "DriverConfiguration": load.get("DriverConfiguration"),
            },
            "SpecialInstructionsAcceptance": {
                "Accepted": True,
                "Exceptions": [],
            },
            "ScheduleAcceptance": schedule_acceptance,
            "StopPlanAcceptance": {
                "Accepted": True,
                "StopCount": stop_summary["stopCount"],
                "StopTypes": list(stop_summary["stopTypes"]),
            },
            "AccessorialPolicyAcceptance": {
                "Accepted": True,
                "AllowedTypes": list(ACTIVE_ACCESSORIAL_TYPES),
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
            "EquipmentClass": "Reefer",
            "EquipmentSubClass": "AirRide",
            "EquipmentTags": ["AirRide"],
            "DriverConfiguration": "Team",
            "TrailerLength": 53,
            "TrailerCount": 1,
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
                and _equipment_matches_search_terms(truck, filters)
                and _driver_configuration_matches(truck, filters)
            ):
                matches.append(truck)
        return matches

    def respond_to_truck_bid(self, bid_request, forced_response="Accept"):
        truck_id = bid_request["TruckID"]
        truck = self.trucks[truck_id]
        min_rate = truck["RateMin"]
        bid_rate = bid_request["Rate"]
        truck_equipment_terms = _extract_equipment_terms(truck)
        equipment_acceptance = bid_request.get("EquipmentAcceptance") or {}
        driver_acceptance = bid_request.get("DriverConfigurationAcceptance") or {}

        if bid_rate["RateModel"] != min_rate["RateModel"]:
            return {
                "TruckID": truck_id,
                "ResponseType": "Reject",
                "VerifiedBadge": "None",
                "ReasonCode": "RateModelMismatch",
            }
        mileage_decision = _per_mile_mileage_decision(min_rate, bid_rate)

        if forced_response == "Counter":
            counter_metadata = {}
            if min_rate["RateModel"] == "PerMile":
                for field in ["AgreedMiles", "MilesSource", "MilesSourceVersion", "MilesCalculatedAt"]:
                    if field in min_rate:
                        counter_metadata[field] = min_rate[field]
            return {
                "TruckID": truck_id,
                "ResponseType": "Counter",
                "ProposedRate": build_rate(
                    min_rate["RateModel"],
                    counter_amount(min_rate["RateModel"], min_rate["Amount"]),
                    **counter_metadata,
                ),
                "ReasonCode": (
                    "MileageDispute" if mileage_decision["requiresCounter"] else "MarketCounter"
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

        if _equipment_acceptance_mismatch(truck_equipment_terms, equipment_acceptance):
            counter_metadata = {}
            if min_rate["RateModel"] == "PerMile":
                for field in ["AgreedMiles", "MilesSource", "MilesSourceVersion", "MilesCalculatedAt"]:
                    if field in min_rate:
                        counter_metadata[field] = min_rate[field]
            return {
                "TruckID": truck_id,
                "ResponseType": "Counter",
                "ProposedRate": build_rate(
                    min_rate["RateModel"],
                    counter_amount(min_rate["RateModel"], min_rate["Amount"]),
                    **counter_metadata,
                ),
                "ReasonCode": "EquipmentCompatibilityDispute",
                "VerifiedBadge": "None",
            }

        if _driver_configuration_acceptance_mismatch(truck.get("DriverConfiguration"), driver_acceptance):
            counter_metadata = {}
            if min_rate["RateModel"] == "PerMile":
                for field in ["AgreedMiles", "MilesSource", "MilesSourceVersion", "MilesCalculatedAt"]:
                    if field in min_rate:
                        counter_metadata[field] = min_rate[field]
            return {
                "TruckID": truck_id,
                "ResponseType": "Counter",
                "ProposedRate": build_rate(
                    min_rate["RateModel"],
                    counter_amount(min_rate["RateModel"], min_rate["Amount"]),
                    **counter_metadata,
                ),
                "ReasonCode": "DriverConfigurationDispute",
                "VerifiedBadge": "None",
            }

        if mileage_decision["requiresCounter"]:
            counter_metadata = {}
            for field in ["AgreedMiles", "MilesSource", "MilesSourceVersion", "MilesCalculatedAt"]:
                if field in min_rate:
                    counter_metadata[field] = min_rate[field]
            return {
                "TruckID": truck_id,
                "ResponseType": "Counter",
                "ProposedRate": build_rate(
                    min_rate["RateModel"],
                    counter_amount(min_rate["RateModel"], min_rate["Amount"]),
                    **counter_metadata,
                ),
                "ReasonCode": mileage_decision["reasonCode"],
                "VerifiedBadge": "None",
            }

        return {
            "TruckID": truck_id,
            "ResponseType": "Accept",
            "ReasonCode": mileage_decision["reasonCode"],
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
            "EquipmentClass": "Van",
            "DriverConfiguration": "Single",
            "LoadReferenceNumbers": {
                "PrimaryReferenceNumber": "SHIP-2026-00112",
                "SecondaryReferenceNumber": "EXT-550184",
            },
            "TrailerLength": 53,
            "Weight": 38000,
            "Commodity": "Packaged Foods",
            "Rate": build_rate("PerMile", 2.15),
            "AccessorialPolicy": {
                "AllowedTypes": list(ACTIVE_ACCESSORIAL_TYPES),
                "RequiresApproval": True,
                "MaxTotal": 300.0,
                "Currency": "USD",
                "Terms": [
                    {
                        "Type": "UnloadingFee",
                        "PricingMode": "Reimbursable",
                        "PayerParty": "Broker",
                        "PayeeParty": "Carrier",
                        "ApprovalRequired": True,
                        "EvidenceRequired": True,
                        "EvidenceType": "Receipt",
                        "CapAmount": 300.0,
                        "Currency": "USD",
                    },
                    {
                        "Type": "OverweightPermit",
                        "PricingMode": "PassThrough",
                        "PayerParty": "Broker",
                        "PayeeParty": "Carrier",
                        "ApprovalRequired": True,
                        "EvidenceRequired": True,
                        "EvidenceType": "Permit",
                        "Currency": "USD",
                    },
                    {
                        "Type": "EscortVehicle",
                        "PricingMode": "TBD",
                        "PayerParty": "Broker",
                        "PayeeParty": "Vendor",
                        "ApprovalRequired": True,
                        "EvidenceRequired": True,
                        "EvidenceType": "EscortInvoice",
                        "Currency": "USD",
                    },
                    {
                        "Type": "Detention",
                        "PricingMode": "Reimbursable",
                        "PayerParty": "Broker",
                        "PayeeParty": "Carrier",
                        "ApprovalRequired": True,
                        "EvidenceRequired": False,
                        "Currency": "USD",
                        "DetentionTerms": {
                            "GracePeriodMinutes": 120,
                            "RateAmount": 25.0,
                            "RateUnit": "Hour",
                            "BillingIncrementMinutes": 60,
                            "RequiresDelayNotice": True,
                            "RequiresLocationEvidence": True,
                            "LocationEvidenceType": "GPS",
                            "Notes": "Delay notice and location evidence are commercial preconditions only.",
                        },
                    },
                ],
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


def run_shipper_load_flow(args, shipper, broker, carrier):
    """Optional shipper-origin load orchestration using existing booking message types."""
    print("\n=== Shipper-Orchestrated Load Flow ===")

    # 1) Shipper posts a tender as NewLoad to broker.
    shipper_tender = shipper.post_tender()
    log_message(shipper.name, broker.name, "NewLoad", shipper_tender)

    # 2) Broker normalizes and ingests tender into its load book.
    try:
        broker_load = broker.ingest_shipper_tender(shipper_tender)
    except ValueError as exc:
        print(f"\n[System] Shipper tender normalization failed: {exc}")
        return

    # 3) Carrier searches and discovers shipper-origin load via broker.
    load_search = carrier.create_load_search_for_load(
        broker_load,
        force_no_match=args.no_match,
    )
    log_message(carrier.name, broker.name, "LoadSearch", load_search)
    matched_loads = broker.search_loads(load_search)
    print("\n[System] Shipper flow load search results:")
    print(json.dumps(matched_loads, indent=2))

    if not matched_loads:
        print("\n[System] No matching shipper-origin loads found. Ending shipper flow.")
        return

    selected_load = next(
        (load for load in matched_loads if load.get("LoadID") == broker_load.get("LoadID")),
        matched_loads[0],
    )

    # 4) Carrier bids on shipper-origin load, broker responds.
    bid_request = carrier.create_bid_request(
        selected_load,
        bid_amount=args.bid_amount,
    )
    log_message(carrier.name, broker.name, "BidRequest", bid_request)

    bid_response = broker.respond_to_bid(bid_request, forced_response=args.response)
    log_message(broker.name, carrier.name, "BidResponse", bid_response)

    if bid_response["ResponseType"] == "Counter":
        print(
            "\n[System] Counter received in shipper flow. Negotiation pending; booking not complete in this run."
        )
        return

    if bid_response["ResponseType"] == "Reject":
        print("\n[System] Bid rejected in shipper flow. Booking not complete in this run.")
        return

    capabilities_ok, capability_reason = negotiate_verification_capability(
        args.provider, broker, carrier
    )
    if not capabilities_ok:
        print(f"\n[System] {capability_reason}")
        print("[System] Verification not attempted in shipper flow due to capability mismatch.")
        return

    # 5) Verification and policy decision.
    print(f"\n[System] Shipper flow verification requested via provider: {args.provider}")
    verification_result, verified_badge = run_verification(
        provider=args.provider,
        status=args.verification_status,
        mc_number=args.mc_number,
        fmcsa_source=args.fmcsa_source,
    )
    print("[System] Shipper flow verification result:")
    print(json.dumps(redact_sensitive(verification_result), indent=2))
    print(f"[System] Shipper flow VerifiedBadge assigned: {verified_badge}")

    policy_decision = evaluate_verification_policy_decision(
        verification_result,
        profile_id=args.policy_profile_id,
        risk_tier=args.risk_tier,
        exception_approved=args.exception_approved,
        exception_approval_ref=args.exception_approval_ref,
    )
    print("[System] Shipper flow policy decision:")
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
        print("\n[System] Policy blocked booking in shipper flow.")
        return

    # 6) Broker confirms booking with ExecutionReport to carrier.
    execution_report = broker.create_execution_report(
        load_id=bid_request["LoadID"],
        bid_request=bid_request,
        verified_badge=verified_badge,
        verification_result=verification_result,
        policy_decision=policy_decision,
    )
    log_message(broker.name, carrier.name, "ExecutionReport", execution_report)

    # 7) Mark complete for booking principals in this flow (broker and carrier).
    carrier.mark_booking_complete(execution_report)
    broker_complete = bid_request["LoadID"] in broker.completed_bookings
    carrier_complete = bid_request["LoadID"] in carrier.completed_bookings
    print(
        f"\n[System] Shipper flow booking completion state -> Broker: {broker_complete}, Carrier: {carrier_complete}"
    )
    print(
        "Shipper-origin booking completed successfully - "
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
    mileage_policy = configure_mileage_dispute_policy(
        policy=args.mileage_dispute_policy,
        abs_tolerance_miles=args.mileage_abs_tolerance_miles,
        rel_tolerance_ratio=args.mileage_rel_tolerance_ratio,
    )

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
        f"exceptionApprovalRef={args.exception_approval_ref or '[none]'}, "
        f"mileagePolicy={mileage_policy['policy']}, "
        f"mileageAbsToleranceMiles={mileage_policy['absToleranceMiles']}, "
        f"mileageRelToleranceRatio={mileage_policy['relToleranceRatio']}"
    )

    # Show AmendRequest exists in protocol but do not execute it in these happy paths.
    amend_preview = FaxpProtocol.amend_request_example("example-load-id")
    print("\nAmendRequest (exists, not executed in this run):")
    print(json.dumps(amend_preview, indent=2))

    # Existing load-centric flow.
    run_load_flow(args, broker, carrier)

    # Optional shipper-origin orchestration flow.
    if args.shipper_flow:
        shipper = ShipperAgent("Shipper Agent")
        run_shipper_load_flow(args, shipper, broker, carrier)

    # Additional reverse flow: carrier truck posting -> broker truck search.
    run_truck_flow(args, broker, carrier)


if __name__ == "__main__":
    main()
