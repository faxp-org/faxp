#!/usr/bin/env python3
"""Regression checks for conformance/verifier_translator.py."""

from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from conformance.verifier_translator import (  # noqa: E402
    TranslationError,
    translate_verifier_payload,
)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def main() -> int:
    keyring = {"translator-kid-1": "translator-demo-secret"}
    fmcsa_payload = {
        "mcNumber": "498282",
        "carrier": {
            "operatingStatus": "ACTIVE",
            "hasCurrentInsurance": True,
            "interstateAuthorityOk": True,
        },
    }
    fmcsa_sig = hmac.new(
        keyring["translator-kid-1"].encode("utf-8"),
        _canonical_json(fmcsa_payload).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    wrapped_fmcsa = {
        "payload": fmcsa_payload,
        "signature": {
            "alg": "HMAC_SHA256",
            "kid": "translator-kid-1",
            "sig": fmcsa_sig,
        },
    }

    translated_fmcsa = translate_verifier_payload(
        "fmcsa",
        wrapped_fmcsa,
        source="hosted-adapter",
        signature_keys=keyring,
        require_signed_wrapper=True,
    )
    fmcsa_result = translated_fmcsa["VerificationResult"]
    _assert(fmcsa_result["status"] == "Success", "FMCSA translation should succeed")
    _assert(fmcsa_result["category"] == "Compliance", "FMCSA category mismatch")
    _assert(fmcsa_result["method"] == "AuthorityRecordCheck", "FMCSA method mismatch")
    _assert(
        fmcsa_result["provider"] == "compliance.authority-record.adapter",
        "FMCSA default provider mismatch",
    )
    _assert(
        translated_fmcsa["ProviderExtensions"]["mcNumber"] == "498282",
        "FMCSA provider extension mcNumber mismatch",
    )

    wrapped_fmcsa_bad_sig = {
        "payload": fmcsa_payload,
        "signature": {
            "alg": "HMAC_SHA256",
            "kid": "translator-kid-1",
            "sig": f"{fmcsa_sig}00",
        },
    }
    try:
        translate_verifier_payload(
            "fmcsa",
            wrapped_fmcsa_bad_sig,
            source="hosted-adapter",
            signature_keys=keyring,
            require_signed_wrapper=True,
        )
    except TranslationError:
        pass
    else:
        raise AssertionError("Expected signature verification failure for FMCSA wrapper.")

    biometric_payload = {
        "livenessPassed": True,
        "documentMatch": True,
        "confidence": 0.93,
        "sessionId": "session-abc",
    }
    translated_biometric = translate_verifier_payload(
        "biometric",
        biometric_payload,
        source="identity-adapter",
    )
    biometric_result = translated_biometric["VerificationResult"]
    _assert(biometric_result["status"] == "Success", "Biometric translation should succeed")
    _assert(biometric_result["category"] == "Biometric", "Biometric category mismatch")
    _assert(biometric_result["score"] == 93, "Biometric score normalization mismatch")

    generic_payload = {
        "status": "Success",
        "category": "Identity",
        "method": "DocumentOnly",
        "provider": "identity.document.adapter",
        "assuranceLevel": "AAL1",
        "score": 88,
        "token": "opaque-token",
    }
    translated_generic = translate_verifier_payload("generic", generic_payload, source="generic")
    _assert(
        translated_generic["VerificationResult"]["provider"] == "identity.document.adapter",
        "Generic provider passthrough mismatch",
    )
    _assert(
        "evidenceRef" in translated_generic["VerificationResult"],
        "Generic translation should backfill evidenceRef",
    )

    try:
        translate_verifier_payload("generic", {"status": "Success"}, source="generic")
    except TranslationError:
        pass
    else:
        raise AssertionError("Expected failure for missing neutral fields in generic translation.")

    for biometric_key in ("faceImage", "RAWBiometric", "face_image", "raw_biometric"):
        try:
            translate_verifier_payload(
                "generic",
                {
                    "status": "Success",
                    "category": "Biometric",
                    "method": "LivenessPlusDocument",
                    "provider": "identity.vendor",
                    "assuranceLevel": "AAL2",
                    "score": 97,
                    "token": "opaque-token",
                    "providerExtensions": {
                        biometric_key: "base64:RAW_BIOMETRIC_SAMPLE",
                        "sessionId": "abc",
                    },
                },
                source="generic",
            )
        except TranslationError as exc:
            _assert(
                "ProviderExtensions" in str(exc),
                "Expected biometric ProviderExtensions rejection message.",
            )
        else:
            raise AssertionError(
                f"Expected failure when ProviderExtensions contain biometric key {biometric_key!r}."
            )

    try:
        translate_verifier_payload(
            "generic",
            {
                "status": "Success",
                "category": "Biometric",
                "method": "LivenessPlusDocument",
                "provider": "identity.vendor",
                "assuranceLevel": "AAL2",
                "score": 97,
                "token": "opaque-token",
                "providerExtensions": {
                    "fаceimage": "base64:RAW_BIOMETRIC_SAMPLE",
                },
            },
            source="generic",
        )
    except TranslationError as exc:
        _assert(
            "non-ASCII key name" in str(exc),
            "Expected non-ASCII key rejection for ProviderExtensions.",
        )
    else:
        raise AssertionError("Expected failure for non-ASCII biometric key in ProviderExtensions.")

    try:
        translate_verifier_payload(
            "generic",
            {"payload": {}, "signature": "not-an-object"},
            source="generic",
            signature_keys=keyring,
            require_signed_wrapper=True,
        )
    except TranslationError as exc:
        _assert(
            "signature must be an object" in str(exc),
            "Expected explicit signature object-type rejection.",
        )
    else:
        raise AssertionError("Expected failure for non-object wrapper signature.")

    print("Verifier translator regression checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
