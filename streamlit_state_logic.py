#!/usr/bin/env python3
"""Pure state helpers for Streamlit sidebar preset behavior."""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping


def build_quick_presets(default_per_mile_bid: float) -> dict[str, dict[str, Any]]:
    return {
        "FMCSA hosted adapter (MC 498282)": {
            "provider": "FMCSA",
            "policy_profile_id": "US_FMCSA_BALANCED_V1",
            "risk_tier": 1,
            "exception_approved": False,
            "exception_approval_ref": "",
            "rate_model": "PerMile",
            "bid_amount": float(default_per_mile_bid),
            "response_type": "Accept",
            "verification_status": "Success",
            "no_match": False,
            "mc_number": "498282",
            "fmcsa_source_local": "hosted-adapter",
            "fmcsa_source_cloud": "hosted-adapter",
        },
        "FMCSA live (MC 498282)": {
            "provider": "FMCSA",
            "policy_profile_id": "US_FMCSA_BALANCED_V1",
            "risk_tier": 1,
            "exception_approved": False,
            "exception_approval_ref": "",
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
            "policy_profile_id": "US_FMCSA_BALANCED_V1",
            "risk_tier": 1,
            "exception_approved": False,
            "exception_approval_ref": "",
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
            "policy_profile_id": "US_FMCSA_BALANCED_V1",
            "risk_tier": 1,
            "exception_approved": False,
            "exception_approval_ref": "",
            "rate_model": "PerMile",
            "bid_amount": float(default_per_mile_bid),
            "response_type": "Accept",
            "verification_status": "Success",
            "no_match": False,
            "mc_number": "",
        },
        "Forced fail demo": {
            "provider": "MockBiometricProvider",
            "policy_profile_id": "US_FMCSA_BALANCED_V1",
            "risk_tier": 2,
            "exception_approved": False,
            "exception_approval_ref": "",
            "rate_model": "PerMile",
            "bid_amount": float(default_per_mile_bid),
            "response_type": "Accept",
            "verification_status": "Fail",
            "no_match": False,
            "mc_number": "",
        },
        "GraceCache with approved exception": {
            "provider": "FMCSA",
            "policy_profile_id": "US_FMCSA_BALANCED_V1",
            "risk_tier": 2,
            "exception_approved": True,
            "exception_approval_ref": "APPROVAL-DEMO-001",
            "rate_model": "PerMile",
            "bid_amount": float(default_per_mile_bid),
            "response_type": "Accept",
            "verification_status": "Success",
            "no_match": False,
            "mc_number": "498282",
            "fmcsa_source_local": "hosted-adapter",
            "fmcsa_source_cloud": "hosted-adapter",
        },
    }


def default_sidebar_state(default_per_mile_bid: float) -> dict[str, Any]:
    return {
        "quick_preset_select": "MockBiometric success",
        "policy_profile_select": "US_FMCSA_BALANCED_V1",
        "risk_tier_select": 1,
        "exception_approved_checkbox": False,
        "exception_approval_ref_input": "",
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
    hosted_fmcsa_configured: bool = False,
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
    state["policy_profile_select"] = str(
        preset.get("policy_profile_id", state.get("policy_profile_select", "US_FMCSA_BALANCED_V1"))
    )
    state["risk_tier_select"] = int(preset.get("risk_tier", state.get("risk_tier_select", 1)))
    state["exception_approved_checkbox"] = bool(
        preset.get("exception_approved", state.get("exception_approved_checkbox", False))
    )
    state["exception_approval_ref_input"] = str(
        preset.get("exception_approval_ref", state.get("exception_approval_ref_input", ""))
    )

    provider = preset["provider"]
    if provider == "FMCSA":
        state["provider_local_select"] = "FMCSA"
        state["provider_cloud_select"] = "FMCSA (Authority)"
        state["fmcsa_source_select_local"] = preset.get(
            "fmcsa_source_local", "carrier-finder"
        )
        cloud_source = preset.get("fmcsa_source_cloud", "authority-mock")
        if cloud_source == "hosted-adapter" and not hosted_fmcsa_configured:
            cloud_source = "authority-mock"
        if cloud_source == "live-fmcsa" and not live_fmcsa_configured:
            cloud_source = "hosted-adapter" if hosted_fmcsa_configured else "authority-mock"
        state["fmcsa_source_select_cloud"] = cloud_source
    else:
        state["provider_local_select"] = "MockBiometricProvider"
        state["provider_cloud_select"] = "MockBiometricProvider"
