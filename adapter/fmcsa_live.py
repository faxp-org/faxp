#!/usr/bin/env python3
"""Live FMCSA lookup helpers for implementer-hosted adapter services."""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request


DEFAULT_EXPECTED_TOP_LEVEL_KEYS = {"content", "result", "data", "error", "errors"}
_DRIFT_LOCK = threading.Lock()
_DRIFT_WARNED_SIGNATURES: set[str] = set()


def _is_truthy(value: object) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "y"}


def _parse_expected_top_level_keys(raw_value: object) -> set[str]:
    keys = {
        str(part).strip().lower()
        for part in str(raw_value or "").split(",")
        if str(part).strip()
    }
    return keys or set(DEFAULT_EXPECTED_TOP_LEVEL_KEYS)


def _fmcsa_config() -> dict[str, object]:
    webkey = os.getenv("FAXP_FMCSA_WEBKEY", "").strip()
    api_base_url = os.getenv(
        "FAXP_FMCSA_API_BASE_URL",
        "https://mobile.fmcsa.dot.gov/qc/services",
    ).strip()
    timeout_raw = os.getenv("FAXP_FMCSA_API_TIMEOUT_SECONDS", "12").strip()
    try:
        timeout_seconds = int(timeout_raw)
    except ValueError:
        timeout_seconds = 12
    timeout_seconds = max(3, min(30, timeout_seconds))
    log_unknown_keys = _is_truthy(os.getenv("FAXP_FMCSA_LOG_UNKNOWN_KEYS", "1"))
    expected_keys = _parse_expected_top_level_keys(
        os.getenv(
            "FAXP_FMCSA_EXPECTED_TOP_LEVEL_KEYS",
            "content,result,data,error,errors",
        )
    )
    return {
        "webkey": webkey,
        "api_base_url": api_base_url,
        "timeout_seconds": timeout_seconds,
        "log_unknown_keys": log_unknown_keys,
        "expected_top_level_keys": expected_keys,
    }


def normalize_digits(value: object) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def normalize_mc(value: object) -> str:
    digits = normalize_digits(value)
    if not digits:
        return ""
    return digits.lstrip("0") or "0"


def unknown_fmcsa_top_level_keys(
    payload: object,
    expected_top_level_keys: set[str] | None = None,
) -> list[str]:
    if not isinstance(payload, dict):
        return []
    expected_keys = expected_top_level_keys or set(DEFAULT_EXPECTED_TOP_LEVEL_KEYS)
    unknown = []
    for key in payload.keys():
        normalized = str(key).strip().lower()
        if normalized and normalized not in expected_keys:
            unknown.append(str(key))
    return sorted(unknown)


def _log_fmcsa_contract_drift(
    endpoint: str,
    payload: object,
    *,
    log_unknown_keys: bool,
    expected_top_level_keys: set[str],
) -> None:
    if not log_unknown_keys:
        return
    unknown = unknown_fmcsa_top_level_keys(payload, expected_top_level_keys)
    if not unknown:
        return

    signature = f"{endpoint}|{','.join(unknown)}"
    with _DRIFT_LOCK:
        if signature in _DRIFT_WARNED_SIGNATURES:
            return
        _DRIFT_WARNED_SIGNATURES.add(signature)

    print(
        f"[WARN] FMCSA response contract drift detected from {endpoint}. "
        f"Unknown top-level keys: {unknown}",
        file=sys.stderr,
    )


def _status_is_active(value: object) -> bool:
    text = str(value or "").strip().upper()
    if not text:
        return False
    if "INACTIVE" in text or "NOT AUTH" in text or "OUT OF SERVICE" in text:
        return False
    if text in {"A", "ACT", "ACTIVE", "AUTHORIZED"}:
        return True
    if text.startswith("ACTIVE") or text.startswith("AUTH"):
        return True
    return False


def _value_indicates_present(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value > 0
    text = str(value or "").strip()
    if not text:
        return False
    normalized = text.upper().replace(",", "").replace("$", "")
    if normalized in {"NO", "N", "NONE", "FALSE", "0", "0.0", "0.00", "N/A", "NA"}:
        return False
    if normalized in {"YES", "Y", "TRUE", "ACTIVE", "AUTHORIZED"}:
        return True
    numeric_match = re.search(r"[-+]?\d*\.?\d+", normalized)
    if numeric_match:
        try:
            return float(numeric_match.group(0)) > 0
        except ValueError:
            return False
    return True


def _parse_bool_flag(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    text = str(value or "").strip().lower()
    if not text:
        return None
    if text in {"1", "true", "t", "yes", "y", "on", "active", "authorized"}:
        return True
    if text in {"0", "false", "f", "no", "n", "off", "inactive"}:
        return False
    return None


def _extract_first_value(mapping: dict, keys: list[str]) -> object:
    for key in keys:
        if key in mapping:
            value = mapping[key]
            if value is not None and value != "":
                return value
    return None


def _iter_dicts(value: object):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _iter_dicts(child)
        return
    if isinstance(value, list):
        for item in value:
            yield from _iter_dicts(item)


def _score_fmcsa_candidate(record: object, target_mc: str) -> int:
    if not isinstance(record, dict):
        return -1

    mc_value = _extract_first_value(
        record,
        ["docketNumber", "mcNumber", "mc_number", "docket_number", "docket", "mc"],
    )
    mc_digits = normalize_mc(mc_value)
    score = 0
    if target_mc and mc_digits == target_mc:
        score += 100
    elif mc_digits:
        score += 20

    if _extract_first_value(record, ["legalName", "carrierName", "name"]):
        score += 10
    if _extract_first_value(record, ["dotNumber", "usdotNumber", "usdot_number"]):
        score += 10
    if _extract_first_value(
        record,
        [
            "operatingStatus",
            "commonAuthorityStatus",
            "contractAuthorityStatus",
            "brokerAuthorityStatus",
            "authorityStatus",
            "allowedToOperate",
            "interstateAuthority",
            "interstateAuthorityOk",
        ],
    ):
        score += 10
    return score


def _record_looks_like_carrier_profile(record: dict) -> bool:
    keys = {
        "legalName",
        "carrierName",
        "name",
        "dotNumber",
        "usdotNumber",
        "usdot_number",
        "operatingStatus",
        "commonAuthorityStatus",
        "contractAuthorityStatus",
        "brokerAuthorityStatus",
        "bipdInsuranceOnFile",
        "bipdOnFile",
        "insuranceOnFile",
    }
    return any(key in record for key in keys)


def _select_fmcsa_candidate(payload: object, target_mc: str) -> dict | None:
    best_score = -1
    best_record = None
    for record in _iter_dicts(payload):
        if not _record_looks_like_carrier_profile(record):
            continue
        score = _score_fmcsa_candidate(record, target_mc)
        if score > best_score:
            best_score = score
            best_record = record
    return best_record if best_score >= 20 else None


def normalize_fmcsa_live_payload(payload: object, requested_mc: object) -> dict:
    target_mc = normalize_mc(requested_mc)
    record = _select_fmcsa_candidate(payload, target_mc)
    if not record:
        return {
            "found": False,
            "status": "Fail",
            "score": 10,
            "usdot_number": None,
            "mc_number": target_mc or None,
            "carrier_name": None,
            "operating_status": None,
            "has_current_insurance": False,
            "interstate_authority_ok": False,
        }

    mc_value = _extract_first_value(
        record,
        ["docketNumber", "mcNumber", "mc_number", "docket_number", "docket", "mc"],
    )
    mc_digits = normalize_mc(mc_value) or target_mc
    if target_mc and mc_digits != target_mc:
        return {
            "found": False,
            "status": "Fail",
            "score": 10,
            "usdot_number": None,
            "mc_number": target_mc,
            "carrier_name": None,
            "operating_status": None,
            "has_current_insurance": False,
            "interstate_authority_ok": False,
        }

    common_status = _extract_first_value(
        record,
        ["commonAuthorityStatus", "common_authority_status", "commonAuthority"],
    )
    contract_status = _extract_first_value(
        record,
        ["contractAuthorityStatus", "contract_authority_status", "contractAuthority"],
    )
    broker_status = _extract_first_value(
        record,
        ["brokerAuthorityStatus", "broker_authority_status", "brokerAuthority"],
    )
    operating_status_raw = _extract_first_value(
        record,
        ["operatingStatus", "authorityStatus", "status"],
    )

    authority_signals = [
        common_status,
        contract_status,
        broker_status,
        _extract_first_value(record, ["allowedToOperate", "interstateAuthority"]),
        operating_status_raw,
    ]
    active = any(_status_is_active(signal) for signal in authority_signals if signal is not None)

    status_parts = []
    if common_status is not None:
        status_parts.append(f"Common={common_status}")
    if contract_status is not None:
        status_parts.append(f"Contract={contract_status}")
    if broker_status is not None:
        status_parts.append(f"Broker={broker_status}")
    if not status_parts and operating_status_raw is not None:
        status_parts.append(str(operating_status_raw))
    operating_status = "; ".join(status_parts) if status_parts else None

    insurance_flags = []
    for key in [
        "bipdInsuranceOnFile",
        "bipdOnFile",
        "bipd_on_file",
        "bipdInsuranceAmountOnFile",
        "bipdAmountOnFile",
        "insuranceOnFileAmount",
        "cargoInsuranceOnFile",
        "insuranceOnFile",
        "hasCurrentInsurance",
        "has_current_insurance",
    ]:
        if key in record:
            value = record.get(key)
            parsed = _parse_bool_flag(value)
            if parsed is not None:
                insurance_flags.append(parsed)
            else:
                insurance_flags.append(_value_indicates_present(value))
    insurance_text = _extract_first_value(
        record,
        ["insuranceStatus", "bipdInsuranceStatus", "cargoInsuranceStatus"],
    )
    if not insurance_flags and insurance_text is not None:
        insurance_flags.append(_status_is_active(insurance_text))
    has_current_insurance = any(insurance_flags) if insurance_flags else False

    interstate_signals = []
    for key in [
        "interstateAuthorityOk",
        "interstate_authority_ok",
        "allowedToOperate",
        "commonAuthorityActive",
        "commonAuthority",
    ]:
        if key in record:
            parsed = _parse_bool_flag(record.get(key))
            if parsed is not None:
                interstate_signals.append(parsed)
    if not interstate_signals:
        interstate_signals.extend(
            _status_is_active(signal) for signal in authority_signals if signal is not None
        )
    interstate_authority_ok = any(interstate_signals) if interstate_signals else False

    score = 50
    if active:
        score += 20
    if has_current_insurance:
        score += 15
    if interstate_authority_ok:
        score += 15
    status = "Success" if (active and has_current_insurance and interstate_authority_ok) else "Fail"

    return {
        "found": True,
        "status": status,
        "score": int(score),
        "usdot_number": _extract_first_value(
            record,
            ["dotNumber", "usdotNumber", "usdot_number", "dot_number"],
        ),
        "mc_number": mc_digits,
        "carrier_name": _extract_first_value(record, ["legalName", "carrierName", "name"]),
        "operating_status": operating_status,
        "has_current_insurance": has_current_insurance,
        "interstate_authority_ok": interstate_authority_ok,
    }


def validate_fmcsa_payload(payload: object, requested_mc: object) -> None:
    if not isinstance(payload, dict):
        raise ValueError("FMCSA payload must be a JSON object.")

    required = {
        "found",
        "status",
        "score",
        "usdot_number",
        "mc_number",
        "carrier_name",
        "operating_status",
        "has_current_insurance",
        "interstate_authority_ok",
    }
    extras = set(payload.keys()) - required
    if extras:
        raise ValueError(f"FMCSA payload returned unexpected fields: {sorted(extras)}")

    missing = [field for field in required if field not in payload]
    if missing:
        raise ValueError(f"FMCSA payload missing fields: {missing}")

    if not isinstance(payload["found"], bool):
        raise ValueError("FMCSA payload 'found' must be boolean.")
    if payload["status"] not in {"Success", "Fail"}:
        raise ValueError("FMCSA payload 'status' must be Success or Fail.")
    if not isinstance(payload["score"], (int, float)) or not (0 <= payload["score"] <= 100):
        raise ValueError("FMCSA payload 'score' must be between 0 and 100.")
    if not isinstance(payload["has_current_insurance"], bool):
        raise ValueError("FMCSA payload 'has_current_insurance' must be boolean.")
    if not isinstance(payload["interstate_authority_ok"], bool):
        raise ValueError("FMCSA payload 'interstate_authority_ok' must be boolean.")

    target_mc = normalize_mc(requested_mc)
    returned_mc = normalize_mc(payload.get("mc_number"))
    if target_mc and returned_mc != target_mc:
        raise ValueError("FMCSA payload returned an MC number that does not match the request.")

    if payload["status"] == "Success" and not payload["found"]:
        raise ValueError("FMCSA payload returned Success with found=false.")


def lookup_fmcsa_live_api(
    mc_number: object,
    *,
    webkey: str | None = None,
    api_base_url: str | None = None,
    timeout_seconds: int | None = None,
    log_unknown_keys: bool | None = None,
    expected_top_level_keys: set[str] | None = None,
) -> dict:
    """Query FMCSA QCMobile API and return normalized compliance payload."""
    config = _fmcsa_config()
    resolved_webkey = str(webkey if webkey is not None else config["webkey"]).strip()
    resolved_base_url = str(
        api_base_url if api_base_url is not None else config["api_base_url"]
    ).strip()
    resolved_timeout = int(timeout_seconds if timeout_seconds is not None else config["timeout_seconds"])
    resolved_timeout = max(3, min(30, resolved_timeout))
    resolved_log_unknown_keys = (
        bool(log_unknown_keys)
        if log_unknown_keys is not None
        else bool(config["log_unknown_keys"])
    )
    resolved_expected_top_level_keys = (
        expected_top_level_keys
        if expected_top_level_keys is not None
        else set(config["expected_top_level_keys"])
    )

    target_mc = normalize_mc(mc_number)
    if not target_mc:
        return {"ok": False, "error": "No MC number provided for live FMCSA verification."}
    if not resolved_webkey:
        return {"ok": False, "error": "Missing FAXP_FMCSA_WEBKEY for live FMCSA verification."}

    base_url = resolved_base_url.rstrip("/")
    if not base_url:
        return {"ok": False, "error": "FAXP_FMCSA_API_BASE_URL is not configured."}

    endpoints = [
        f"{base_url}/carriers/docket-number/{urllib.parse.quote(target_mc)}",
        f"{base_url}/carriers/{urllib.parse.quote(target_mc)}",
    ]
    errors = []
    for endpoint in endpoints:
        url = endpoint + "?webKey=" + urllib.parse.quote(resolved_webkey)
        request = urllib.request.Request(
            url,
            headers={"Accept": "application/json"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=resolved_timeout) as response:
                raw_text = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            errors.append(f"{endpoint} -> HTTP {exc.code}: {body[:180]}")
            continue
        except urllib.error.URLError as exc:
            errors.append(f"{endpoint} -> {exc.reason}")
            continue
        except Exception as exc:
            errors.append(f"{endpoint} -> {exc}")
            continue

        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError:
            errors.append(f"{endpoint} -> non-JSON response.")
            continue

        _log_fmcsa_contract_drift(
            endpoint,
            payload,
            log_unknown_keys=resolved_log_unknown_keys,
            expected_top_level_keys=resolved_expected_top_level_keys,
        )
        normalized = normalize_fmcsa_live_payload(payload, target_mc)
        try:
            validate_fmcsa_payload(normalized, requested_mc=target_mc)
        except ValueError as exc:
            errors.append(f"{endpoint} -> response validation error: {exc}")
            continue

        normalized["ok"] = True
        return normalized

    joined = "; ".join(errors) if errors else "Unknown FMCSA response error."
    return {"ok": False, "error": f"live-fmcsa query failed: {joined}"}

