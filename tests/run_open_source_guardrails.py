#!/usr/bin/env python3
"""Validate open-source governance guardrails and contributor safety rails."""

from __future__ import annotations

from pathlib import Path
import re


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = PROJECT_ROOT / ".github" / "workflows"

ALLOWED_ACTION_REPOS = {
    "actions/checkout",
    "actions/setup-python",
    "actions/upload-artifact",
    "actions/github-script",
}

FULL_SHA_PATTERN = re.compile(r"^[a-f0-9]{40}$")
WRITE_SCOPE_PATTERN = re.compile(r"^\s*([a-z-]+)\s*:\s*write\s*$")

WORKFLOW_WRITE_SCOPE_ALLOWLIST = {
    "a2a-watch.yml": {"issues: write"},
    "mcp-watch.yml": {"issues: write"},
}


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _validate_workflow_action_sources() -> None:
    _assert(WORKFLOWS_DIR.exists(), ".github/workflows directory must exist.")

    violations: list[str] = []
    for workflow in sorted(WORKFLOWS_DIR.glob("*.yml")):
        for line_no, raw in enumerate(workflow.read_text(encoding="utf-8").splitlines(), start=1):
            line = raw.strip()
            if not line.startswith("uses:"):
                continue
            value = line.split(":", 1)[1].strip()
            if value.startswith("./"):
                continue
            if value.startswith("docker://"):
                violations.append(
                    f"{workflow.relative_to(PROJECT_ROOT)}:{line_no} uses docker action reference ({value}); "
                    "only allowlisted GitHub actions pinned to full commit SHA are permitted."
                )
                continue
            if "@" not in value:
                violations.append(
                    f"{workflow.relative_to(PROJECT_ROOT)}:{line_no} has malformed uses reference ({value})."
                )
                continue

            action_repo, ref = value.split("@", 1)
            if action_repo not in ALLOWED_ACTION_REPOS:
                violations.append(
                    f"{workflow.relative_to(PROJECT_ROOT)}:{line_no} uses non-allowlisted action ({action_repo})."
                )
                continue
            if not FULL_SHA_PATTERN.fullmatch(ref):
                violations.append(
                    f"{workflow.relative_to(PROJECT_ROOT)}:{line_no} must pin {action_repo} "
                    f"to full 40-char commit SHA, got ({ref})."
                )

    _assert(
        not violations,
        "Workflow action pinning/allowlist violations:\n" + "\n".join(f"- {item}" for item in violations),
    )


def _validate_workflow_permissions_and_events() -> None:
    violations: list[str] = []
    for workflow in sorted(WORKFLOWS_DIR.glob("*.yml")):
        rel = workflow.relative_to(PROJECT_ROOT)
        contents = workflow.read_text(encoding="utf-8")
        lines = contents.splitlines()

        if "permissions:" not in contents:
            violations.append(f"{rel}: must declare explicit workflow/job permissions.")

        if re.search(r"(?m)^\s*pull_request_target\s*:", contents):
            violations.append(
                f"{rel}: pull_request_target is disallowed by repository policy due to elevated token risk."
            )

        if re.search(r"(?m)^\s*permissions\s*:\s*write-all\s*$", contents):
            violations.append(f"{rel}: permissions: write-all is disallowed.")

        if re.search(r"(?m)^\s*contents\s*:\s*write\s*$", contents):
            violations.append(f"{rel}: contents: write is disallowed in workflow permissions.")

        allowed_scopes = WORKFLOW_WRITE_SCOPE_ALLOWLIST.get(workflow.name, set())
        for line_no, line in enumerate(lines, start=1):
            match = WRITE_SCOPE_PATTERN.match(line)
            if not match:
                continue
            scope = f"{match.group(1)}: write"
            if scope not in allowed_scopes:
                violations.append(
                    f"{rel}:{line_no}: write scope '{scope}' is not in workflow allowlist for {workflow.name}."
                )

    _assert(
        not violations,
        "Workflow permission/event guardrail violations:\n" + "\n".join(f"- {item}" for item in violations),
    )


def main() -> int:
    required_files = [
        PROJECT_ROOT / "CODE_OF_CONDUCT.md",
        PROJECT_ROOT / "SUPPORT.md",
        PROJECT_ROOT / "SECURITY.md",
        PROJECT_ROOT / "docs" / "governance" / "REPLAY_RUNTIME_POLICY.md",
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
    _assert(
        "docs/governance/REPLAY_RUNTIME_POLICY.md" in readme,
        "README.md must reference replay runtime policy.",
    )
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
    _assert(
        "replay_single_instance_override_active" in security,
        "SECURITY.md must document single-instance replay override startup audit event.",
    )
    _assert(
        "redis_shared" in security,
        "SECURITY.md must document shared replay backend requirement.",
    )
    _assert(
        "24" in security and "hour" in security.lower(),
        "SECURITY.md must document max 24-hour replay override lifetime.",
    )
    _assert(
        "approved public domains" in security.lower(),
        "SECURITY.md must document approved-domain public redaction guardrail.",
    )
    _assert(
        "credential-like literals" in security.lower(),
        "SECURITY.md must document credential-like literal detection in public redaction guardrails.",
    )
    _assert(
        "FAXP_PRIVATE_REDACTION_TERMS" in security,
        "SECURITY.md must document optional private redaction terms env var.",
    )
    _assert(
        "full-length commit SHA" in security,
        "SECURITY.md must require GitHub Actions pinning to full-length commit SHA.",
    )
    _assert(
        "action allowlist" in security.lower(),
        "SECURITY.md must require an explicit GitHub Actions allowlist policy.",
    )
    _assert(
        "pull_request_target" in security,
        "SECURITY.md must document pull_request_target policy.",
    )
    _assert(
        "write scopes" in security.lower(),
        "SECURITY.md must document workflow write-scope restrictions.",
    )

    ci = _read(PROJECT_ROOT / ".github" / "workflows" / "ci.yml")
    _assert("Gitleaks secret scan" in ci, "CI workflow must include gitleaks secret scan step.")
    _assert("gitleaks detect" in ci, "CI workflow must run gitleaks detect command.")
    _validate_workflow_action_sources()
    _validate_workflow_permissions_and_events()

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
