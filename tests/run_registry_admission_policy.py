#!/usr/bin/env python3
"""Validate certification registry artifacts against docs/governance/REGISTRY_ADMISSION_POLICY.md."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json
import re
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]

POLICY_DOC_PATH = PROJECT_ROOT / "docs" / "governance" / "REGISTRY_ADMISSION_POLICY.md"
REGISTRY_SAMPLE_PATH = PROJECT_ROOT / "conformance" / "certification_registry.sample.json"
REGISTRY_AFTER_UPDATE_PATH = (
    PROJECT_ROOT / "conformance" / "certification_registry.sample.after_update.json"
)

MARKER_BEGIN = "<!-- REGISTRY_ADMISSION_POLICY_BEGIN -->"
MARKER_END = "<!-- REGISTRY_ADMISSION_POLICY_END -->"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _parse_utc(value: str, context: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AssertionError(f"{context} must be ISO-8601.") from exc


def _load_policy_config(path: Path) -> dict:
    document = path.read_text(encoding="utf-8")
    start = document.find(MARKER_BEGIN)
    end = document.find(MARKER_END)
    if start == -1 or end == -1 or end <= start:
        raise AssertionError("docs/governance/REGISTRY_ADMISSION_POLICY.md markers are missing or malformed.")
    raw = document[start + len(MARKER_BEGIN) : end].strip()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AssertionError("docs/governance/REGISTRY_ADMISSION_POLICY.md policy block is not valid JSON.") from exc
    _assert(isinstance(payload, dict), "Registry admission policy block must be an object.")
    return payload


def _validate_entry_admission(registry: dict, policy: dict, label: str) -> None:
    entry_policy = policy["entryAdmission"]
    allowed_tiers = set(entry_policy["activeAllowedTiers"])
    report_ref_re = re.compile(entry_policy["conformanceReportRefPattern"])
    profile_re = re.compile(entry_policy["profileIdPattern"])
    max_days_by_tier = entry_policy["maxValidityDaysByTier"]
    require_security_true = bool(entry_policy.get("requireSecurityAttestationTrue", False))

    for entry in registry.get("entries", []):
        adapter_id = str(entry.get("adapterId") or "<unknown>")
        status = str(entry.get("status") or "")
        tier = str(entry.get("certificationTier") or "")

        if status == "Active":
            _assert(
                tier in allowed_tiers,
                f"{label}:{adapter_id} active status is not allowed for tier {tier}.",
            )

        if require_security_true:
            security = entry.get("securityAttestation") or {}
            _assert(
                bool(security.get("signedRequests"))
                and bool(security.get("signedResponses"))
                and bool(security.get("replayProtection")),
                f"{label}:{adapter_id} requires signedRequests/signedResponses/replayProtection=true.",
            )

        report_ref = str(entry.get("conformanceReportRef") or "")
        _assert(
            bool(report_ref_re.fullmatch(report_ref)),
            f"{label}:{adapter_id} invalid conformanceReportRef format.",
        )

        for profile_id in entry.get("profilesSupported", []):
            profile_value = str(profile_id)
            _assert(
                bool(profile_re.fullmatch(profile_value)),
                f"{label}:{adapter_id} invalid profile ID format: {profile_value}",
            )

        last_certified_at = _parse_utc(str(entry.get("lastCertifiedAt") or ""), f"{label}:{adapter_id}:lastCertifiedAt")
        expires_at = _parse_utc(str(entry.get("expiresAt") or ""), f"{label}:{adapter_id}:expiresAt")
        _assert(
            expires_at > last_certified_at,
            f"{label}:{adapter_id} expiresAt must be later than lastCertifiedAt.",
        )

        max_days = int(max_days_by_tier.get(tier, 0))
        validity_days = (expires_at - last_certified_at).total_seconds() / 86400.0
        _assert(
            validity_days <= max_days,
            f"{label}:{adapter_id} validity window exceeds tier max ({validity_days:.2f}d > {max_days}d).",
        )


def _validate_renewal(before: dict, after: dict, policy: dict) -> None:
    renewal = policy["renewal"]
    allowed_transitions = {tuple(item) for item in renewal["allowedTierTransitions"]}
    require_status_active = bool(renewal.get("requireStatusActive", False))
    require_last_cert_monotonic = bool(renewal.get("requireLastCertifiedMonotonic", False))
    require_expires_increase = bool(renewal.get("requireExpiresAtIncrease", False))

    before_entries = {str(item["adapterId"]): item for item in before.get("entries", [])}
    after_entries = {str(item["adapterId"]): item for item in after.get("entries", [])}
    shared_ids = sorted(set(before_entries).intersection(after_entries))
    _assert(shared_ids, "Renewal check requires at least one shared adapterId across registry snapshots.")

    for adapter_id in shared_ids:
        old = before_entries[adapter_id]
        new = after_entries[adapter_id]

        if require_status_active:
            _assert(
                str(old.get("status")) == "Active" and str(new.get("status")) == "Active",
                f"renewal:{adapter_id} requires Active status before and after.",
            )

        if require_last_cert_monotonic:
            old_cert = _parse_utc(str(old.get("lastCertifiedAt") or ""), f"renewal:{adapter_id}:old.lastCertifiedAt")
            new_cert = _parse_utc(str(new.get("lastCertifiedAt") or ""), f"renewal:{adapter_id}:new.lastCertifiedAt")
            _assert(
                new_cert >= old_cert,
                f"renewal:{adapter_id} lastCertifiedAt must be monotonic non-decreasing.",
            )

        if require_expires_increase:
            old_exp = _parse_utc(str(old.get("expiresAt") or ""), f"renewal:{adapter_id}:old.expiresAt")
            new_exp = _parse_utc(str(new.get("expiresAt") or ""), f"renewal:{adapter_id}:new.expiresAt")
            _assert(new_exp > old_exp, f"renewal:{adapter_id} expiresAt must increase.")

        transition = (str(old.get("certificationTier")), str(new.get("certificationTier")))
        _assert(
            transition in allowed_transitions,
            f"renewal:{adapter_id} disallowed tier transition {transition}.",
        )


def _validate_non_active_handling(registries: list[tuple[str, dict]], policy: dict) -> None:
    non_active = policy["nonActiveHandling"]
    if not non_active.get("requireReasonCodeInNotes", False):
        return

    reason_re = re.compile(non_active["reasonCodePattern"])
    for label, registry in registries:
        for entry in registry.get("entries", []):
            status = str(entry.get("status") or "")
            if status not in {"Suspended", "Revoked"}:
                continue
            adapter_id = str(entry.get("adapterId") or "<unknown>")
            notes = str(entry.get("notes") or "")
            _assert(
                bool(reason_re.search(notes)),
                f"{label}:{adapter_id} non-active entry requires reason code in notes.",
            )


def main() -> int:
    policy = _load_policy_config(POLICY_DOC_PATH)
    registry_before = _load_json(REGISTRY_SAMPLE_PATH)
    registry_after = _load_json(REGISTRY_AFTER_UPDATE_PATH)

    _validate_entry_admission(registry_before, policy, "registry.sample")
    _validate_entry_admission(registry_after, policy, "registry.sample.after_update")
    _validate_renewal(registry_before, registry_after, policy)
    _validate_non_active_handling(
        [
            ("registry.sample", registry_before),
            ("registry.sample.after_update", registry_after),
        ],
        policy,
    )

    print("Registry admission policy checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
