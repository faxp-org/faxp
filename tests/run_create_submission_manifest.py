#!/usr/bin/env python3
"""Regression checks for conformance/create_submission_manifest.py."""

from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys
import tempfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CREATE_SCRIPT_PATH = PROJECT_ROOT / "conformance" / "create_submission_manifest.py"
VERIFY_SCRIPT_PATH = PROJECT_ROOT / "tests" / "run_submission_manifest.py"
TEMPLATE_PATH = PROJECT_ROOT / "conformance" / "submission_manifest.sample.json"
KEYRING_PATH = PROJECT_ROOT / "conformance" / "submission_manifest_keys.sample.json"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="faxp-submission-create-test-") as temp_dir:
        output_path = Path(temp_dir) / "submission_manifest.generated.json"
        completed = subprocess.run(
            [
                sys.executable,
                str(CREATE_SCRIPT_PATH),
                "--template",
                str(TEMPLATE_PATH),
                "--keyring",
                str(KEYRING_PATH),
                "--kid",
                "faxp-submission-kid-2026q1",
                "--submission-id",
                "faxp-submission-generated-0001",
                "--submitted-at",
                "2026-02-23T00:00:00Z",
                "--output",
                str(output_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        _assert("[SubmissionCreate] wrote signed manifest" in completed.stdout, "missing write confirmation")
        _assert(output_path.exists(), "expected generated submission manifest file")

        generated = _load_json(output_path)
        _assert(
            generated.get("submissionId") == "faxp-submission-generated-0001",
            "unexpected submissionId override",
        )
        _assert(
            generated.get("submittedAt") == "2026-02-23T00:00:00Z",
            "unexpected submittedAt override",
        )
        signature = generated.get("submissionSignature") or {}
        _assert(signature.get("kid") == "faxp-submission-kid-2026q1", "unexpected signature kid")
        _assert(signature.get("sig"), "missing generated submission signature")

        subprocess.run(
            [
                sys.executable,
                str(VERIFY_SCRIPT_PATH),
                "--manifest",
                str(output_path),
                "--keyring",
                str(KEYRING_PATH),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    print("Submission manifest create helper checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

