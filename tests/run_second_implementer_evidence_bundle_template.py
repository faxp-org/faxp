#!/usr/bin/env python3
"""Validate second implementer evidence bundle template structure and public-safety baseline."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json
import re


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = PROJECT_ROOT / "docs" / "builders" / "SECOND_IMPLEMENTER_EVIDENCE_BUNDLE_TEMPLATE.json"
ALLOWED_RESULT = {"PASS", "PARTIAL", "BLOCKED", "IN_PROGRESS"}
ALLOWED_CHECK_RESULT = {"PASS", "PARTIAL", "FAIL", "NOT_RUN"}
REQUIRED_EXECUTION_CHECKS = {
    "sandboxAuth",
    "createReadPath",
    "deterministicUpdateByStableIds",
    "postUpdateReadbackNoDuplicateStops",
    "faxpBodyValidation",
    "faxpEnvelopeValidation",
}
LOCAL_PATH_PATTERNS = (
    re.compile(r"/Users/[A-Za-z0-9._-]+/"),
    re.compile(r"[A-Za-z]:\\\\Users\\\\"),
)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _parse_iso8601(value: str, context: str) -> None:
    try:
        datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise AssertionError(f"{context} must be ISO-8601.") from exc


def _assert_no_local_path(value: str, context: str) -> None:
    for pattern in LOCAL_PATH_PATTERNS:
        _assert(not pattern.search(value), f"{context} must not include local absolute filesystem paths.")


def main() -> int:
    _assert(TEMPLATE_PATH.exists(), f"Missing template: {TEMPLATE_PATH}")
    payload = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    _assert(isinstance(payload, dict), "Template root must be a JSON object.")

    required_top_level = {
        "schemaVersion",
        "maturity",
        "result",
        "evaluationWindow",
        "implementer",
        "independenceQualification",
        "scopeValidation",
        "executionChecks",
        "publicSafety",
        "evidenceRefs",
        "notes",
    }
    missing = sorted(required_top_level - set(payload.keys()))
    _assert(not missing, f"Template missing required top-level keys: {missing}")

    _assert(str(payload.get("schemaVersion") or "").strip() == "1.0.0", "schemaVersion must be '1.0.0'.")
    _assert(
        str(payload.get("maturity") or "").strip() == "experimental_sandbox_only",
        "maturity must be experimental_sandbox_only.",
    )

    result = str(payload.get("result") or "").strip().upper()
    _assert(result in ALLOWED_RESULT, f"Invalid result value: {result!r}")

    window = payload.get("evaluationWindow") or {}
    _assert(isinstance(window, dict), "evaluationWindow must be an object.")
    _parse_iso8601(str(window.get("startedAtUtc") or ""), "evaluationWindow.startedAtUtc")
    _parse_iso8601(str(window.get("finishedAtUtc") or ""), "evaluationWindow.finishedAtUtc")

    implementer = payload.get("implementer") or {}
    _assert(isinstance(implementer, dict), "implementer must be an object.")
    alias = str(implementer.get("alias") or "").strip()
    integration_type = str(implementer.get("integrationType") or "").strip()
    _assert(alias, "implementer.alias must be non-empty.")
    _assert(integration_type, "implementer.integrationType must be non-empty.")
    _assert_no_local_path(alias, "implementer.alias")

    independence = payload.get("independenceQualification") or {}
    _assert(isinstance(independence, dict), "independenceQualification must be an object.")
    for key in [
        "isIndependentImplementer",
        "separateImplementationOwner",
        "separateRuntimeCredentials",
        "realSandboxExecution",
        "syntheticOnlyOrMockedFlow",
    ]:
        _assert(isinstance(independence.get(key), bool), f"independenceQualification.{key} must be boolean.")
    _assert(
        independence.get("isIndependentImplementer") is True,
        "independenceQualification.isIndependentImplementer must be true in template baseline.",
    )
    _assert(
        independence.get("separateImplementationOwner") is True,
        "independenceQualification.separateImplementationOwner must be true in template baseline.",
    )
    _assert(
        independence.get("separateRuntimeCredentials") is True,
        "independenceQualification.separateRuntimeCredentials must be true in template baseline.",
    )
    _assert(
        independence.get("realSandboxExecution") is True,
        "independenceQualification.realSandboxExecution must be true in template baseline.",
    )
    _assert(
        independence.get("syntheticOnlyOrMockedFlow") is False,
        "independenceQualification.syntheticOnlyOrMockedFlow must be false in template baseline.",
    )
    reviewer = str(independence.get("evidenceReviewedByOwner") or "").strip()
    _assert(reviewer, "independenceQualification.evidenceReviewedByOwner must be non-empty.")
    _assert_no_local_path(reviewer, "independenceQualification.evidenceReviewedByOwner")
    reviewed_at = str(independence.get("reviewedAtUtc") or "").strip()
    _parse_iso8601(reviewed_at, "independenceQualification.reviewedAtUtc")

    scope_validation = payload.get("scopeValidation") or {}
    _assert(isinstance(scope_validation, dict), "scopeValidation must be an object.")
    for key in [
        "bookingPlaneOnly",
        "dispatchOrSettlementOutOfScope",
        "protocolVsAdapterBoundaryConfirmed",
    ]:
        _assert(isinstance(scope_validation.get(key), bool), f"scopeValidation.{key} must be boolean.")

    execution_checks = payload.get("executionChecks") or {}
    _assert(isinstance(execution_checks, dict), "executionChecks must be an object.")
    _assert(
        set(execution_checks.keys()) == REQUIRED_EXECUTION_CHECKS,
        (
            "executionChecks keys mismatch. "
            f"expected={sorted(REQUIRED_EXECUTION_CHECKS)} actual={sorted(execution_checks.keys())}"
        ),
    )
    for check_name, check_result in execution_checks.items():
        normalized = str(check_result or "").strip().upper()
        _assert(
            normalized in ALLOWED_CHECK_RESULT,
            f"executionChecks.{check_name} has invalid value: {check_result!r}",
        )

    public_safety = payload.get("publicSafety") or {}
    _assert(isinstance(public_safety, dict), "publicSafety must be an object.")
    for key in [
        "partnerIdentifiersRemoved",
        "credentialsTokensRemoved",
        "localAbsolutePathsRemoved",
        "traceableIdsReplacedWithSyntheticValues",
    ]:
        _assert(public_safety.get(key) is True, f"publicSafety.{key} must be true in template baseline.")

    evidence_refs = payload.get("evidenceRefs") or []
    _assert(isinstance(evidence_refs, list) and evidence_refs, "evidenceRefs must be a non-empty array.")
    for ref in evidence_refs:
        value = str(ref or "").strip()
        _assert(value, "evidenceRefs entries must be non-empty.")
        _assert(not value.startswith("/"), "evidenceRefs entries must be repo-relative paths.")
        _assert_no_local_path(value, "evidenceRefs entry")

    notes = payload.get("notes") or []
    _assert(isinstance(notes, list) and notes, "notes must be a non-empty array.")
    for note in notes:
        value = str(note or "").strip()
        _assert(value, "notes entries must be non-empty.")

    print("Second implementer evidence bundle template checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
