#!/usr/bin/env python3
"""Validate release-readiness checklist coverage against files, suite checks, CI, and governance index."""

from __future__ import annotations

from pathlib import Path
import json
import os
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHECKLIST_PATH = PROJECT_ROOT / "docs" / "governance" / "RELEASE_READINESS_CHECKLIST.md"
GOVERNANCE_INDEX_PATH = PROJECT_ROOT / "docs" / "governance" / "GOVERNANCE_INDEX.json"
CI_WORKFLOW_PATH = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"
CONFORMANCE_SUITE_PATH = PROJECT_ROOT / "conformance" / "run_all_checks.py"
REPLAY_GATES_PATH = PROJECT_ROOT / "docs" / "governance" / "REPLAY_OPERATIONS_GATES.md"

BLOCK_BEGIN = "<!-- RELEASE_READINESS_REQUIREMENTS_BEGIN -->"
BLOCK_END = "<!-- RELEASE_READINESS_REQUIREMENTS_END -->"
REPLAY_BLOCK_BEGIN = "<!-- REPLAY_OPERATIONS_GATES_BEGIN -->"
REPLAY_BLOCK_END = "<!-- REPLAY_OPERATIONS_GATES_END -->"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _extract_block(document: str, begin: str, end: str) -> str:
    start = document.find(begin)
    stop = document.find(end)
    _assert(start != -1 and stop != -1 and stop > start, f"Missing or invalid block: {begin}")
    return document[start + len(begin) : stop].strip()


def _resolve(path_ref: str) -> Path:
    path = Path(path_ref)
    if path.is_absolute():
        return path
    return (PROJECT_ROOT / path).resolve()


def _validate_unique(items: list[str], context: str) -> None:
    duplicates = sorted({item for item in items if items.count(item) > 1})
    _assert(not duplicates, f"{context} has duplicate values: {duplicates}")


def _is_truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "y"}


def _is_strict_release_mode() -> bool:
    app_mode = str(os.getenv("FAXP_APP_MODE", "local") or "").strip().lower()
    release_channel = str(os.getenv("FAXP_RELEASE_CHANNEL", "") or "").strip().lower()
    strict_override = _is_truthy(os.getenv("FAXP_RELEASE_STRICT_GATES", "0"))
    strict_legacy_override = _is_truthy(os.getenv("FAXP_ENFORCE_STRICT_RELEASE_GATES", "0"))
    if strict_override:
        return True
    if strict_legacy_override:
        return True
    if app_mode not in {"local", "dev", "development", "test"}:
        return True
    return release_channel in {"beta", "rc", "candidate", "release", "production"}


def _extract_replay_checklist_rows(document: str) -> list[str]:
    rows = []
    for raw_line in document.splitlines():
        line = raw_line.strip()
        if not line.startswith("| Replay "):
            continue
        rows.append(line)
    return rows


def _validate_replay_checklist_rows_if_required(checklist_doc: str) -> None:
    if not _is_strict_release_mode():
        return
    rows = _extract_replay_checklist_rows(checklist_doc)
    _assert(rows, "Strict release-mode requires replay checklist rows to be present.")
    non_done_rows = []
    for row in rows:
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        if len(cells) < 4:
            non_done_rows.append({"row": row, "reason": "invalid-row-format"})
            continue
        owner, due, status = cells[1], cells[2], cells[3]
        if owner.upper() == "TBD" or due.upper() == "TBD" or status.lower() != "done":
            non_done_rows.append({"row": row, "owner": owner, "due": due, "status": status})
    _assert(
        not non_done_rows,
        (
            "Strict release-mode readiness failed: replay checklist rows must be fully closed "
            f"(owner/due set and status=Done). Outstanding: {non_done_rows}"
        ),
    )


def _validate_strict_replay_gate_closure_if_required() -> None:
    if not _is_strict_release_mode():
        return

    _assert(REPLAY_GATES_PATH.exists(), "Missing replay operations gates document.")
    replay_doc = REPLAY_GATES_PATH.read_text(encoding="utf-8")
    payload = json.loads(_extract_block(replay_doc, REPLAY_BLOCK_BEGIN, REPLAY_BLOCK_END))
    gates = payload.get("gates") or []
    _assert(isinstance(gates, list) and gates, "Replay gate manifest must include non-empty gates.")

    not_closed = []
    for gate in gates:
        gate_id = str((gate or {}).get("id") or "").strip()
        status = str((gate or {}).get("status") or "").strip().lower()
        if not gate_id:
            continue
        if status != "done":
            not_closed.append({"id": gate_id, "status": status or "missing"})

    _assert(
        not not_closed,
        (
            "Strict release-mode gate closure failed: all replay operation gates must be status=done "
            f"before beta/release promotion. Outstanding: {not_closed}"
        ),
    )


def main() -> int:
    checklist_doc = CHECKLIST_PATH.read_text(encoding="utf-8")
    requirements = json.loads(_extract_block(checklist_doc, BLOCK_BEGIN, BLOCK_END))
    _validate_replay_checklist_rows_if_required(checklist_doc)

    required_fields = [
        "requiredArtifacts",
        "requiredTests",
        "requiredSuiteChecks",
        "requireGovernanceIndexSync",
    ]
    for field in required_fields:
        _assert(field in requirements, f"Checklist requirements missing field: {field}")

    required_artifacts = [str(item) for item in requirements.get("requiredArtifacts") or []]
    required_tests = [str(item) for item in requirements.get("requiredTests") or []]
    required_suite_checks = [str(item) for item in requirements.get("requiredSuiteChecks") or []]
    require_governance_sync = bool(requirements.get("requireGovernanceIndexSync"))

    _assert(required_artifacts, "requiredArtifacts must be non-empty.")
    _assert(required_tests, "requiredTests must be non-empty.")
    _assert(required_suite_checks, "requiredSuiteChecks must be non-empty.")
    _validate_unique(required_artifacts, "requiredArtifacts")
    _validate_unique(required_tests, "requiredTests")
    _validate_unique(required_suite_checks, "requiredSuiteChecks")

    for rel_path in required_artifacts:
        _assert(_resolve(rel_path).exists(), f"Missing required artifact: {rel_path}")
    for rel_path in required_tests:
        _assert(_resolve(rel_path).exists(), f"Missing required test: {rel_path}")

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
            f"Missing required conformance suite check: {check_name}",
        )

    ci_contents = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    for test_ref in required_tests:
        _assert(
            test_ref in ci_contents,
            f"CI workflow missing required test reference: {test_ref}",
        )

    if require_governance_sync:
        governance = _load_json(GOVERNANCE_INDEX_PATH)
        gov_tests = set(str(item) for item in governance.get("requiredTests") or [])
        gov_checks = set(str(item) for item in governance.get("requiredSuiteChecks") or [])
        _assert(
            "tests/run_release_readiness.py" in gov_tests,
            "GOVERNANCE_INDEX.json must include tests/run_release_readiness.py in requiredTests.",
        )
        _assert(
            "release_readiness" in gov_checks,
            "GOVERNANCE_INDEX.json must include release_readiness in requiredSuiteChecks.",
        )
        suite_map = governance.get("suiteCheckToTest") or {}
        _assert(
            str(suite_map.get("release_readiness") or "") == "tests/run_release_readiness.py",
            "GOVERNANCE_INDEX suiteCheckToTest.release_readiness must map to tests/run_release_readiness.py.",
        )

    _validate_strict_replay_gate_closure_if_required()

    print("Release readiness checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
