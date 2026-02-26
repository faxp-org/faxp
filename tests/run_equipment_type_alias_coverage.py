#!/usr/bin/env python3
"""Validate EquipmentType alias coverage profile alignment with runtime normalization maps."""

from __future__ import annotations

from pathlib import Path
import json
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from faxp_mvp_simulation import (  # noqa: E402
    EQUIPMENT_TYPE_CLASS_ALIASES,
    EQUIPMENT_TYPE_SUBCLASS_ALIASES,
    VALID_EQUIPMENT_CLASSES,
    VALID_EQUIPMENT_SUBCLASSES,
)


PROFILE_PATH = PROJECT_ROOT / "conformance" / "equipment_type_alias_coverage.v1.json"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    _assert(isinstance(payload, dict), f"{path.name} must contain a JSON object.")
    return payload


def _validate_alias_map(alias_map: dict, context: str) -> None:
    _assert(alias_map, f"{context} must be non-empty.")
    _assert(all(isinstance(k, str) and k for k in alias_map), f"{context} keys must be non-empty strings.")
    _assert(
        all(k == k.strip() and k == k.lower() and " " not in k for k in alias_map),
        f"{context} keys must be normalized lowercase tokens without spaces.",
    )
    _assert(all(isinstance(v, str) and v for v in alias_map.values()), f"{context} values must be strings.")


def main() -> int:
    profile = _load_json(PROFILE_PATH)

    for field in [
        "profileVersion",
        "profileId",
        "protocol",
        "description",
        "classAliasMap",
        "subclassAliasMap",
        "requiredTypoAliases",
        "conformanceRequirements",
    ]:
        _assert(field in profile, f"equipment type alias profile missing field: {field}")

    _assert(profile.get("protocol") == "FAXP", "protocol must be FAXP")
    _assert(
        profile.get("profileId") == "equipment-type-alias-coverage.v1",
        "profileId must be equipment-type-alias-coverage.v1",
    )

    class_alias_map = profile.get("classAliasMap") or {}
    subclass_alias_map = profile.get("subclassAliasMap") or {}
    _assert(isinstance(class_alias_map, dict), "classAliasMap must be an object.")
    _assert(isinstance(subclass_alias_map, dict), "subclassAliasMap must be an object.")
    _validate_alias_map(class_alias_map, "classAliasMap")
    _validate_alias_map(subclass_alias_map, "subclassAliasMap")

    _assert(
        class_alias_map == EQUIPMENT_TYPE_CLASS_ALIASES,
        "classAliasMap must match EQUIPMENT_TYPE_CLASS_ALIASES runtime constant",
    )
    _assert(
        subclass_alias_map == EQUIPMENT_TYPE_SUBCLASS_ALIASES,
        "subclassAliasMap must match EQUIPMENT_TYPE_SUBCLASS_ALIASES runtime constant",
    )

    invalid_classes = sorted(set(class_alias_map.values()) - set(VALID_EQUIPMENT_CLASSES))
    _assert(not invalid_classes, f"classAliasMap contains unsupported class targets: {invalid_classes}")
    invalid_subclasses = sorted(set(subclass_alias_map.values()) - set(VALID_EQUIPMENT_SUBCLASSES))
    _assert(
        not invalid_subclasses,
        f"subclassAliasMap contains unsupported subclass targets: {invalid_subclasses}",
    )

    typo_aliases = [str(item) for item in profile.get("requiredTypoAliases") or []]
    _assert(typo_aliases, "requiredTypoAliases must be non-empty.")
    for alias in typo_aliases:
        _assert(
            alias in class_alias_map or alias in subclass_alias_map,
            f"required typo alias missing from both maps: {alias}",
        )

    conformance_requirements = profile.get("conformanceRequirements") or {}
    required_tests = [str(item) for item in conformance_requirements.get("requiredTests") or []]
    required_checks = [str(item) for item in conformance_requirements.get("requiredSuiteChecks") or []]
    _assert(
        required_tests == ["tests/run_equipment_type_alias_coverage.py"],
        "requiredTests must include run_equipment_type_alias_coverage",
    )
    _assert(
        required_checks == ["equipment_type_alias_coverage"],
        "requiredSuiteChecks must include equipment_type_alias_coverage",
    )

    print("Equipment type alias coverage checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
