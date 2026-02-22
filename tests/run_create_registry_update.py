#!/usr/bin/env python3
"""Regression checks for conformance/create_registry_update.py."""

from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys
import tempfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CREATE_SCRIPT_PATH = PROJECT_ROOT / "conformance" / "create_registry_update.py"
VERIFY_SCRIPT_PATH = PROJECT_ROOT / "tests" / "run_registry_ops_artifacts.py"
TEMPLATE_PATH = PROJECT_ROOT / "conformance" / "registry_update.sample.json"
KEYRING_PATH = PROJECT_ROOT / "conformance" / "registry_update_keys.sample.json"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="faxp-regops-create-test-") as temp_dir:
        output_path = Path(temp_dir) / "registry_update.generated.json"

        completed = subprocess.run(
            [
                sys.executable,
                str(CREATE_SCRIPT_PATH),
                "--template",
                str(TEMPLATE_PATH),
                "--keyring",
                str(KEYRING_PATH),
                "--kid",
                "faxp-regops-kid-2026q1",
                "--change-set-id",
                "faxp-regops-generated-0001",
                "--submitted-at",
                "2026-02-23T00:00:00Z",
                "--approver-ref",
                "review-ticket-generated-001",
                "--output",
                str(output_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        _assert(
            "[RegistryUpdateCreate] wrote signed request" in completed.stdout,
            "expected create helper write confirmation",
        )
        _assert(output_path.exists(), "expected generated registry update request file")

        generated = _load_json(output_path)
        _assert(generated.get("changeSetId") == "faxp-regops-generated-0001", "unexpected changeSetId")
        _assert(
            generated.get("submittedAt") == "2026-02-23T00:00:00Z",
            "unexpected submittedAt override value",
        )
        signature = generated.get("requestSignature") or {}
        _assert(signature.get("kid") == "faxp-regops-kid-2026q1", "unexpected signature kid")
        _assert(signature.get("sig"), "missing generated signature")

        # Validate generated file through registry ops artifact validator.
        subprocess.run(
            [
                sys.executable,
                str(VERIFY_SCRIPT_PATH),
                "--request",
                str(output_path),
                "--keyring",
                str(KEYRING_PATH),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    print("Registry update create helper checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

