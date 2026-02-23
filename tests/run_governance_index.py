#!/usr/bin/env python3
"""Validate governance index coverage against artifacts, suite checks, and CI references."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = PROJECT_ROOT / "GOVERNANCE_INDEX.json"
CI_WORKFLOW_PATH = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"
CONFORMANCE_SUITE_PATH = PROJECT_ROOT / "conformance" / "run_all_checks.py"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _parse_iso8601(value: str, context: str) -> None:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AssertionError(f"{context} must be ISO-8601.") from exc


def _validate_unique(values: list[str], context: str) -> None:
    duplicates = sorted({value for value in values if values.count(value) > 1})
    _assert(not duplicates, f"{context} contains duplicates: {duplicates}")


def main() -> int:
    index_payload = _load_json(INDEX_PATH)

    required_top_level = [
        "indexVersion",
        "generatedAt",
        "policyArtifacts",
        "requiredTests",
        "requiredSuiteChecks",
        "suiteCheckToTest",
    ]
    for field in required_top_level:
        _assert(field in index_payload, f"GOVERNANCE_INDEX.json missing field: {field}")

    _parse_iso8601(str(index_payload["generatedAt"]), "generatedAt")

    policy_artifacts = [str(item) for item in index_payload.get("policyArtifacts") or []]
    required_tests = [str(item) for item in index_payload.get("requiredTests") or []]
    required_suite_checks = [str(item) for item in index_payload.get("requiredSuiteChecks") or []]
    suite_map = index_payload.get("suiteCheckToTest") or {}

    _assert(policy_artifacts, "policyArtifacts must be non-empty.")
    _assert(required_tests, "requiredTests must be non-empty.")
    _assert(required_suite_checks, "requiredSuiteChecks must be non-empty.")
    _assert(isinstance(suite_map, dict) and suite_map, "suiteCheckToTest must be a non-empty object.")

    _validate_unique(policy_artifacts, "policyArtifacts")
    _validate_unique(required_tests, "requiredTests")
    _validate_unique(required_suite_checks, "requiredSuiteChecks")

    for rel_path in policy_artifacts:
        path = (PROJECT_ROOT / rel_path).resolve()
        _assert(path.exists(), f"policy artifact not found: {rel_path}")

    for rel_path in required_tests:
        path = (PROJECT_ROOT / rel_path).resolve()
        _assert(path.exists(), f"required test not found: {rel_path}")

    map_check_names = sorted(str(name) for name in suite_map.keys())
    _assert(
        sorted(required_suite_checks) == map_check_names,
        "requiredSuiteChecks must match suiteCheckToTest keys.",
    )

    for check_name, test_ref in suite_map.items():
        test_path = str(test_ref)
        _assert(
            test_path in required_tests,
            f"suiteCheckToTest '{check_name}' points to test not in requiredTests: {test_path}",
        )
        _assert((PROJECT_ROOT / test_path).resolve().exists(), f"suite map test does not exist: {test_path}")

    listed_checks_run = subprocess.run(
        [sys.executable, str(CONFORMANCE_SUITE_PATH), "--list-checks"],
        check=True,
        capture_output=True,
        text=True,
    )
    listed_checks = set(line.strip() for line in listed_checks_run.stdout.splitlines() if line.strip())
    for check_name in required_suite_checks:
        _assert(
            check_name in listed_checks,
            f"required suite check missing from conformance/run_all_checks.py: {check_name}",
        )

    ci_contents = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    for test_ref in required_tests:
        _assert(
            test_ref in ci_contents,
            f"CI workflow missing required governance test reference: {test_ref}",
        )

    # Governance index test must remain self-referential in both requiredTests and suite map.
    _assert("tests/run_governance_index.py" in required_tests, "Self-check test must be required.")
    _assert(
        suite_map.get("governance_index") == "tests/run_governance_index.py",
        "suiteCheckToTest['governance_index'] must point to tests/run_governance_index.py",
    )

    print("Governance index checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
