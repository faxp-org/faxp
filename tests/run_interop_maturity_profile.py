#!/usr/bin/env python3
"""Validate interop maturity profile artifact and alignment with current A2A/MCP evidence."""

from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = PROJECT_ROOT / "conformance" / "interop_maturity_profile.v1.json"
CONFORMANCE_SUITE_PATH = PROJECT_ROOT / "conformance" / "run_all_checks.py"


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

    for field in [
        "profileVersion",
        "profileId",
        "protocol",
        "scope",
        "tracks",
        "maturityLevels",
        "governanceRules",
        "certificationMapping",
        "conformanceRequirements",
    ]:
        _assert(field in profile, f"interop maturity profile missing field: {field}")

    _assert(profile["protocol"] == "FAXP", "interop maturity profile protocol must be FAXP")

    tracks = profile.get("tracks") or {}
    _assert(set(tracks.keys()) == {"A2A", "MCP"}, "tracks must contain exactly A2A and MCP")

    expected_track_requirements = {
        "A2A": {
            "artifacts": {
                "docs/interop/A2A_COMPATIBILITY_PROFILE.md",
                "conformance/a2a_translator_contract.json",
                "conformance/a2a_roundtrip_fixtures.json",
                "docs/interop/A2A_UPSTREAM_TRACKING.json",
                ".github/workflows/a2a-watch.yml",
            },
            "tests": {
                "tests/run_a2a_profile_check.py",
                "tests/run_a2a_roundtrip_translation.py",
                "tests/run_a2a_watch_artifacts.py",
            },
            "checks": {"a2a_profile", "a2a_roundtrip", "a2a_watch_artifacts"},
        },
        "MCP": {
            "artifacts": {
                "docs/interop/MCP_COMPATIBILITY_PROFILE.md",
                "conformance/mcp_tooling_contract.json",
                "docs/interop/MCP_UPSTREAM_TRACKING.json",
                ".github/workflows/mcp-watch.yml",
            },
            "tests": {
                "tests/run_mcp_profile_check.py",
                "tests/run_mcp_watch_artifacts.py",
            },
            "checks": {"mcp_profile", "mcp_watch_artifacts"},
        },
    }

    for track_name, expected in expected_track_requirements.items():
        track = tracks.get(track_name) or {}
        _assert(
            bool(track.get("hostingModel")) and str(track.get("hostingModel")) == "BuilderHosted",
            f"{track_name} hostingModel must be BuilderHosted",
        )
        _assert(
            track.get("coreProtocolChangesRequired") is False,
            f"{track_name} coreProtocolChangesRequired must be false",
        )
        for rel_path in expected["artifacts"]:
            _assert(rel_path in (track.get("requiredArtifacts") or []), f"{track_name} missing artifact {rel_path}")
            _assert((PROJECT_ROOT / rel_path).exists(), f"{track_name} artifact missing from repo: {rel_path}")
        for rel_path in expected["tests"]:
            _assert(rel_path in (track.get("requiredTests") or []), f"{track_name} missing test {rel_path}")
            _assert((PROJECT_ROOT / rel_path).exists(), f"{track_name} test missing from repo: {rel_path}")
        check_names = {str(item) for item in track.get("requiredSuiteChecks") or []}
        _assert(check_names == expected["checks"], f"{track_name} requiredSuiteChecks mismatch")

    maturity_levels = profile.get("maturityLevels") or {}
    _assert(
        list(maturity_levels.keys()) == ["L1-Declared", "L2-Tested", "L3-Watched", "L4-Certifiable"],
        "maturityLevels must preserve the canonical order L1->L4",
    )

    rules = profile.get("governanceRules") or {}
    for field in [
        "optionalInteropOnly",
        "noMandatoryA2AMcpDependencyInCore",
        "maturityClaimsMustBeEvidenceBacked",
        "watchFailuresRequireGovernanceFollowup",
    ]:
        _assert(rules.get(field) is True, f"governanceRules.{field} must be true")

    certification = profile.get("certificationMapping") or {}
    _assert(
        certification.get("representedInRegistryEntries") is False,
        "certificationMapping.representedInRegistryEntries must be false",
    )
    _assert(
        certification.get("inferredFromEvidenceBundle") is True,
        "certificationMapping.inferredFromEvidenceBundle must be true",
    )
    _assert(
        int(certification.get("minimumReviewCadenceDaysForL3Watched") or 0) == 30,
        "minimumReviewCadenceDaysForL3Watched must be 30",
    )
    _assert(
        certification.get("l4RequiresInteropIncidentDrillEvidence") is False,
        "l4RequiresInteropIncidentDrillEvidence must be false for v0.3",
    )

    conformance = profile.get("conformanceRequirements") or {}
    required_tests = {str(item) for item in conformance.get("requiredTests") or []}
    required_checks = {str(item) for item in conformance.get("requiredSuiteChecks") or []}
    _assert(
        required_tests == {"tests/run_interop_maturity_profile.py"},
        "interop maturity profile must self-reference its required test",
    )
    _assert(
        required_checks == {"interop_maturity_profile"},
        "interop maturity profile must require suite check interop_maturity_profile",
    )

    listed_checks_run = subprocess.run(
        [sys.executable, str(CONFORMANCE_SUITE_PATH), "--list-checks"],
        check=True,
        capture_output=True,
        text=True,
    )
    listed_checks = {line.strip() for line in listed_checks_run.stdout.splitlines() if line.strip()}
    _assert("interop_maturity_profile" in listed_checks, "run_all_checks.py missing interop_maturity_profile")

    print("Interop maturity profile checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
