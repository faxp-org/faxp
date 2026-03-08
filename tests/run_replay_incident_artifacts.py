#!/usr/bin/env python3
"""Validate replay incident artifact output schema from incident drill workflow."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json
import os


DEFAULT_ARTIFACT_PATH = "/tmp/faxp_replay_incident_artifact.json"
PLACEHOLDER_TOKENS = {
    "tbd",
    "todo",
    "sample",
    "template",
    "placeholder",
    "n/a",
    "na",
}


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _parse_iso8601(value: str, context: str) -> None:
    try:
        datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise AssertionError(f"{context} must be ISO-8601.") from exc


def _assert_not_placeholder(value: object, context: str) -> None:
    normalized = str(value or "").strip()
    lowered = normalized.lower()
    _assert(normalized, f"{context} must be non-empty.")
    _assert(lowered not in PLACEHOLDER_TOKENS, f"{context} contains placeholder content.")


def main() -> int:
    artifact_path = Path(
        os.getenv("FAXP_INCIDENT_ARTIFACT_PATH", DEFAULT_ARTIFACT_PATH)
    ).expanduser()
    _assert(artifact_path.exists(), f"Missing replay incident artifact: {artifact_path}")
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    _assert(isinstance(payload, dict), "Replay incident artifact must be a JSON object.")

    required_fields = [
        "artifactVersion",
        "drillType",
        "startedAt",
        "finishedAt",
        "status",
        "timeline",
        "decisions",
        "closureNotes",
        "correctiveActions",
    ]
    for field in required_fields:
        _assert(field in payload, f"Replay incident artifact missing field: {field}")

    _parse_iso8601(payload["startedAt"], "startedAt")
    _parse_iso8601(payload["finishedAt"], "finishedAt")
    _assert(payload["status"] in {"pass", "fail"}, "status must be pass|fail.")

    timeline = payload.get("timeline") or []
    _assert(isinstance(timeline, list) and timeline, "timeline must be a non-empty array.")
    for index, entry in enumerate(timeline):
        _assert(isinstance(entry, dict), f"timeline entry {index} must be object.")
        _assert_not_placeholder(entry.get("event"), f"timeline entry {index} event")
        _assert_not_placeholder(entry.get("result"), f"timeline entry {index} result")
        _parse_iso8601(str(entry.get("time") or ""), f"timeline[{index}].time")

    decisions = payload.get("decisions") or []
    _assert(isinstance(decisions, list) and decisions, "decisions must be a non-empty array.")
    _assert(
        all(str(item).strip() for item in decisions),
        "decisions must contain non-empty entries.",
    )
    for index, decision in enumerate(decisions):
        _assert_not_placeholder(decision, f"decisions entry {index}")

    corrective_actions = payload.get("correctiveActions") or []
    _assert(
        isinstance(corrective_actions, list) and corrective_actions,
        "correctiveActions must be a non-empty array.",
    )
    _assert(
        all(str(item).strip() for item in corrective_actions),
        "correctiveActions must contain non-empty entries.",
    )
    for index, action in enumerate(corrective_actions):
        _assert_not_placeholder(action, f"correctiveActions entry {index}")

    closure_notes = str(payload.get("closureNotes") or "").strip()
    _assert_not_placeholder(closure_notes, "closureNotes")

    print("Replay incident artifact checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
