#!/usr/bin/env python3
"""Helpers for loading normative policy-profile cases from POLICY_PROFILES.md."""

from __future__ import annotations

from pathlib import Path
import json


MATRIX_BEGIN = "<!-- POLICY_TEST_MATRIX_BEGIN -->"
MATRIX_END = "<!-- POLICY_TEST_MATRIX_END -->"


def _extract_matrix_block(document: str) -> str:
    start = document.find(MATRIX_BEGIN)
    end = document.find(MATRIX_END)
    if start == -1 or end == -1 or end <= start:
        raise ValueError("POLICY_PROFILES.md is missing policy test matrix markers.")
    return document[start + len(MATRIX_BEGIN) : end].strip()


def load_policy_test_matrix(project_root: Path) -> list[dict]:
    policy_doc_path = project_root / "POLICY_PROFILES.md"
    document = policy_doc_path.read_text(encoding="utf-8")
    matrix_payload = _extract_matrix_block(document)

    try:
        cases = json.loads(matrix_payload)
    except json.JSONDecodeError as exc:
        raise ValueError("POLICY_PROFILES.md matrix block is not valid JSON.") from exc

    if not isinstance(cases, list) or not cases:
        raise ValueError("Policy test matrix must be a non-empty JSON array.")

    seen_ids: set[str] = set()
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("Each policy test matrix case must be an object.")
        case_id = str(case.get("id") or "").strip()
        if not case_id:
            raise ValueError("Each policy test matrix case must include a non-empty id.")
        if case_id in seen_ids:
            raise ValueError(f"Duplicate policy test case id detected: {case_id}")
        seen_ids.add(case_id)

        profile_id = str(case.get("profileId") or "").strip()
        if not profile_id:
            raise ValueError(f"Policy test case {case_id} missing profileId.")
        verification = case.get("verification")
        expected = case.get("expected")
        if not isinstance(verification, dict):
            raise ValueError(f"Policy test case {case_id} must include object verification payload.")
        if not isinstance(expected, dict):
            raise ValueError(f"Policy test case {case_id} must include object expected payload.")

    return cases
