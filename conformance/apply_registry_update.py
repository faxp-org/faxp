#!/usr/bin/env python3
"""Apply validated registry update operations and emit a deterministic registry artifact."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from pathlib import Path
import argparse
import json
import sys

from jsonschema import Draft202012Validator
from registry_update_signing import verify_request_signature


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFORMANCE_DIR = PROJECT_ROOT / "conformance"

REGISTRY_SCHEMA_PATH = CONFORMANCE_DIR / "certification_registry.schema.json"
REGISTRY_UPDATE_SCHEMA_PATH = CONFORMANCE_DIR / "registry_update.schema.json"
REGISTRY_UPDATE_SAMPLE_PATH = CONFORMANCE_DIR / "registry_update.sample.json"
REGISTRY_UPDATE_KEYS_SAMPLE_PATH = CONFORMANCE_DIR / "registry_update_keys.sample.json"

ALLOWED_PATCH_FIELDS = {
    "certificationTier",
    "status",
    "profilesSupported",
    "conformanceReportRef",
    "expiresAt",
    "notes",
    "securityAttestation",
}


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _validate(schema: dict, payload: dict, label: str) -> None:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda item: item.path)
    if errors:
        detail = "; ".join(err.message for err in errors[:3])
        raise AssertionError(f"{label} failed schema validation: {detail}")


def _validate_iso_datetime(value: str, context: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AssertionError(f"{context} must be ISO-8601.") from exc


def _resolve_ref(path_ref: str) -> Path:
    ref = Path(path_ref)
    if ref.is_absolute():
        resolved = ref
    else:
        resolved = (PROJECT_ROOT / ref).resolve()
    _assert(resolved.exists(), f"Referenced file does not exist: {path_ref}")
    return resolved


def _entry_index_by_adapter(entries: list[dict]) -> dict[str, int]:
    index: dict[str, int] = {}
    for idx, entry in enumerate(entries):
        adapter_id = str(entry.get("adapterId") or "")
        if adapter_id:
            index[adapter_id] = idx
    return index


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Apply registry update request to a base certification registry."
    )
    parser.add_argument(
        "--request",
        default=str(REGISTRY_UPDATE_SAMPLE_PATH),
        help="Path to registry update request JSON.",
    )
    parser.add_argument(
        "--registry",
        default="",
        help="Optional override path to base registry JSON.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional output path. If omitted, prints resulting registry JSON to stdout.",
    )
    parser.add_argument(
        "--keyring",
        default=str(REGISTRY_UPDATE_KEYS_SAMPLE_PATH),
        help="Registry update signing keyring JSON path.",
    )
    parser.add_argument(
        "--allow-unsigned",
        action="store_true",
        help="Allow unsigned requests (default is fail-closed requiring requestSignature).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    request_path = Path(args.request).expanduser().resolve()
    keyring_path = Path(args.keyring).expanduser().resolve()

    registry_schema = _load_json(REGISTRY_SCHEMA_PATH)
    update_schema = _load_json(REGISTRY_UPDATE_SCHEMA_PATH)
    request_payload = _load_json(request_path)
    keyring_payload = _load_json(keyring_path)

    _validate(update_schema, request_payload, "registry update request")
    _validate_iso_datetime(str(request_payload["submittedAt"]), "submittedAt")
    _assert(
        bool(request_payload.get("approvals", {}).get("policyApproved")),
        "approvals.policyApproved must be true.",
    )
    verify_request_signature(
        request_payload,
        keyring=keyring_payload,
        require_signature=not args.allow_unsigned,
    )
    signature = request_payload.get("requestSignature") or {}
    if signature:
        _validate_iso_datetime(str(signature.get("signedAt") or ""), "requestSignature.signedAt")

    if args.registry.strip():
        base_registry_path = Path(args.registry).expanduser().resolve()
    else:
        base_registry_path = _resolve_ref(request_payload["baseRegistryRef"])
    base_registry = _load_json(base_registry_path)
    _validate(registry_schema, base_registry, "base registry")

    if request_payload.get("auditTrailRef"):
        _resolve_ref(str(request_payload["auditTrailRef"]))

    result_registry = deepcopy(base_registry)
    entries = result_registry.get("entries", [])
    _assert(entries, "base registry must include at least one entry.")
    adapter_index = _entry_index_by_adapter(entries)

    seen_op_ids: set[str] = set()
    op_history: dict[str, dict] = {}
    latest_effective: datetime | None = None

    operations = request_payload.get("operations", [])
    _assert(operations, "registry update request must include operations.")

    for idx, op in enumerate(operations, start=1):
        op_id = str(op["opId"])
        _assert(op_id not in seen_op_ids, f"duplicate opId detected: {op_id}")
        seen_op_ids.add(op_id)

        effective_at = _validate_iso_datetime(str(op["effectiveAt"]), f"operations[{idx}].effectiveAt")
        if latest_effective is None or effective_at > latest_effective:
            latest_effective = effective_at

        adapter_id = str(op["adapterId"])
        action = str(op["action"])
        _assert(adapter_id in adapter_index, f"unknown adapterId in operation: {adapter_id}")
        entry = entries[adapter_index[adapter_id]]

        current_status = str(entry["status"])
        expected = op.get("expectedCurrentStatus")
        if expected is not None:
            _assert(
                str(expected) == current_status,
                f"{op_id}: expectedCurrentStatus={expected} but current status is {current_status}",
            )

        pre_entry = deepcopy(entry)

        if action == "UPSERT":
            patch = op.get("patch") or {}
            for key, value in patch.items():
                _assert(key in ALLOWED_PATCH_FIELDS, f"{op_id}: unsupported patch field '{key}'")
                entry[key] = value
        elif action == "SUSPEND":
            _assert(current_status == "Active", f"{op_id}: SUSPEND only allowed from Active, got {current_status}")
            entry["status"] = "Suspended"
        elif action == "REVOKE":
            _assert(
                current_status in {"Active", "Suspended"},
                f"{op_id}: REVOKE only allowed from Active/Suspended, got {current_status}",
            )
            entry["status"] = "Revoked"
        elif action == "ROLLBACK":
            rollback = op.get("rollback") or {}
            target_op_id = str(rollback.get("targetOpId") or "").strip()
            _assert(target_op_id, f"{op_id}: rollback.targetOpId is required.")
            _assert(target_op_id in op_history, f"{op_id}: unknown rollback targetOpId {target_op_id}")
            target = op_history[target_op_id]
            _assert(
                str(target["adapterId"]) == adapter_id,
                f"{op_id}: rollback target adapter mismatch for target {target_op_id}",
            )
            restored = deepcopy(target["pre_entry"])
            entries[adapter_index[adapter_id]] = restored
            entry = entries[adapter_index[adapter_id]]
        else:
            raise AssertionError(f"{op_id}: unsupported action {action}")

        entry["lastCertifiedAt"] = str(op["effectiveAt"])
        op_history[op_id] = {
            "adapterId": adapter_id,
            "action": action,
            "pre_entry": pre_entry,
            "post_entry": deepcopy(entry),
        }

    if latest_effective is not None:
        result_registry["generatedAt"] = latest_effective.replace(microsecond=0).isoformat().replace(
            "+00:00", "Z"
        )

    _validate(registry_schema, result_registry, "result registry")

    if args.output.strip():
        output_path = Path(args.output).expanduser().resolve()
        _write_json(output_path, result_registry)
        print(f"[RegistryApply] wrote updated registry to {output_path}")
    else:
        print(json.dumps(result_registry, indent=2))

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"[RegistryApply] error: {exc}", file=sys.stderr)
        raise SystemExit(1)
