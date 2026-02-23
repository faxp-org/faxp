#!/usr/bin/env python3
"""Verify rate model profile signature and fail closed on tampering."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from conformance.rate_model_profile_signing import verify_profile_signature  # noqa: E402


PROFILE_PATH = PROJECT_ROOT / "conformance" / "rate_model_profile.v1.json"
KEYRING_PATH = PROJECT_ROOT / "conformance" / "rate_model_profile_keys.sample.json"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    _assert(isinstance(payload, dict), f"{path.name} must contain a JSON object.")
    return payload


def main() -> int:
    profile = _load_json(PROFILE_PATH)
    keyring = _load_json(KEYRING_PATH)

    verify_profile_signature(profile, keyring=keyring, require_signature=True)

    tampered = deepcopy(profile)
    tampered["activeRateModels"] = ["Flat"]
    try:
        verify_profile_signature(tampered, keyring=keyring, require_signature=True)
    except ValueError as exc:
        _assert(
            "profileSignature payload digest mismatch" in str(exc)
            or "profileSignature verification failed" in str(exc),
            "tamper case should fail on digest/signature mismatch.",
        )
    else:
        raise AssertionError("Expected tampered profile to fail signature verification.")

    missing = deepcopy(profile)
    missing.pop("profileSignature", None)
    try:
        verify_profile_signature(missing, keyring=keyring, require_signature=True)
    except ValueError as exc:
        _assert("Missing profileSignature." in str(exc), "missing-signature case must fail closed.")
    else:
        raise AssertionError("Expected missing profile signature to fail verification.")

    print("Rate model profile signature checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
