#!/usr/bin/env python3
"""FAXP Streamlit demo: NewLoad -> Bid -> Verification -> ExecutionReport."""

from datetime import datetime, timezone
import json
import os
import secrets
import time

import streamlit as st

from faxp_mvp_simulation import (
    BrokerAgent,
    CarrierAgent,
    DEFAULT_CARRIER_FINDER_PATH,
    FaxpProtocol,
    build_envelope,
    default_bid_amount,
    format_rate,
    redact_sensitive,
    reset_protocol_runtime_state,
    resolve_allowed_carrier_finder_path,
    run_verification,
    validate_envelope,
)

ACCESS_KEY = os.getenv("FAXP_STREAMLIT_ACCESS_KEY", "").strip()
MAX_VERIFICATION_CALLS_PER_HOUR = int(os.getenv("FAXP_MAX_VERIFICATIONS_PER_HOUR", "30"))
APP_MODE = os.getenv("FAXP_APP_MODE", "local").strip().lower()
NON_LOCAL_MODE = APP_MODE not in {"local", "dev", "development"}
MAX_AUTH_FAILURES = int(os.getenv("FAXP_AUTH_MAX_FAILURES", "5"))
AUTH_LOCKOUT_SECONDS = int(os.getenv("FAXP_AUTH_LOCKOUT_SECONDS", "300"))
GLOBAL_VERIFICATION_CALL_TIMES = []


def now_utc():
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def envelope(sender, receiver, message_type, body):
    return build_envelope(sender, receiver, message_type, body)


def reset_state():
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
    broker = st.session_state.broker
    carrier = st.session_state.carrier

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
        return
    st.session_state.verification_result = verification_result
    st.session_state.verified_badge = verified_badge

    if verification_result.get("status") != "Success":
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

if NON_LOCAL_MODE and not ACCESS_KEY:
    st.error("Secure mode requires FAXP_STREAMLIT_ACCESS_KEY.")
    st.stop()

with st.sidebar:
    st.header("Scenario")
    if ACCESS_KEY:
        st.text_input("Access Key", type="password", key="access_key_input")
    rate_model = st.selectbox("Rate Model", ["PerMile", "Flat"], index=0)
    bid_amount = st.number_input(
        "Bid Amount",
        min_value=0.0,
        value=float(default_bid_amount(rate_model)),
        step=0.01,
        format="%.2f",
        help="PerMile uses $/mile. Flat uses total trip amount.",
    )
    response_type = st.selectbox("BidResponse", ["Accept", "Counter", "Reject"], index=0)
    provider = st.selectbox("Verification Provider", ["FMCSA", "iDenfy"], index=0)

    if provider == "FMCSA":
        fmcsa_source = st.selectbox(
            "FMCSA Source",
            ["carrier-finder", "live-fmcsa"],
            index=0,
            help="live-fmcsa is a placeholder for future direct API integration.",
        )
        mc_number = st.text_input("MC Number", value="498282")
        carrier_finder_path = secure_carrier_finder_path()
        st.caption(f"carrier-finder path: {carrier_finder_path or '[not allowlisted]'}")
    else:
        fmcsa_source = "carrier-finder"
        mc_number = ""
        carrier_finder_path = secure_carrier_finder_path()

    verification_status = st.selectbox("Mock Verification Status", ["Success", "Fail"], index=0)
    no_match = st.checkbox("Force no load match", value=False)

    run_clicked = st.button("Run NewLoad -> Bid Flow", type="primary", use_container_width=True)
    reset_clicked = st.button("Reset", use_container_width=True)

if run_clicked:
    if not is_authorized():
        if st.session_state.auth_locked_until > time.time():
            wait_seconds = int(st.session_state.auth_locked_until - time.time())
            st.session_state.status_line = f"Unauthorized. Locked for {wait_seconds}s."
        else:
            st.session_state.status_line = "Unauthorized."
    elif provider == "FMCSA" and not carrier_finder_path:
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
