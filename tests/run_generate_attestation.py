#!/usr/bin/env python3
"""Regression checks for conformance/generate_attestation.py."""

from __future__ import annotations

from pathlib import Path
import hashlib
import hmac
import json
import subprocess
import sys
import tempfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "conformance" / "generate_attestation.py"
PROFILE_SAMPLE_PATH = PROJECT_ROOT / "conformance" / "adapter_profile.sample.json"
KEYRING_SAMPLE_PATH = PROJECT_ROOT / "conformance" / "attestation_keys.sample.json"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def main() -> int:
    profile = _load_json(PROFILE_SAMPLE_PATH)
    keyring = _load_json(KEYRING_SAMPLE_PATH)

    # Tamper payload to ensure regeneration actually changes digest/signature.
    profile["securityCapabilities"]["clockSkewSeconds"] = 45
    profile["selfAttestation"]["payloadDigestSha256"] = "sha256:deadbeef"
    profile["selfAttestation"]["sig"] = "0" * 64

    with tempfile.TemporaryDirectory(prefix="faxp-attestation-test-") as temp_dir:
        temp_profile_path = Path(temp_dir) / "adapter_profile.json"
        temp_keyring_path = Path(temp_dir) / "attestation_keys.json"
        temp_profile_path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
        temp_keyring_path.write_text(json.dumps(keyring, indent=2), encoding="utf-8")

        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "--profile",
                str(temp_profile_path),
                "--keyring",
                str(temp_keyring_path),
                "--kid",
                "faxp-lab-selfattest-2026q1",
                "--signed-at",
                "2026-02-22T00:00:00Z",
                "--expires-at",
                "2026-08-22T00:00:00Z",
                "--in-place",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        _assert("Updated attestation in" in completed.stdout, "expected update confirmation output")

        updated_profile = _load_json(temp_profile_path)
        attestation = updated_profile.get("selfAttestation", {})
        payload = attestation.get("payload", {})
        payload_canonical = _canonical_json(payload)
        expected_digest = hashlib.sha256(payload_canonical.encode("utf-8")).hexdigest()
        expected_sig = hmac.new(
            b"faxp-selfattest-demo-key-change-me",
            payload_canonical.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        _assert(
            attestation.get("payloadDigestSha256") == f"sha256:{expected_digest}",
            "unexpected regenerated digest",
        )
        _assert(
            attestation.get("sig") == expected_sig,
            "unexpected regenerated signature",
        )
        _assert(attestation.get("alg") == "HMAC_SHA256", "unexpected signing algorithm")
        _assert(attestation.get("kid") == "faxp-lab-selfattest-2026q1", "unexpected key id")

    print("Attestation generator regression checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
