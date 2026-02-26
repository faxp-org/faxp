#!/usr/bin/env python3
"""Validate multi-stop commercial-terms profile alignment with runtime and governance scope."""

from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from faxp_mvp_simulation import VALID_STOP_TYPES  # noqa: E402


PROFILE_PATH = PROJECT_ROOT / "conformance" / "multi_stop_terms_profile.v1.json"
SCOPE_PATH = PROJECT_ROOT / "docs" / "governance" / "SCOPE_GUARDRAILS.md"
COMMERCIAL_TERMS_DOC_PATH = PROJECT_ROOT / "docs" / "governance" / "BOOKING_PLANE_COMMERCIAL_TERMS.md"
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
        "stopTypes",
        "newLoadTerms",
        "loadSearchTerms",
        "bidRequestTerms",
        "normativeConstraints",
        "conformanceRequirements",
    ]:
        _assert(field in profile, f"multi-stop profile missing field: {field}")

    _assert(profile["protocol"] == "FAXP", "multi-stop profile protocol must be FAXP")
    _assert(
        profile["scope"] == "booking-plane-commercial-terms",
        "multi-stop profile scope must be booking-plane-commercial-terms",
    )
    _assert(
        set(profile.get("stopTypes") or []) == set(VALID_STOP_TYPES),
        "stopTypes must match VALID_STOP_TYPES",
    )

    new_load_terms = profile.get("newLoadTerms") or {}
    _assert(new_load_terms.get("field") == "Stops", "newLoadTerms.field must be Stops")
    _assert(
        set(new_load_terms.get("requiredStopFields") or []) == {"StopSequence", "StopType", "Location"},
        "newLoadTerms.requiredStopFields drifted from runtime contract",
    )
    _assert(int(new_load_terms.get("minStops") or 0) == 2, "newLoadTerms.minStops must equal 2")

    load_search_terms = profile.get("loadSearchTerms") or {}
    _assert(
        set(load_search_terms.get("optionalFields") or [])
        == {"RequireMultiStop", "StopCountMin", "StopCountMax", "RequiredStopTypes"},
        "loadSearchTerms.optionalFields drifted from runtime contract",
    )

    bid_terms = profile.get("bidRequestTerms") or {}
    _assert(bid_terms.get("field") == "StopPlanAcceptance", "bidRequestTerms.field must be StopPlanAcceptance")
    _assert(
        set(bid_terms.get("requiredFields") or []) == {"Accepted"},
        "bidRequestTerms.requiredFields must include only Accepted",
    )

    constraints = profile.get("normativeConstraints") or {}
    for key in [
        "orderedStopsRequiredWhenProvided",
        "firstStopMustMatchOrigin",
        "lastStopMustMatchDestination",
        "pickupAndDropRequired",
        "singleStopCompatibilityRetained",
        "stopPlanMismatchMayCounter",
        "dispatchTrackingOutOfScope",
    ]:
        _assert(constraints.get(key) is True, f"normativeConstraints.{key} must be true")

    conformance_requirements = profile.get("conformanceRequirements") or {}
    required_tests = [str(item) for item in conformance_requirements.get("requiredTests") or []]
    required_checks = [str(item) for item in conformance_requirements.get("requiredSuiteChecks") or []]
    _assert(
        set(required_tests) == {"tests/run_multi_stop_terms.py", "tests/run_multi_stop_terms_profile.py"},
        "requiredTests must include multi-stop runtime + profile checks",
    )
    _assert(
        set(required_checks) == {"multi_stop_terms", "multi_stop_terms_profile"},
        "requiredSuiteChecks must include multi_stop_terms and multi_stop_terms_profile",
    )

    for rel_path in required_tests:
        _assert((PROJECT_ROOT / rel_path).exists(), f"required test not found: {rel_path}")

    listed_checks_run = subprocess.run(
        [sys.executable, str(CONFORMANCE_SUITE_PATH), "--list-checks"],
        check=True,
        capture_output=True,
        text=True,
    )
    listed_checks = set(line.strip() for line in listed_checks_run.stdout.splitlines() if line.strip())
    for check_name in required_checks:
        _assert(check_name in listed_checks, f"missing suite check from run_all_checks.py: {check_name}")

    scope_doc = SCOPE_PATH.read_text(encoding="utf-8")
    _assert(
        "stop-level dispatch updates" in scope_doc,
        "scope guardrails must keep stop-level dispatch updates out of scope",
    )
    commercial_doc = COMMERCIAL_TERMS_DOC_PATH.read_text(encoding="utf-8")
    _assert(
        "Multi-stop terms are booking-plane commercial commitments" in commercial_doc,
        "booking-plane commercial terms doc must include multi-stop guidance",
    )

    print("Multi-stop terms profile checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
