#!/usr/bin/env python3
"""Validate booking-plane commercial terms governance documentation and backlog linkage."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "governance" / "BOOKING_PLANE_COMMERCIAL_TERMS.md"
COMMERCIAL_BACKLOG_PATH = PROJECT_ROOT / "docs" / "roadmap" / "V0_3_0_COMMERCIAL_MODEL_BACKLOG.md"
RFC_BACKLOG_PATH = PROJECT_ROOT / "docs" / "roadmap" / "V0_3_0_RFC_BACKLOG.md"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _contains_all(text: str, required: list[str], context: str) -> None:
    missing = [item for item in required if item not in text]
    _assert(not missing, f"{context} missing required text: {missing}")


def main() -> int:
    _assert(DOC_PATH.exists(), "BOOKING_PLANE_COMMERCIAL_TERMS.md is missing")
    _assert(COMMERCIAL_BACKLOG_PATH.exists(), "V0_3_0_COMMERCIAL_MODEL_BACKLOG.md is missing")
    _assert(RFC_BACKLOG_PATH.exists(), "V0_3_0_RFC_BACKLOG.md is missing")

    doc_text = DOC_PATH.read_text(encoding="utf-8")
    _contains_all(
        doc_text,
        [
            "In Scope (Protocol Core)",
            "Out of Scope (Protocol Core)",
            "PricingMode",
            "PayerParty",
            "PayeeParty",
            "CapAmount",
            "SpecialInstructions",
            "ScheduleAcceptance",
            "PassThrough",
            "Reimbursable",
            "Settlement and payment execution",
            "POD/BOL",
            "FAXP-OPS",
        ],
        "BOOKING_PLANE_COMMERCIAL_TERMS.md",
    )

    commercial_backlog = COMMERCIAL_BACKLOG_PATH.read_text(encoding="utf-8")
    _contains_all(
        commercial_backlog,
        [
            "Scope-Lock Baseline (Commercial Terms)",
            "Booking-plane accessorial/addendum contract baseline",
            "Operations-plane communications track (`FAXP-OPS`) governance placeholder",
        ],
        "V0_3_0_COMMERCIAL_MODEL_BACKLOG.md",
    )

    rfc_backlog = RFC_BACKLOG_PATH.read_text(encoding="utf-8")
    _contains_all(
        rfc_backlog,
        [
            "Operations-plane agent messaging profile (`FAXP-OPS`)",
            "scope expansions",
        ],
        "V0_3_0_RFC_BACKLOG.md",
    )

    print("Booking-plane commercial terms documentation checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
