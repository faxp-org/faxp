#!/usr/bin/env python3
"""Create/update/sign registry update request payloads from a template."""

from __future__ import annotations

from pathlib import Path
import argparse
import json

from jsonschema import Draft202012Validator

from registry_update_signing import build_request_signature, now_utc


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFORMANCE_DIR = PROJECT_ROOT / "conformance"
DEFAULT_TEMPLATE_PATH = CONFORMANCE_DIR / "registry_update.sample.json"
DEFAULT_SCHEMA_PATH = CONFORMANCE_DIR / "registry_update.schema.json"
DEFAULT_KEYRING_PATH = CONFORMANCE_DIR / "registry_update_keys.sample.json"


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _validate(schema: dict, payload: dict, label: str) -> None:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda item: item.path)
    if errors:
        detail = "; ".join(err.message for err in errors[:3])
        raise ValueError(f"{label} failed schema validation: {detail}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a signed registry update request from a template."
    )
    parser.add_argument(
        "--template",
        default=str(DEFAULT_TEMPLATE_PATH),
        help="Template registry update JSON path.",
    )
    parser.add_argument(
        "--schema",
        default=str(DEFAULT_SCHEMA_PATH),
        help="Registry update schema path.",
    )
    parser.add_argument(
        "--keyring",
        default=str(DEFAULT_KEYRING_PATH),
        help="Registry update keyring JSON path.",
    )
    parser.add_argument("--kid", default="faxp-regops-kid-2026q1", help="Signing key ID.")
    parser.add_argument("--secret", default="", help="Raw signing secret override.")
    parser.add_argument("--change-set-id", default="", help="Override changeSetId.")
    parser.add_argument("--submitted-at", default="", help="Override submittedAt (ISO-8601 UTC).")
    parser.add_argument("--base-registry-ref", default="", help="Override baseRegistryRef.")
    parser.add_argument("--organization", default="", help="Override requestedBy.organization.")
    parser.add_argument("--contact-email", default="", help="Override requestedBy.contactEmail.")
    parser.add_argument("--approver-ref", default="", help="Override approvals.approverRef.")
    parser.add_argument("--audit-trail-ref", default="", help="Override auditTrailRef.")
    parser.add_argument("--notes", default="", help="Override top-level notes.")
    parser.add_argument(
        "--output",
        default="",
        help="Output path. If omitted, prints JSON to stdout.",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Write updates back to --template path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    template_path = Path(args.template).expanduser().resolve()
    schema_path = Path(args.schema).expanduser().resolve()
    keyring_path = Path(args.keyring).expanduser().resolve()

    request_payload = _load_json(template_path)
    schema = _load_json(schema_path)

    if args.change_set_id.strip():
        request_payload["changeSetId"] = args.change_set_id.strip()
    if args.submitted_at.strip():
        request_payload["submittedAt"] = args.submitted_at.strip()
    elif not str(request_payload.get("submittedAt") or "").strip():
        request_payload["submittedAt"] = now_utc()

    if args.base_registry_ref.strip():
        request_payload["baseRegistryRef"] = args.base_registry_ref.strip()
    if args.organization.strip():
        request_payload.setdefault("requestedBy", {})["organization"] = args.organization.strip()
    if args.contact_email.strip():
        request_payload.setdefault("requestedBy", {})["contactEmail"] = args.contact_email.strip()
    if args.approver_ref.strip():
        request_payload.setdefault("approvals", {})["approverRef"] = args.approver_ref.strip()
    if args.audit_trail_ref.strip():
        request_payload["auditTrailRef"] = args.audit_trail_ref.strip()
    if args.notes.strip():
        request_payload["notes"] = args.notes.strip()

    kid = args.kid.strip()
    secret = args.secret.strip()
    if not secret:
        keyring = _load_json(keyring_path)
        secret = str((keyring.get("keys") or {}).get(kid) or "").strip()
    if not secret:
        raise ValueError(f"No signing secret found for kid '{kid}'.")

    request_payload["requestSignature"] = build_request_signature(
        request_payload,
        kid=kid,
        secret=secret,
        signed_at=request_payload.get("submittedAt") or now_utc(),
    )
    _validate(schema, request_payload, "registry update request")

    if args.in_place:
        _write_json(template_path, request_payload)
        print(f"[RegistryUpdateCreate] wrote signed request to {template_path}")
        return 0

    if args.output.strip():
        output_path = Path(args.output).expanduser().resolve()
        _write_json(output_path, request_payload)
        print(f"[RegistryUpdateCreate] wrote signed request to {output_path}")
        return 0

    print(json.dumps(request_payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
