#!/usr/bin/env python3
"""Validate registry changelog policy and sample artifact cross-link integrity."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json
import re


PROJECT_ROOT = Path(__file__).resolve().parents[1]

POLICY_PATH = PROJECT_ROOT / "REGISTRY_CHANGELOG_POLICY.md"
CHANGELOG_SAMPLE_PATH = PROJECT_ROOT / "conformance" / "registry_changelog.sample.json"

POLICY_BEGIN = "<!-- REGISTRY_CHANGELOG_POLICY_BEGIN -->"
POLICY_END = "<!-- REGISTRY_CHANGELOG_POLICY_END -->"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _extract_block(document: str, begin: str, end: str) -> str:
    start = document.find(begin)
    stop = document.find(end)
    _assert(start != -1 and stop != -1 and stop > start, f"Missing or invalid policy block: {begin}")
    return document[start + len(begin) : stop].strip()


def _parse_iso8601(value: str, context: str) -> datetime:
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
    _assert(resolved.exists(), f"Referenced artifact does not exist: {path_ref}")
    return resolved


def _entry_by_adapter(registry: dict, adapter_id: str, context: str) -> dict:
    for entry in registry.get("entries", []):
        if str(entry.get("adapterId")) == adapter_id:
            return entry
    raise AssertionError(f"{context}: adapterId not found: {adapter_id}")


def main() -> int:
    policy_doc = POLICY_PATH.read_text(encoding="utf-8")
    policy = json.loads(_extract_block(policy_doc, POLICY_BEGIN, POLICY_END))
    changelog = _load_json(CHANGELOG_SAMPLE_PATH)

    required_top = list(policy.get("requiredTopLevelFields") or [])
    required_entry = list(policy.get("requiredEntryFields") or [])
    _assert(required_top, "Policy missing requiredTopLevelFields.")
    _assert(required_entry, "Policy missing requiredEntryFields.")

    for field in required_top:
        _assert(field in changelog, f"Changelog missing required top-level field: {field}")

    _parse_iso8601(str(changelog.get("generatedAt") or ""), "generatedAt")

    change_id_re = re.compile(str(policy.get("changeIdPattern") or ""))
    op_id_re = re.compile(str(policy.get("opIdPattern") or ""))
    reason_re = re.compile(str(policy.get("reasonCodePattern") or ""))
    allowed_actions = set(policy.get("allowedActions") or [])
    allowed_statuses = set(policy.get("allowedStatuses") or [])
    allowed_entry_states = set(policy.get("allowedEntryStates") or [])

    request_payload = _load_json(_resolve_ref(str(changelog["requestRef"])))
    audit_log_path = _resolve_ref(str(changelog["auditTrailRef"]))
    decision_record = _load_json(_resolve_ref(str(changelog["decisionRecordRef"])))
    registry_before = _load_json(_resolve_ref(str(changelog["registrySnapshotBeforeRef"])))
    registry_after = _load_json(_resolve_ref(str(changelog["registrySnapshotAfterRef"])))

    if policy.get("requireAuditTrailRef", False):
        _assert(audit_log_path.stat().st_size > 0, "auditTrailRef must point to non-empty log.")
    if policy.get("requireDecisionRecordRef", False):
        _assert(str(decision_record.get("decisionId") or "").strip(), "decisionRecordRef missing decisionId.")

    _assert(
        str(changelog.get("changeSetId") or "") == str(request_payload.get("changeSetId") or ""),
        "changeSetId must match requestRef changeSetId.",
    )

    request_ops = {str(op.get("opId")): op for op in request_payload.get("operations", [])}
    _assert(request_ops, "requestRef must include operations.")

    entries = changelog.get("entries") or []
    _assert(isinstance(entries, list) and entries, "entries must be a non-empty array.")

    timestamps: list[datetime] = []
    seen_change_ids: set[str] = set()
    seen_op_ids: set[str] = set()
    state_by_adapter: dict[str, dict[str, str]] = {}

    for entry in entries:
        _assert(isinstance(entry, dict), "Each changelog entry must be an object.")
        for field in required_entry:
            _assert(field in entry, f"Changelog entry missing required field: {field}")

        change_id = str(entry.get("changeId") or "")
        op_id = str(entry.get("opId") or "")
        action = str(entry.get("action") or "")
        adapter_id = str(entry.get("adapterId") or "")
        reason_code = str(entry.get("reasonCode") or "")
        status_before = str(entry.get("statusBefore") or "")
        status_after = str(entry.get("statusAfter") or "")
        tier_before = str(entry.get("tierBefore") or "")
        tier_after = str(entry.get("tierAfter") or "")
        entry_state = str(entry.get("status") or "")

        _assert(bool(change_id_re.fullmatch(change_id)), f"Invalid changeId format: {change_id}")
        _assert(bool(op_id_re.fullmatch(op_id)), f"Invalid opId format: {op_id}")
        _assert(change_id not in seen_change_ids, f"Duplicate changeId: {change_id}")
        _assert(op_id not in seen_op_ids, f"Duplicate opId in changelog entries: {op_id}")
        seen_change_ids.add(change_id)
        seen_op_ids.add(op_id)

        _assert(action in allowed_actions, f"Unsupported action in changelog: {action}")
        _assert(status_before in allowed_statuses, f"Invalid statusBefore: {status_before}")
        _assert(status_after in allowed_statuses, f"Invalid statusAfter: {status_after}")
        _assert(entry_state in allowed_entry_states, f"Invalid entry status: {entry_state}")
        _assert(bool(reason_re.fullmatch(reason_code)), f"Invalid reasonCode format: {reason_code}")

        effective_at = _parse_iso8601(str(entry.get("effectiveAt") or ""), f"{change_id}.effectiveAt")
        timestamps.append(effective_at)

        _assert(op_id in request_ops, f"{change_id}: opId not found in requestRef operations: {op_id}")
        request_op = request_ops[op_id]
        _assert(str(request_op.get("action")) == action, f"{change_id}: action mismatch with requestRef")
        _assert(
            str(request_op.get("adapterId")) == adapter_id,
            f"{change_id}: adapterId mismatch with requestRef",
        )
        _assert(
            str(request_op.get("reasonCode")) == reason_code,
            f"{change_id}: reasonCode mismatch with requestRef",
        )
        _assert(
            str(request_op.get("effectiveAt")) == str(entry.get("effectiveAt")),
            f"{change_id}: effectiveAt mismatch with requestRef",
        )

        if action == "ROLLBACK":
            rollback_target = str(entry.get("rollbackTargetOpId") or "")
            _assert(rollback_target, f"{change_id}: rollbackTargetOpId is required for ROLLBACK")
            request_target = str((request_op.get("rollback") or {}).get("targetOpId") or "")
            _assert(
                rollback_target == request_target,
                f"{change_id}: rollbackTargetOpId mismatch with requestRef",
            )

        if adapter_id not in state_by_adapter:
            before_entry = _entry_by_adapter(registry_before, adapter_id, "registrySnapshotBeforeRef")
            state_by_adapter[adapter_id] = {
                "status": str(before_entry.get("status")),
                "tier": str(before_entry.get("certificationTier")),
            }

        prior_status = state_by_adapter[adapter_id]["status"]
        prior_tier = state_by_adapter[adapter_id]["tier"]
        _assert(
            prior_status == status_before,
            f"{change_id}: statusBefore {status_before} does not match prior status {prior_status}",
        )
        _assert(
            prior_tier == tier_before,
            f"{change_id}: tierBefore {tier_before} does not match prior tier {prior_tier}",
        )
        state_by_adapter[adapter_id] = {"status": status_after, "tier": tier_after}

    if policy.get("requireChronologicalOrder", False):
        _assert(timestamps == sorted(timestamps), "Changelog entries must be chronological by effectiveAt.")

    if policy.get("requireRequestOperationMatch", False):
        missing_ops = sorted(set(request_ops) - seen_op_ids)
        _assert(not missing_ops, f"Changelog missing request operation(s): {missing_ops}")

    for adapter_id, state in state_by_adapter.items():
        after_entry = _entry_by_adapter(registry_after, adapter_id, "registrySnapshotAfterRef")
        _assert(
            str(after_entry.get("status")) == state["status"],
            f"Post-snapshot status mismatch for {adapter_id}.",
        )
        _assert(
            str(after_entry.get("certificationTier")) == state["tier"],
            f"Post-snapshot tier mismatch for {adapter_id}.",
        )

    decision_adapter_id = str(decision_record.get("adapterId") or "")
    _assert(
        decision_adapter_id in state_by_adapter,
        "decisionRecordRef.adapterId must match a changelog adapterId.",
    )

    print("Registry changelog artifact checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
