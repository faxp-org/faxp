#!/usr/bin/env python3
"""Validate open-source governance guardrails and contributor safety rails."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> int:
    required_files = [
        PROJECT_ROOT / "CODE_OF_CONDUCT.md",
        PROJECT_ROOT / "SUPPORT.md",
        PROJECT_ROOT / "SECURITY.md",
        PROJECT_ROOT / ".gitleaks.toml",
        PROJECT_ROOT / ".pre-commit-config.yaml",
        PROJECT_ROOT / "scripts" / "install_precommit.sh",
        PROJECT_ROOT / ".github" / "ISSUE_TEMPLATE" / "config.yml",
        PROJECT_ROOT / "tests" / "run_public_redaction_guardrails.py",
    ]
    for path in required_files:
        _assert(path.exists(), f"Missing required open-source guardrail file: {path.relative_to(PROJECT_ROOT)}")

    issue_config = _read(PROJECT_ROOT / ".github" / "ISSUE_TEMPLATE" / "config.yml")
    _assert("blank_issues_enabled: false" in issue_config, "Issue template config must disable blank issues.")
    _assert("SECURITY.md" in issue_config, "Issue template config must link SECURITY.md.")
    _assert("SUPPORT.md" in issue_config, "Issue template config must link SUPPORT.md.")

    contributing = _read(PROJECT_ROOT / "CONTRIBUTING.md")
    _assert("docs/governance/SCOPE_GUARDRAILS.md" in contributing, "CONTRIBUTING.md must reference scope guardrails.")
    _assert("REFERENCE_RUNTIME_BOUNDARY.md" in contributing, "CONTRIBUTING.md must reference runtime boundary.")
    _assert("SECURITY.md" in contributing, "CONTRIBUTING.md must reference SECURITY.md.")
    _assert("CODE_OF_CONDUCT.md" in contributing, "CONTRIBUTING.md must reference CODE_OF_CONDUCT.md.")
    _assert("SUPPORT.md" in contributing, "CONTRIBUTING.md must reference SUPPORT.md.")
    _assert("scripts/install_precommit.sh" in contributing, "CONTRIBUTING.md must reference pre-commit installer.")
    _assert(".pre-commit-config.yaml" in contributing, "CONTRIBUTING.md must reference pre-commit config.")
    _assert(
        "tests/run_public_redaction_guardrails.py" in contributing,
        "CONTRIBUTING.md must include public redaction guardrails check.",
    )

    readme = _read(PROJECT_ROOT / "README.md")
    _assert("CONTRIBUTING.md" in readme, "README.md must reference CONTRIBUTING.md.")
    _assert("SECURITY.md" in readme, "README.md must reference SECURITY.md.")
    _assert("CODE_OF_CONDUCT.md" in readme, "README.md must reference CODE_OF_CONDUCT.md.")
    _assert("SUPPORT.md" in readme, "README.md must reference SUPPORT.md.")
    _assert("scripts/install_precommit.sh" in readme, "README.md must reference pre-commit installer.")

    security = _read(PROJECT_ROOT / "SECURITY.md")
    _assert("Secret scanning" in security, "SECURITY.md must document Secret scanning requirement.")
    _assert("Push protection" in security, "SECURITY.md must document Push protection requirement.")
    _assert("Dependabot alerts" in security, "SECURITY.md must document Dependabot alerts requirement.")
    _assert(
        "Dependabot security updates" in security,
        "SECURITY.md must document Dependabot security updates requirement.",
    )
    _assert("pre-commit" in security, "SECURITY.md must mention local pre-commit guardrails.")

    ci = _read(PROJECT_ROOT / ".github" / "workflows" / "ci.yml")
    _assert("Gitleaks secret scan" in ci, "CI workflow must include gitleaks secret scan step.")
    _assert("gitleaks detect" in ci, "CI workflow must run gitleaks detect command.")

    precommit = _read(PROJECT_ROOT / ".pre-commit-config.yaml")
    _assert("faxp-security-gate" in precommit, "pre-commit config must include security gate hook.")
    _assert(
        "tests/run_public_redaction_guardrails.py" in precommit,
        "pre-commit config must include public redaction guardrails hook.",
    )
    _assert(
        "tests/run_open_source_guardrails.py" in precommit,
        "pre-commit config must include open-source guardrails hook.",
    )

    print("Open-source guardrails checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
