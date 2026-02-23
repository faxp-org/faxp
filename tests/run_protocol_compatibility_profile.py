#!/usr/bin/env python3
"""Validate protocol compatibility profile artifact and runtime alignment."""

from __future__ import annotations

from pathlib import Path
import json
import re
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from faxp_mvp_simulation import (  # noqa: E402
    FaxpProtocol,
    negotiate_protocol_version,
)
from conformance.protocol_compatibility_signing import verify_profile_signature  # noqa: E402


PROFILE_PATH = PROJECT_ROOT / "conformance" / "protocol_compatibility_profile.v1.json"
PROFILE_KEYRING_PATH = PROJECT_ROOT / "conformance" / "protocol_compatibility_keys.sample.json"
FIXTURES_PATH = PROJECT_ROOT / "tests" / "protocol_version_fixtures.json"
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    _assert(isinstance(payload, dict), f"{path.name} must contain a JSON object.")
    return payload


def _validate_versions(values: list[str], context: str) -> None:
    _assert(values, f"{context} must be non-empty.")
    _assert(len(values) == len(set(values)), f"{context} must not contain duplicates.")
    for value in values:
        _assert(SEMVER_PATTERN.fullmatch(value), f"{context} contains invalid semver: {value}")


def main() -> int:
    profile = _load_json(PROFILE_PATH)
    profile_keyring = _load_json(PROFILE_KEYRING_PATH)
    fixtures_payload = _load_json(FIXTURES_PATH)
    fixtures = fixtures_payload.get("fixtures")
    _assert(isinstance(fixtures, list) and fixtures, "protocol_version_fixtures must be non-empty.")

    required_fields = [
        "profileVersion",
        "protocol",
        "runtimeVersions",
        "incomingVersions",
        "compatibilityMatrix",
        "acceptedStatuses",
        "rejectedStatus",
        "expectedReasonCodes",
        "requiredFixturePairs",
        "requiredIncompatibleFixtureReasons",
        "profileSignature",
    ]
    for field in required_fields:
        _assert(field in profile, f"profile missing required field: {field}")

    _assert(profile["protocol"] == FaxpProtocol.NAME, "profile protocol must match FaxpProtocol.NAME")
    verify_profile_signature(profile, keyring=profile_keyring, require_signature=True)

    runtime_versions = [str(item) for item in profile["runtimeVersions"]]
    incoming_versions = [str(item) for item in profile["incomingVersions"]]
    _validate_versions(runtime_versions, "runtimeVersions")
    _validate_versions(incoming_versions, "incomingVersions")
    _assert(
        set(runtime_versions) == set(incoming_versions),
        "runtimeVersions and incomingVersions must include same version set.",
    )
    _assert(
        set(incoming_versions) == set(FaxpProtocol.SUPPORTED_PROTOCOL_VERSIONS),
        "profile incomingVersions must match FaxpProtocol.SUPPORTED_PROTOCOL_VERSIONS.",
    )
    _assert(
        set(runtime_versions) == set(FaxpProtocol.VERSION_COMPATIBILITY_MATRIX.keys()),
        "profile runtimeVersions must match FaxpProtocol.VERSION_COMPATIBILITY_MATRIX keys.",
    )

    compatibility_matrix = profile["compatibilityMatrix"]
    _assert(isinstance(compatibility_matrix, dict), "compatibilityMatrix must be an object.")
    _assert(
        set(compatibility_matrix.keys()) == set(runtime_versions),
        "compatibilityMatrix runtime keys must match runtimeVersions.",
    )

    accepted_statuses = set(str(item) for item in profile["acceptedStatuses"])
    _assert(
        accepted_statuses == {"Compatible", "Degradable"},
        "acceptedStatuses must be exactly ['Compatible', 'Degradable'].",
    )
    _assert(profile["rejectedStatus"] == "Incompatible", "rejectedStatus must be 'Incompatible'.")

    reason_codes = profile["expectedReasonCodes"]
    _assert(isinstance(reason_codes, dict), "expectedReasonCodes must be an object.")
    for key in [
        "Compatible",
        "Degradable",
        "Unsupported",
        "InvalidFormat",
        "Missing",
        "IncompatiblePair",
    ]:
        _assert(key in reason_codes, f"expectedReasonCodes missing key: {key}")

    status_reason_map = {
        "Compatible": reason_codes["Compatible"],
        "Degradable": reason_codes["Degradable"],
    }

    fixture_status_pairs = set()
    fixture_incompatible_reasons = set()
    for fixture in fixtures:
        fixture_id = str(fixture.get("id") or "").strip()
        _assert(fixture_id, "each fixture requires non-empty id")
        runtime = str(fixture.get("runtimeVersion") or "").strip()
        incoming = str(fixture.get("incomingVersion") or "").strip()
        expected_status = str(fixture.get("expectedStatus") or "").strip()
        expected_reason = str(fixture.get("expectedReasonCode") or "").strip()
        _assert(runtime and incoming and expected_status and expected_reason, f"{fixture_id}: missing fields")
        fixture_status_pairs.add((runtime, incoming, expected_status))
        if expected_status == "Incompatible":
            fixture_incompatible_reasons.add(expected_reason)

    for runtime in runtime_versions:
        row = compatibility_matrix.get(runtime)
        _assert(isinstance(row, dict), f"compatibilityMatrix[{runtime}] must be an object.")
        _assert(
            set(row.keys()) == set(incoming_versions),
            f"compatibilityMatrix[{runtime}] incoming keys must match incomingVersions.",
        )
        runtime_matrix_row = FaxpProtocol.VERSION_COMPATIBILITY_MATRIX.get(runtime, {})
        for incoming in incoming_versions:
            expected_status = str(row[incoming])
            _assert(
                expected_status in {"Compatible", "Degradable", "Incompatible"},
                f"invalid compatibility status {runtime}->{incoming}: {expected_status}",
            )
            _assert(
                runtime_matrix_row.get(incoming) == expected_status,
                (
                    f"profile drift for runtime {runtime}, incoming {incoming}: "
                    f"profile={expected_status} runtime={runtime_matrix_row.get(incoming)}"
                ),
            )
            decision = negotiate_protocol_version(incoming, runtime_version=runtime)
            _assert(
                decision["status"] == expected_status,
                (
                    f"runtime decision mismatch for {runtime}->{incoming}: "
                    f"expected {expected_status}, got {decision['status']}"
                ),
            )
            expected_reason = status_reason_map.get(expected_status)
            if expected_reason:
                _assert(
                    decision["reasonCode"] == expected_reason,
                    (
                        f"reason mismatch for {runtime}->{incoming}: "
                        f"expected {expected_reason}, got {decision['reasonCode']}"
                    ),
                )
            _assert(
                (runtime, incoming, expected_status) in fixture_status_pairs,
                f"missing fixture for runtime/incoming pair {runtime}->{incoming} ({expected_status})",
            )

    unsupported_decision = negotiate_protocol_version("9.9.9", runtime_version=runtime_versions[0])
    _assert(
        unsupported_decision["reasonCode"] == reason_codes["Unsupported"],
        "unsupported reason code mismatch.",
    )
    invalid_format_decision = negotiate_protocol_version("v0.3", runtime_version=runtime_versions[0])
    _assert(
        invalid_format_decision["reasonCode"] == reason_codes["InvalidFormat"],
        "invalid-format reason code mismatch.",
    )
    missing_decision = negotiate_protocol_version("", runtime_version=runtime_versions[0])
    _assert(
        missing_decision["reasonCode"] == reason_codes["Missing"],
        "missing reason code mismatch.",
    )

    required_pairs = [str(item) for item in profile["requiredFixturePairs"]]
    for pair in required_pairs:
        _assert("->" in pair, f"requiredFixturePairs entry invalid: {pair}")
        runtime, incoming = [item.strip() for item in pair.split("->", 1)]
        matched = any(
            fixture_runtime == runtime and fixture_incoming == incoming
            for fixture_runtime, fixture_incoming, _ in fixture_status_pairs
        )
        _assert(matched, f"required fixture pair missing in fixtures: {pair}")

    required_incompatible_reasons = [
        str(item) for item in profile["requiredIncompatibleFixtureReasons"]
    ]
    for reason in required_incompatible_reasons:
        _assert(
            reason in fixture_incompatible_reasons,
            f"required incompatible fixture reason missing: {reason}",
        )

    print("Protocol compatibility profile checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
