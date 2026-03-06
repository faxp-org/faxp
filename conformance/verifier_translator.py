#!/usr/bin/env python3
"""Reference verifier translator wrapper for provider-native payloads."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import json
import re


ALLOWED_STATUSES = {"Success", "Fail", "Pending"}
FORBIDDEN_BIOMETRIC_FIELDS = {
    "faceimage",
    "selfieimage",
    "documentimage",
    "biometrictemplate",
    "rawbiometric",
    "fingerprintimage",
    "irisimage",
}


class TranslationError(ValueError):
    """Raised when provider-native payload cannot be translated safely."""


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _now_utc() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _sha256_ref(value: object) -> str:
    digest = hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()
    return f"sha256:{digest[:24]}"


def _normalize_key(key: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(key).strip().lower())


def _assert_ascii_keys(value: object, context: str) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if not str(key).isascii():
                raise TranslationError(f"{context} contains non-ASCII key name: {key!r}")
            _assert_ascii_keys(item, context)
        return
    if isinstance(value, list):
        for item in value:
            _assert_ascii_keys(item, context)


def _contains_forbidden_biometric(value: object) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if _normalize_key(key) in FORBIDDEN_BIOMETRIC_FIELDS:
                return True
            if _contains_forbidden_biometric(item):
                return True
        return False
    if isinstance(value, list):
        return any(_contains_forbidden_biometric(item) for item in value)
    return False


def _coerce_score(value: object, default: int) -> int:
    if value is None:
        return int(default)
    if isinstance(value, (int, float)):
        if 0 <= float(value) <= 1:
            return int(round(float(value) * 100))
        return int(round(float(value)))
    raise TranslationError("Score must be numeric.")


def _require_neutral_fields(result: dict) -> None:
    required = [
        "status",
        "category",
        "method",
        "provider",
        "assuranceLevel",
        "score",
        "token",
        "evidenceRef",
        "verifiedAt",
    ]
    missing = [field for field in required if field not in result]
    if missing:
        raise TranslationError(f"Missing required neutral verification fields: {missing}")
    if result["status"] not in ALLOWED_STATUSES:
        raise TranslationError("Verification status must be Success, Fail, or Pending.")
    score = result["score"]
    if not isinstance(score, (int, float)) or not (0 <= float(score) <= 100):
        raise TranslationError("Verification score must be between 0 and 100.")
    if _contains_forbidden_biometric(result):
        raise TranslationError("Raw biometric artifacts are not allowed in VerificationResult.")


def _verify_signed_wrapper(
    payload: dict,
    signature: dict | None,
    *,
    signature_keys: dict | None,
    require_signed_wrapper: bool,
) -> None:
    if not signature and not require_signed_wrapper:
        return
    if not signature:
        raise TranslationError("Signed wrapper is required but signature is missing.")
    if not isinstance(signature, dict):
        raise TranslationError("Wrapper signature must be an object.")
    if not signature_keys:
        raise TranslationError("No signature keyring provided for signed wrapper validation.")
    alg = str(signature.get("alg") or "").strip().upper()
    kid = str(signature.get("kid") or "").strip()
    sig = str(signature.get("sig") or "").strip()
    if alg != "HMAC_SHA256":
        raise TranslationError("Only HMAC_SHA256 wrapper signatures are supported by translator.")
    if not kid or kid not in signature_keys:
        raise TranslationError("Wrapper signature key ID is missing or untrusted.")
    expected = hmac.new(
        str(signature_keys[kid]).encode("utf-8"),
        _canonical_json(payload).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise TranslationError("Wrapper signature verification failed.")


def _unwrap_provider_payload(
    raw_payload: dict,
    *,
    signature_keys: dict | None,
    require_signed_wrapper: bool,
) -> dict:
    if not isinstance(raw_payload, dict):
        raise TranslationError("Provider payload must be an object.")
    if "payload" in raw_payload:
        payload = raw_payload.get("payload")
        if not isinstance(payload, dict):
            raise TranslationError("Wrapped provider payload must include object field 'payload'.")
        _verify_signed_wrapper(
            payload,
            raw_payload.get("signature"),
            signature_keys=signature_keys,
            require_signed_wrapper=require_signed_wrapper,
        )
        return payload
    if require_signed_wrapper:
        raise TranslationError("Signed wrapper required but 'payload' wrapper was not provided.")
    return raw_payload


def _translate_fmcsa(payload: dict, provider: str, source: str) -> tuple[dict, dict]:
    mc_number = (
        payload.get("mcNumber")
        or payload.get("mc")
        or payload.get("mc_number")
        or ""
    )
    operating_status = str(
        payload.get("operatingStatus")
        or (payload.get("carrier") or {}).get("operatingStatus")
        or ""
    ).upper()
    has_current_insurance = bool(
        payload.get("hasCurrentInsurance")
        if "hasCurrentInsurance" in payload
        else (payload.get("carrier") or {}).get("hasCurrentInsurance")
    )
    interstate_ok = bool(
        payload.get("interstateAuthorityOk")
        if "interstateAuthorityOk" in payload
        else (payload.get("carrier") or {}).get("interstateAuthorityOk")
    )
    active = operating_status in {"ACTIVE", "A", "ACT", "AUTHORIZED"}

    status = str(payload.get("status") or "").strip()
    if status not in ALLOWED_STATUSES:
        status = "Success" if (active and has_current_insurance and interstate_ok) else "Fail"

    score = _coerce_score(payload.get("score"), 0)
    if "score" not in payload:
        score = 50 + (20 if active else 0) + (15 if has_current_insurance else 0) + (15 if interstate_ok else 0)
    token = str(payload.get("token") or f"compliance-{hashlib.sha256(str(mc_number).encode('utf-8')).hexdigest()[:14]}")

    verification_result = {
        "status": status,
        "category": "Compliance",
        "method": "AuthorityRecordCheck",
        "provider": provider,
        "assuranceLevel": "AAL1",
        "score": int(score),
        "token": token,
        "evidenceRef": str(payload.get("evidenceRef") or _sha256_ref(payload)),
        "verifiedAt": str(payload.get("verifiedAt") or _now_utc()),
        "source": source,
    }

    provider_extensions = {
        "sourceAuthority": "FMCSA",
        "mcNumber": str(mc_number),
        "carrier": payload.get("carrier", {}),
    }
    if payload.get("error"):
        provider_extensions["error"] = str(payload["error"])
    return verification_result, provider_extensions


def _translate_biometric(payload: dict, provider: str, source: str) -> tuple[dict, dict]:
    liveness_passed = bool(payload.get("livenessPassed", False))
    document_match = bool(payload.get("documentMatch", False))
    status = str(payload.get("status") or "").strip()
    if status not in ALLOWED_STATUSES:
        status = "Success" if (liveness_passed and document_match) else "Fail"
    score = _coerce_score(payload.get("score", payload.get("confidence")), 0)
    if payload.get("score") is None and payload.get("confidence") is None:
        score = 92 if status == "Success" else 40
    token = str(payload.get("token") or f"biometric-{hashlib.sha256(_canonical_json(payload).encode('utf-8')).hexdigest()[:14]}")

    verification_result = {
        "status": status,
        "category": "Biometric",
        "method": "LivenessPlusDocument",
        "provider": provider,
        "assuranceLevel": str(payload.get("assuranceLevel") or "AAL2"),
        "score": int(score),
        "token": token,
        "evidenceRef": str(payload.get("evidenceRef") or _sha256_ref(payload)),
        "verifiedAt": str(payload.get("verifiedAt") or _now_utc()),
        "source": source,
    }
    provider_extensions = {
        "sessionId": payload.get("sessionId", ""),
        "vendorReference": payload.get("vendorReference", ""),
    }
    if payload.get("error"):
        provider_extensions["error"] = str(payload["error"])
    return verification_result, provider_extensions


def _translate_generic(payload: dict, provider: str, source: str) -> tuple[dict, dict]:
    result = dict(payload)
    if "provider" not in result:
        result["provider"] = provider
    if "verifiedAt" not in result:
        result["verifiedAt"] = _now_utc()
    if "evidenceRef" not in result:
        result["evidenceRef"] = _sha256_ref(payload)
    if "source" not in result:
        result["source"] = source
    extensions = dict(result.pop("providerExtensions", {})) if isinstance(result.get("providerExtensions"), dict) else {}
    return result, extensions


def translate_verifier_payload(
    provider_kind: str,
    raw_payload: dict,
    *,
    source: str,
    provider_id: str | None = None,
    signature_keys: dict | None = None,
    require_signed_wrapper: bool = False,
) -> dict:
    """
    Translate provider-native payload into neutral FAXP verification shape.

    Returns:
    {
      "VerificationResult": {neutral required fields...},
      "ProviderExtensions": {optional vendor-specific metadata}
    }
    """
    payload = _unwrap_provider_payload(
        raw_payload,
        signature_keys=signature_keys,
        require_signed_wrapper=require_signed_wrapper,
    )
    normalized_kind = str(provider_kind or "").strip().lower()
    provider = str(provider_id or "").strip()
    if not provider:
        provider = {
            "fmcsa": "compliance.authority-record.adapter",
            "biometric": "identity.liveness-document.adapter",
            "generic": "provider.generic.adapter",
        }.get(normalized_kind, "provider.generic.adapter")

    if normalized_kind == "fmcsa":
        verification_result, provider_extensions = _translate_fmcsa(payload, provider, source)
    elif normalized_kind == "biometric":
        verification_result, provider_extensions = _translate_biometric(payload, provider, source)
    elif normalized_kind == "generic":
        verification_result, provider_extensions = _translate_generic(payload, provider, source)
    else:
        raise TranslationError(f"Unsupported provider kind: {provider_kind!r}")

    _require_neutral_fields(verification_result)
    _assert_ascii_keys(verification_result, "VerificationResult")
    _assert_ascii_keys(provider_extensions, "ProviderExtensions")
    if _contains_forbidden_biometric(provider_extensions):
        raise TranslationError("Raw biometric artifacts are not allowed in ProviderExtensions.")
    return {
        "VerificationResult": verification_result,
        "ProviderExtensions": provider_extensions,
    }
