#!/usr/bin/env python3
"""Validate key lifecycle policy, rotation overlap, and active KID bindings."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import argparse
import json

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFORMANCE_DIR = PROJECT_ROOT / "conformance"

POLICY_SCHEMA_PATH = CONFORMANCE_DIR / "key_lifecycle_policy.schema.json"
POLICY_SAMPLE_PATH = CONFORMANCE_DIR / "key_lifecycle_policy.sample.json"


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


def _get_nested_value(payload: dict, path: list[str]) -> object:
    current: object = payload
    for segment in path:
        _assert(isinstance(current, dict), f"Invalid path traversal at segment '{segment}'.")
        current = current.get(segment)
    return current


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate conformance key lifecycle policy.")
    parser.add_argument(
        "--policy",
        default=str(POLICY_SAMPLE_PATH),
        help="Path to key lifecycle policy JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    policy_path = Path(args.policy).expanduser().resolve()
    policy = _load_json(policy_path)
    schema = _load_json(POLICY_SCHEMA_PATH)
    _validate(schema, policy, "key lifecycle policy")

    as_of = _validate_iso_datetime(str(policy["asOf"]), "policy asOf")
    max_age_days = int(policy["maxKeyAgeDays"])
    max_validity_days = int(policy["maxKeyValidityDays"])
    min_overlap_days = int(policy["minRotationOverlapDays"])

    key_sets = policy.get("keySets", [])
    key_set_index: dict[str, dict] = {}

    for key_set in key_sets:
        name = str(key_set["name"])
        key_set_index[name] = key_set

        keyring = _load_json(_resolve_ref(str(key_set["keyringRef"])))
        keyring_keys = keyring.get("keys") or {}
        _assert(isinstance(keyring_keys, dict) and keyring_keys, f"{name}: keyring keys missing.")

        key_entries = key_set.get("keys", [])
        key_entry_index = {str(entry["kid"]): entry for entry in key_entries}
        active_kids = [str(kid) for kid in key_set.get("activeKids", [])]
        _assert(active_kids, f"{name}: activeKids must not be empty.")

        for kid in active_kids:
            _assert(kid in key_entry_index, f"{name}: active kid '{kid}' missing from policy keys.")
            _assert(kid in keyring_keys, f"{name}: active kid '{kid}' missing from keyring.")
            _assert(
                str(key_entry_index[kid]["status"]) == "Active",
                f"{name}: active kid '{kid}' must have status=Active.",
            )

        for entry in key_entries:
            kid = str(entry["kid"])
            created = _validate_iso_datetime(str(entry["createdAt"]), f"{name}:{kid}:createdAt")
            expires = _validate_iso_datetime(str(entry["expiresAt"]), f"{name}:{kid}:expiresAt")
            _assert(created < expires, f"{name}:{kid}: createdAt must be before expiresAt.")

            validity_days = (expires - created).total_seconds() / 86400.0
            _assert(
                validity_days <= max_validity_days,
                f"{name}:{kid}: validity {validity_days:.1f}d exceeds maxKeyValidityDays={max_validity_days}.",
            )

            if str(entry["status"]) == "Active":
                age_days = (as_of - created).total_seconds() / 86400.0
                _assert(
                    age_days <= max_age_days,
                    f"{name}:{kid}: age {age_days:.1f}d exceeds maxKeyAgeDays={max_age_days}.",
                )

            if entry.get("rotatedFrom"):
                prev_kid = str(entry["rotatedFrom"])
                _assert(prev_kid in key_entry_index, f"{name}:{kid}: rotatedFrom '{prev_kid}' missing.")
                prev = key_entry_index[prev_kid]
                prev_created = _validate_iso_datetime(
                    str(prev["createdAt"]), f"{name}:{prev_kid}:createdAt"
                )
                prev_expires = _validate_iso_datetime(
                    str(prev["expiresAt"]), f"{name}:{prev_kid}:expiresAt"
                )
                _assert(
                    prev_created < created,
                    f"{name}:{kid}: rotatedFrom key must be older than new key.",
                )
                overlap_days = (prev_expires - created).total_seconds() / 86400.0
                _assert(
                    overlap_days >= min_overlap_days,
                    f"{name}:{kid}: overlap {overlap_days:.1f}d below minRotationOverlapDays={min_overlap_days}.",
                )

    bindings = policy.get("signatureBindings", [])
    _assert(bindings, "signatureBindings must not be empty.")
    for binding in bindings:
        binding_name = str(binding["name"])
        key_set_name = str(binding["expectedKeySet"])
        _assert(key_set_name in key_set_index, f"{binding_name}: unknown key set '{key_set_name}'.")
        key_set = key_set_index[key_set_name]
        active_kids = {str(kid) for kid in key_set.get("activeKids", [])}

        document = _load_json(_resolve_ref(str(binding["documentRef"])))
        kid_path = list(binding.get("kidPath") or [])
        kid_value = _get_nested_value(document, kid_path)
        kid = str(kid_value or "").strip()
        _assert(kid, f"{binding_name}: kid path resolved to empty value.")
        _assert(
            kid in active_kids,
            f"{binding_name}: kid '{kid}' is not in activeKids for key set '{key_set_name}'.",
        )

    print("Key lifecycle policy checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

