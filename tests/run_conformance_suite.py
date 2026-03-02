#!/usr/bin/env python3
"""Regression check for conformance/run_all_checks.py."""

from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys
import tempfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "conformance" / "run_all_checks.py"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    listed_checks = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--list-checks",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    _assert(
        "policy_profile_sync" in listed_checks.stdout.splitlines(),
        "conformance suite must include policy_profile_sync in default checks",
    )
    _assert(
        "registry_admission_policy" in listed_checks.stdout.splitlines(),
        "conformance suite must include registry_admission_policy in default checks",
    )
    _assert(
        "decision_record_template" in listed_checks.stdout.splitlines(),
        "conformance suite must include decision_record_template in default checks",
    )
    _assert(
        "decision_record_artifacts" in listed_checks.stdout.splitlines(),
        "conformance suite must include decision_record_artifacts in default checks",
    )
    _assert(
        "verification_policy_profile" in listed_checks.stdout.splitlines(),
        "conformance suite must include verification_policy_profile in default checks",
    )
    _assert(
        "policy_decisions" in listed_checks.stdout.splitlines(),
        "conformance suite must include policy_decisions in default checks",
    )
    _assert(
        "registry_changelog_artifacts" in listed_checks.stdout.splitlines(),
        "conformance suite must include registry_changelog_artifacts in default checks",
    )
    _assert(
        "governance_index" in listed_checks.stdout.splitlines(),
        "conformance suite must include governance_index in default checks",
    )
    _assert(
        "release_readiness" in listed_checks.stdout.splitlines(),
        "conformance suite must include release_readiness in default checks",
    )
    _assert(
        "booking_plane_commercial_terms_doc" in listed_checks.stdout.splitlines(),
        "conformance suite must include booking_plane_commercial_terms_doc in default checks",
    )
    _assert(
        "a2a_profile" in listed_checks.stdout.splitlines(),
        "conformance suite must include a2a_profile in default checks",
    )
    _assert(
        "adapter_certification_profile_v2" in listed_checks.stdout.splitlines(),
        "conformance suite must include adapter_certification_profile_v2 in default checks",
    )
    _assert(
        "a2a_roundtrip" in listed_checks.stdout.splitlines(),
        "conformance suite must include a2a_roundtrip in default checks",
    )
    _assert(
        "a2a_watch_artifacts" in listed_checks.stdout.splitlines(),
        "conformance suite must include a2a_watch_artifacts in default checks",
    )
    _assert(
        "mcp_profile" in listed_checks.stdout.splitlines(),
        "conformance suite must include mcp_profile in default checks",
    )
    _assert(
        "mcp_watch_artifacts" in listed_checks.stdout.splitlines(),
        "conformance suite must include mcp_watch_artifacts in default checks",
    )
    _assert(
        "interop_maturity_profile" in listed_checks.stdout.splitlines(),
        "conformance suite must include interop_maturity_profile in default checks",
    )
    _assert(
        "rate_model_profile" in listed_checks.stdout.splitlines(),
        "conformance suite must include rate_model_profile in default checks",
    )
    _assert(
        "rate_model_profile_signature" in listed_checks.stdout.splitlines(),
        "conformance suite must include rate_model_profile_signature in default checks",
    )
    _assert(
        "rate_model_extensibility" in listed_checks.stdout.splitlines(),
        "conformance suite must include rate_model_extensibility in default checks",
    )
    _assert(
        "rate_model_requirements" in listed_checks.stdout.splitlines(),
        "conformance suite must include rate_model_requirements in default checks",
    )
    _assert(
        "rate_search_requirements" in listed_checks.stdout.splitlines(),
        "conformance suite must include rate_search_requirements in default checks",
    )
    _assert(
        "accessorial_terms" in listed_checks.stdout.splitlines(),
        "conformance suite must include accessorial_terms in default checks",
    )
    _assert(
        "accessorial_terms_profile" in listed_checks.stdout.splitlines(),
        "conformance suite must include accessorial_terms_profile in default checks",
    )
    _assert(
        "detention_terms_profile" in listed_checks.stdout.splitlines(),
        "conformance suite must include detention_terms_profile in default checks",
    )
    _assert(
        "accessorial_type_registry" in listed_checks.stdout.splitlines(),
        "conformance suite must include accessorial_type_registry in default checks",
    )
    _assert(
        "operational_handoff_terms" in listed_checks.stdout.splitlines(),
        "conformance suite must include operational_handoff_terms in default checks",
    )
    _assert(
        "operational_handoff_profile" in listed_checks.stdout.splitlines(),
        "conformance suite must include operational_handoff_profile in default checks",
    )
    _assert(
        "booking_identity_terms" in listed_checks.stdout.splitlines(),
        "conformance suite must include booking_identity_terms in default checks",
    )
    _assert(
        "booking_identity_profile" in listed_checks.stdout.splitlines(),
        "conformance suite must include booking_identity_profile in default checks",
    )
    _assert(
        "multi_stop_terms" in listed_checks.stdout.splitlines(),
        "conformance suite must include multi_stop_terms in default checks",
    )
    _assert(
        "multi_stop_terms_profile" in listed_checks.stdout.splitlines(),
        "conformance suite must include multi_stop_terms_profile in default checks",
    )
    _assert(
        "special_instructions_terms" in listed_checks.stdout.splitlines(),
        "conformance suite must include special_instructions_terms in default checks",
    )
    _assert(
        "special_instructions_profile" in listed_checks.stdout.splitlines(),
        "conformance suite must include special_instructions_profile in default checks",
    )
    _assert(
        "schedule_terms" in listed_checks.stdout.splitlines(),
        "conformance suite must include schedule_terms in default checks",
    )
    _assert(
        "schedule_terms_profile" in listed_checks.stdout.splitlines(),
        "conformance suite must include schedule_terms_profile in default checks",
    )
    _assert(
        "driver_configuration_terms" in listed_checks.stdout.splitlines(),
        "conformance suite must include driver_configuration_terms in default checks",
    )
    _assert(
        "driver_configuration_profile" in listed_checks.stdout.splitlines(),
        "conformance suite must include driver_configuration_profile in default checks",
    )
    _assert(
        "load_reference_numbers_terms" in listed_checks.stdout.splitlines(),
        "conformance suite must include load_reference_numbers_terms in default checks",
    )
    _assert(
        "load_reference_numbers_profile" in listed_checks.stdout.splitlines(),
        "conformance suite must include load_reference_numbers_profile in default checks",
    )
    _assert(
        "equipment_terms" in listed_checks.stdout.splitlines(),
        "conformance suite must include equipment_terms in default checks",
    )
    _assert(
        "equipment_profile" in listed_checks.stdout.splitlines(),
        "conformance suite must include equipment_profile in default checks",
    )
    _assert(
        "equipment_type_alias_coverage" in listed_checks.stdout.splitlines(),
        "conformance suite must include equipment_type_alias_coverage in default checks",
    )
    _assert(
        "protocol_compatibility_profile" in listed_checks.stdout.splitlines(),
        "conformance suite must include protocol_compatibility_profile in default checks",
    )
    _assert(
        "protocol_compatibility_signature" in listed_checks.stdout.splitlines(),
        "conformance suite must include protocol_compatibility_signature in default checks",
    )
    _assert(
        "protocol_version_negotiation" in listed_checks.stdout.splitlines(),
        "conformance suite must include protocol_version_negotiation in default checks",
    )
    _assert(
        "cross_version_fixtures" in listed_checks.stdout.splitlines(),
        "conformance suite must include cross_version_fixtures in default checks",
    )
    _assert(
        "trusted_verifier_registry" in listed_checks.stdout.splitlines(),
        "conformance suite must include trusted_verifier_registry in default checks",
    )
    _assert(
        "vendor_direct_profile" in listed_checks.stdout.splitlines(),
        "conformance suite must include vendor_direct_profile in default checks",
    )
    _assert(
        "vendor_direct_attestation_flow" in listed_checks.stdout.splitlines(),
        "conformance suite must include vendor_direct_attestation_flow in default checks",
    )
    _assert(
        "trust_profile" in listed_checks.stdout.splitlines(),
        "conformance suite must include trust_profile in default checks",
    )
    _assert(
        "role_capability_policy" in listed_checks.stdout.splitlines(),
        "conformance suite must include role_capability_policy in default checks",
    )
    _assert(
        "shipper_orchestration_minimal" in listed_checks.stdout.splitlines(),
        "conformance suite must include shipper_orchestration_minimal in default checks",
    )
    _assert(
        "shipper_orchestration_profile" in listed_checks.stdout.splitlines(),
        "conformance suite must include shipper_orchestration_profile in default checks",
    )
    _assert(
        "builder_integration_profile" in listed_checks.stdout.splitlines(),
        "conformance suite must include builder_integration_profile in default checks",
    )

    with tempfile.TemporaryDirectory(prefix="faxp-conformance-suite-") as temp_dir:
        output_path = Path(temp_dir) / "suite_report.json"
        log_dir = Path(temp_dir) / "suite_logs"

        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "--checks",
                "adapter_test_profile,submission_manifest,key_lifecycle_policy",
                "--output",
                str(output_path),
                "--log-dir",
                str(log_dir),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        _assert("[ConformanceSuite] report:" in completed.stdout, "missing suite report output line")
        _assert(output_path.exists(), "suite report was not written")
        _assert(log_dir.exists(), "suite log directory was not written")

        report = _load_json(output_path)
        summary = report.get("summary") or {}
        checks = report.get("checks") or []
        _assert(summary.get("passed") is True, "conformance suite summary did not pass")
        _assert(summary.get("failedChecks") == 0, "conformance suite reported failures")
        _assert(len(checks) == 3, "conformance suite did not execute expected subset of checks")
        _assert(
            all(Path(item.get("stdoutLog", "")).exists() for item in checks),
            "one or more stdout log files are missing",
        )
        _assert(
            all(Path(item.get("stderrLog", "")).exists() for item in checks),
            "one or more stderr log files are missing",
        )

    print("Conformance suite orchestrator checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
