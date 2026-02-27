#!/usr/bin/env python3
"""Validate minimal shipper orchestration profile alignment with runtime and governance scope."""

from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from faxp_mvp_simulation import ROLE_CAPABILITIES  # noqa: E402


PROFILE_PATH = PROJECT_ROOT / "conformance" / "shipper_orchestration_profile.v1.json"
SCOPE_PATH = PROJECT_ROOT / "docs" / "governance" / "SCOPE_GUARDRAILS.md"
RFC_PATH = PROJECT_ROOT / "docs" / "rfc" / "RFC-v0.3-shipper-orchestration-minimal.md"
SIMULATION_PATH = PROJECT_ROOT / "faxp_mvp_simulation.py"
CONFORMANCE_SUITE_PATH = PROJECT_ROOT / "conformance" / "run_all_checks.py"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    _assert(isinstance(payload, dict), f"{path.name} must contain a JSON object.")
    return payload


def _camelize_capabilities(role_capabilities: dict[str, dict[str, bool]]) -> dict[str, dict[str, bool]]:
    return {
        role: {
            "postLoad": bool(values.get("post_load", False)),
            "postTruck": bool(values.get("post_truck", False)),
            "bookLoad": bool(values.get("book_load", False)),
            "bookTruck": bool(values.get("book_truck", False)),
        }
        for role, values in role_capabilities.items()
    }


def main() -> int:
    profile = _load_json(PROFILE_PATH)

    for field in [
        "profileVersion",
        "profileId",
        "protocol",
        "scope",
        "description",
        "actors",
        "capabilityMatrix",
        "messageFlow",
        "normativeConstraints",
        "conformanceRequirements",
    ]:
        _assert(field in profile, f"shipper orchestration profile missing field: {field}")

    _assert(profile["protocol"] == "FAXP", "protocol must be FAXP")
    _assert(
        profile["scope"] == "booking-plane-orchestration",
        "scope must be booking-plane-orchestration",
    )
    _assert(
        set(profile.get("actors") or []) == {"Shipper", "Broker", "Carrier"},
        "actors must be exactly Shipper/Broker/Carrier",
    )

    expected_matrix = _camelize_capabilities(ROLE_CAPABILITIES)
    _assert(
        profile.get("capabilityMatrix") == expected_matrix,
        "capabilityMatrix must match ROLE_CAPABILITIES runtime constant",
    )

    message_flow = profile.get("messageFlow") or {}
    _assert(
        set(message_flow.get("requiredMessageTypes") or [])
        == {"NewLoad", "LoadSearch", "BidRequest", "BidResponse", "ExecutionReport", "AmendRequest"},
        "messageFlow.requiredMessageTypes drifted from runtime contract",
    )
    _assert(
        bool(message_flow.get("noNewMessageTypesRequired")) is True,
        "messageFlow.noNewMessageTypesRequired must be true",
    )
    _assert(
        bool(message_flow.get("defaultFlowRetained")) is True,
        "messageFlow.defaultFlowRetained must be true",
    )
    _assert(
        str(message_flow.get("optionalEntryPointFlag") or "") == "--shipper-flow",
        "messageFlow.optionalEntryPointFlag must be --shipper-flow",
    )

    constraints = profile.get("normativeConstraints") or {}
    for key in [
        "senderAndReceiverCapabilityChecksRequired",
        "shipperFlowMustBeOptional",
        "defaultBrokerOriginFlowMustRemain",
        "verificationPolicyPathUnchanged",
        "operationsAndSettlementOutOfScope",
    ]:
        _assert(constraints.get(key) is True, f"normativeConstraints.{key} must be true")

    conformance_requirements = profile.get("conformanceRequirements") or {}
    required_tests = [str(item) for item in conformance_requirements.get("requiredTests") or []]
    required_checks = [str(item) for item in conformance_requirements.get("requiredSuiteChecks") or []]
    _assert(
        set(required_tests)
        == {
            "tests/run_role_capability_policy.py",
            "tests/run_shipper_orchestration_minimal.py",
            "tests/run_shipper_orchestration_profile.py",
        },
        "requiredTests must include role/capability, minimal flow, and profile checks",
    )
    _assert(
        set(required_checks)
        == {"role_capability_policy", "shipper_orchestration_minimal", "shipper_orchestration_profile"},
        "requiredSuiteChecks must include role/minimal/profile checks",
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
        "booking-plane protocol" in scope_doc,
        "scope guardrails must keep orchestration in booking-plane boundary",
    )
    _assert(RFC_PATH.exists(), "shipper orchestration RFC is missing")

    simulation_source = SIMULATION_PATH.read_text(encoding="utf-8")
    _assert(
        "--shipper-flow" in simulation_source,
        "simulation must include --shipper-flow CLI flag",
    )
    _assert(
        "def run_shipper_load_flow" in simulation_source,
        "simulation must include run_shipper_load_flow implementation",
    )

    print("Shipper orchestration profile checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
