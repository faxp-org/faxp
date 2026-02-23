#!/usr/bin/env python3
"""Validate certification decision record template requirements and evidence links."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json
import re


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = PROJECT_ROOT / "CERTIFICATION_DECISION_RECORD_TEMPLATE.md"

REQ_BEGIN = "<!-- CERT_DECISION_TEMPLATE_REQUIREMENTS_BEGIN -->"
REQ_END = "<!-- CERT_DECISION_TEMPLATE_REQUIREMENTS_END -->"
EXAMPLE_BEGIN = "<!-- CERT_DECISION_TEMPLATE_EXAMPLE_BEGIN -->"
EXAMPLE_END = "<!-- CERT_DECISION_TEMPLATE_EXAMPLE_END -->"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _extract_block(document: str, start_marker: str, end_marker: str) -> str:
    start = document.find(start_marker)
    end = document.find(end_marker)
    _assert(start != -1 and end != -1 and end > start, f"Missing or invalid block: {start_marker}")
    return document[start + len(start_marker) : end].strip()


def _parse_iso8601(value: str, context: str) -> None:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AssertionError(f"{context} must be ISO-8601.") from exc


def main() -> int:
    document = TEMPLATE_PATH.read_text(encoding="utf-8")

    requirements = json.loads(_extract_block(document, REQ_BEGIN, REQ_END))
    example = json.loads(_extract_block(document, EXAMPLE_BEGIN, EXAMPLE_END))

    required_fields = list(requirements.get("requiredFields") or [])
    _assert(required_fields, "Template requirements must include requiredFields.")
    for field in required_fields:
        _assert(field in example, f"Decision record example missing required field: {field}")

    _parse_iso8601(str(example["decisionTimestamp"]), "decisionTimestamp")

    allowed_outcomes = set(requirements.get("allowedDecisionOutcomes") or [])
    _assert(allowed_outcomes, "Template requirements must include allowedDecisionOutcomes.")
    _assert(
        str(example["decisionOutcome"]) in allowed_outcomes,
        "decisionOutcome in example is not allowed by requirements.",
    )

    reason_code_re = re.compile(str(requirements.get("reasonCodePattern") or ""))
    reason_codes = example.get("decisionReasonCodes") or []
    _assert(isinstance(reason_codes, list) and reason_codes, "decisionReasonCodes must be non-empty list.")
    for code in reason_codes:
        code_value = str(code)
        _assert(
            bool(reason_code_re.fullmatch(code_value)),
            f"decisionReasonCode does not match pattern: {code_value}",
        )

    evidence_links = example.get("evidenceLinks") or []
    _assert(isinstance(evidence_links, list) and evidence_links, "evidenceLinks must be non-empty list.")
    evidence_ref_re = re.compile(str(requirements.get("evidenceRefPattern") or ""))
    required_evidence_types = set(requirements.get("requiredEvidenceTypes") or [])
    seen_types: set[str] = set()

    for item in evidence_links:
        _assert(isinstance(item, dict), "Each evidence link must be an object.")
        ev_type = str(item.get("type") or "")
        ev_ref = str(item.get("ref") or "")
        _assert(ev_type, "Evidence link type is required.")
        _assert(ev_ref, "Evidence link ref is required.")
        _assert(
            bool(evidence_ref_re.fullmatch(ev_ref)),
            f"Evidence ref format invalid: {ev_ref}",
        )
        seen_types.add(ev_type)

        if not ev_ref.startswith("http://") and not ev_ref.startswith("https://"):
            local_path = (PROJECT_ROOT / ev_ref).resolve()
            _assert(local_path.exists(), f"Evidence link path does not exist: {ev_ref}")

    missing_types = sorted(required_evidence_types - seen_types)
    _assert(not missing_types, f"Missing required evidence link types: {missing_types}")

    approver = example.get("approver") or {}
    _assert(isinstance(approver, dict), "approver must be an object.")
    _assert(str(approver.get("organization") or "").strip(), "approver.organization is required.")
    _assert(str(approver.get("approverRef") or "").strip(), "approver.approverRef is required.")
    _assert(str(approver.get("approvalMode") or "").strip(), "approver.approvalMode is required.")

    print("Certification decision record template checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
