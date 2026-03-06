#!/usr/bin/env python3
"""Regression checks for Streamlit preset/state helpers."""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from streamlit_state_logic import (  # noqa: E402
    apply_preset_to_state,
    build_quick_presets,
    default_sidebar_state,
    ensure_state_defaults,
)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    defaults = default_sidebar_state(2.62)
    presets = build_quick_presets(2.62)
    state: dict[str, object] = {}
    _assert(
        "Compliance mock (balanced)" in presets,
        "compliance balanced preset should be available",
    )
    _assert(
        "Compliance strict mileage policy" in presets,
        "strict mileage policy preset should be available",
    )
    _assert(
        "Identity verifier (mock success)" in presets,
        "identity mock success preset should be available",
    )
    _assert(
        "Shipper-origin flow (identity mock)" in presets,
        "shipper-origin preset should be available",
    )

    ensure_state_defaults(state, defaults)
    _assert(
        state["quick_preset_select"] == "Identity verifier (mock success)",
        "default preset mismatch",
    )
    _assert(state["shipper_flow_checkbox"] is False, "default shipper-flow toggle mismatch")
    _assert(
        state["provider_cloud_select"] == "ComplianceVerifier (Mock)",
        "default provider mismatch",
    )
    _assert(
        state["policy_profile_select"] == "US_VERIFICATION_BALANCED_V1",
        "default policy profile mismatch",
    )
    _assert(state["risk_tier_select"] == 1, "default risk tier mismatch")
    _assert(state["mileage_policy_select"] == "balanced", "default mileage policy mismatch")
    _assert(
        float(state["mileage_abs_tolerance_input"]) == 25.0,
        "default mileage abs tolerance mismatch",
    )
    _assert(
        abs(float(state["mileage_rel_tolerance_input"]) - 0.02) < 1e-9,
        "default mileage relative tolerance mismatch",
    )

    prior_preset_selection = state["quick_preset_select"]
    apply_preset_to_state(state, presets, "Compliance mock (balanced)")
    _assert(
        state["compliance_source_select_cloud"] == "authority-mock",
        "compliance source should remain authority-mock",
    )
    _assert(
        state["provider_cloud_select"] == "ComplianceVerifier (Mock)",
        "cloud provider label mismatch",
    )
    _assert(
        state["quick_preset_select"] == prior_preset_selection,
        "preset selection key should remain user-owned",
    )

    apply_preset_to_state(state, presets, "Shipper-origin flow (identity mock)")
    _assert(state["shipper_flow_checkbox"] is True, "shipper preset should enable shipper flow")
    _assert(state["provider_local_select"] == "MockBiometricProvider", "shipper preset provider mismatch")

    apply_preset_to_state(state, presets, "Forced fail demo")
    _assert(state["provider_local_select"] == "MockBiometricProvider", "local provider mismatch")
    _assert(state["verification_status_select"] == "Fail", "forced fail status mismatch")
    _assert(state["risk_tier_select"] == 2, "forced fail risk tier mismatch")
    _assert(state["mileage_policy_select"] == "balanced", "forced fail mileage policy mismatch")

    apply_preset_to_state(state, presets, "GraceCache with approved exception")
    _assert(state["exception_approved_checkbox"] is True, "exception flag mismatch")
    _assert(
        state["exception_approval_ref_input"] == "APPROVAL-DEMO-001",
        "exception approval ref mismatch",
    )

    apply_preset_to_state(state, presets, "Compliance strict mileage policy")
    _assert(
        state["provider_local_select"] == "ComplianceVerifier (Mock)",
        "strict preset provider mismatch",
    )
    _assert(state["mileage_policy_select"] == "strict", "strict preset mileage policy mismatch")

    source = (PROJECT_ROOT / "streamlit_app.py").read_text(encoding="utf-8")
    _assert(
        'if "access_key_input" not in st.session_state:' in source,
        "reset_state guard for access_key_input is missing",
    )
    _assert(
        '"shipper_flow_checkbox"' in source,
        "streamlit app should include shipper flow sidebar toggle key",
    )

    print("Streamlit state helper regression checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
