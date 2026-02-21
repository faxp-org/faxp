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
    DEFAULT_CARRIER_FINDER_PATH,
    FaxpProtocol,
    build_envelope,
    default_bid_amount,
    format_rate,
    negotiate_verification_capability,
    redact_sensitive,
    get_protocol_run_id,
    reset_protocol_runtime_state,
    resolve_allowed_carrier_finder_path,
    run_verification,
    set_protocol_run_id,
    validate_envelope,
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
LIVE_FMCSA_CONFIGURED = bool(os.getenv("FAXP_FMCSA_WEBKEY", "").strip())
MAX_AUTH_FAILURES = int(os.getenv("FAXP_AUTH_MAX_FAILURES", "5"))
AUTH_LOCKOUT_SECONDS = int(os.getenv("FAXP_AUTH_LOCKOUT_SECONDS", "300"))
GLOBAL_VERIFICATION_CALL_TIMES = []
QUICK_PRESETS = {
    "FMCSA live (MC 498282)": {
        "provider": "FMCSA",
        "rate_model": "PerMile",
        "bid_amount": float(default_bid_amount("PerMile")),
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
        "bid_amount": float(default_bid_amount("PerMile")),
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
        "bid_amount": float(default_bid_amount("PerMile")),
        "response_type": "Accept",
        "verification_status": "Success",
        "no_match": False,
        "mc_number": "",
    },
    "Forced fail demo": {
        "provider": "MockBiometricProvider",
        "rate_model": "PerMile",
        "bid_amount": float(default_bid_amount("PerMile")),
        "response_type": "Accept",
        "verification_status": "Fail",
        "no_match": False,
        "mc_number": "",
    },
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
    defaults = {
        "quick_preset_select": "MockBiometric success",
        "rate_model_select": "PerMile",
        "bid_amount_input": float(default_bid_amount("PerMile")),
        "response_type_select": "Accept",
        "provider_local_select": "FMCSA",
        "provider_cloud_select": "MockBiometricProvider",
        "fmcsa_source_select_local": "carrier-finder",
        "fmcsa_source_select_cloud": "authority-mock",
        "mc_number_input": "498282",
        "verification_status_select": "Success",
        "no_match_checkbox": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def apply_quick_preset(preset_name):
    preset = QUICK_PRESETS.get(preset_name)
    if not preset:
        return
    st.session_state.rate_model_select = preset["rate_model"]
    st.session_state.bid_amount_input = float(preset["bid_amount"])
    st.session_state.response_type_select = preset["response_type"]
    st.session_state.verification_status_select = preset["verification_status"]
    st.session_state.no_match_checkbox = bool(preset["no_match"])
    st.session_state.mc_number_input = str(preset.get("mc_number", ""))

    provider = preset["provider"]
    if provider == "FMCSA":
        st.session_state.provider_local_select = "FMCSA"
        st.session_state.provider_cloud_select = "FMCSA (Authority)"
        st.session_state.fmcsa_source_select_local = preset.get(
            "fmcsa_source_local", "carrier-finder"
        )
        cloud_source = preset.get("fmcsa_source_cloud", "authority-mock")
        if cloud_source == "live-fmcsa" and not LIVE_FMCSA_CONFIGURED:
            cloud_source = "authority-mock"
        st.session_state.fmcsa_source_select_cloud = cloud_source
    else:
        st.session_state.provider_local_select = "MockBiometricProvider"
        st.session_state.provider_cloud_select = "MockBiometricProvider"


def reset_state():
    existing_history = st.session_state.get("verifier_diagnostics_history", [])
    existing_access_key = st.session_state.get("access_key_input", "")
    reset_protocol_runtime_state()
    st.session_state.broker = BrokerAgent("Broker Agent")
    st.session_state.carrier = CarrierAgent("Carrier Agent")
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


def secure_carrier_finder_path():
    try:
        return resolve_allowed_carrier_finder_path(DEFAULT_CARRIER_FINDER_PATH)
    except ValueError:
        return None


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

    st.session_state.summary = (
        "Booking completed successfully - "
        f"RunID: {get_protocol_run_id()}, "
        f"LoadID: {report['LoadID']}, "
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

    report["Accessorials"].append(
        {
            "Type": accessorial_type,
            "Amount": round(float(amount), 2),
            "Currency": policy.get("Currency", "USD"),
            "Status": "Approved",
            "ApprovedAt": now_utc(),
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
    carrier_finder_path,
    fmcsa_source,
):
    reset_state()
    run_id = set_protocol_run_id()
    broker = st.session_state.broker
    carrier = st.session_state.carrier
    st.session_state.last_verifier_diagnostics = {
        "run_id": run_id,
        "provider": provider,
        "fmcsa_source": fmcsa_source if provider == "FMCSA" else "n/a",
        "mc_number": (mc_number or "").strip() if provider == "FMCSA" else "",
        "live_fmcsa_configured": LIVE_FMCSA_CONFIGURED,
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
            carrier_finder_path=carrier_finder_path,
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
    push_verifier_history(diag)

    if verification_result.get("status") != "Success":
        reason = verification_result.get("error")
        if reason:
            st.session_state.status_line = f"Verification unavailable: {reason}"
        else:
            st.session_state.status_line = "Verification failed."
        return

    # 6) ExecutionReport
    execution_report = broker.create_execution_report(
        load_id=bid_request["LoadID"],
        bid_request=bid_request,
        verified_badge=verified_badge,
        verification_result=verification_result,
    )
    if not append_message(broker.name, carrier.name, "ExecutionReport", execution_report):
        return

    # 7) Complete for both parties
    carrier.mark_booking_complete(execution_report)
    st.session_state.execution_report = execution_report
    st.session_state.status_line = "Booking completed."
    update_summary_from_report()


st.set_page_config(page_title="FAXP Demo", layout="wide")
st.title(f"FAXP v{FaxpProtocol.VERSION} - Freight Agent eXchange Protocol Demo")
st.caption("Mock FAXP client embedded in Streamlit: NewLoad -> Bid -> Verification -> ExecutionReport")

if "broker" not in st.session_state:
    reset_state()

ensure_sidebar_defaults()

if NON_LOCAL_MODE and not ACCESS_KEY:
    st.error("Secure mode requires FAXP_STREAMLIT_ACCESS_KEY.")
    st.stop()

with st.sidebar:
    st.header("Scenario")
    st.caption(
        f"Runtime mode: {'cloud-safe' if CLOUD_SAFE_MODE else 'full/local'} "
        f"(FAXP_APP_MODE={APP_MODE})"
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
    rate_model = st.selectbox("Rate Model", ["PerMile", "Flat"], key="rate_model_select")
    bid_amount = st.number_input(
        "Bid Amount",
        min_value=0.0,
        value=float(st.session_state.bid_amount_input),
        step=0.01,
        format="%.2f",
        help="PerMile uses $/mile. Flat uses total trip amount.",
        key="bid_amount_input",
    )
    response_type = st.selectbox(
        "BidResponse", ["Accept", "Counter", "Reject"], key="response_type_select"
    )
    if CLOUD_SAFE_MODE:
        provider_choice = st.selectbox(
            "Verification Provider",
            ["MockBiometricProvider", "FMCSA (Authority)"],
            key="provider_cloud_select",
            help="Cloud-safe mode disables local-only verifier paths.",
        )
        provider = "FMCSA" if provider_choice.startswith("FMCSA") else "MockBiometricProvider"
    else:
        provider = st.selectbox(
            "Verification Provider",
            ["FMCSA", "MockBiometricProvider", "iDenfy (Legacy Alias)"],
            key="provider_local_select",
            help="iDenfy label is maintained as a legacy alias.",
        )
        if provider == "iDenfy (Legacy Alias)":
            provider = "iDenfy"

    if provider == "FMCSA":
        if CLOUD_SAFE_MODE:
            options = ["authority-mock"]
            if LIVE_FMCSA_CONFIGURED:
                options.insert(0, "live-fmcsa")
            if st.session_state.get("fmcsa_source_select_cloud") not in options:
                st.session_state.fmcsa_source_select_cloud = options[0]
            cloud_fmcsa_mode = st.selectbox(
                "FMCSA Source",
                options,
                key="fmcsa_source_select_cloud",
                help="authority-mock uses local mock compliance scoring only.",
            )
            if cloud_fmcsa_mode == "live-fmcsa":
                fmcsa_source = "live-fmcsa"
                mc_number = st.text_input("MC Number", key="mc_number_input")
                st.caption("Live FMCSA mode enabled via FAXP_FMCSA_WEBKEY.")
            else:
                fmcsa_source = "carrier-finder"
                mc_number = ""
                st.caption("FMCSA authority-mock mode (no external API call).")
            carrier_finder_path = None
        else:
            fmcsa_source = st.selectbox(
                "FMCSA Source",
                ["carrier-finder", "live-fmcsa"],
                key="fmcsa_source_select_local",
                help="carrier-finder uses local adapter; live-fmcsa calls FMCSA QCMobile API directly.",
            )
            mc_number = st.text_input("MC Number", key="mc_number_input")
            if fmcsa_source == "carrier-finder":
                carrier_finder_path = secure_carrier_finder_path()
                st.caption(f"carrier-finder path: {carrier_finder_path or '[not allowlisted]'}")
            else:
                carrier_finder_path = None
                if LIVE_FMCSA_CONFIGURED:
                    st.caption("Live FMCSA mode enabled via FAXP_FMCSA_WEBKEY.")
                else:
                    st.caption("Missing FAXP_FMCSA_WEBKEY; live FMCSA calls will fail closed.")
    else:
        fmcsa_source = "carrier-finder"
        mc_number = ""
        carrier_finder_path = None if CLOUD_SAFE_MODE else secure_carrier_finder_path()

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
    elif (
        provider == "FMCSA"
        and fmcsa_source == "carrier-finder"
        and not CLOUD_SAFE_MODE
        and not carrier_finder_path
    ):
        st.session_state.status_line = "carrier-finder path is not allowlisted."
    else:
        run_flow(
            response_type=response_type,
            provider=provider,
            verification_status=verification_status,
            no_match=no_match,
            rate_model=rate_model,
            bid_amount=bid_amount,
            mc_number=mc_number,
            carrier_finder_path=carrier_finder_path,
            fmcsa_source=fmcsa_source,
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

st.subheader("Verifier Diagnostics")
diag = st.session_state.get("last_verifier_diagnostics", {})
if not diag:
    st.info("Run a flow to populate verifier diagnostics.")
else:
    diag_json = json.dumps(
        {
            "runId": diag.get("run_id", "n/a"),
            "provider": diag.get("provider", "n/a"),
            "fmcsaSource": diag.get("fmcsa_source", "n/a"),
            "liveFmcsaConfigured": diag.get("live_fmcsa_configured"),
            "cloudSafeMode": diag.get("cloud_safe_mode"),
            "resultStatus": diag.get("result_status", "n/a"),
            "resultProvider": diag.get("result_provider", "n/a"),
            "resultSource": diag.get("result_source", "n/a"),
            "resultError": diag.get("result_error", ""),
            "mcNumber": diag.get("mc_number", ""),
            "timestamp": diag.get("timestamp", "n/a"),
        },
        indent=2,
    )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Configured Provider", diag.get("provider", "n/a"))
    c2.metric("FMCSA Source", diag.get("fmcsa_source", "n/a"))
    c3.metric(
        "FMCSA WebKey",
        "Configured" if diag.get("live_fmcsa_configured") else "Missing",
    )
    c4.metric("Last Result", diag.get("result_status", "n/a"))
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
            "liveFmcsaConfigured": LIVE_FMCSA_CONFIGURED,
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
            {"Check": "FMCSA_WEBKEY_CONFIGURED", "Value": LIVE_FMCSA_CONFIGURED},
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
