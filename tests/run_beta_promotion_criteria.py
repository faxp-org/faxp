#!/usr/bin/env python3
"""Validate developer beta promotion criteria structure and evidence mappings."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CRITERIA_DOC_PATH = PROJECT_ROOT / "docs" / "governance" / "DEVELOPER_BETA_PROMOTION_CRITERIA.md"
BLOCK_BEGIN = "<!-- DEVELOPER_BETA_PROMOTION_CRITERIA_BEGIN -->"
BLOCK_END = "<!-- DEVELOPER_BETA_PROMOTION_CRITERIA_END -->"

EXPECTED_IDS = {
    "strict_release_readiness",
    "replay_operational_gates_closed",
    "security_posture_checkpoint",
    "public_safe_packet_published",
    "second_independent_implementer_demo",
    "open_source_guardrails_green",
}
ALLOWED_STATUSES = {"not_started", "in_progress", "blocked", "done"}
ALLOWED_DECISIONS = {"ready", "not_ready"}
DISALLOWED_OWNER_TOKENS = ("tbd", "todo", "unassigned", "<owner>")


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _extract_block(document: str, begin: str, end: str) -> str:
    start = document.find(begin)
    stop = document.find(end)
    _assert(start != -1 and stop != -1 and stop > start, f"Missing or invalid block: {begin}")
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
    _assert(CRITERIA_DOC_PATH.exists(), "Missing developer beta promotion criteria document.")
    document = CRITERIA_DOC_PATH.read_text(encoding="utf-8")
    payload = json.loads(_extract_block(document, BLOCK_BEGIN, BLOCK_END))

    _assert(isinstance(payload, dict), "Beta criteria manifest must be a JSON object.")
    _assert("updatedAt" in payload, "Manifest missing updatedAt.")
    _assert("minimumIndependentImplementerDemos" in payload, "Manifest missing minimumIndependentImplementerDemos.")
    _assert("betaDecision" in payload, "Manifest missing betaDecision.")
    _assert("criteria" in payload, "Manifest missing criteria.")
    _parse_iso8601(str(payload["updatedAt"]), "updatedAt")

    minimum_demos = int(payload["minimumIndependentImplementerDemos"])
    _assert(minimum_demos >= 2, "minimumIndependentImplementerDemos must be >= 2.")

    decision = str(payload["betaDecision"] or "").strip().lower()
    _assert(decision in ALLOWED_DECISIONS, f"Invalid betaDecision: {decision!r}")

    criteria = payload.get("criteria") or []
    _assert(isinstance(criteria, list) and criteria, "criteria must be a non-empty array.")

    ids_seen = set()
    has_in_progress = False
    all_done = True
    for item in criteria:
        _assert(isinstance(item, dict), "Each criteria entry must be an object.")
        criterion_id = str(item.get("id") or "").strip()
        owner = str(item.get("owner") or "").strip()
        due = str(item.get("due") or "").strip()
        status = str(item.get("status") or "").strip().lower()
        evidence = item.get("evidence") or []

        _assert(criterion_id, "Criterion id must be non-empty.")
        _assert(criterion_id not in ids_seen, f"Duplicate criterion id: {criterion_id}")
        ids_seen.add(criterion_id)

        _assert(owner, f"Owner missing for criterion: {criterion_id}")
        lowered_owner = owner.lower()
        _assert(
            all(token not in lowered_owner for token in DISALLOWED_OWNER_TOKENS),
            f"Owner contains placeholder token for criterion {criterion_id}: {owner}",
        )
        _parse_due_date(due, f"due ({criterion_id})")
        _assert(status in ALLOWED_STATUSES, f"Invalid status '{status}' for criterion {criterion_id}")

        if status == "in_progress":
            has_in_progress = True
        if status != "done":
            all_done = False

        _assert(isinstance(evidence, list) and evidence, f"Evidence list required for criterion {criterion_id}.")
        for evidence_ref in evidence:
            evidence_path = (PROJECT_ROOT / str(evidence_ref)).resolve()
            _assert(evidence_path.exists(), f"Missing evidence path for {criterion_id}: {evidence_ref}")

    _assert(
        ids_seen == EXPECTED_IDS,
        f"Criterion IDs mismatch. expected={sorted(EXPECTED_IDS)} actual={sorted(ids_seen)}",
    )

    expected_decision = "ready" if all_done else "not_ready"
    _assert(
        decision == expected_decision,
        f"betaDecision mismatch: expected '{expected_decision}' from statuses but found '{decision}'.",
    )

    if decision == "not_ready":
        _assert(
            has_in_progress or any(
                str((item or {}).get("status") or "").strip().lower() in {"blocked", "not_started"}
                for item in criteria
            ),
            "betaDecision=not_ready requires at least one non-done criterion.",
        )

    print("Developer beta promotion criteria checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
