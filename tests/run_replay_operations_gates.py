#!/usr/bin/env python3
"""Validate replay operational gate assignments and evidence artifacts."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GATES_DOC_PATH = PROJECT_ROOT / "docs" / "governance" / "REPLAY_OPERATIONS_GATES.md"
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

    _assert(
        gate_ids == EXPECTED_GATE_IDS,
        f"Gate IDs mismatch. expected={sorted(EXPECTED_GATE_IDS)} actual={sorted(gate_ids)}",
    )

    print("Replay operations gate checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
