#!/usr/bin/env python3
"""Run conformance bundle checks and emit a machine-readable report."""

from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from conformance.conformance_bundle import evaluate_bundle  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate adapter profile + registry entry conformance bundle."
    )
    parser.add_argument(
        "--profile",
        default=str(PROJECT_ROOT / "conformance" / "adapter_profile.sample.json"),
        help="Path to adapter profile JSON.",
    )
    parser.add_argument(
        "--registry-entry",
        default=str(PROJECT_ROOT / "conformance" / "certification_registry.sample.json"),
        help="Path to registry entry JSON or full registry JSON with entries[].",
    )
    parser.add_argument(
        "--keyring",
        default=str(PROJECT_ROOT / "conformance" / "attestation_keys.sample.json"),
        help="Path to attestation keyring JSON.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional output report JSON path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    profile_path = Path(args.profile).expanduser().resolve()
    registry_path = Path(args.registry_entry).expanduser().resolve()
    keyring_path = Path(args.keyring).expanduser().resolve()
    report = evaluate_bundle(
        profile_path=profile_path,
        registry_path=registry_path,
        keyring_path=keyring_path,
        conformance_dir=PROJECT_ROOT / "conformance",
    )
    report_json = json.dumps(report, indent=2)
    print(report_json)
    if args.output:
        output_path = Path(args.output).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report_json + "\n", encoding="utf-8")
        print(f"[ConformanceBundle] wrote report to {output_path}")
    return 0 if report["summary"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
