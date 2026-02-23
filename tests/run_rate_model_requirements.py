#!/usr/bin/env python3
"""Regression checks for active rate model requirement enforcement."""

from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from faxp_mvp_simulation import (  # noqa: E402
    RATE_MODEL_REQUIREMENTS,
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
    per_mile_req = RATE_MODEL_REQUIREMENTS.get("PerMile") or {}
    flat_req = RATE_MODEL_REQUIREMENTS.get("Flat") or {}
    _assert(per_mile_req.get("status") == "active", "PerMile requirements must be active.")
    _assert(flat_req.get("status") == "active", "Flat requirements must be active.")
    _assert("UnitBasis" in (per_mile_req.get("requiredFields") or []), "PerMile must require UnitBasis.")
    _assert("UnitBasis" in (flat_req.get("requiredFields") or []), "Flat must require UnitBasis.")

    valid_per_mile = build_rate("PerMile", 2.62)
    validate_message_body("BidRequest", {"LoadID": "load-permile-ok", "Rate": valid_per_mile})

    valid_flat = build_rate("Flat", 1950.0)
    validate_message_body("BidRequest", {"LoadID": "load-flat-ok", "Rate": valid_flat})

    missing_unit_basis = {"RateModel": "PerMile", "Amount": 2.62, "Currency": "USD"}
    _expect_validation_error(
        "BidRequest",
        {"LoadID": "load-permile-missing-unit", "Rate": missing_unit_basis},
        "UnitBasis is required for RateModel 'PerMile'",
    )

    invalid_per_mile_basis = build_rate("PerMile", 2.62, UnitBasis="load")
    _expect_validation_error(
        "BidRequest",
        {"LoadID": "load-permile-bad-basis", "Rate": invalid_per_mile_basis},
        "UnitBasis must be one of ['mile']",
    )

    invalid_flat_basis = build_rate("Flat", 1950.0, UnitBasis="mile")
    _expect_validation_error(
        "BidRequest",
        {"LoadID": "load-flat-bad-basis", "Rate": invalid_flat_basis},
        "UnitBasis must be one of ['load']",
    )

    print("Rate model requirement checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
