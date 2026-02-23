#!/usr/bin/env python3
"""Validate FAXP A2A bridge profile and translator contract artifacts."""

from __future__ import annotations

from pathlib import Path
import json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = PROJECT_ROOT / "docs" / "interop" / "A2A_COMPATIBILITY_PROFILE.md"
CONTRACT_PATH = PROJECT_ROOT / "conformance" / "a2a_translator_contract.json"

PROFILE_BEGIN = "<!-- A2A_PROFILE_BEGIN -->"
PROFILE_END = "<!-- A2A_PROFILE_END -->"

EXPECTED_MESSAGE_TYPES = [
    "NewLoad",
    "LoadSearch",
    "NewTruck",
    "TruckSearch",
    "BidRequest",
    "BidResponse",
    "ExecutionReport",
    "AmendRequest",
]


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _extract_json_block(document: str, begin: str, end: str) -> dict:
    start = document.find(begin)
    stop = document.find(end)
    _assert(start != -1 and stop != -1 and stop > start, "Missing A2A profile JSON block markers.")
    raw = document[start + len(begin) : stop].strip()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AssertionError("A2A profile JSON block is invalid.") from exc
    _assert(isinstance(payload, dict), "A2A profile JSON block must be an object.")
    return payload


def main() -> int:
    profile_doc = PROFILE_PATH.read_text(encoding="utf-8")
    profile = _extract_json_block(profile_doc, PROFILE_BEGIN, PROFILE_END)
    contract = _load_json(CONTRACT_PATH)

    _assert(profile.get("mode") == "TranslatorOnly", "A2A profile mode must be TranslatorOnly.")
    _assert(
        profile.get("coreProtocolChangesRequired") is False,
        "A2A profile must declare coreProtocolChangesRequired=false.",
    )
    _assert(
        profile.get("hostingModel") == "BuilderHosted",
        "A2A profile hostingModel must be BuilderHosted.",
    )

    profile_message_types = list(profile.get("requiredFaxpMessageTypes") or [])
    _assert(
        sorted(profile_message_types) == sorted(EXPECTED_MESSAGE_TYPES),
        "A2A profile requiredFaxpMessageTypes must match FAXP protocol message set.",
    )

    profile_mappings = profile.get("taskMappings") or {}
    _assert(isinstance(profile_mappings, dict) and profile_mappings, "A2A profile taskMappings missing.")
    for msg_type in EXPECTED_MESSAGE_TYPES:
        mapping = profile_mappings.get(msg_type) or {}
        _assert(mapping.get("a2aTaskType"), f"A2A profile missing a2aTaskType for {msg_type}.")

    _assert(
        contract.get("mode") == "TranslatorOnly",
        "a2a_translator_contract mode must be TranslatorOnly.",
    )
    _assert(
        contract.get("coreProtocolChangesRequired") is False,
        "a2a_translator_contract must declare coreProtocolChangesRequired=false.",
    )
    _assert(
        contract.get("hostingModel") == "BuilderHosted",
        "a2a_translator_contract hostingModel must be BuilderHosted.",
    )

    required_envelope_fields = list(contract.get("requiredEnvelopeFields") or [])
    for field in [
        "Protocol",
        "ProtocolVersion",
        "MessageType",
        "From",
        "To",
        "Timestamp",
        "MessageID",
        "Nonce",
        "Body",
    ]:
        _assert(field in required_envelope_fields, f"Missing required envelope field in contract: {field}")

    contract_mappings = contract.get("mappings") or {}
    _assert(isinstance(contract_mappings, dict) and contract_mappings, "Contract mappings missing.")
    _assert(
        sorted(contract_mappings.keys()) == sorted(EXPECTED_MESSAGE_TYPES),
        "Contract mappings must cover all FAXP message types.",
    )
    for msg_type, mapping in contract_mappings.items():
        _assert(mapping.get("a2aTaskType"), f"Contract missing a2aTaskType for {msg_type}.")
        required_body_fields = mapping.get("requiredBodyFields") or []
        _assert(
            isinstance(required_body_fields, list) and required_body_fields,
            f"Contract requiredBodyFields missing for {msg_type}.",
        )

    controls = contract.get("securityControls") or {}
    expected_controls = {
        "preserveFaxpSignatures": True,
        "verifyReplayAndTtlBeforeTranslation": True,
        "rejectUnmappedTaskTypes": True,
        "requireDeterministicRoundTrip": True,
    }
    for key, expected_value in expected_controls.items():
        _assert(
            controls.get(key) is expected_value,
            f"Contract securityControls.{key} must be {expected_value}.",
        )

    print("A2A profile compatibility checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
