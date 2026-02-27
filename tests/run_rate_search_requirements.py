#!/usr/bin/env python3
"""Regression checks for rate-model requirements on search filters."""

from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from faxp_mvp_simulation import (  # noqa: E402
    BrokerAgent,
    CarrierAgent,
    default_search_max,
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
    carrier = CarrierAgent("Carrier Agent")
    broker = BrokerAgent("Broker Agent")

    valid_load_search = carrier.create_load_search(force_no_match=False, rate_model="PerMile")
    validate_message_body("LoadSearch", valid_load_search)

    valid_truck_search = broker.create_truck_search(rate_model="Flat")
    validate_message_body("TruckSearch", valid_truck_search)

    valid_pallet_search = carrier.create_load_search(force_no_match=False, rate_model="PerPallet")
    validate_message_body("LoadSearch", valid_pallet_search)

    valid_cwt_truck_search = broker.create_truck_search(rate_model="CWT")
    validate_message_body("TruckSearch", valid_cwt_truck_search)

    valid_per_hour_search = carrier.create_load_search(force_no_match=False, rate_model="PerHour")
    validate_message_body("LoadSearch", valid_per_hour_search)

    valid_lane_min_truck_search = broker.create_truck_search(rate_model="LaneMinimum")
    validate_message_body("TruckSearch", valid_lane_min_truck_search)

    missing_basis_load = {
        "OriginState": "TX",
        "DestinationState": "GA",
        "EquipmentType": "Reefer",
        "PickupDate": "2026-03-01",
        "RateModel": "PerMile",
        "MaxRate": default_search_max("PerMile"),
    }
    _expect_validation_error(
        "LoadSearch",
        missing_basis_load,
        "LoadSearch.UnitBasis is required for RateModel 'PerMile'",
    )

    invalid_basis_load = dict(missing_basis_load)
    invalid_basis_load["UnitBasis"] = "load"
    _expect_validation_error(
        "LoadSearch",
        invalid_basis_load,
        "LoadSearch.UnitBasis must be one of ['mile']",
    )

    missing_basis_truck = {
        "LocationRadiusMiles": 120,
        "OriginState": "TX",
        "EquipmentType": "Reefer",
        "AvailableFrom": "2026-03-01",
        "AvailableTo": "2026-03-02",
        "RateModel": "Flat",
        "MinRate": 1800.0,
        "MaxRate": 2200.0,
    }
    _expect_validation_error(
        "TruckSearch",
        missing_basis_truck,
        "TruckSearch.UnitBasis is required for RateModel 'Flat'",
    )

    invalid_basis_truck = dict(missing_basis_truck)
    invalid_basis_truck["UnitBasis"] = "mile"
    _expect_validation_error(
        "TruckSearch",
        invalid_basis_truck,
        "TruckSearch.UnitBasis must be one of ['load']",
    )

    missing_basis_pallet_load = {
        "OriginState": "TX",
        "DestinationState": "GA",
        "EquipmentType": "Reefer",
        "PickupDate": "2026-03-01",
        "RateModel": "PerPallet",
        "MaxRate": default_search_max("PerPallet"),
    }
    _expect_validation_error(
        "LoadSearch",
        missing_basis_pallet_load,
        "LoadSearch.UnitBasis is required for RateModel 'PerPallet'",
    )

    invalid_basis_cwt_truck = {
        "LocationRadiusMiles": 120,
        "OriginState": "TX",
        "EquipmentType": "Reefer",
        "AvailableFrom": "2026-03-01",
        "AvailableTo": "2026-03-02",
        "RateModel": "CWT",
        "UnitBasis": "mile",
        "MinRate": 4.8,
        "MaxRate": 6.0,
    }
    _expect_validation_error(
        "TruckSearch",
        invalid_basis_cwt_truck,
        "TruckSearch.UnitBasis must be one of ['cwt']",
    )

    invalid_basis_per_hour_load = {
        "OriginState": "TX",
        "DestinationState": "GA",
        "EquipmentType": "Reefer",
        "PickupDate": "2026-03-01",
        "RateModel": "PerHour",
        "UnitBasis": "mile",
        "MaxRate": default_search_max("PerHour"),
    }
    _expect_validation_error(
        "LoadSearch",
        invalid_basis_per_hour_load,
        "LoadSearch.UnitBasis must be one of ['hour']",
    )

    invalid_basis_lane_min_truck = {
        "LocationRadiusMiles": 120,
        "OriginState": "TX",
        "EquipmentType": "Reefer",
        "AvailableFrom": "2026-03-01",
        "AvailableTo": "2026-03-02",
        "RateModel": "LaneMinimum",
        "UnitBasis": "load",
        "MinRate": 1800.0,
        "MaxRate": 2200.0,
    }
    _expect_validation_error(
        "TruckSearch",
        invalid_basis_lane_min_truck,
        "TruckSearch.UnitBasis must be one of ['lane']",
    )

    print("Rate search requirement checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
