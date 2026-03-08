#!/usr/bin/env python3
"""Validate replay operational gate assignments and evidence artifacts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import re


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GATES_DOC_PATH = PROJECT_ROOT / "docs" / "governance" / "REPLAY_OPERATIONS_GATES.md"
ONCALL_DOC_PATH = PROJECT_ROOT / "docs" / "governance" / "REPLAY_ONCALL_OWNERSHIP.md"
REVIEW_LOG_PATH = PROJECT_ROOT / "docs" / "governance" / "REPLAY_OVERRIDE_AUDIT_REVIEW_LOG.md"
BLOCK_BEGIN = "<!-- REPLAY_OPERATIONS_GATES_BEGIN -->"
BLOCK_END = "<!-- REPLAY_OPERATIONS_GATES_END -->"

EXPECTED_GATE_IDS = {
    "replay_claim_slo_error_budget",
    "replay_reject_rate_alerting",
    "replay_redis_ha_failover",
    "replay_incident_runbook_signoff",
    "replay_oncall_ownership_and_override_review",
}
ALLOWED_STATUSES = {"planned", "in_progress", "done"}
DISALLOWED_OWNER_TOKENS = ("tbd", "todo", "unassigned", "<owner>")
DISALLOWED_BACKUP_TOKENS = ("designate", "tbd", "todo", "unassigned", "<backup>")
DISALLOWED_REVIEW_TOKENS = ("sample", "template", "tbd", "todo")
REVIEW_RECENCY_DAYS = 14
ACTIVE_REVIEW_STATUSES = {"active", "open", "in_progress"}
REQUIRED_EVIDENCE_BY_GATE = {
    "replay_claim_slo_error_budget": {
        "tests/run_replay_ops_monitoring.py",
        "scripts/evaluate_replay_ops.py",
    },
    "replay_reject_rate_alerting": {
        "tests/run_replay_ops_monitoring.py",
        "scripts/evaluate_replay_ops.py",
    },
    "replay_incident_runbook_signoff": {
        "tests/run_replay_incident_artifacts.py",
        "scripts/incident_drill.sh",
    },
}


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _extract_block(document: str, begin: str, end: str) -> str:
    start = document.find(begin)
    stop = document.find(end)
    _assert(start != -1 and stop != -1 and stop > start, f"Missing block markers: {begin}")
    return document[start + len(begin) : stop].strip()


def _parse_iso8601(value: str, context: str) -> None:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AssertionError(f"{context} must be ISO-8601.") from exc


def _parse_due_date(value: str, context: str) -> None:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise AssertionError(f"{context} must be YYYY-MM-DD.") from exc


def _validate_oncall_backup_identity() -> None:
    _assert(ONCALL_DOC_PATH.exists(), "Missing replay on-call ownership document.")
    contents = ONCALL_DOC_PATH.read_text(encoding="utf-8")
    match = re.search(r"^- Backup on-call:\s*(.+)$", contents, flags=re.MULTILINE)
    _assert(match is not None, "Replay on-call ownership doc missing backup on-call line.")
    value = (match.group(1) or "").strip()
    _assert(value, "Backup on-call value must be non-empty.")
    lowered = value.lower()
    _assert(
        all(token not in lowered for token in DISALLOWED_BACKUP_TOKENS),
        f"Backup on-call value is still placeholder-like: {value}",
    )


def _parse_review_log_rows(document: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for raw_line in document.splitlines():
        line = raw_line.strip()
        if not line.startswith("|"):
            continue
        if line.startswith("| ---"):
            continue
        if "ReviewDateUTC" in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 7:
            continue
        rows.append(cells)
    return rows


def _validate_override_review_log() -> None:
    _assert(REVIEW_LOG_PATH.exists(), "Missing replay override review log document.")
    contents = REVIEW_LOG_PATH.read_text(encoding="utf-8")
    rows = _parse_review_log_rows(contents)
    _assert(rows, "Replay override review log must include at least one review row.")

    now = datetime.now(timezone.utc)
    latest_review = None
    for index, row in enumerate(rows):
        review_date, reviewer, ticket, owner, expires_at, status, notes = row
        _parse_due_date(review_date, f"ReviewDateUTC row {index}")
        _parse_iso8601(expires_at, f"ExpiresAtUTC row {index}")

        lowered_status = status.strip().lower()
        lowered_notes = notes.strip().lower()
        _assert(reviewer.strip(), f"Reviewer must be non-empty in row {index}.")
        _assert(ticket.strip(), f"OverrideTicket must be non-empty in row {index}.")
        _assert(owner.strip(), f"Owner must be non-empty in row {index}.")
        _assert(lowered_status, f"Status must be non-empty in row {index}.")
        _assert(
            all(token not in lowered_status for token in DISALLOWED_REVIEW_TOKENS),
            f"Status contains disallowed placeholder token in row {index}: {status}",
        )
        _assert(
            all(token not in lowered_notes for token in DISALLOWED_REVIEW_TOKENS),
            f"Notes contains disallowed placeholder token in row {index}: {notes}",
        )

        review_dt = datetime.strptime(review_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if latest_review is None or review_dt > latest_review:
            latest_review = review_dt

        expires_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00")).astimezone(timezone.utc)
        if lowered_status in ACTIVE_REVIEW_STATUSES:
            _assert(
                expires_dt > now,
                f"Active override row {index} is already expired ({expires_at}).",
            )

    _assert(latest_review is not None, "Unable to determine latest replay override review date.")
    _assert(
        now - latest_review <= timedelta(days=REVIEW_RECENCY_DAYS),
        f"Latest override review is older than {REVIEW_RECENCY_DAYS} days: {latest_review.date()}",
    )


def main() -> int:
    _assert(GATES_DOC_PATH.exists(), "Missing replay operations gates document.")
    document = GATES_DOC_PATH.read_text(encoding="utf-8")
    payload = json.loads(_extract_block(document, BLOCK_BEGIN, BLOCK_END))

    _assert(isinstance(payload, dict), "Gate manifest must be a JSON object.")
    _assert("updatedAt" in payload, "Gate manifest missing updatedAt.")
    _assert("gates" in payload, "Gate manifest missing gates.")
    _parse_iso8601(str(payload["updatedAt"]), "updatedAt")

    gates = payload.get("gates") or []
    _assert(isinstance(gates, list) and gates, "gates must be a non-empty array.")

    gate_ids = set()
    for gate in gates:
        _assert(isinstance(gate, dict), "Each gate entry must be an object.")
        gate_id = str(gate.get("id") or "").strip()
        owner = str(gate.get("owner") or "").strip()
        due = str(gate.get("due") or "").strip()
        status = str(gate.get("status") or "").strip()
        evidence = gate.get("evidence") or []

        _assert(gate_id, "Gate id must be non-empty.")
        _assert(gate_id not in gate_ids, f"Duplicate gate id: {gate_id}")
        gate_ids.add(gate_id)

        _assert(owner, f"Gate owner must be set for {gate_id}.")
        lowered_owner = owner.lower()
        _assert(
            all(token not in lowered_owner for token in DISALLOWED_OWNER_TOKENS),
            f"Gate owner contains placeholder token for {gate_id}: {owner}",
        )

        _parse_due_date(due, f"due ({gate_id})")
        _assert(status in ALLOWED_STATUSES, f"Invalid status '{status}' for gate {gate_id}.")
        _assert(isinstance(evidence, list) and evidence, f"Evidence list required for gate {gate_id}.")

        for evidence_ref in evidence:
            evidence_path = (PROJECT_ROOT / str(evidence_ref)).resolve()
            _assert(evidence_path.exists(), f"Missing evidence path for {gate_id}: {evidence_ref}")
        required_refs = REQUIRED_EVIDENCE_BY_GATE.get(gate_id) or set()
        missing_refs = sorted(required_refs - {str(ref) for ref in evidence})
        _assert(
            not missing_refs,
            f"Gate {gate_id} missing required executable evidence references: {missing_refs}",
        )

    _assert(
        gate_ids == EXPECTED_GATE_IDS,
        f"Gate IDs mismatch. expected={sorted(EXPECTED_GATE_IDS)} actual={sorted(gate_ids)}",
    )
    _validate_oncall_backup_identity()
    _validate_override_review_log()

    print("Replay operations gate checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
