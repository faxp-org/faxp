#!/usr/bin/env python3
"""Reference FAXP<->A2A bridge translator (translator-layer only)."""

from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
import json
import re


DEFAULT_CONTRACT_PATH = Path(__file__).resolve().parent / "a2a_translator_contract.json"
MAX_SANITIZE_DEPTH = 256
MAX_SANITIZE_NODES = 20000


class A2ABridgeError(ValueError):
    """Raised when bridge translation cannot satisfy contract guarantees."""


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_contract(path: str | Path | None = None) -> dict:
    contract_path = Path(path).expanduser().resolve() if path else DEFAULT_CONTRACT_PATH
    payload = _load_json(contract_path)
    if not isinstance(payload, dict):
        raise A2ABridgeError("A2A translator contract must be a JSON object.")
    return payload


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise A2ABridgeError(message)


def _validate_envelope(envelope: dict, contract: dict) -> None:
    _assert(isinstance(envelope, dict), "FAXP envelope must be an object.")
    required_fields = list(contract.get("requiredEnvelopeFields") or [])
    for field in required_fields:
        _assert(field in envelope, f"Missing required envelope field: {field}")

    message_type = str(envelope.get("MessageType") or "").strip()
    mappings = contract.get("mappings") or {}
    _assert(message_type in mappings, f"Unmapped FAXP MessageType: {message_type!r}")

    body = envelope.get("Body")
    _assert(isinstance(body, dict), "FAXP envelope Body must be an object.")

    required_body_fields = list((mappings[message_type] or {}).get("requiredBodyFields") or [])
    for field in required_body_fields:
        _assert(field in body, f"Missing required Body field for {message_type}: {field}")
    if message_type == "ExecutionReport" and "VerificationResult" in body:
        _assert(
            isinstance(body.get("VerificationResult"), dict),
            "ExecutionReport Body.VerificationResult must be an object when present.",
        )


def _a2a_task_type_to_message_type(contract: dict) -> dict[str, str]:
    mappings = contract.get("mappings") or {}
    reverse: dict[str, str] = {}
    for message_type, mapping in mappings.items():
        task_type = str((mapping or {}).get("a2aTaskType") or "").strip()
        if task_type:
            reverse[task_type] = str(message_type)
    return reverse


def faxp_to_a2a_task(envelope: dict, *, contract: dict | None = None) -> dict:
    """Translate one FAXP envelope to an A2A task payload while preserving reversibility."""
    contract_payload = contract or load_contract()
    _validate_envelope(envelope, contract_payload)

    mappings = contract_payload.get("mappings") or {}
    message_type = str(envelope["MessageType"])
    mapping = mappings[message_type]

    task = {
        "a2aTaskType": str(mapping["a2aTaskType"]),
        "taskId": f"faxp-{envelope['MessageID']}",
        "contextId": str(envelope["MessageID"]),
        "from": str(envelope["From"]),
        "to": str(envelope["To"]),
        "createdAt": str(envelope["Timestamp"]),
        "payload": {
            "faxpEnvelope": deepcopy(envelope),
        },
        "metadata": {
            "bridgeMode": str(contract_payload.get("mode") or "TranslatorOnly"),
            "faxpMessageType": message_type,
            "faxpProtocol": str(envelope.get("Protocol") or "FAXP"),
            "faxpProtocolVersion": str(envelope.get("ProtocolVersion") or ""),
            "faxpMessageId": str(envelope["MessageID"]),
            "faxpNonce": str(envelope["Nonce"]),
        },
    }
    return task


def _token_ref(value: object) -> str:
    digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()
    return f"sha256:{digest[:24]}"


def _normalize_key(key: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(key).strip().lower())


def _is_token_like_key(key: object) -> bool:
    normalized = _normalize_key(key)
    if not normalized:
        return False
    return normalized != "tokenref" and normalized.endswith("token")


def _assert_ascii_keys(value: object, context: str) -> None:
    stack: list[tuple[object, int]] = [(value, 0)]
    seen_nodes = 0
    while stack:
        node, depth = stack.pop()
        seen_nodes += 1
        if seen_nodes > MAX_SANITIZE_NODES:
            raise A2ABridgeError(f"{context} exceeded max traversal nodes ({MAX_SANITIZE_NODES}).")
        if depth > MAX_SANITIZE_DEPTH:
            raise A2ABridgeError(f"{context} exceeded max traversal depth ({MAX_SANITIZE_DEPTH}).")
        if isinstance(node, dict):
            for key, item in node.items():
                if not str(key).isascii():
                    raise A2ABridgeError(f"{context} contains non-ASCII key name: {key!r}")
                if isinstance(item, (dict, list)):
                    stack.append((item, depth + 1))
        elif isinstance(node, list):
            for item in node:
                if isinstance(item, (dict, list)):
                    stack.append((item, depth + 1))


def _scrub_token_like_fields(value: object, context: str) -> object:
    stack: list[tuple[object, int]] = [(value, 0)]
    seen_nodes = 0
    while stack:
        node, depth = stack.pop()
        seen_nodes += 1
        if seen_nodes > MAX_SANITIZE_NODES:
            raise A2ABridgeError(f"{context} exceeded max traversal nodes ({MAX_SANITIZE_NODES}).")
        if depth > MAX_SANITIZE_DEPTH:
            raise A2ABridgeError(f"{context} exceeded max traversal depth ({MAX_SANITIZE_DEPTH}).")
        if isinstance(node, dict):
            for key in list(node.keys()):
                if _is_token_like_key(key):
                    node.pop(key, None)
                    continue
                item = node.get(key)
                if isinstance(item, (dict, list)):
                    stack.append((item, depth + 1))
        elif isinstance(node, list):
            for item in node:
                if isinstance(item, (dict, list)):
                    stack.append((item, depth + 1))
    return value


def _assert_bounded_structure(value: object, context: str) -> None:
    stack: list[tuple[object, int]] = [(value, 0)]
    seen_nodes = 0
    while stack:
        node, depth = stack.pop()
        seen_nodes += 1
        if seen_nodes > MAX_SANITIZE_NODES:
            raise A2ABridgeError(f"{context} exceeded max traversal nodes ({MAX_SANITIZE_NODES}).")
        if depth > MAX_SANITIZE_DEPTH:
            raise A2ABridgeError(f"{context} exceeded max traversal depth ({MAX_SANITIZE_DEPTH}).")
        if isinstance(node, dict):
            for item in node.values():
                if isinstance(item, (dict, list)):
                    stack.append((item, depth + 1))
        elif isinstance(node, list):
            for item in node:
                if isinstance(item, (dict, list)):
                    stack.append((item, depth + 1))


def _sanitize_envelope_for_export(envelope: dict) -> dict:
    sanitized = deepcopy(envelope)
    sanitized["Nonce"] = "[REDACTED]"
    sanitized.pop("Signature", None)
    sanitized.pop("SignatureAlgorithm", None)
    sanitized.pop("SignatureKeyID", None)
    body = sanitized.get("Body")
    if isinstance(body, dict):
        verification_result = body.get("VerificationResult")
        if isinstance(verification_result, dict):
            _assert_ascii_keys(
                verification_result,
                "ExecutionReport Body.VerificationResult",
            )
            token = verification_result.pop("token", None)
            verification_result = _scrub_token_like_fields(
                verification_result,
                "ExecutionReport Body.VerificationResult",
            )
            body["VerificationResult"] = verification_result
            if token and "tokenRef" not in verification_result:
                verification_result["tokenRef"] = _token_ref(token)
    return sanitized


def faxp_to_a2a_task_sanitized_export(envelope: dict, *, contract: dict | None = None) -> dict:
    """Translate envelope for external/shared artifacts with sensitive fields redacted."""
    _assert_bounded_structure(envelope, "FAXP envelope")
    task = faxp_to_a2a_task(envelope, contract=contract)
    sanitized_task = deepcopy(task)
    payload = sanitized_task.get("payload")
    if isinstance(payload, dict):
        faxp_envelope = payload.get("faxpEnvelope")
        if isinstance(faxp_envelope, dict):
            payload["faxpEnvelope"] = _sanitize_envelope_for_export(faxp_envelope)
    metadata = sanitized_task.get("metadata")
    if isinstance(metadata, dict):
        if "faxpNonce" in metadata:
            metadata["faxpNonce"] = "[REDACTED]"
        metadata["sanitizedExport"] = True
    return sanitized_task


def a2a_task_to_faxp(task: dict, *, contract: dict | None = None) -> dict:
    """Translate bridged A2A task payload back to original FAXP envelope."""
    contract_payload = contract or load_contract()
    controls = contract_payload.get("securityControls") or {}

    _assert(isinstance(task, dict), "A2A task must be an object.")
    task_type = str(task.get("a2aTaskType") or "").strip()
    reverse_map = _a2a_task_type_to_message_type(contract_payload)

    if bool(controls.get("rejectUnmappedTaskTypes", True)):
        _assert(task_type in reverse_map, f"Unmapped A2A task type: {task_type!r}")

    payload = task.get("payload")
    _assert(isinstance(payload, dict), "A2A task payload must be an object.")
    envelope = payload.get("faxpEnvelope")
    _assert(isinstance(envelope, dict), "A2A task payload must include faxpEnvelope object.")

    _validate_envelope(envelope, contract_payload)

    expected_message_type = reverse_map.get(task_type, "")
    if expected_message_type:
        _assert(
            str(envelope.get("MessageType") or "") == expected_message_type,
            "A2A task type and embedded FAXP MessageType do not match contract mapping.",
        )

    return deepcopy(envelope)


def assert_round_trip(envelope: dict, *, contract: dict | None = None) -> None:
    """Enforce deterministic FAXP->A2A->FAXP round-trip."""
    contract_payload = contract or load_contract()
    controls = contract_payload.get("securityControls") or {}

    translated = faxp_to_a2a_task(envelope, contract=contract_payload)
    recovered = a2a_task_to_faxp(translated, contract=contract_payload)

    if bool(controls.get("requireDeterministicRoundTrip", True)):
        _assert(
            _canonical_json(envelope) == _canonical_json(recovered),
            "Deterministic round-trip check failed for FAXP<->A2A translation.",
        )


def assert_round_trip_from_a2a(task: dict, *, contract: dict | None = None) -> None:
    """Enforce deterministic A2A->FAXP->A2A round-trip."""
    contract_payload = contract or load_contract()
    controls = contract_payload.get("securityControls") or {}

    envelope = a2a_task_to_faxp(task, contract=contract_payload)
    recovered = faxp_to_a2a_task(envelope, contract=contract_payload)

    if bool(controls.get("requireDeterministicRoundTrip", True)):
        _assert(
            _canonical_json(task) == _canonical_json(recovered),
            "Deterministic round-trip check failed for A2A<->FAXP translation.",
        )
