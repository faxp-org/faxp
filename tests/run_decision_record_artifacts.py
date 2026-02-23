#!/usr/bin/env python3
"""Validate sample certification decision record artifact and cross-link integrity."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json
import re


PROJECT_ROOT = Path(__file__).resolve().parents[1]

TEMPLATE_PATH = PROJECT_ROOT / "CERTIFICATION_DECISION_RECORD_TEMPLATE.md"
DECISION_SAMPLE_PATH = PROJECT_ROOT / "conformance" / "certification_decision_record.sample.json"
CONFORMANCE_REPORT_PATH = PROJECT_ROOT / "conformance" / "sample_conformance_report.json"
REGISTRY_BEFORE_PATH = PROJECT_ROOT / "conformance" / "certification_registry.sample.json"
REGISTRY_AFTER_PATH = PROJECT_ROOT / "conformance" / "certification_registry.sample.after_update.json"
SUBMISSION_MANIFEST_PATH = PROJECT_ROOT / "conformance" / "submission_manifest.sample.json"

REQ_BEGIN = "<!-- CERT_DECISION_TEMPLATE_REQUIREMENTS_BEGIN -->"
REQ_END = "<!-- CERT_DECISION_TEMPLATE_REQUIREMENTS_END -->"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _extract_block(document: str, start_marker: str, end_marker: str) -> str:
    start = document.find(start_marker)
    end = document.find(end_marker)
    _assert(start != -1 and end != -1 and end > start, f"Missing or invalid block: {start_marker}")
    return document[start + len(start_marker) : end].strip()


def _parse_iso8601(value: str, context: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AssertionError(f"{context} must be ISO-8601.") from exc


def _entry_by_adapter(registry: dict, adapter_id: str, context: str) -> dict:
    for entry in registry.get("entries", []):
        if str(entry.get("adapterId")) == adapter_id:
            return entry
    raise AssertionError(f"{context}: adapterId not found: {adapter_id}")


def main() -> int:
    template_doc = TEMPLATE_PATH.read_text(encoding="utf-8")
    requirements = json.loads(_extract_block(template_doc, REQ_BEGIN, REQ_END))
    decision = _load_json(DECISION_SAMPLE_PATH)
    conformance_report = _load_json(CONFORMANCE_REPORT_PATH)
    registry_before = _load_json(REGISTRY_BEFORE_PATH)
    registry_after = _load_json(REGISTRY_AFTER_PATH)
    submission_manifest = _load_json(SUBMISSION_MANIFEST_PATH)

    required_fields = list(requirements.get("requiredFields") or [])
    _assert(required_fields, "Template requirements must include requiredFields.")
    for field in required_fields:
        _assert(field in decision, f"Decision artifact missing required field: {field}")

    _parse_iso8601(str(decision["decisionTimestamp"]), "decisionTimestamp")

    allowed_outcomes = set(requirements.get("allowedDecisionOutcomes") or [])
    _assert(
        str(decision.get("decisionOutcome")) in allowed_outcomes,
        "Decision artifact outcome is not allowed by template.",
    )

    reason_re = re.compile(str(requirements.get("reasonCodePattern") or ""))
    reason_codes = decision.get("decisionReasonCodes") or []
    _assert(isinstance(reason_codes, list) and reason_codes, "decisionReasonCodes must be non-empty list.")
    for code in reason_codes:
        _assert(bool(reason_re.fullmatch(str(code))), f"Invalid decision reason code: {code}")

    evidence_links = decision.get("evidenceLinks") or []
    _assert(isinstance(evidence_links, list) and evidence_links, "evidenceLinks must be non-empty list.")
    evidence_ref_re = re.compile(str(requirements.get("evidenceRefPattern") or ""))
    required_types = set(requirements.get("requiredEvidenceTypes") or [])

    evidence_by_type: dict[str, str] = {}
    for item in evidence_links:
        _assert(isinstance(item, dict), "Each evidence link must be an object.")
        ev_type = str(item.get("type") or "")
        ev_ref = str(item.get("ref") or "")
        _assert(ev_type, "Evidence type is required.")
        _assert(ev_ref, "Evidence ref is required.")
        _assert(bool(evidence_ref_re.fullmatch(ev_ref)), f"Invalid evidence ref format: {ev_ref}")
        _assert(ev_type not in evidence_by_type, f"Duplicate evidence type found: {ev_type}")
        evidence_by_type[ev_type] = ev_ref

        if not ev_ref.startswith("http://") and not ev_ref.startswith("https://"):
            _assert((PROJECT_ROOT / ev_ref).resolve().exists(), f"Evidence path not found: {ev_ref}")

    missing_types = sorted(required_types - set(evidence_by_type))
    _assert(not missing_types, f"Missing required evidence types: {missing_types}")

    adapter_id = str(decision.get("adapterId") or "")
    _assert(adapter_id, "adapterId is required.")
    _assert(
        str(conformance_report.get("adapterId") or "") == adapter_id,
        "Conformance report adapterId must match decision adapterId.",
    )
    _assert(
        bool((conformance_report.get("summary") or {}).get("passed")),
        "Conformance report must indicate passed=true for approved sample decision.",
    )

    _assert(
        str(decision.get("conformanceReportRef") or "") == evidence_by_type["ConformanceSuiteReport"],
        "conformanceReportRef must match ConformanceSuiteReport evidence ref.",
    )

    before_entry = _entry_by_adapter(registry_before, adapter_id, "registry_before")
    after_entry = _entry_by_adapter(registry_after, adapter_id, "registry_after")

    _assert(
        str(decision.get("registryVersionEvaluated") or "") == str(registry_before.get("registryVersion") or ""),
        "registryVersionEvaluated should match registry snapshot version.",
    )
    _assert(
        str(before_entry.get("status") or "") in {"Active", "Suspended", "Revoked"},
        "registry_before status is invalid.",
    )
    _assert(
        str(after_entry.get("status") or "") in {"Active", "Suspended", "Revoked"},
        "registry_after status is invalid.",
    )

    _assert(
        str(submission_manifest.get("adapterId") or "") == adapter_id,
        "Submission manifest adapterId must match decision adapterId.",
    )

    outcome = str(decision.get("decisionOutcome") or "")
    decided_tier = str(decision.get("decidedTier") or "")
    if outcome == "Approve":
        _assert(
            str(after_entry.get("status") or "") == "Active",
            "Approved decision requires Active status in post-decision registry snapshot.",
        )
        _assert(
            str(after_entry.get("certificationTier") or "") == decided_tier,
            "Approved decision decidedTier must match post-decision registry tier.",
        )

    approver = decision.get("approver") or {}
    _assert(isinstance(approver, dict), "approver must be an object.")
    _assert(str(approver.get("organization") or "").strip(), "approver.organization is required.")
    _assert(str(approver.get("approverRef") or "").strip(), "approver.approverRef is required.")
    _assert(str(approver.get("approvalMode") or "").strip(), "approver.approvalMode is required.")

    print("Certification decision record artifact checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
