#!/usr/bin/env python3
"""Validate registry update/revoke/rollback artifacts and transition safety rules."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import argparse
import json

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFORMANCE_DIR = PROJECT_ROOT / "conformance"

REGISTRY_SCHEMA_PATH = CONFORMANCE_DIR / "certification_registry.schema.json"
REGISTRY_UPDATE_SCHEMA_PATH = CONFORMANCE_DIR / "registry_update.schema.json"
REGISTRY_UPDATE_SAMPLE_PATH = CONFORMANCE_DIR / "registry_update.sample.json"


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate registry operations artifacts (update/revoke/rollback)."
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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    request_path = Path(args.request).expanduser().resolve()

    registry_schema = _load_json(REGISTRY_SCHEMA_PATH)
    update_schema = _load_json(REGISTRY_UPDATE_SCHEMA_PATH)
    request_payload = _load_json(request_path)

    _validate(update_schema, request_payload, "registry update request")
    _validate_iso_datetime(str(request_payload["submittedAt"]), "submittedAt")
    _assert(
        bool(request_payload.get("approvals", {}).get("policyApproved")),
        "approvals.policyApproved must be true.",
    )

    if args.registry.strip():
        base_registry_path = Path(args.registry).expanduser().resolve()
    else:
        base_registry_path = _resolve_ref(request_payload["baseRegistryRef"])
    base_registry = _load_json(base_registry_path)
    _validate(registry_schema, base_registry, "base registry")

    if request_payload.get("auditTrailRef"):
        _resolve_ref(str(request_payload["auditTrailRef"]))

    entries = base_registry.get("entries", [])
    _assert(entries, "base registry must include at least one entry.")
    registry_state: dict[str, dict] = {
        str(entry["adapterId"]): {
            "status": str(entry["status"]),
            "certificationTier": str(entry["certificationTier"]),
        }
        for entry in entries
    }

    operations = request_payload.get("operations", [])
    _assert(operations, "registry update request must include operations.")

    seen_op_ids: set[str] = set()
    op_history: dict[str, dict] = {}

    for idx, op in enumerate(operations, start=1):
        op_id = str(op["opId"])
        _assert(op_id not in seen_op_ids, f"duplicate opId detected: {op_id}")
        seen_op_ids.add(op_id)

        _validate_iso_datetime(str(op["effectiveAt"]), f"operations[{idx}].effectiveAt")
        adapter_id = str(op["adapterId"])
        action = str(op["action"])
        _assert(adapter_id in registry_state, f"unknown adapterId in operation: {adapter_id}")

        current_status = registry_state[adapter_id]["status"]
        current_tier = registry_state[adapter_id]["certificationTier"]
        expected = op.get("expectedCurrentStatus")
        if expected is not None:
            _assert(
                str(expected) == current_status,
                f"{op_id}: expectedCurrentStatus={expected} but current status is {current_status}",
            )

        pre_status = current_status
        pre_tier = current_tier
        post_status = current_status
        post_tier = current_tier

        if action == "UPSERT":
            patch = op.get("patch") or {}
            if "status" in patch:
                post_status = str(patch["status"])
            if "certificationTier" in patch:
                post_tier = str(patch["certificationTier"])
        elif action == "SUSPEND":
            _assert(
                current_status == "Active",
                f"{op_id}: SUSPEND only allowed from Active, got {current_status}",
            )
            post_status = "Suspended"
        elif action == "REVOKE":
            _assert(
                current_status in {"Active", "Suspended"},
                f"{op_id}: REVOKE only allowed from Active/Suspended, got {current_status}",
            )
            post_status = "Revoked"
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
            post_status = str(target["pre_status"])
            post_tier = str(target["pre_tier"])
        else:
            raise AssertionError(f"{op_id}: unsupported action {action}")

        registry_state[adapter_id]["status"] = post_status
        registry_state[adapter_id]["certificationTier"] = post_tier
        op_history[op_id] = {
            "adapterId": adapter_id,
            "action": action,
            "pre_status": pre_status,
            "post_status": post_status,
            "pre_tier": pre_tier,
            "post_tier": post_tier,
        }

    print("Registry operations artifact checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

