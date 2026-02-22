#!/usr/bin/env python3
"""Regression checks for conformance/apply_registry_update.py."""

from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys
import tempfile

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "conformance" / "apply_registry_update.py"
REGISTRY_SCHEMA_PATH = PROJECT_ROOT / "conformance" / "certification_registry.schema.json"
REQUEST_PATH = PROJECT_ROOT / "conformance" / "registry_update.sample.json"
EXPECTED_PATH = PROJECT_ROOT / "conformance" / "certification_registry.sample.after_update.json"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="faxp-registry-apply-test-") as temp_dir:
        output_path = Path(temp_dir) / "registry.after.json"
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "--request",
                str(REQUEST_PATH),
                "--output",
                str(output_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        _assert("[RegistryApply] wrote updated registry" in completed.stdout, "missing apply confirmation")
        _assert(output_path.exists(), "expected output registry artifact was not written")

        produced = _load_json(output_path)
        expected = _load_json(EXPECTED_PATH)
        _assert(produced == expected, "applied registry output did not match expected fixture")

        registry_schema = _load_json(REGISTRY_SCHEMA_PATH)
        validator = Draft202012Validator(registry_schema)
        errors = sorted(validator.iter_errors(produced), key=lambda item: item.path)
        if errors:
            raise AssertionError(f"produced registry failed schema validation: {errors[0].message}")

    print("Registry apply regression checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
