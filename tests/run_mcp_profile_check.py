#!/usr/bin/env python3
"""Validate FAXP MCP interoperability profile and tooling contract artifacts."""

from __future__ import annotations

from pathlib import Path
import json
import re


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = PROJECT_ROOT / "docs" / "interop" / "MCP_COMPATIBILITY_PROFILE.md"
CONTRACT_PATH = PROJECT_ROOT / "conformance" / "mcp_tooling_contract.json"

PROFILE_BEGIN = "<!-- MCP_PROFILE_BEGIN -->"
PROFILE_END = "<!-- MCP_PROFILE_END -->"

EXPECTED_MESSAGE_TYPES = [
    "NewLoad",
    "LoadSearch",
    "NewTruck",
    "TruckSearch",
    "BidRequest",
    "BidResponse",
    "ExecutionReport",
    "AmendRequest",
]


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _extract_json_block(document: str, begin: str, end: str) -> dict:
    start = document.find(begin)
    stop = document.find(end)
    _assert(start != -1 and stop != -1 and stop > start, "Missing MCP profile JSON block markers.")
    raw = document[start + len(begin) : stop].strip()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AssertionError("MCP profile JSON block is invalid.") from exc
    _assert(isinstance(payload, dict), "MCP profile JSON block must be an object.")
    return payload


def main() -> int:
    profile_doc = PROFILE_PATH.read_text(encoding="utf-8")
    profile = _extract_json_block(profile_doc, PROFILE_BEGIN, PROFILE_END)
    contract = _load_json(CONTRACT_PATH)

    _assert(profile.get("mode") == "LooseCoupledInterop", "MCP profile mode mismatch.")
    _assert(profile.get("coreProtocolChangesRequired") is False, "MCP profile must not require core changes.")
    _assert(profile.get("mcpRequired") is False, "MCP profile must keep MCP optional.")
    _assert(profile.get("hostingModel") == "BuilderHosted", "MCP profile hostingModel must be BuilderHosted.")

    supported_patterns = list(profile.get("supportedPatterns") or [])
    for item in ["HybridAgent", "ToolDelegation", "EvidenceDigestOnly"]:
        _assert(item in supported_patterns, f"MCP profile missing supported pattern: {item}")

    allowed_fields = list(profile.get("allowedToolEvidenceFields") or [])
    for field in [
        "toolLayer",
        "serverId",
        "action",
        "outputDigest",
        "executedAt",
        "policyRef",
        "correlationRef",
    ]:
        _assert(field in allowed_fields, f"MCP profile missing allowedToolEvidenceField: {field}")

    required_controls = list(profile.get("requiredSecurityControls") or [])
    for control in [
        "LeastPrivilegeScopes",
        "ServerAllowlist",
        "AuditCorrelation",
        "FailClosedCriticalChecks",
    ]:
        _assert(control in required_controls, f"MCP profile missing requiredSecurityControl: {control}")

    correlation_fields = list(profile.get("faxpCorrelationFields") or [])
    for field in ["MessageID", "ContractID"]:
        _assert(field in correlation_fields, f"MCP profile missing faxpCorrelationField: {field}")

    _assert(contract.get("mode") == "LooseCoupledInterop", "MCP contract mode mismatch.")
    _assert(contract.get("coreProtocolChangesRequired") is False, "MCP contract must not require core changes.")
    _assert(contract.get("mcpRequired") is False, "MCP contract must keep MCP optional.")
    _assert(contract.get("hostingModel") == "BuilderHosted", "MCP contract hostingModel mismatch.")

    evidence_schema = contract.get("toolEvidenceSchema") or {}
    required_fields = list(evidence_schema.get("requiredFields") or [])
    for field in [
        "toolLayer",
        "serverId",
        "action",
        "outputDigest",
        "executedAt",
        "policyRef",
        "correlationRef",
    ]:
        _assert(field in required_fields, f"MCP contract toolEvidenceSchema missing required field: {field}")

    digest_pattern = str(evidence_schema.get("digestPattern") or "")
    correlation_pattern = str(evidence_schema.get("correlationRefPattern") or "")
    _assert(bool(re.fullmatch(digest_pattern, "sha256:1234abcd")), "MCP contract digestPattern check failed.")
    _assert(bool(re.fullmatch(correlation_pattern, "MSG-2026-ABC123")), "MCP contract correlationRefPattern check failed.")

    controls = contract.get("securityControls") or {}
    expected_controls = {
        "leastPrivilegeScopes": True,
        "serverAllowlist": True,
        "auditCorrelation": True,
        "failClosedCriticalChecks": True,
        "rejectRawSensitivePayloads": True,
    }
    for key, expected in expected_controls.items():
        _assert(controls.get(key) is expected, f"MCP contract securityControls.{key} must be {expected}.")

    faxp_compat = contract.get("faxpCompatibility") or {}
    required_message_types = list(faxp_compat.get("requiredMessageTypes") or [])
    _assert(
        sorted(required_message_types) == sorted(EXPECTED_MESSAGE_TYPES),
        "MCP contract requiredMessageTypes must match FAXP message set.",
    )
    _assert(
        faxp_compat.get("noCoreEnvelopeMutation") is True,
        "MCP contract must enforce noCoreEnvelopeMutation=true.",
    )
    _assert(
        faxp_compat.get("noMandatoryMcpFieldsInCore") is True,
        "MCP contract must enforce noMandatoryMcpFieldsInCore=true.",
    )

    print("MCP profile compatibility checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
