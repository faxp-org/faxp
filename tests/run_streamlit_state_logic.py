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

    ensure_state_defaults(state, defaults)
    _assert(state["quick_preset_select"] == "MockBiometric success", "default preset mismatch")
    _assert(state["provider_cloud_select"] == "MockBiometricProvider", "default provider mismatch")
    _assert(state["policy_profile_select"] == "US_FMCSA_BALANCED_V1", "default policy profile mismatch")
    _assert(state["risk_tier_select"] == 1, "default risk tier mismatch")

    # Regression: applying preset must not mutate the selectbox widget key directly.
    prior_preset_selection = state["quick_preset_select"]
    apply_preset_to_state(
        state,
        presets,
        "FMCSA hosted adapter (MC 498282)",
        hosted_fmcsa_configured=False,
    )
    _assert(
        state["fmcsa_source_select_cloud"] == "authority-mock",
        "hosted adapter should downgrade to authority-mock when adapter is not configured",
    )

    _assert(
        state["quick_preset_select"] == prior_preset_selection,
        "preset selection key should remain user-owned",
    )
    _assert(state["provider_cloud_select"] == "FMCSA (Authority)", "cloud provider label mismatch")

    apply_preset_to_state(
        state,
        presets,
        "FMCSA hosted adapter (MC 498282)",
        hosted_fmcsa_configured=True,
    )
    _assert(
        state["fmcsa_source_select_cloud"] == "hosted-adapter",
        "hosted adapter should remain selected when configured",
    )

    apply_preset_to_state(
        state,
        presets,
        "Forced fail demo",
        hosted_fmcsa_configured=True,
    )
    _assert(state["provider_local_select"] == "MockBiometricProvider", "local provider mismatch")
    _assert(state["verification_status_select"] == "Fail", "forced fail status mismatch")
    _assert(state["risk_tier_select"] == 2, "forced fail risk tier mismatch")

    apply_preset_to_state(
        state,
        presets,
        "GraceCache with approved exception",
        hosted_fmcsa_configured=True,
    )
    _assert(state["exception_approved_checkbox"] is True, "exception flag mismatch")
    _assert(
        state["exception_approval_ref_input"] == "APPROVAL-DEMO-001",
        "exception approval ref mismatch",
    )

    source = (PROJECT_ROOT / "streamlit_app.py").read_text(encoding="utf-8")
    _assert(
        'if "access_key_input" not in st.session_state:' in source,
        "reset_state guard for access_key_input is missing",
    )

    print("Streamlit state helper regression checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
