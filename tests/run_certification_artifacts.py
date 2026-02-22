#!/usr/bin/env python3
"""Validate verification profile and certification registry artifacts."""

from __future__ import annotations

import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILE_SCHEMA_PATH = PROJECT_ROOT / "profiles" / "verification" / "profile.schema.json"
STRICT_PROFILE_PATH = PROJECT_ROOT / "profiles" / "verification" / "US_FMCSA_STRICT_V1.json"
BALANCED_PROFILE_PATH = PROJECT_ROOT / "profiles" / "verification" / "US_FMCSA_BALANCED_V1.json"
REGISTRY_SCHEMA_PATH = PROJECT_ROOT / "conformance" / "certification_registry.schema.json"
REGISTRY_SAMPLE_PATH = PROJECT_ROOT / "conformance" / "certification_registry.sample.json"


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _validate(schema: dict, payload: dict, label: str) -> None:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda item: item.path)
    if errors:
        detail = "; ".join(err.message for err in errors[:3])
        raise AssertionError(f"{label} failed schema validation: {detail}")


def _assert_tier_coverage(profile: dict, label: str) -> None:
    tiers = [entry.get("tier") for entry in profile.get("riskTiers", [])]
    _assert(sorted(tiers) == [0, 1, 2, 3], f"{label} must define tiers 0..3.")


def main() -> int:
    profile_schema = _load_json(PROFILE_SCHEMA_PATH)
    strict_profile = _load_json(STRICT_PROFILE_PATH)
    balanced_profile = _load_json(BALANCED_PROFILE_PATH)
    registry_schema = _load_json(REGISTRY_SCHEMA_PATH)
    registry_sample = _load_json(REGISTRY_SAMPLE_PATH)

    _validate(profile_schema, strict_profile, "strict profile")
    _validate(profile_schema, balanced_profile, "balanced profile")
    _validate(registry_schema, registry_sample, "certification registry sample")

    _assert_tier_coverage(strict_profile, "strict profile")
    _assert_tier_coverage(balanced_profile, "balanced profile")

    _assert(
        strict_profile["policyDefaults"]["degradedMode"] == "HardBlock",
        "strict profile degraded mode should be HardBlock.",
    )
    _assert(
        balanced_profile["policyDefaults"]["degradedMode"] in {"SoftHold", "GraceCache"},
        "balanced profile degraded mode should permit continuity behavior.",
    )
    _assert(
        balanced_profile["policyDefaults"]["maxFallbackDurationSeconds"]
        >= strict_profile["policyDefaults"]["maxFallbackDurationSeconds"],
        "balanced profile must not be stricter than strict profile fallback duration.",
    )

    entries = registry_sample.get("entries", [])
    _assert(entries, "registry sample must include at least one entry.")
    first_entry = entries[0]
    _assert(
        first_entry["hostingModel"] == "ImplementerHosted",
        "registry sample should reflect implementer-hosted production model.",
    )
    _assert(
        bool(first_entry.get("profilesSupported")),
        "registry sample entry must include supported profiles.",
    )

    print("Certification artifact checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
