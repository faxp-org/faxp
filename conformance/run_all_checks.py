#!/usr/bin/env python3
"""Run the FAXP certification/conformance suite and emit a single summary report."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import subprocess
import sys
import time
import uuid


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = PROJECT_ROOT / "tests"


def _now_utc() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _suite_commands() -> list[tuple[str, list[str]]]:
    python = sys.executable
    return [
        ("adapter_test_profile", [python, str(TESTS_DIR / "run_adapter_test_profile.py")]),
        ("submission_create", [python, str(TESTS_DIR / "run_create_submission_manifest.py")]),
        ("submission_manifest", [python, str(TESTS_DIR / "run_submission_manifest.py")]),
        ("key_lifecycle_policy", [python, str(TESTS_DIR / "run_key_lifecycle_policy.py")]),
        ("registry_create", [python, str(TESTS_DIR / "run_create_registry_update.py")]),
        ("registry_ops", [python, str(TESTS_DIR / "run_registry_ops_artifacts.py")]),
        ("registry_admission_policy", [python, str(TESTS_DIR / "run_registry_admission_policy.py")]),
        ("registry_changelog_artifacts", [python, str(TESTS_DIR / "run_registry_changelog_artifacts.py")]),
        ("decision_record_template", [python, str(TESTS_DIR / "run_decision_record_template.py")]),
        ("decision_record_artifacts", [python, str(TESTS_DIR / "run_decision_record_artifacts.py")]),
        ("governance_index", [python, str(TESTS_DIR / "run_governance_index.py")]),
        ("release_readiness", [python, str(TESTS_DIR / "run_release_readiness.py")]),
        ("a2a_profile", [python, str(TESTS_DIR / "run_a2a_profile_check.py")]),
        ("a2a_roundtrip", [python, str(TESTS_DIR / "run_a2a_roundtrip_translation.py")]),
        ("mcp_profile", [python, str(TESTS_DIR / "run_mcp_profile_check.py")]),
        ("mcp_watch_artifacts", [python, str(TESTS_DIR / "run_mcp_watch_artifacts.py")]),
        ("registry_apply", [python, str(TESTS_DIR / "run_apply_registry_update.py")]),
        ("certification_artifacts", [python, str(TESTS_DIR / "run_certification_artifacts.py")]),
        ("policy_profile_sync", [python, str(TESTS_DIR / "run_policy_profile_sync.py")]),
        ("conformance_bundle", [python, str(TESTS_DIR / "run_conformance_bundle.py")]),
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run FAXP certification/conformance checks and emit a summary report."
    )
    parser.add_argument(
        "--output",
        default=str(Path("/tmp") / "faxp_conformance_suite_report.json"),
        help="Path to write summary report JSON.",
    )
    parser.add_argument(
        "--log-dir",
        default="",
        help="Directory to write per-step stdout/stderr logs. Defaults to /tmp/faxp-conformance-<id>.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on first failure. Default is to run full suite and report all results.",
    )
    parser.add_argument(
        "--checks",
        default="",
        help="Optional comma-separated check names to run (defaults to full suite order).",
    )
    parser.add_argument(
        "--list-checks",
        action="store_true",
        help="Print available check names and exit.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_id = str(uuid.uuid4())
    started_at = _now_utc()
    full_suite = _suite_commands()

    if args.list_checks:
        for name, _ in full_suite:
            print(name)
        return 0

    if args.checks.strip():
        requested = [item.strip() for item in args.checks.split(",") if item.strip()]
        selected_names = set(requested)
        suite = [(name, cmd) for name, cmd in full_suite if name in selected_names]
        missing = [name for name in requested if name not in {item[0] for item in full_suite}]
        if missing:
            print(f"[ConformanceSuite] unknown check names: {', '.join(missing)}", file=sys.stderr)
            return 1
        if not suite:
            print("[ConformanceSuite] no checks selected.", file=sys.stderr)
            return 1
    else:
        suite = full_suite

    if args.log_dir.strip():
        log_dir = Path(args.log_dir).expanduser().resolve()
    else:
        log_dir = Path("/tmp") / f"faxp-conformance-{run_id}"
    log_dir.mkdir(parents=True, exist_ok=True)

    checks: list[dict] = []
    suite_started = time.monotonic()
    failed = False

    for name, cmd in suite:
        step_started = time.monotonic()
        completed = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        duration_ms = int((time.monotonic() - step_started) * 1000)

        stdout_path = log_dir / f"{name}.stdout.log"
        stderr_path = log_dir / f"{name}.stderr.log"
        stdout_path.write_text(completed.stdout or "", encoding="utf-8")
        stderr_path.write_text(completed.stderr or "", encoding="utf-8")

        passed = completed.returncode == 0
        checks.append(
            {
                "name": name,
                "command": cmd,
                "passed": passed,
                "exitCode": completed.returncode,
                "durationMs": duration_ms,
                "stdoutLog": str(stdout_path),
                "stderrLog": str(stderr_path),
            }
        )
        if not passed:
            failed = True
            if args.fail_fast:
                break

    total_duration_ms = int((time.monotonic() - suite_started) * 1000)
    passed_count = sum(1 for check in checks if check["passed"])
    failed_count = len(checks) - passed_count

    report = {
        "runId": run_id,
        "startedAt": started_at,
        "finishedAt": _now_utc(),
        "projectRoot": str(PROJECT_ROOT),
        "logDir": str(log_dir),
        "summary": {
            "totalChecks": len(checks),
            "passedChecks": passed_count,
            "failedChecks": failed_count,
            "passed": not failed,
            "durationMs": total_duration_ms,
        },
        "checks": checks,
    }

    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(report["summary"], indent=2))
    print(f"[ConformanceSuite] report: {output_path}")
    print(f"[ConformanceSuite] logs:   {log_dir}")

    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
