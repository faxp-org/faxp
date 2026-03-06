#!/usr/bin/env python3
"""Pure state helpers for Streamlit sidebar preset behavior."""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping


def build_quick_presets(default_per_mile_bid: float) -> dict[str, dict[str, Any]]:
    compliance_mock_preset = {
        "provider": "MockComplianceProvider",
        "policy_profile_id": "US_VERIFICATION_BALANCED_V1",
        "risk_tier": 1,
        "mileage_dispute_policy": "balanced",
        "mileage_abs_tolerance_miles": 25.0,
        "mileage_rel_tolerance_ratio": 0.02,
        "exception_approved": False,
        "exception_approval_ref": "",
        "rate_model": "PerMile",
        "bid_amount": float(default_per_mile_bid),
        "response_type": "Accept",
        "verification_status": "Success",
        "no_match": False,
        "compliance_source_local": "authority-mock",
        "compliance_source_cloud": "authority-mock",
    }
    strict_mileage_policy = {
        "provider": "MockComplianceProvider",
        "policy_profile_id": "US_VERIFICATION_BALANCED_V1",
        "risk_tier": 1,
        "mileage_dispute_policy": "strict",
        "mileage_abs_tolerance_miles": 25.0,
        "mileage_rel_tolerance_ratio": 0.02,
        "exception_approved": False,
        "exception_approval_ref": "",
        "rate_model": "PerMile",
        "bid_amount": float(default_per_mile_bid),
        "response_type": "Accept",
        "verification_status": "Success",
        "no_match": False,
        "compliance_source_local": "authority-mock",
        "compliance_source_cloud": "authority-mock",
    }
    return {
        "Compliance mock (balanced)": dict(compliance_mock_preset),
        "Compliance strict mileage policy": dict(strict_mileage_policy),
        "Shipper-origin flow (identity mock)": {
            "shipper_flow": True,
            "provider": "MockBiometricProvider",
            "policy_profile_id": "US_VERIFICATION_BALANCED_V1",
            "risk_tier": 1,
            "mileage_dispute_policy": "balanced",
            "mileage_abs_tolerance_miles": 25.0,
            "mileage_rel_tolerance_ratio": 0.02,
            "exception_approved": False,
            "exception_approval_ref": "",
            "rate_model": "PerMile",
            "bid_amount": float(default_per_mile_bid),
            "response_type": "Accept",
            "verification_status": "Success",
            "no_match": False,
        },
        "Identity verifier (mock success)": {
            "provider": "MockBiometricProvider",
            "policy_profile_id": "US_VERIFICATION_BALANCED_V1",
            "risk_tier": 1,
            "mileage_dispute_policy": "balanced",
            "mileage_abs_tolerance_miles": 25.0,
            "mileage_rel_tolerance_ratio": 0.02,
            "exception_approved": False,
            "exception_approval_ref": "",
            "rate_model": "PerMile",
            "bid_amount": float(default_per_mile_bid),
            "response_type": "Accept",
            "verification_status": "Success",
            "no_match": False,
        },
        "Forced fail demo": {
            "provider": "MockBiometricProvider",
            "policy_profile_id": "US_VERIFICATION_BALANCED_V1",
            "risk_tier": 2,
            "mileage_dispute_policy": "balanced",
            "mileage_abs_tolerance_miles": 25.0,
            "mileage_rel_tolerance_ratio": 0.02,
            "exception_approved": False,
            "exception_approval_ref": "",
            "rate_model": "PerMile",
            "bid_amount": float(default_per_mile_bid),
            "response_type": "Accept",
            "verification_status": "Fail",
            "no_match": False,
        },
        "GraceCache with approved exception": {
            "provider": "MockComplianceProvider",
            "policy_profile_id": "US_VERIFICATION_BALANCED_V1",
            "risk_tier": 2,
            "mileage_dispute_policy": "balanced",
            "mileage_abs_tolerance_miles": 25.0,
            "mileage_rel_tolerance_ratio": 0.02,
            "exception_approved": True,
            "exception_approval_ref": "APPROVAL-DEMO-001",
            "rate_model": "PerMile",
            "bid_amount": float(default_per_mile_bid),
            "response_type": "Accept",
            "verification_status": "Success",
            "no_match": False,
            "compliance_source_local": "authority-mock",
            "compliance_source_cloud": "authority-mock",
        },
    }


def default_sidebar_state(default_per_mile_bid: float) -> dict[str, Any]:
    return {
        "quick_preset_select": "Identity verifier (mock success)",
        "shipper_flow_checkbox": False,
        "policy_profile_select": "US_VERIFICATION_BALANCED_V1",
        "risk_tier_select": 1,
        "mileage_policy_select": "balanced",
        "mileage_abs_tolerance_input": 25.0,
        "mileage_rel_tolerance_input": 0.02,
        "exception_approved_checkbox": False,
        "exception_approval_ref_input": "",
        "rate_model_select": "PerMile",
        "bid_amount_input": float(default_per_mile_bid),
        "response_type_select": "Accept",
        "provider_local_select": "ComplianceVerifier (Mock)",
        "provider_cloud_select": "ComplianceVerifier (Mock)",
        "compliance_source_select_local": "authority-mock",
        "compliance_source_select_cloud": "authority-mock",
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
) -> None:
    preset = presets.get(preset_name)
    if not preset:
        return

    state["rate_model_select"] = preset["rate_model"]
    state["shipper_flow_checkbox"] = bool(
        preset.get("shipper_flow", state.get("shipper_flow_checkbox", False))
    )
    state["bid_amount_input"] = float(preset["bid_amount"])
    state["response_type_select"] = preset["response_type"]
    state["verification_status_select"] = preset["verification_status"]
    state["no_match_checkbox"] = bool(preset["no_match"])
    state["policy_profile_select"] = str(
        preset.get(
            "policy_profile_id",
            state.get("policy_profile_select", "US_VERIFICATION_BALANCED_V1"),
        )
    )
    state["risk_tier_select"] = int(preset.get("risk_tier", state.get("risk_tier_select", 1)))
    state["mileage_policy_select"] = str(
        preset.get("mileage_dispute_policy", state.get("mileage_policy_select", "balanced"))
    )
    state["mileage_abs_tolerance_input"] = float(
        preset.get("mileage_abs_tolerance_miles", state.get("mileage_abs_tolerance_input", 25.0))
    )
    state["mileage_rel_tolerance_input"] = float(
        preset.get("mileage_rel_tolerance_ratio", state.get("mileage_rel_tolerance_input", 0.02))
    )
    state["exception_approved_checkbox"] = bool(
        preset.get("exception_approved", state.get("exception_approved_checkbox", False))
    )
    state["exception_approval_ref_input"] = str(
        preset.get("exception_approval_ref", state.get("exception_approval_ref_input", ""))
    )

    provider = preset["provider"]
    if provider == "MockComplianceProvider":
        state["provider_local_select"] = "ComplianceVerifier (Mock)"
        state["provider_cloud_select"] = "ComplianceVerifier (Mock)"
        state["compliance_source_select_local"] = preset.get(
            "compliance_source_local",
            "authority-mock",
        )
        state["compliance_source_select_cloud"] = preset.get(
            "compliance_source_cloud",
            "authority-mock",
        )
    else:
        state["provider_local_select"] = "MockBiometricProvider"
        state["provider_cloud_select"] = "MockBiometricProvider"
