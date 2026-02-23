#!/usr/bin/env python3
"""Regression checks for rate model extensibility scaffolding."""

from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from faxp_mvp_simulation import (  # noqa: E402
    PLANNED_RATE_MODELS,
    RATE_MODEL_CATALOG,
    VALID_RATE_MODELS,
    build_rate,
    validate_message_body,
)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _expect_validation_error(message_type: str, body: dict, text: str) -> None:
    try:
        validate_message_body(message_type, body)
    except ValueError as exc:
        _assert(text in str(exc), f"expected '{text}' in error, got: {exc}")
        return
    raise AssertionError(f"{message_type} should fail validation with: {text}")


def main() -> int:
    _assert(
        VALID_RATE_MODELS == {"PerMile", "Flat"},
        "active executable rate models must remain PerMile and Flat.",
    )
    _assert(
        {"PerPallet", "CWT"}.issubset(PLANNED_RATE_MODELS),
        "planned future rate models should include PerPallet and CWT.",
    )
    _assert(
        RATE_MODEL_CATALOG.get("PerPallet", {}).get("status") == "planned",
        "PerPallet should be marked as planned.",
    )
    _assert(
        RATE_MODEL_CATALOG.get("CWT", {}).get("status") == "planned",
        "CWT should be marked as planned.",
    )

    # Backward-compatible active model with optional extension fields.
    per_mile_rate = build_rate(
        "PerMile",
        2.62,
        UnitBasis="mile",
        DistanceMiles=925.5,
        Quantity=1,
        LineHaulAmount=2100.0,
        FuelSurchargeAmount=180.0,
        FuelSurchargePercent=8.57,
        ReferenceID="lane-tx-ga-001",
        Notes="Reefer temp 34F requested.",
        Extensions={"MultiStopCount": 2, "InternalCode": "LH-2026-Q1"},
    )
    validate_message_body("BidRequest", {"LoadID": "load-123", "Rate": per_mile_rate})

    flat_rate = build_rate(
        "Flat",
        1950.0,
        UnitBasis="load",
        Quantity=1,
        Notes="Flat plus approved accessorials.",
    )
    validate_message_body("BidRequest", {"LoadID": "load-flat-123", "Rate": flat_rate})

    invalid_distance = dict(per_mile_rate)
    invalid_distance["DistanceMiles"] = -1
    _expect_validation_error("BidRequest", {"LoadID": "load-123", "Rate": invalid_distance}, "DistanceMiles")

    invalid_fuel_percent = dict(per_mile_rate)
    invalid_fuel_percent["FuelSurchargePercent"] = 120
    _expect_validation_error(
        "BidRequest",
        {"LoadID": "load-123", "Rate": invalid_fuel_percent},
        "FuelSurchargePercent",
    )

    invalid_extensions = dict(per_mile_rate)
    invalid_extensions["Extensions"] = ["not", "an", "object"]
    _expect_validation_error(
        "BidRequest",
        {"LoadID": "load-123", "Rate": invalid_extensions},
        "Extensions",
    )

    planned_model_rate = build_rate(
        "PerPallet",
        1200.0,
        UnitBasis="pallet",
        Quantity=26,
    )
    _expect_validation_error(
        "BidRequest",
        {"LoadID": "load-123", "Rate": planned_model_rate},
        "RateModel",
    )
    _expect_validation_error(
        "LoadSearch",
        {
            "OriginState": "TX",
            "DestinationState": "GA",
            "EquipmentType": "Reefer",
            "PickupDate": "2026-03-01",
            "RateModel": "PerPallet",
            "MaxRate": 2500.0,
        },
        "RateModel",
    )

    print("Rate model extensibility checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
