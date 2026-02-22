#!/usr/bin/env python3
"""Create/update/sign certification submission manifest payloads from a template."""

from __future__ import annotations

from pathlib import Path
import argparse
import json

from jsonschema import Draft202012Validator

from submission_manifest_signing import build_submission_signature, now_utc


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFORMANCE_DIR = PROJECT_ROOT / "conformance"
DEFAULT_TEMPLATE_PATH = CONFORMANCE_DIR / "submission_manifest.sample.json"
DEFAULT_SCHEMA_PATH = CONFORMANCE_DIR / "submission_manifest.schema.json"
DEFAULT_KEYRING_PATH = CONFORMANCE_DIR / "submission_manifest_keys.sample.json"


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
        description="Generate a signed submission manifest from a template."
    )
    parser.add_argument(
        "--template",
        default=str(DEFAULT_TEMPLATE_PATH),
        help="Template submission manifest JSON path.",
    )
    parser.add_argument(
        "--schema",
        default=str(DEFAULT_SCHEMA_PATH),
        help="Submission manifest schema path.",
    )
    parser.add_argument(
        "--keyring",
        default=str(DEFAULT_KEYRING_PATH),
        help="Submission manifest signing keyring JSON path.",
    )
    parser.add_argument("--kid", default="faxp-submission-kid-2026q1", help="Signing key ID.")
    parser.add_argument("--secret", default="", help="Raw signing secret override.")
    parser.add_argument("--submission-id", default="", help="Override submissionId.")
    parser.add_argument("--submitted-at", default="", help="Override submittedAt (ISO-8601 UTC).")
    parser.add_argument("--organization", default="", help="Override submitter.organization.")
    parser.add_argument("--contact-email", default="", help="Override submitter.contactEmail.")
    parser.add_argument("--attestor-role", default="", help="Override submitter.attestorRole.")
    parser.add_argument("--requested-tier", default="", help="Override requestedTier.")
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

    manifest_payload = _load_json(template_path)
    schema = _load_json(schema_path)

    if args.submission_id.strip():
        manifest_payload["submissionId"] = args.submission_id.strip()
    if args.submitted_at.strip():
        manifest_payload["submittedAt"] = args.submitted_at.strip()
    elif not str(manifest_payload.get("submittedAt") or "").strip():
        manifest_payload["submittedAt"] = now_utc()

    if args.organization.strip():
        manifest_payload.setdefault("submitter", {})["organization"] = args.organization.strip()
    if args.contact_email.strip():
        manifest_payload.setdefault("submitter", {})["contactEmail"] = args.contact_email.strip()
    if args.attestor_role.strip():
        manifest_payload.setdefault("submitter", {})["attestorRole"] = args.attestor_role.strip()
    if args.requested_tier.strip():
        manifest_payload["requestedTier"] = args.requested_tier.strip()
    if args.notes.strip():
        manifest_payload["notes"] = args.notes.strip()

    kid = args.kid.strip()
    secret = args.secret.strip()
    if not secret:
        keyring = _load_json(keyring_path)
        secret = str((keyring.get("keys") or {}).get(kid) or "").strip()
    if not secret:
        raise ValueError(f"No signing secret found for kid '{kid}'.")

    manifest_payload["submissionSignature"] = build_submission_signature(
        manifest_payload,
        kid=kid,
        secret=secret,
        signed_at=manifest_payload.get("submittedAt") or now_utc(),
    )
    _validate(schema, manifest_payload, "submission manifest")

    if args.in_place:
        _write_json(template_path, manifest_payload)
        print(f"[SubmissionCreate] wrote signed manifest to {template_path}")
        return 0

    if args.output.strip():
        output_path = Path(args.output).expanduser().resolve()
        _write_json(output_path, manifest_payload)
        print(f"[SubmissionCreate] wrote signed manifest to {output_path}")
        return 0

    print(json.dumps(manifest_payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

