#!/usr/bin/env python3
"""Validate adoption execution runbook packet integrity and tracker template coverage."""

from __future__ import annotations

from pathlib import Path
import re


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNBOOK_PATH = PROJECT_ROOT / "docs" / "builders" / "ADOPTION_EXECUTION_RUNBOOK.md"
PACKET_PATH = PROJECT_ROOT / "docs" / "builders" / "PUBLIC_OUTREACH_EVALUATION_PACKET.md"
TRACKER_TEMPLATE_PATH = PROJECT_ROOT / "docs" / "builders" / "ADOPTION_EXECUTION_TRACKER_TEMPLATE.md"

DISCLAIMER_LINE = (
    "FAXP is experimental and early-stage. This is a sandbox-first evaluation, not a production rollout."
)
EXPECTED_STAGES = {
    "Intro Sent",
    "Packet Shared",
    "Sandbox Access Requested",
    "Sandbox Access Granted",
    "Technical Evaluation Active",
    "Feedback Received",
    "Paused",
    "Closed",
}
LOCAL_PATH_PATTERNS = (
    re.compile(r"/Users/[A-Za-z0-9._-]+/"),
    re.compile(r"[A-Za-z]:\\\\Users\\\\"),
)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _extract_section(text: str, heading: str) -> str:
    marker = f"## {heading}"
    start = text.find(marker)
    _assert(start != -1, f"Missing section: {heading}")
    remaining = text[start + len(marker):]
    next_heading = remaining.find("\n## ")
    if next_heading == -1:
        return remaining.strip()
    return remaining[:next_heading].strip()


def _assert_no_local_paths(text: str, context: str) -> None:
    for pattern in LOCAL_PATH_PATTERNS:
        _assert(not pattern.search(text), f"{context} must not include local absolute filesystem paths.")


def main() -> int:
    for path in [RUNBOOK_PATH, PACKET_PATH, TRACKER_TEMPLATE_PATH]:
        _assert(path.exists(), f"Missing required document: {path}")

    runbook = RUNBOOK_PATH.read_text(encoding="utf-8")
    packet = PACKET_PATH.read_text(encoding="utf-8")
    tracker = TRACKER_TEMPLATE_PATH.read_text(encoding="utf-8")

    _assert(DISCLAIMER_LINE in runbook, "Runbook must include the exact experimental disclaimer line.")

    required_packet_section = _extract_section(runbook, "Required Packet")
    packet_refs = re.findall(r"^\d+\.\s+`([^`]+)`", required_packet_section, flags=re.MULTILINE)
    _assert(packet_refs, "Runbook required packet section must include numbered path references.")
    _assert(
        "docs/builders/ADOPTION_EXECUTION_TRACKER_TEMPLATE.md" in packet_refs,
        "Runbook required packet must include ADOPTION_EXECUTION_TRACKER_TEMPLATE.md.",
    )

    for ref in packet_refs:
        ref_path = (PROJECT_ROOT / ref).resolve()
        _assert(ref_path.exists(), f"Runbook required packet reference does not exist: {ref}")

    _assert(
        "docs/builders/ADOPTION_EXECUTION_TRACKER_TEMPLATE.md" in packet,
        "Public outreach packet must reference ADOPTION_EXECUTION_TRACKER_TEMPLATE.md.",
    )

    _assert("| DateUTC | ImplementerAlias | Channel | Stage |" in tracker, "Tracker template missing table header.")
    stages_found = set(re.findall(r"^- `([^`]+)`$", tracker, flags=re.MULTILINE))
    _assert(stages_found == EXPECTED_STAGES, f"Tracker stage values mismatch: {sorted(stages_found)}")

    _assert_no_local_paths(runbook, "Adoption runbook")
    _assert_no_local_paths(packet, "Public outreach packet")
    _assert_no_local_paths(tracker, "Adoption tracker template")

    print("Adoption execution runbook checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
