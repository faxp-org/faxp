#!/usr/bin/env python3
"""FAXP Streamlit demo: NewLoad -> Bid -> Verification -> ExecutionReport."""

from datetime import datetime, timezone
import base64
import hashlib
import json
import os
import secrets
import time

import streamlit as st
import streamlit.components.v1 as components

from faxp_mvp_simulation import (
    BrokerAgent,
    CarrierAgent,
    DEFAULT_RISK_TIER,
    FaxpProtocol,
    VERIFICATION_POLICY_PROFILE_ID,
    build_envelope,
    configure_mileage_dispute_policy,
    default_bid_amount,
    evaluate_verification_policy_decision,
    format_rate,
    negotiate_verification_capability,
    redact_sensitive,
    get_protocol_run_id,
    reset_protocol_runtime_state,
    run_verification,
    resolve_agent_id,
    set_protocol_run_id,
    validate_envelope,
)
from streamlit_state_logic import (
    apply_preset_to_state,
    build_quick_presets,
    default_sidebar_state,
    ensure_state_defaults,
)

ACCESS_KEY = os.getenv("FAXP_STREAMLIT_ACCESS_KEY", "").strip()
MAX_VERIFICATION_CALLS_PER_HOUR = int(os.getenv("FAXP_MAX_VERIFICATIONS_PER_HOUR", "30"))
APP_MODE = os.getenv("FAXP_APP_MODE", "local").strip().lower()
NON_LOCAL_MODE = APP_MODE not in {"local", "dev", "development"}
SIGNATURE_SCHEME = os.getenv("FAXP_SIGNATURE_SCHEME", "HMAC_SHA256").strip().upper()
VERIFIER_SIGNATURE_SCHEME = os.getenv(
    "FAXP_VERIFIER_SIGNATURE_SCHEME", "HMAC_SHA256"
).strip().upper()
SIGNED_VERIFIER_REQUIRED = os.getenv("FAXP_REQUIRE_SIGNED_VERIFIER", "1").strip() in {
    "1",
    "true",
    "TRUE",
    "yes",
    "on",
}
_cloud_safe_setting = os.getenv("FAXP_CLOUD_SAFE_MODE", "auto").strip().lower()
if _cloud_safe_setting in {"1", "true", "yes", "on"}:
    CLOUD_SAFE_MODE = True
elif _cloud_safe_setting in {"0", "false", "no", "off"}:
    CLOUD_SAFE_MODE = False
else:
    CLOUD_SAFE_MODE = NON_LOCAL_MODE
HOSTED_FMCSA_CONFIGURED = bool(os.getenv("FAXP_FMCSA_ADAPTER_BASE_URL", "").strip())
MAX_AUTH_FAILURES = int(os.getenv("FAXP_AUTH_MAX_FAILURES", "5"))
AUTH_LOCKOUT_SECONDS = int(os.getenv("FAXP_AUTH_LOCKOUT_SECONDS", "300"))
GLOBAL_VERIFICATION_CALL_TIMES = []
DEFAULT_PER_MILE_BID = float(default_bid_amount("PerMile"))
QUICK_PRESETS = build_quick_presets(DEFAULT_PER_MILE_BID)
SIDEBAR_DEFAULTS = default_sidebar_state(DEFAULT_PER_MILE_BID)
POLICY_PROFILE_OPTIONS = [
    "US_FMCSA_BALANCED_V1",
    "US_FMCSA_SOFTHOLD_V1",
    "US_FMCSA_STRICT_V1",
]
POLICY_PROFILE_LABELS = {
    "US_FMCSA_BALANCED_V1": "US Compliance Balanced v1 (GraceCache)",
    "US_FMCSA_SOFTHOLD_V1": "US Compliance SoftHold v1",
    "US_FMCSA_STRICT_V1": "US Compliance Strict v1 (HardBlock)",
}
MILEAGE_POLICY_OPTIONS = ["balanced", "strict"]
MILEAGE_POLICY_LABELS = {
    "balanced": "Balanced (tolerance-based)",
    "strict": "Strict (counter any mismatch)",
}
DEFAULT_POLICY_PROFILE = (
    VERIFICATION_POLICY_PROFILE_ID
    if VERIFICATION_POLICY_PROFILE_ID in POLICY_PROFILE_OPTIONS
    else "US_FMCSA_BALANCED_V1"
)
COMPLIANCE_SOURCE_LABELS = {
    "authority-mock": "authority-mock",
    "implementer-adapter": "implementer-adapter",
    "vendor-direct": "vendor-direct",
    # Backward-compatible alias.
    "hosted-adapter": "implementer-adapter (legacy alias: hosted-adapter)",
}


def now_utc():
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def envelope(sender, receiver, message_type, body):
    return build_envelope(sender, receiver, message_type, body)


def render_copy_button(label, text, key):
    payload_b64 = base64.b64encode(text.encode("utf-8")).decode("ascii")
    components.html(
        f"""
        <div style="display:flex;align-items:center;gap:10px;">
          <button id="{key}" onclick="
            navigator.clipboard.writeText(atob('{payload_b64}')).then(() => {{
              document.getElementById('{key}_status').textContent = 'Copied';
            }}).catch(() => {{
              document.getElementById('{key}_status').textContent = 'Copy failed';
            }});
          " style="padding:6px 12px;border:1px solid #999;border-radius:6px;background:#f5f5f5;cursor:pointer;">
            {label}
          </button>
          <span id="{key}_status" style="font-size:0.9em;color:#666;"></span>
        </div>
        """,
        height=46,
    )


def ensure_sidebar_defaults():
    ensure_state_defaults(st.session_state, SIDEBAR_DEFAULTS)


def apply_quick_preset(preset_name):
    apply_preset_to_state(
        st.session_state,
        QUICK_PRESETS,
        preset_name,
        hosted_fmcsa_configured=HOSTED_FMCSA_CONFIGURED,
    )


def reset_state():
    existing_history = st.session_state.get("verifier_diagnostics_history", [])
    existing_access_key = st.session_state.get("access_key_input", "")
    reset_protocol_runtime_state()
    st.session_state.broker = BrokerAgent("Broker Agent")
    st.session_state.carrier = CarrierAgent("Carrier Agent")
    st.session_state.broker_agent_id = resolve_agent_id(st.session_state.broker.name)
    st.session_state.carrier_agent_id = resolve_agent_id(st.session_state.carrier.name)
    st.session_state.messages = []
    st.session_state.summary = ""
    st.session_state.execution_report = None
    st.session_state.verification_result = None
    st.session_state.verified_badge = "None"
    st.session_state.status_line = "Ready"
    st.session_state.search_results = None
    st.session_state.amend_example = FaxpProtocol.amend_request_example("example-load-id")
    st.session_state.accessorial_note = ""
    st.session_state.validation_errors = []
    st.session_state.validated_messages = 0
    st.session_state.verification_call_times = []
    st.session_state.auth_failures = 0
    st.session_state.auth_locked_until = 0.0
    st.session_state.policy_decision = None
    st.session_state.last_verifier_diagnostics = {}
    st.session_state.verifier_diagnostics_history = list(existing_history)[:5]
    if "access_key_input" not in st.session_state:
        st.session_state.access_key_input = existing_access_key


def push_verifier_history(entry):
    history = list(st.session_state.get("verifier_diagnostics_history", []))
    history.insert(0, dict(entry))
    st.session_state.verifier_diagnostics_history = history[:5]


def append_message(sender, receiver, message_type, body):
    msg = envelope(sender, receiver, message_type, body)
    try:
        validate_envelope(msg)
        msg["Validation"] = "Pass"
        st.session_state.validated_messages += 1
    except ValueError as exc:
        msg["Validation"] = "Fail"
        msg["ValidationError"] = str(exc)
        st.session_state.validation_errors.append(
            {
                "MessageType": message_type,
                "Error": str(exc),
                "Timestamp": msg["Timestamp"],
            }
        )
        st.session_state.status_line = f"Validation failed: {message_type}"
    except Exception as exc:
        # Keep the demo fail-closed and user-visible instead of crashing the Streamlit process.
        msg["Validation"] = "Fail"
        msg["ValidationError"] = f"Internal validation error: {type(exc).__name__}"
        st.session_state.validation_errors.append(
            {
                "MessageType": message_type,
                "Error": f"{type(exc).__name__}: {exc}",
                "Timestamp": msg["Timestamp"],
            }
        )
        st.session_state.status_line = f"Internal validation error: {message_type}"
    st.session_state.messages.append(msg)
    return msg["Validation"] == "Pass"


def is_authorized():
    if NON_LOCAL_MODE and not ACCESS_KEY:
        return False
    if not ACCESS_KEY:
        return True
    if st.session_state.auth_locked_until > time.time():
        return False
    provided = st.session_state.get("access_key_input", "")
    if secrets.compare_digest(provided, ACCESS_KEY):
        st.session_state.auth_failures = 0
        return True
    st.session_state.auth_failures += 1
    if st.session_state.auth_failures >= MAX_AUTH_FAILURES:
        st.session_state.auth_locked_until = time.time() + AUTH_LOCKOUT_SECONDS
    return False


def allow_verification_attempt():
    global GLOBAL_VERIFICATION_CALL_TIMES
    now = time.time()
    cutoff = now - 3600
    recent = [t for t in GLOBAL_VERIFICATION_CALL_TIMES if t >= cutoff]
    GLOBAL_VERIFICATION_CALL_TIMES = recent
    if len(recent) >= MAX_VERIFICATION_CALLS_PER_HOUR:
        return False
    GLOBAL_VERIFICATION_CALL_TIMES.append(now)
    return True


def accessorial_total(execution_report):
    return round(
        sum(
            float(item.get("Amount", 0.0))
            for item in execution_report.get("Accessorials", [])
            if item.get("Status") == "Approved"
        ),
        2,
    )


def update_summary_from_report():
    report = st.session_state.execution_report
    if report is None:
        st.session_state.summary = ""
        return

    dispatch_auth = report.get("DispatchAuthorization", "Allowed")
    load_id = report.get("LoadID", report.get("TruckID", "n/a"))
    if dispatch_auth == "Hold":
        st.session_state.summary = (
            "Booking provisionally completed (dispatch hold) - "
            f"RunID: {get_protocol_run_id()}, "
            f"LoadID: {load_id}, "
            f"Verified: {st.session_state.verified_badge}, "
            f"BaseRate: {format_rate(report['AgreedRate'])}, "
            f"ApprovedAccessorials: ${accessorial_total(report):.2f}"
        )
    else:
        st.session_state.summary = (
            "Booking completed successfully - "
            f"RunID: {get_protocol_run_id()}, "
            f"LoadID: {load_id}, "
            f"Verified: {st.session_state.verified_badge}, "
            f"BaseRate: {format_rate(report['AgreedRate'])}, "
            f"ApprovedAccessorials: ${accessorial_total(report):.2f}"
        )


def approve_accessorial(accessorial_type, amount, note):
    report = st.session_state.execution_report
    if report is None:
        st.session_state.status_line = "No booked load available for accessorial approval."
        return

    policy = report.get("AccessorialPolicy", {})
    allowed_types = policy.get("AllowedTypes", [])
    max_total = float(policy.get("MaxTotal", 0.0))

    if accessorial_type not in allowed_types:
        st.session_state.status_line = f"Accessorial '{accessorial_type}' is not allowed by policy."
        return

    if amount <= 0:
        st.session_state.status_line = "Accessorial amount must be greater than zero."
        return

    new_total = accessorial_total(report) + float(amount)
    if max_total > 0 and new_total > max_total:
        st.session_state.status_line = f"Accessorial exceeds policy max (${max_total:.2f})."
        return

    term_metadata = {}
    for term in policy.get("Terms", []):
        if isinstance(term, dict) and term.get("Type") == accessorial_type:
            term_metadata = term
            break

    report["Accessorials"].append(
        {
            "Type": accessorial_type,
            "Amount": round(float(amount), 2),
            "Currency": policy.get("Currency", "USD"),
            "Status": "Approved",
            "ApprovedAt": now_utc(),
            "PricingMode": term_metadata.get("PricingMode", "Reimbursable"),
            "PayerParty": term_metadata.get("PayerParty", "Broker"),
            "PayeeParty": term_metadata.get("PayeeParty", "Carrier"),
            "EvidenceRequired": bool(term_metadata.get("EvidenceRequired", False)),
            "EvidenceType": term_metadata.get("EvidenceType", "Other"),
            "Note": note.strip(),
        }
    )
    st.session_state.status_line = f"Accessorial approved: {accessorial_type} ${float(amount):.2f}"
    update_summary_from_report()


def run_flow(
    response_type,
    provider,
    verification_status,
    no_match,
    rate_model,
    bid_amount,
    mc_number,
    fmcsa_source,
    policy_profile_id,
    risk_tier,
    mileage_dispute_policy,
    mileage_abs_tolerance_miles,
    mileage_rel_tolerance_ratio,
    exception_approved,
    exception_approval_ref,
):
    reset_state()
    run_id = set_protocol_run_id()
    effective_mileage_policy = configure_mileage_dispute_policy(
        policy=mileage_dispute_policy,
        abs_tolerance_miles=mileage_abs_tolerance_miles,
        rel_tolerance_ratio=mileage_rel_tolerance_ratio,
    )
    broker = st.session_state.broker
    carrier = st.session_state.carrier
    st.session_state.last_verifier_diagnostics = {
        "run_id": run_id,
        "provider": provider,
        "fmcsa_source": fmcsa_source if provider == "FMCSA" else "n/a",
        "mc_number": (mc_number or "").strip() if provider == "FMCSA" else "",
        "policy_profile_id": policy_profile_id,
        "risk_tier": int(risk_tier),
        "mileage_dispute_policy": effective_mileage_policy.get("policy", "balanced"),
        "mileage_abs_tolerance_miles": effective_mileage_policy.get("absToleranceMiles", 0.0),
        "mileage_rel_tolerance_ratio": effective_mileage_policy.get("relToleranceRatio", 0.0),
        "exception_approved": bool(exception_approved),
        "exception_approval_ref": str(exception_approval_ref or "").strip(),
        "hosted_fmcsa_configured": HOSTED_FMCSA_CONFIGURED,
        "cloud_safe_mode": CLOUD_SAFE_MODE,
        "result_status": "NotStarted",
        "result_source": "n/a",
        "result_provider": "n/a",
        "result_error": "",
        "timestamp": now_utc(),
    }

    # Show AmendRequest exists but do not execute it in this flow.
    st.session_state.amend_example = FaxpProtocol.amend_request_example("example-load-id")

    # 1) NewLoad
    new_load = broker.post_new_load(rate_model=rate_model)
    if not append_message(broker.name, carrier.name, "NewLoad", new_load):
        return

    # 2) LoadSearch
    load_search = carrier.create_load_search(force_no_match=no_match, rate_model=rate_model)
    if not append_message(carrier.name, broker.name, "LoadSearch", load_search):
        return
    matched_loads = broker.search_loads(load_search)
    st.session_state.search_results = matched_loads

    if not matched_loads:
        st.session_state.status_line = "No matching loads found."
        return

    # 3) BidRequest
    selected_load = matched_loads[0]
    bid_request = carrier.create_bid_request(selected_load, bid_amount=bid_amount)
    if not append_message(carrier.name, broker.name, "BidRequest", bid_request):
        return

    # 4) BidResponse
    bid_response = broker.respond_to_bid(bid_request, forced_response=response_type)
    if not append_message(broker.name, carrier.name, "BidResponse", bid_response):
        return

    if bid_response["ResponseType"] == "Counter":
        st.session_state.status_line = "Counter received. Negotiation pending."
        return

    if bid_response["ResponseType"] == "Reject":
        st.session_state.status_line = "Bid rejected."
        return

    capabilities_ok, capability_reason = negotiate_verification_capability(
        provider, broker, carrier
    )
    if not capabilities_ok:
        st.session_state.status_line = capability_reason
        return

    # 5) Verification
    if not allow_verification_attempt():
        st.session_state.status_line = "Verification rate limit reached. Try again later."
        return

    try:
        verification_result, verified_badge = run_verification(
            provider=provider,
            status=verification_status,
            mc_number=(mc_number.strip() or None),
            fmcsa_source=fmcsa_source,
        )
    except Exception:
        st.session_state.status_line = "Verification process error."
        diag = st.session_state.last_verifier_diagnostics
        diag["result_status"] = "Error"
        diag["result_error"] = "Verification process error."
        diag["timestamp"] = now_utc()
        push_verifier_history(diag)
        return
    st.session_state.verification_result = verification_result
    st.session_state.verified_badge = verified_badge
    diag = st.session_state.last_verifier_diagnostics
    diag["result_status"] = verification_result.get("status", "Unknown")
    diag["result_source"] = verification_result.get("source", "n/a")
    diag["result_provider"] = verification_result.get("provider", "n/a")
    diag["result_error"] = verification_result.get("error", "")
    diag["timestamp"] = now_utc()

    policy_decision = evaluate_verification_policy_decision(
        verification_result,
        profile_id=policy_profile_id,
        risk_tier=int(risk_tier),
        exception_approved=bool(exception_approved),
        exception_approval_ref=str(exception_approval_ref or "").strip(),
    )
    st.session_state.policy_decision = policy_decision
    diag["policy_dispatch_authorization"] = policy_decision["DispatchAuthorization"]
    diag["policy_decision_reason_code"] = policy_decision["DecisionReasonCode"]
    diag["policy_rule_id"] = policy_decision["PolicyRuleID"]
    diag["policy_should_book"] = policy_decision["ShouldBook"]
    diag["timestamp"] = now_utc()
    push_verifier_history(diag)

    if not policy_decision["ShouldBook"]:
        st.session_state.status_line = (
            "Booking blocked by policy: "
            f"{policy_decision['DecisionReasonCode']} "
            f"({policy_decision['DispatchAuthorization']})"
        )
        return

    # 6) ExecutionReport
    execution_report = broker.create_execution_report(
        load_id=bid_request["LoadID"],
        bid_request=bid_request,
        verified_badge=verified_badge,
        verification_result=verification_result,
        policy_decision=policy_decision,
    )
    if not append_message(broker.name, carrier.name, "ExecutionReport", execution_report):
        return

    # 7) Complete for both parties
    carrier.mark_booking_complete(execution_report)
    st.session_state.execution_report = execution_report
    if execution_report.get("DispatchAuthorization") == "Hold":
        st.session_state.status_line = "Booking provisionally completed. Dispatch is on hold."
    else:
        st.session_state.status_line = "Booking completed."
    update_summary_from_report()


st.set_page_config(page_title="FAXP Demo", layout="wide")
st.title(f"FAXP v{FaxpProtocol.VERSION} - Freight Agent eXchange Protocol Demo")
st.caption("Mock FAXP client embedded in Streamlit: NewLoad -> Bid -> Verification -> ExecutionReport")

if "broker" not in st.session_state:
    reset_state()

ensure_sidebar_defaults()
if st.session_state.get("policy_profile_select") not in POLICY_PROFILE_OPTIONS:
    st.session_state.policy_profile_select = DEFAULT_POLICY_PROFILE
if st.session_state.get("mileage_policy_select") not in MILEAGE_POLICY_OPTIONS:
    st.session_state.mileage_policy_select = "balanced"
try:
    parsed_risk_tier = int(st.session_state.get("risk_tier_select", DEFAULT_RISK_TIER))
except (TypeError, ValueError):
    parsed_risk_tier = DEFAULT_RISK_TIER
if parsed_risk_tier not in {0, 1, 2, 3}:
    parsed_risk_tier = DEFAULT_RISK_TIER
st.session_state.risk_tier_select = max(0, min(parsed_risk_tier, 3))
if NON_LOCAL_MODE:
    st.session_state.provider_cloud_select = "ComplianceVerifier (Trusted Adapter)"
    st.session_state.provider_local_select = "FMCSA"
    st.session_state.fmcsa_source_select_cloud = "implementer-adapter"
    st.session_state.fmcsa_source_select_local = "implementer-adapter"
elif CLOUD_SAFE_MODE and st.session_state.get("provider_cloud_select") not in {
    "ComplianceVerifier (Authority Mock)",
    "IdentityVerifier (Mock)",
}:
    st.session_state.provider_cloud_select = "ComplianceVerifier (Authority Mock)"

if NON_LOCAL_MODE and not ACCESS_KEY:
    st.error("Secure mode requires FAXP_STREAMLIT_ACCESS_KEY.")
    st.stop()

with st.sidebar:
    st.header("Scenario")
    st.caption(
        f"Runtime mode: {'cloud-safe' if CLOUD_SAFE_MODE else 'full/local'} "
        f"(FAXP_APP_MODE={APP_MODE})"
    )
    st.caption(
        f"Agent IDs: Broker={st.session_state.get('broker_agent_id', 'n/a')} | "
        f"Carrier={st.session_state.get('carrier_agent_id', 'n/a')}"
    )
    preset_name = st.selectbox(
        "Quick Preset",
        list(QUICK_PRESETS.keys()),
        key="quick_preset_select",
    )
    if st.button("Apply Preset", key="apply_quick_preset_button", use_container_width=True):
        apply_quick_preset(preset_name)
    if ACCESS_KEY:
        st.text_input("Access Key", type="password", key="access_key_input")
    rate_model = st.selectbox(
        "Rate Model",
        ["PerMile", "Flat", "PerPallet", "CWT"],
        key="rate_model_select",
    )
    bid_amount = st.number_input(
        "Bid Amount",
        min_value=0.0,
        step=0.01,
        format="%.2f",
        help="PerMile uses $/mile. Flat uses total trip amount. PerPallet uses $/pallet. CWT uses $/cwt.",
        key="bid_amount_input",
    )
    response_type = st.selectbox(
        "BidResponse", ["Accept", "Counter", "Reject"], key="response_type_select"
    )
    policy_profile_id = st.selectbox(
        "Verification Policy Profile",
        POLICY_PROFILE_OPTIONS,
        key="policy_profile_select",
        format_func=lambda value: POLICY_PROFILE_LABELS.get(value, value),
    )
    risk_tier = st.selectbox(
        "Risk Tier",
        [0, 1, 2, 3],
        format_func=lambda value: {
            0: "0 - Low",
            1: "1 - Medium",
            2: "2 - High",
            3: "3 - Critical",
        }[value],
        key="risk_tier_select",
    )
    mileage_dispute_policy = st.selectbox(
        "Mileage Dispute Policy",
        MILEAGE_POLICY_OPTIONS,
        key="mileage_policy_select",
        format_func=lambda value: MILEAGE_POLICY_LABELS.get(value, value),
        help="Controls whether PerMile agreed-miles variances auto-counter or allow tolerance.",
    )
    mileage_abs_tolerance_miles = st.number_input(
        "Mileage Abs Tolerance (miles)",
        min_value=0.0,
        step=1.0,
        format="%.1f",
        key="mileage_abs_tolerance_input",
        help="Balanced mode absolute miles tolerance before countering a PerMile variance.",
    )
    mileage_rel_tolerance_ratio = st.number_input(
        "Mileage Relative Tolerance",
        min_value=0.0,
        step=0.005,
        format="%.3f",
        key="mileage_rel_tolerance_input",
        help="Balanced mode relative tolerance ratio (0.02 = 2%).",
    )
    exception_approved = st.checkbox(
        "Exception Approved",
        key="exception_approved_checkbox",
        help="Set when a human exception approval was granted for degraded verification.",
    )
    exception_approval_ref = st.text_input(
        "Exception Approval Ref",
        key="exception_approval_ref_input",
        placeholder="Example: APPROVAL-2026-0001",
    )
    if NON_LOCAL_MODE:
        st.selectbox(
            "Verification Provider",
            ["ComplianceVerifier (Trusted Adapter)"],
            key="provider_cloud_select",
            disabled=True,
            help="Non-local mode permits only trusted external compliance attestations.",
        )
        provider = "FMCSA"
    elif CLOUD_SAFE_MODE:
        provider_choice = st.selectbox(
            "Verification Provider",
            ["ComplianceVerifier (Authority Mock)", "IdentityVerifier (Mock)"],
            key="provider_cloud_select",
            help="Cloud-safe mode disables local-only verifier paths.",
        )
        provider = (
            "FMCSA"
            if provider_choice.startswith("ComplianceVerifier")
            else "MockBiometricProvider"
        )
    else:
        provider = st.selectbox(
            "Verification Provider",
            ["ComplianceVerifier (FMCSA)", "IdentityVerifier (Mock)", "iDenfy (Legacy Alias)"],
            key="provider_local_select",
            help="iDenfy label is maintained as a legacy alias.",
        )
        if provider == "ComplianceVerifier (FMCSA)":
            provider = "FMCSA"
        if provider == "IdentityVerifier (Mock)":
            provider = "MockBiometricProvider"
        if provider == "iDenfy (Legacy Alias)":
            provider = "iDenfy"

    if provider == "FMCSA":
        if NON_LOCAL_MODE:
            fmcsa_source = "implementer-adapter"
            mc_number = st.text_input("MC Number", key="mc_number_input")
            if HOSTED_FMCSA_CONFIGURED:
                st.caption("Trusted external compliance endpoint mode is active.")
            else:
                st.caption("Missing FAXP_FMCSA_ADAPTER_BASE_URL; verification fails closed in non-local mode.")
        elif CLOUD_SAFE_MODE:
            options = []
            if HOSTED_FMCSA_CONFIGURED:
                options.extend(["implementer-adapter", "vendor-direct"])
            options.append("authority-mock")
            if st.session_state.get("fmcsa_source_select_cloud") == "hosted-adapter":
                st.session_state.fmcsa_source_select_cloud = "implementer-adapter"
            if st.session_state.get("fmcsa_source_select_cloud") not in options:
                st.session_state.fmcsa_source_select_cloud = options[0]
            cloud_fmcsa_mode = st.selectbox(
                "Compliance Source",
                options,
                key="fmcsa_source_select_cloud",
                format_func=lambda key: COMPLIANCE_SOURCE_LABELS.get(key, key),
                help=(
                    "authority-mock uses local mock compliance scoring only. "
                    "implementer-adapter and vendor-direct require a configured trusted endpoint."
                ),
            )
            if cloud_fmcsa_mode in {"implementer-adapter", "vendor-direct"}:
                fmcsa_source = cloud_fmcsa_mode
                mc_number = st.text_input("MC Number", key="mc_number_input")
                st.caption("Trusted compliance endpoint mode enabled via FAXP_FMCSA_ADAPTER_BASE_URL.")
            else:
                fmcsa_source = "authority-mock"
                mc_number = ""
                st.caption("Compliance authority-mock mode (no external API call).")
        else:
            local_fmcsa_options = ["authority-mock", "implementer-adapter", "vendor-direct"]
            if st.session_state.get("fmcsa_source_select_local") == "hosted-adapter":
                st.session_state.fmcsa_source_select_local = "implementer-adapter"
            if st.session_state.get("fmcsa_source_select_local") not in local_fmcsa_options:
                st.session_state.fmcsa_source_select_local = local_fmcsa_options[0]
            fmcsa_source = st.selectbox(
                "Compliance Source",
                local_fmcsa_options,
                key="fmcsa_source_select_local",
                format_func=lambda key: COMPLIANCE_SOURCE_LABELS.get(key, key),
                help=(
                    "authority-mock uses local mock compliance scoring only; "
                    "implementer-adapter and vendor-direct call your trusted compliance endpoint."
                ),
            )
            mc_number = st.text_input("MC Number", key="mc_number_input")
            if fmcsa_source in {"implementer-adapter", "vendor-direct"}:
                if HOSTED_FMCSA_CONFIGURED:
                    st.caption("Trusted compliance endpoint mode enabled via FAXP_FMCSA_ADAPTER_BASE_URL.")
                else:
                    st.caption(
                        "Missing FAXP_FMCSA_ADAPTER_BASE_URL; external compliance calls will fail closed."
                    )
            else:
                st.caption("Compliance authority-mock mode (no external API call).")
    else:
        fmcsa_source = "authority-mock"
        mc_number = ""

    verification_status = st.selectbox(
        "Mock Verification Status", ["Success", "Fail"], key="verification_status_select"
    )
    no_match = st.checkbox("Force no load match", key="no_match_checkbox")

    run_clicked = st.button("Run NewLoad -> Bid Flow", type="primary", use_container_width=True)
    reset_clicked = st.button("Reset", use_container_width=True)

if run_clicked:
    if not is_authorized():
        if st.session_state.auth_locked_until > time.time():
            wait_seconds = int(st.session_state.auth_locked_until - time.time())
            st.session_state.status_line = f"Unauthorized. Locked for {wait_seconds}s."
        else:
            st.session_state.status_line = "Unauthorized."
    elif NON_LOCAL_MODE and not HOSTED_FMCSA_CONFIGURED:
        st.session_state.status_line = (
            "Trusted compliance endpoint is required in non-local mode "
            "(set FAXP_FMCSA_ADAPTER_BASE_URL)."
        )
    else:
        run_flow(
            response_type=response_type,
            provider=provider,
            verification_status=verification_status,
            no_match=no_match,
            rate_model=rate_model,
            bid_amount=bid_amount,
            mc_number=mc_number,
            fmcsa_source=fmcsa_source,
            policy_profile_id=policy_profile_id,
            risk_tier=int(risk_tier),
            mileage_dispute_policy=mileage_dispute_policy,
            mileage_abs_tolerance_miles=float(mileage_abs_tolerance_miles),
            mileage_rel_tolerance_ratio=float(mileage_rel_tolerance_ratio),
            exception_approved=bool(exception_approved),
            exception_approval_ref=exception_approval_ref,
        )

if reset_clicked:
    reset_state()

col1, col2, col3 = st.columns(3)
col1.metric("Status", st.session_state.status_line)
col2.metric("VerifiedBadge", st.session_state.verified_badge)
ver_status = (st.session_state.verification_result or {}).get("status", "N/A")
col3.metric("Verification", ver_status)
col4, col5 = st.columns(2)
col4.metric("Validated Messages", st.session_state.validated_messages)
col5.metric("Validation Errors", len(st.session_state.validation_errors))

if st.session_state.summary:
    st.success(st.session_state.summary)

st.subheader("Validation")
if st.session_state.validation_errors:
    st.error("One or more messages failed validation.")
    st.json(st.session_state.validation_errors)
else:
    st.success("All emitted messages passed FAXP validation.")

st.subheader("Protocol Message Types")
st.json(FaxpProtocol.MESSAGE_TYPES)

st.subheader("Verification Capabilities")
st.json(
    {
        "Broker": getattr(st.session_state.broker, "verification_capabilities", {}),
        "Carrier": getattr(st.session_state.carrier, "verification_capabilities", {}),
    }
)

st.subheader("Agent Identity")
st.json(
    {
        "BrokerName": getattr(st.session_state.broker, "name", "n/a"),
        "BrokerAgentID": st.session_state.get("broker_agent_id", "n/a"),
        "CarrierName": getattr(st.session_state.carrier, "name", "n/a"),
        "CarrierAgentID": st.session_state.get("carrier_agent_id", "n/a"),
        "IdentityBinding": "Envelope.FromAgentID/ToAgentID are signed and validated against key mapping.",
    }
)

st.subheader("Verifier Diagnostics")
diag = st.session_state.get("last_verifier_diagnostics", {})
if not diag:
    st.info("Run a flow to populate verifier diagnostics.")
else:
    diag_json = json.dumps(
        {
            "runId": diag.get("run_id", "n/a"),
            "provider": diag.get("provider", "n/a"),
            "complianceSource": diag.get("fmcsa_source", "n/a"),
            "fmcsaSource": diag.get("fmcsa_source", "n/a"),
            "hostedFmcsaConfigured": diag.get("hosted_fmcsa_configured"),
            "cloudSafeMode": diag.get("cloud_safe_mode"),
            "resultStatus": diag.get("result_status", "n/a"),
            "resultProvider": diag.get("result_provider", "n/a"),
            "resultSource": diag.get("result_source", "n/a"),
            "resultError": diag.get("result_error", ""),
            "policyProfile": diag.get("policy_profile_id", "n/a"),
            "riskTier": diag.get("risk_tier", "n/a"),
            "mileageDisputePolicy": diag.get("mileage_dispute_policy", "n/a"),
            "mileageAbsToleranceMiles": diag.get("mileage_abs_tolerance_miles", "n/a"),
            "mileageRelToleranceRatio": diag.get("mileage_rel_tolerance_ratio", "n/a"),
            "policyDispatchAuthorization": diag.get("policy_dispatch_authorization", "n/a"),
            "policyDecisionReasonCode": diag.get("policy_decision_reason_code", "n/a"),
            "policyRuleID": diag.get("policy_rule_id", "n/a"),
            "policyShouldBook": diag.get("policy_should_book", "n/a"),
            "mcNumber": diag.get("mc_number", ""),
            "timestamp": diag.get("timestamp", "n/a"),
        },
        indent=2,
    )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Configured Provider", diag.get("provider", "n/a"))
    c2.metric("Compliance Source", diag.get("fmcsa_source", "n/a"))
    c3.metric(
        "FMCSA Adapter",
        "Configured" if diag.get("hosted_fmcsa_configured") else "Missing",
    )
    c4.metric("Last Result", diag.get("result_status", "n/a"))
    st.caption(
        "Policy: "
        f"{diag.get('policy_profile_id', 'n/a')} | "
        f"RiskTier={diag.get('risk_tier', 'n/a')} | "
        f"Mileage={diag.get('mileage_dispute_policy', 'n/a')} | "
        f"Dispatch={diag.get('policy_dispatch_authorization', 'n/a')}"
    )
    run_id_value = str(diag.get("run_id", "n/a"))
    st.caption(f"RunID: {run_id_value}")
    if run_id_value and run_id_value != "n/a":
        render_copy_button("Copy RunID", run_id_value, "diag_copy_runid_button")
    st.caption(f"Updated: {diag.get('timestamp', 'n/a')}")
    render_copy_button("Copy diagnostics JSON", diag_json, "diag_copy_button")
    timestamp_safe = str(diag.get("timestamp", "now")).replace(":", "-")
    run_id_safe = str(diag.get("run_id", "run")).replace("/", "_")
    st.download_button(
        "Download diagnostics.json",
        data=diag_json,
        file_name=f"faxp_diagnostics_{run_id_safe}_{timestamp_safe}.json",
        mime="application/json",
    )
    support_bundle = {
        "generatedAt": now_utc(),
        "protocol": {
            "name": FaxpProtocol.NAME,
            "version": FaxpProtocol.VERSION,
        },
        "runtime": {
            "appMode": APP_MODE,
            "cloudSafeMode": CLOUD_SAFE_MODE,
            "hostedFmcsaConfigured": HOSTED_FMCSA_CONFIGURED,
            "maxVerificationsPerHour": MAX_VERIFICATION_CALLS_PER_HOUR,
        },
        "diagnostics": json.loads(diag_json),
        "history": [
            {
                "runId": row.get("run_id", "n/a"),
                "status": row.get("result_status", "n/a"),
                "provider": row.get("result_provider", row.get("provider", "n/a")),
                "source": row.get("result_source", row.get("fmcsa_source", "n/a")),
                "mcNumber": row.get("mc_number", ""),
                "timestamp": row.get("timestamp", "n/a"),
                "error": row.get("result_error", ""),
            }
            for row in st.session_state.get("verifier_diagnostics_history", [])
        ],
        "latestMessages": [
            redact_sensitive(msg)
            for msg in st.session_state.get("messages", [])[-5:]
        ],
        "validation": {
            "validatedMessages": st.session_state.get("validated_messages", 0),
            "validationErrors": st.session_state.get("validation_errors", []),
        },
        "policyDecision": st.session_state.get("policy_decision"),
    }
    support_bundle_json = json.dumps(support_bundle, indent=2)
    support_bundle_hash = hashlib.sha256(
        support_bundle_json.encode("utf-8")
    ).hexdigest()
    st.download_button(
        "Download support-bundle.json",
        data=support_bundle_json,
        file_name=f"faxp_support_bundle_{run_id_safe}_{timestamp_safe}.json",
        mime="application/json",
    )
    st.caption(f"Support bundle SHA256: `{support_bundle_hash}`")
    render_copy_button(
        "Copy support bundle hash",
        support_bundle_hash,
        "diag_copy_support_bundle_hash_button",
    )
    st.caption("Environment Health (non-secret)")
    st.table(
        [
            {"Check": "SIGNED_VERIFIER_REQUIRED", "Value": SIGNED_VERIFIER_REQUIRED},
            {"Check": "SIGNATURE_SCHEME", "Value": SIGNATURE_SCHEME},
            {"Check": "VERIFIER_SIGNATURE_SCHEME", "Value": VERIFIER_SIGNATURE_SCHEME},
            {"Check": "FMCSA_ADAPTER_CONFIGURED", "Value": HOSTED_FMCSA_CONFIGURED},
            {"Check": "CLOUD_SAFE_MODE", "Value": CLOUD_SAFE_MODE},
            {"Check": "APP_MODE", "Value": APP_MODE},
        ]
    )
    st.code(diag_json, language="json")
    if st.button("Clear History", key="clear_verifier_history_button"):
        st.session_state.verifier_diagnostics_history = []
        history_rows = []
    else:
        history_rows = st.session_state.get("verifier_diagnostics_history", [])
    if history_rows:
        st.caption("Recent Verifications (last 5)")
        st.table(
            [
                {
                    "RunID": row.get("run_id", "n/a"),
                    "Status": row.get("result_status", "n/a"),
                    "Provider": row.get("result_provider", row.get("provider", "n/a")),
                    "Source": row.get("result_source", row.get("fmcsa_source", "n/a")),
                    "MC": row.get("mc_number", ""),
                    "Updated": row.get("timestamp", "n/a"),
                    "Error": row.get("result_error", ""),
                }
                for row in history_rows
            ]
        )

st.subheader("AmendRequest (exists, not executed)")
st.json(st.session_state.get("amend_example", FaxpProtocol.amend_request_example("example-load-id")))

if st.session_state.get("search_results") is not None:
    st.subheader("Load Search Results")
    st.json(st.session_state.search_results)

if st.session_state.verification_result is not None:
    st.subheader("Verification Result")
    st.json(redact_sensitive(st.session_state.verification_result))

if st.session_state.policy_decision is not None:
    st.subheader("Policy Decision")
    st.json(redact_sensitive(st.session_state.policy_decision))

if st.session_state.execution_report is not None:
    st.subheader("Post-Booking Accessorials (Mock)")
    accessorial_policy = st.session_state.execution_report.get("AccessorialPolicy", {})
    allowed_types = accessorial_policy.get("AllowedTypes", [])
    current_total = accessorial_total(st.session_state.execution_report)
    st.caption(
        f"Allowed: {', '.join(allowed_types) or 'None'} | "
        f"RequiresApproval: {accessorial_policy.get('RequiresApproval', False)} | "
        f"MaxTotal: ${float(accessorial_policy.get('MaxTotal', 0.0)):.2f} | "
        f"ApprovedTotal: ${current_total:.2f}"
    )
    col_a, col_b = st.columns([1, 1])
    with col_a:
        accessorial_type = st.selectbox(
            "Accessorial Type",
            options=allowed_types or ["UnloadingFee"],
            key="accessorial_type",
        )
    with col_b:
        accessorial_amount = st.number_input(
            "Amount",
            min_value=0.0,
            value=75.0,
            step=5.0,
            format="%.2f",
            key="accessorial_amount",
        )
    accessorial_note = st.text_input(
        "Note",
        value=st.session_state.accessorial_note,
        key="accessorial_note",
        placeholder="Example: Receiver required hand-unload",
    )
    approve_clicked = st.button("Approve Accessorial", use_container_width=False)
    if approve_clicked:
        approve_accessorial(accessorial_type, accessorial_amount, accessorial_note)

    st.subheader("Execution Report")
    st.json(redact_sensitive(st.session_state.execution_report))

st.subheader("Message Log")
if not st.session_state.messages:
    st.info("Run the flow to see NewLoad, LoadSearch, BidRequest, BidResponse, and ExecutionReport messages.")
else:
    for idx, msg in enumerate(st.session_state.messages, start=1):
        st.markdown(f"**{idx}. {msg['MessageType']}** - {msg['From']} -> {msg['To']}")
        st.code(json.dumps(redact_sensitive(msg), indent=2), language="json")
