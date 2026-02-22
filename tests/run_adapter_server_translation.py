#!/usr/bin/env python3
"""Regression checks for adapter server translator integration."""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import fmcsa_adapter_server as adapter_server  # noqa: E402


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    ok_result = {
        "ok": True,
        "status": "Success",
        "score": 93,
        "mc_number": "498282",
        "usdot_number": 1292301,
        "carrier_name": "CA FREIGHT XPRESS INC",
        "operating_status": "ACTIVE",
        "has_current_insurance": True,
        "interstate_authority_ok": True,
    }
    ok_payload = adapter_server._normalize_live_result_to_neutral_payload(  # noqa: SLF001
        ok_result,
        requested_mc="498282",
    )
    _assert(ok_payload["ok"] is True, "ok payload should preserve ok=true")
    _assert("VerificationResult" in ok_payload, "missing VerificationResult")
    _assert("ProviderExtensions" in ok_payload, "missing ProviderExtensions")
    _assert(
        ok_payload["VerificationResult"]["provider"] == adapter_server.ADAPTER_PROVIDER_ID,
        "provider ID should match adapter provider ID configuration",
    )
    _assert(
        ok_payload["ProviderExtensions"]["mcNumber"] == "498282",
        "provider extension mcNumber mismatch",
    )

    fail_result = {
        "ok": False,
        "error": "live-fmcsa query failed: upstream timeout",
        "mc_number": "498282",
    }
    fail_payload = adapter_server._normalize_live_result_to_neutral_payload(  # noqa: SLF001
        fail_result,
        requested_mc="498282",
    )
    _assert(fail_payload["ok"] is False, "fail payload should preserve ok=false")
    _assert(fail_payload["VerificationResult"]["status"] == "Fail", "fail status mismatch")
    _assert("error" in fail_payload, "fail payload should include top-level error")
    _assert(
        "error" in fail_payload["ProviderExtensions"],
        "fail payload should include provider extension error",
    )

    print("Adapter server translator integration checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
