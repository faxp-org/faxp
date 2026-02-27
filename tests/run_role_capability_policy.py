#!/usr/bin/env python3
"""Validate role capability policy for posting and booking permissions."""

from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from faxp_mvp_simulation import _validate_route_policy  # noqa: E402


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _envelope(message_type: str, sender: str, receiver: str, body: dict | None = None) -> dict:
    return {
        "MessageType": message_type,
        "From": sender,
        "To": receiver,
        "Body": body or {},
    }


def _expect_allowed(message_type: str, sender: str, receiver: str, body: dict | None = None) -> None:
    _validate_route_policy(_envelope(message_type, sender, receiver, body))


def _expect_denied(
    message_type: str,
    sender: str,
    receiver: str,
    expected_substring: str,
    body: dict | None = None,
) -> None:
    try:
        _validate_route_policy(_envelope(message_type, sender, receiver, body))
    except ValueError as exc:
        _assert(
            expected_substring in str(exc),
            f"Expected error containing '{expected_substring}', got: {exc}",
        )
        return
    raise AssertionError(f"Expected ValueError for {message_type} {sender}->{receiver}")


def main() -> int:
    # Allowed matrix examples.
    _expect_allowed("NewLoad", "Shipper Agent", "Broker Agent")
    _expect_allowed("NewLoad", "Broker Agent", "Carrier Agent")
    _expect_allowed("NewTruck", "Carrier Agent", "Broker Agent")
    _expect_allowed("NewTruck", "Broker Agent", "Shipper Agent")
    _expect_allowed("LoadSearch", "Carrier Agent", "Broker Agent")
    _expect_allowed("LoadSearch", "Broker Agent", "Shipper Agent")
    _expect_allowed("TruckSearch", "Shipper Agent", "Carrier Agent")
    _expect_allowed("TruckSearch", "Broker Agent", "Carrier Agent")
    _expect_allowed(
        "BidRequest",
        "Carrier Agent",
        "Broker Agent",
        {"LoadID": "load-1"},
    )
    _expect_allowed(
        "BidRequest",
        "Shipper Agent",
        "Carrier Agent",
        {"TruckID": "truck-1"},
    )
    _expect_allowed(
        "BidRequest",
        "Broker Agent",
        "Carrier Agent",
        {"TruckID": "truck-2"},
    )

    # Denied sender capability examples.
    _expect_denied(
        "NewTruck",
        "Shipper Agent",
        "Broker Agent",
        "not allowed to post trucks",
    )
    _expect_denied(
        "NewLoad",
        "Carrier Agent",
        "Broker Agent",
        "not allowed to post loads",
    )
    _expect_denied(
        "LoadSearch",
        "Shipper Agent",
        "Broker Agent",
        "not allowed to search/book loads",
    )
    _expect_denied(
        "TruckSearch",
        "Carrier Agent",
        "Broker Agent",
        "not allowed to search/book trucks",
    )
    _expect_denied(
        "BidRequest",
        "Carrier Agent",
        "Broker Agent",
        "not allowed to book trucks",
        {"TruckID": "truck-3"},
    )
    _expect_denied(
        "BidRequest",
        "Shipper Agent",
        "Broker Agent",
        "not allowed to book loads",
        {"LoadID": "load-2"},
    )

    # Denied receiver capability examples.
    _expect_denied(
        "NewTruck",
        "Broker Agent",
        "Carrier Agent",
        "not allowed to receive posted trucks",
    )
    _expect_denied(
        "NewLoad",
        "Broker Agent",
        "Shipper Agent",
        "not allowed to receive posted loads",
    )
    _expect_denied(
        "TruckSearch",
        "Broker Agent",
        "Shipper Agent",
        "not allowed to respond to truck searches",
    )

    # Unknown sender/receiver inference must fail closed.
    _expect_denied(
        "NewLoad",
        "Unknown Agent",
        "Broker Agent",
        "Unknown sender role inferred",
    )
    _expect_denied(
        "NewLoad",
        "Broker Agent",
        "Unknown Agent",
        "Unknown receiver role inferred",
    )

    print("Role capability policy checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
