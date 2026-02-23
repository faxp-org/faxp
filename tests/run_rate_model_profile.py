#!/usr/bin/env python3
"""Validate rate model profile artifact alignment with runtime constants."""

from __future__ import annotations

from pathlib import Path
import json
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from faxp_mvp_simulation import (  # noqa: E402
    PLANNED_RATE_MODELS,
    RATE_MODEL_CATALOG,
    RATE_MODEL_REQUIREMENTS,
    VALID_RATE_MODELS,
)


PROFILE_PATH = PROJECT_ROOT / "conformance" / "rate_model_profile.v1.json"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    _assert(isinstance(payload, dict), f"{path.name} must contain a JSON object.")
    return payload


def _normalize_catalog(payload: dict) -> dict:
    normalized = {}
    for model, details in payload.items():
        _assert(isinstance(details, dict), f"catalog entry for {model} must be an object")
        normalized[str(model)] = {
            "status": str(details.get("status") or "").strip(),
            "unitBasis": str(details.get("unitBasis") or "").strip(),
        }
    return normalized


def _normalize_requirements(payload: dict) -> dict:
    normalized = {}
    for model, details in payload.items():
        _assert(isinstance(details, dict), f"requirements entry for {model} must be an object")
        normalized[str(model)] = {
            "requiredFields": [str(item) for item in details.get("requiredFields") or []],
            "allowedUnitBasis": [str(item) for item in details.get("allowedUnitBasis") or []],
            "status": str(details.get("status") or "").strip(),
        }
    return normalized


def main() -> int:
    profile = _load_json(PROFILE_PATH)
    _assert(profile.get("protocol") == "FAXP", "rate model profile protocol must be FAXP")
    _assert(str(profile.get("profileVersion") or "").strip(), "profileVersion must be non-empty")

    active_models = [str(item) for item in profile.get("activeRateModels") or []]
    planned_models = [str(item) for item in profile.get("plannedRateModels") or []]
    _assert(active_models, "activeRateModels must be non-empty")
    _assert(planned_models, "plannedRateModels must be non-empty")
    _assert(
        len(active_models) == len(set(active_models)),
        "activeRateModels must not contain duplicates",
    )
    _assert(
        len(planned_models) == len(set(planned_models)),
        "plannedRateModels must not contain duplicates",
    )
    _assert(
        set(active_models) == set(VALID_RATE_MODELS),
        "activeRateModels must match VALID_RATE_MODELS",
    )
    _assert(
        set(planned_models) == set(PLANNED_RATE_MODELS),
        "plannedRateModels must match PLANNED_RATE_MODELS",
    )

    profile_catalog = _normalize_catalog(profile.get("rateModelCatalog") or {})
    runtime_catalog = _normalize_catalog(RATE_MODEL_CATALOG)
    _assert(profile_catalog == runtime_catalog, "rateModelCatalog drift versus runtime constants")

    profile_requirements = _normalize_requirements(profile.get("rateModelRequirements") or {})
    runtime_requirements = _normalize_requirements(RATE_MODEL_REQUIREMENTS)
    _assert(
        profile_requirements == runtime_requirements,
        "rateModelRequirements drift versus runtime constants",
    )

    for model in active_models:
        details = profile_requirements.get(model) or {}
        _assert(details.get("status") == "active", f"{model} requirements must be active")
        _assert(
            "UnitBasis" in details.get("requiredFields", []),
            f"{model} requirements must include UnitBasis",
        )
        unit_basis = (profile_catalog.get(model) or {}).get("unitBasis")
        _assert(
            unit_basis in details.get("allowedUnitBasis", []),
            f"{model} allowedUnitBasis should include catalog unitBasis",
        )

    search_requirements = profile.get("searchRequirements") or {}
    for message_type in ["LoadSearch", "TruckSearch"]:
        details = search_requirements.get(message_type) or {}
        _assert(
            bool(details.get("enforceModelRequirements")),
            f"searchRequirements.{message_type}.enforceModelRequirements must be true",
        )

    print("Rate model profile checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
