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
JOB_HEADER_PATTERN = re.compile(r"^  ([A-Za-z0-9_-]+):\s*$")

WORKFLOW_WRITE_SCOPE_ALLOWLIST = {
    "a2a-watch.yml": {"issues: write"},
    "mcp-watch.yml": {"issues: write"},
}


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_top_level_block(lines: list[str], key: str) -> list[str]:
    header = f"{key}:"
    start = -1
    for idx, line in enumerate(lines):
        if line.strip() == header and not line.startswith(" "):
            start = idx
            break
    if start == -1:
        return []

    block = [lines[start]]
    for idx in range(start + 1, len(lines)):
        line = lines[idx]
        if line.strip() == "":
            block.append(line)
            continue
        if line.startswith("  "):
            block.append(line)
            continue
        break
    return block


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

        top_permissions = _extract_top_level_block(lines, "permissions")
        if not top_permissions:
            violations.append(f"{rel}: must declare top-level permissions.")
        else:
            top_permissions_body = "\n".join(top_permissions)
            if not re.search(r"(?m)^\s{2}contents:\s*read\s*$", top_permissions_body):
                violations.append(f"{rel}: top-level permissions must include 'contents: read'.")
            if re.search(r"(?m)^\s{2}[a-z-]+:\s*write\s*$", top_permissions_body):
                violations.append(f"{rel}: top-level permissions must not include write scopes.")

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


def _validate_workflow_job_timeouts() -> None:
    violations: list[str] = []
    for workflow in sorted(WORKFLOWS_DIR.glob("*.yml")):
        rel = workflow.relative_to(PROJECT_ROOT)
        contents = workflow.read_text(encoding="utf-8")
        lines = contents.splitlines()
        if "jobs:" not in contents:
            continue

        jobs_start = next((idx for idx, line in enumerate(lines) if line.strip() == "jobs:"), -1)
        if jobs_start == -1:
            continue

        job_indices: list[tuple[str, int, int]] = []
        for idx in range(jobs_start + 1, len(lines)):
            match = JOB_HEADER_PATTERN.match(lines[idx])
            if match:
                job_indices.append((match.group(1), idx, idx + 1))

        for i, (job_name, header_idx, start_idx) in enumerate(job_indices):
            end_idx = job_indices[i + 1][1] if i + 1 < len(job_indices) else len(lines)
            block = lines[start_idx:end_idx]
            has_runs_on = any(re.match(r"^\s{4}runs-on:\s*", line) for line in block)
            if not has_runs_on:
                continue
            has_timeout = any(re.match(r"^\s{4}timeout-minutes:\s*\d+\s*$", line) for line in block)
            if not has_timeout:
                violations.append(f"{rel}:{header_idx + 1}: job '{job_name}' must declare timeout-minutes.")

    _assert(
        not violations,
        "Workflow timeout guardrail violations:\n" + "\n".join(f"- {item}" for item in violations),
    )


def _validate_workflow_concurrency_policy() -> None:
    violations: list[str] = []
    for workflow in sorted(WORKFLOWS_DIR.glob("*.yml")):
        rel = workflow.relative_to(PROJECT_ROOT)
        contents = workflow.read_text(encoding="utf-8")
        if "concurrency:" not in contents:
            violations.append(f"{rel}: must declare top-level concurrency policy.")
            continue
        if not re.search(r"(?m)^concurrency:\s*$", contents):
            violations.append(f"{rel}: concurrency block must be top-level.")
        if not re.search(r"(?m)^\s{2}group:\s*.+$", contents):
            violations.append(f"{rel}: concurrency block must define group.")
        if not re.search(r"(?m)^\s{2}cancel-in-progress:\s*(true|false)\s*$", contents):
            violations.append(f"{rel}: concurrency block must define cancel-in-progress.")

    _assert(
        not violations,
        "Workflow concurrency guardrail violations:\n" + "\n".join(f"- {item}" for item in violations),
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
        PROJECT_ROOT / "tests" / "run_python_compile_checks.py",
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
    _assert(
        "Never post local absolute filesystem paths in public GitHub issues, PR comments, or discussions."
        in contributing,
        "CONTRIBUTING.md must include explicit no-local-paths rule for public collaboration.",
    )
    _assert(
        "Never post partner-specific names/identifiers in public GitHub issues, PR comments, or discussions"
        in contributing,
        "CONTRIBUTING.md must include explicit partner-identifier hygiene rule for public collaboration.",
    )
    _assert(
        "Never post tokens, credentials, bearer strings, or secret-like material in public GitHub issues, PR comments, or discussions."
        in contributing,
        "CONTRIBUTING.md must include explicit no-secrets rule for public collaboration.",
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
    _assert(
        "experimental and early-stage" in readme.lower(),
        "README.md must include explicit experimental/early-stage maturity notice.",
    )
    _assert(
        "not production guarantees" in readme.lower(),
        "README.md must state pilot/evaluation artifacts are not production guarantees.",
    )
    _assert(
        "legacy compliance-provider labels" in readme.lower(),
        "README.md must document that legacy provider labels can appear in reference-runtime compatibility paths.",
    )
    _assert(
        "not protocol-core requirements" in readme.lower(),
        "README.md must state legacy provider labels are not protocol-core requirements.",
    )

    runtime_boundary = _read(PROJECT_ROOT / "REFERENCE_RUNTIME_BOUNDARY.md")
    _assert(
        "verification ownership boundary" in runtime_boundary.lower(),
        "REFERENCE_RUNTIME_BOUNDARY.md must include verification ownership boundary section.",
    )
    _assert(
        "fmcsa/compliance lookup execution" in runtime_boundary.lower(),
        "REFERENCE_RUNTIME_BOUNDARY.md must document builder-side compliance lookup ownership.",
    )
    _assert(
        "faxp does not execute verifier operations" in runtime_boundary.lower(),
        "REFERENCE_RUNTIME_BOUNDARY.md must state verifier operations stay builder-side.",
    )

    docs_index = _read(PROJECT_ROOT / "docs" / "INDEX.md")
    _assert(
        "experimental and early-stage" in docs_index.lower(),
        "docs/INDEX.md must include explicit experimental/early-stage maturity notice.",
    )
    _assert(
        "pilot/evaluation" in docs_index.lower(),
        "docs/INDEX.md must include pilot/evaluation usage guidance.",
    )

    builders_start = _read(PROJECT_ROOT / "docs" / "BUILDERS_START_HERE.md")
    _assert(
        "experimental and early-stage" in builders_start.lower(),
        "docs/BUILDERS_START_HERE.md must include explicit experimental/early-stage maturity notice.",
    )
    _assert(
        "sandbox/test environments first" in builders_start.lower(),
        "docs/BUILDERS_START_HERE.md must direct builders to sandbox/test environments first.",
    )

    required_diagram_paths = [
        "docs/diagrams/01_scope_boundary.md",
        "docs/diagrams/02_booking_message_flow.md",
        "docs/diagrams/03_replay_protection_runtime.md",
    ]
    required_diagram_source_paths = [
        "docs/diagrams/01_scope_boundary.mmd",
        "docs/diagrams/02_booking_message_flow.mmd",
        "docs/diagrams/03_replay_protection_runtime.mmd",
    ]
    diagram_source_map = {
        "docs/diagrams/01_scope_boundary.md": "docs/diagrams/01_scope_boundary.mmd",
        "docs/diagrams/02_booking_message_flow.md": "docs/diagrams/02_booking_message_flow.mmd",
        "docs/diagrams/03_replay_protection_runtime.md": "docs/diagrams/03_replay_protection_runtime.mmd",
    }
    for rel_path in required_diagram_paths:
        _assert(
            (PROJECT_ROOT / rel_path).exists(),
            f"Missing required diagram doc: {rel_path}",
        )
        _assert(
            rel_path in readme,
            f"README.md must reference diagram doc: {rel_path}",
        )
        _assert(
            rel_path in docs_index,
            f"docs/INDEX.md must reference diagram doc: {rel_path}",
        )
        diagram_doc = _read(PROJECT_ROOT / rel_path)
        _assert(
            "This diagram is explanatory, not normative." in diagram_doc,
            f"{rel_path} must explicitly state it is explanatory/non-normative.",
        )
        _assert(
            "Canonical" in diagram_doc,
            f"{rel_path} must include canonical policy/source references.",
        )
        expected_source = diagram_source_map[rel_path]
        _assert(
            expected_source in diagram_doc,
            f"{rel_path} must reference Mermaid source file: {expected_source}",
        )

    for rel_path in required_diagram_source_paths:
        _assert(
            (PROJECT_ROOT / rel_path).exists(),
            f"Missing required Mermaid source file: {rel_path}",
        )

    _assert(
        "docs/diagrams/01_scope_boundary.md" in builders_start,
        "docs/BUILDERS_START_HERE.md must reference scope boundary diagram.",
    )
    _assert(
        "docs/diagrams/02_booking_message_flow.md" in builders_start,
        "docs/BUILDERS_START_HERE.md must reference booking message flow diagram.",
    )

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
    _assert(
        "top-level permissions" in security.lower(),
        "SECURITY.md must document top-level workflow permissions policy.",
    )
    _assert(
        "timeout-minutes" in security,
        "SECURITY.md must document workflow timeout-minutes requirement.",
    )
    _assert(
        "concurrency" in security.lower(),
        "SECURITY.md must document workflow concurrency policy requirement.",
    )
    _assert(
        "checksum" in security.lower(),
        "SECURITY.md must document checksum verification requirement for downloaded CI binaries.",
    )
    _assert(
        "python compile checks" in security.lower(),
        "SECURITY.md must document local python compile checks in pre-commit guardrails.",
    )

    pr_template = _read(PROJECT_ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md")
    _assert(
        "No partner-specific identifiers were added to public files." in pr_template,
        "PR template must require partner-identifier hygiene confirmation.",
    )
    _assert(
        "No local absolute filesystem paths were added to public files." in pr_template,
        "PR template must require local-path hygiene confirmation.",
    )
    _assert(
        "No secrets or key material were added." in pr_template,
        "PR template must require secret hygiene confirmation.",
    )

    bug_template = _read(PROJECT_ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.md")
    _assert(
        "I removed secrets/tokens/key material." in bug_template,
        "Bug report template must require secret removal hygiene check.",
    )
    _assert(
        "I removed partner-specific identifiers not suitable for public issues." in bug_template,
        "Bug report template must require partner-identifier hygiene check.",
    )
    _assert(
        "I removed local absolute filesystem paths." in bug_template,
        "Bug report template must require local-path hygiene check.",
    )

    feature_template = _read(PROJECT_ROOT / ".github" / "ISSUE_TEMPLATE" / "feature_request.md")
    _assert(
        "No partner-specific identifiers are required to understand this request." in feature_template,
        "Feature request template must require partner-identifier hygiene check.",
    )
    _assert(
        "No local absolute filesystem paths are included." in feature_template,
        "Feature request template must require local-path hygiene check.",
    )

    ci = _read(PROJECT_ROOT / ".github" / "workflows" / "ci.yml")
    _assert("Gitleaks secret scan" in ci, "CI workflow must include gitleaks secret scan step.")
    _assert("gitleaks detect" in ci, "CI workflow must run gitleaks detect command.")
    _assert("gitleaks_checksums.txt" in ci, "CI workflow must fetch gitleaks checksums for verification.")
    _assert("sha256sum -c" in ci, "CI workflow must verify downloaded binary checksum before install.")
    _validate_workflow_action_sources()
    _validate_workflow_permissions_and_events()
    _validate_workflow_job_timeouts()
    _validate_workflow_concurrency_policy()

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
    _assert(
        "tests/run_python_compile_checks.py" in precommit,
        "pre-commit config must include python compile checks hook.",
    )

    print("Open-source guardrails checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
