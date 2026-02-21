#!/usr/bin/env python3
"""Pure state helpers for Streamlit sidebar preset behavior."""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping


def build_quick_presets(default_per_mile_bid: float) -> dict[str, dict[str, Any]]:
    return {
        "FMCSA live (MC 498282)": {
            "provider": "FMCSA",
            "rate_model": "PerMile",
            "bid_amount": float(default_per_mile_bid),
            "response_type": "Accept",
            "verification_status": "Success",
            "no_match": False,
            "mc_number": "498282",
            "fmcsa_source_local": "live-fmcsa",
            "fmcsa_source_cloud": "live-fmcsa",
        },
        "FMCSA authority-mock": {
            "provider": "FMCSA",
            "rate_model": "PerMile",
            "bid_amount": float(default_per_mile_bid),
            "response_type": "Accept",
            "verification_status": "Success",
            "no_match": False,
            "mc_number": "498282",
            "fmcsa_source_local": "carrier-finder",
            "fmcsa_source_cloud": "authority-mock",
        },
        "MockBiometric success": {
            "provider": "MockBiometricProvider",
            "rate_model": "PerMile",
            "bid_amount": float(default_per_mile_bid),
            "response_type": "Accept",
            "verification_status": "Success",
            "no_match": False,
            "mc_number": "",
        },
        "Forced fail demo": {
            "provider": "MockBiometricProvider",
            "rate_model": "PerMile",
            "bid_amount": float(default_per_mile_bid),
            "response_type": "Accept",
            "verification_status": "Fail",
            "no_match": False,
            "mc_number": "",
        },
    }


def default_sidebar_state(default_per_mile_bid: float) -> dict[str, Any]:
    return {
        "quick_preset_select": "MockBiometric success",
        "rate_model_select": "PerMile",
        "bid_amount_input": float(default_per_mile_bid),
        "response_type_select": "Accept",
        "provider_local_select": "FMCSA",
        "provider_cloud_select": "MockBiometricProvider",
        "fmcsa_source_select_local": "carrier-finder",
        "fmcsa_source_select_cloud": "authority-mock",
        "mc_number_input": "498282",
        "verification_status_select": "Success",
        "no_match_checkbox": False,
    }


def ensure_state_defaults(
    state: MutableMapping[str, Any], defaults: Mapping[str, Any]
) -> None:
    for key, value in defaults.items():
        if key not in state:
            state[key] = value


def apply_preset_to_state(
    state: MutableMapping[str, Any],
    presets: Mapping[str, Mapping[str, Any]],
    preset_name: str,
    *,
    live_fmcsa_configured: bool,
) -> None:
    preset = presets.get(preset_name)
    if not preset:
        return

    state["rate_model_select"] = preset["rate_model"]
    state["bid_amount_input"] = float(preset["bid_amount"])
    state["response_type_select"] = preset["response_type"]
    state["verification_status_select"] = preset["verification_status"]
    state["no_match_checkbox"] = bool(preset["no_match"])
    state["mc_number_input"] = str(preset.get("mc_number", ""))

    provider = preset["provider"]
    if provider == "FMCSA":
        state["provider_local_select"] = "FMCSA"
        state["provider_cloud_select"] = "FMCSA (Authority)"
        state["fmcsa_source_select_local"] = preset.get(
            "fmcsa_source_local", "carrier-finder"
        )
        cloud_source = preset.get("fmcsa_source_cloud", "authority-mock")
        if cloud_source == "live-fmcsa" and not live_fmcsa_configured:
            cloud_source = "authority-mock"
        state["fmcsa_source_select_cloud"] = cloud_source
    else:
        state["provider_local_select"] = "MockBiometricProvider"
        state["provider_cloud_select"] = "MockBiometricProvider"
