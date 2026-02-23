# Release Readiness Checklist

Use this checklist as the final go/no-go gate before a tagged release.

## Goals
- Ensure protocol, security, conformance, and governance controls are all present.
- Ensure required automated checks are wired into both CI and conformance suite.
- Prevent release drift where docs claim controls that are not actually enforced.

## Manual Checklist
- [ ] Protocol schemas and simulation artifacts are present and version-aligned.
- [ ] Security scripts and baseline policies are present.
- [ ] Governance policies, templates, and runbooks are present.
- [ ] Conformance and certification artifacts are present.
- [ ] CI and conformance suite include all mandatory release-readiness checks.

## Normative Requirements (Test-Enforced)

<!-- RELEASE_READINESS_REQUIREMENTS_BEGIN -->
{
  "requiredArtifacts": [
    "faxp.schema.json",
    "faxp.v0.2.schema.json",
    "faxp_mvp_simulation.py",
    "security_gate.sh",
    "incident_drill.sh",
    "run_secure_demo.sh",
    "SCOPE_GUARDRAILS.md",
    "RFC_TEMPLATE.md",
    "POLICY_PROFILES.md",
    "REGISTRY_ADMISSION_POLICY.md",
    "REGISTRY_CHANGELOG_POLICY.md",
    "CERTIFICATION_DECISION_RECORD_TEMPLATE.md",
    "DECISION_RECORDS_RUNBOOK.md",
    "CERTIFICATION_PLAYBOOK.md",
    "GOVERNANCE_INDEX.json",
    "conformance/certification_registry.sample.json",
    "conformance/certification_registry.sample.after_update.json",
    "conformance/registry_update.sample.json",
    "conformance/registry_changelog.sample.json",
    "conformance/certification_decision_record.sample.json",
    "conformance/sample_conformance_report.json"
  ],
  "requiredTests": [
    "tests/run_scope_guardrails.py",
    "tests/run_policy_profile_sync.py",
    "tests/run_registry_admission_policy.py",
    "tests/run_registry_changelog_artifacts.py",
    "tests/run_decision_record_template.py",
    "tests/run_decision_record_artifacts.py",
    "tests/run_governance_index.py",
    "tests/run_release_readiness.py"
  ],
  "requiredSuiteChecks": [
    "policy_profile_sync",
    "registry_admission_policy",
    "registry_changelog_artifacts",
    "decision_record_template",
    "decision_record_artifacts",
    "governance_index",
    "release_readiness"
  ],
  "requireGovernanceIndexSync": true
}
<!-- RELEASE_READINESS_REQUIREMENTS_END -->
