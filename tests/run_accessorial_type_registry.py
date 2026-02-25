#!/usr/bin/env python3
"""Validate canonical accessorial type registry profile alignment with runtime constants."""

from __future__ import annotations

from pathlib import Path
import json
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from faxp_mvp_simulation import (  # noqa: E402
    ACCESSORIAL_TYPE_CATALOG,
    ACTIVE_ACCESSORIAL_TYPES,
    BrokerAgent,
    CarrierAgent,
    PLANNED_ACCESSORIAL_TYPES,
    ShipperAgent,
)


PROFILE_PATH = PROJECT_ROOT / "conformance" / "accessorial_type_registry.v1.json"


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
        "activeTypes",
        "plannedTypes",
        "changePolicy",
        "conformanceRequirements",
    ]:
        _assert(field in profile, f"accessorial type registry profile missing field: {field}")

    _assert(profile.get("protocol") == "FAXP", "protocol must be FAXP")

    active_types = [str(item) for item in profile.get("activeTypes") or []]
    planned_types = [str(item) for item in profile.get("plannedTypes") or []]
    _assert(active_types, "activeTypes must be non-empty")
    _assert(planned_types, "plannedTypes must be non-empty")
    _assert(len(active_types) == len(set(active_types)), "activeTypes must not contain duplicates")
    _assert(len(planned_types) == len(set(planned_types)), "plannedTypes must not contain duplicates")
    _assert(
        not set(active_types).intersection(planned_types),
        "activeTypes and plannedTypes must not overlap",
    )

    _assert(
        set(active_types) == set(ACTIVE_ACCESSORIAL_TYPES),
        "activeTypes must match ACTIVE_ACCESSORIAL_TYPES runtime constant",
    )
    _assert(
        set(planned_types) == set(PLANNED_ACCESSORIAL_TYPES),
        "plannedTypes must match PLANNED_ACCESSORIAL_TYPES runtime constant",
    )

    catalog_keys = set(ACCESSORIAL_TYPE_CATALOG.keys())
    _assert(
        catalog_keys == set(active_types).union(planned_types),
        "ACCESSORIAL_TYPE_CATALOG keys must match active+planned profile types",
    )

    change_policy = profile.get("changePolicy") or {}
    _assert(
        change_policy.get("requireProfileUpdateBeforeRuntimeUse") is True,
        "changePolicy.requireProfileUpdateBeforeRuntimeUse must be true",
    )
    _assert(
        change_policy.get("allowUnknownTypesInRuntime") is False,
        "changePolicy.allowUnknownTypesInRuntime must be false",
    )

    conformance_requirements = profile.get("conformanceRequirements") or {}
    required_tests = [str(item) for item in conformance_requirements.get("requiredTests") or []]
    required_checks = [str(item) for item in conformance_requirements.get("requiredSuiteChecks") or []]
    _assert(
        required_tests == ["tests/run_accessorial_type_registry.py"],
        "conformanceRequirements.requiredTests must include run_accessorial_type_registry",
    )
    _assert(
        required_checks == ["accessorial_type_registry"],
        "conformanceRequirements.requiredSuiteChecks must include accessorial_type_registry",
    )

    # Runtime default payloads must only emit active canonical types.
    broker_load_types = set(BrokerAgent("Broker Agent").post_new_load()["AccessorialPolicy"]["AllowedTypes"])
    shipper_tender_types = set(ShipperAgent("Shipper Agent").post_tender()["AccessorialPolicy"]["AllowedTypes"])
    bid_accept_types = set(
        (CarrierAgent("Carrier Agent").create_bid_request(BrokerAgent("Broker Agent").post_new_load())["AccessorialPolicyAcceptance"]["AllowedTypes"])
    )

    expected_active = set(active_types)
    _assert(broker_load_types == expected_active, "BrokerAgent default accessorial types must match active profile types")
    _assert(shipper_tender_types == expected_active, "ShipperAgent default accessorial types must match active profile types")
    _assert(bid_accept_types == expected_active, "CarrierAgent acceptance types must match active profile types")

    print("Accessorial type registry checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
