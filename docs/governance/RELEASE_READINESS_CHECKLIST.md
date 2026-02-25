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
    "scripts/security_gate.sh",
    "scripts/incident_drill.sh",
    "scripts/run_secure_demo.sh",
    "docs/governance/SCOPE_GUARDRAILS.md",
    "docs/rfc/RFC_TEMPLATE.md",
    "docs/governance/POLICY_PROFILES.md",
    "docs/governance/REGISTRY_ADMISSION_POLICY.md",
    "docs/governance/REGISTRY_CHANGELOG_POLICY.md",
    "docs/governance/TRUSTED_VERIFIER_ADMISSION_REQUIREMENTS.md",
    "docs/governance/BOOKING_PLANE_COMMERCIAL_TERMS.md",
    "docs/governance/TRUST_MODEL.md",
    "docs/governance/VERIFICATION_RESPONSIBILITY_MODEL.md",
    "docs/governance/CERTIFICATION_DECISION_RECORD_TEMPLATE.md",
    "docs/governance/DECISION_RECORDS_RUNBOOK.md",
    "docs/governance/CERTIFICATION_PLAYBOOK.md",
    "docs/governance/GOVERNANCE_INDEX.json",
    "conformance/rate_model_profile.v1.json",
    "conformance/rate_model_profile_keys.sample.json",
    "conformance/protocol_compatibility_profile.v1.json",
    "conformance/protocol_compatibility_keys.sample.json",
    "conformance/vendor_direct_verifier_profile.v1.json",
    "conformance/trust_profile.v1.json",
    "conformance/accessorial_terms_profile.v1.json",
    "conformance/certification_registry.sample.json",
    "conformance/certification_registry.sample.after_update.json",
    "conformance/trusted_verifier_registry.sample.json",
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
    "tests/run_trusted_verifier_registry.py",
    "tests/run_vendor_direct_profile.py",
    "tests/run_trust_profile.py",
    "tests/run_decision_record_template.py",
    "tests/run_decision_record_artifacts.py",
    "tests/run_rate_model_profile.py",
    "tests/run_rate_model_profile_signature.py",
    "tests/run_accessorial_terms.py",
    "tests/run_accessorial_terms_profile.py",
    "tests/run_booking_plane_commercial_terms_doc.py",
    "tests/run_protocol_compatibility_profile.py",
    "tests/run_protocol_compatibility_signature.py",
    "tests/run_governance_index.py",
    "tests/run_release_readiness.py"
  ],
  "requiredSuiteChecks": [
    "policy_profile_sync",
    "registry_admission_policy",
    "registry_changelog_artifacts",
    "trusted_verifier_registry",
    "vendor_direct_profile",
    "trust_profile",
    "decision_record_template",
    "decision_record_artifacts",
    "rate_model_profile",
    "rate_model_profile_signature",
    "accessorial_terms",
    "accessorial_terms_profile",
    "booking_plane_commercial_terms_doc",
    "protocol_compatibility_profile",
    "protocol_compatibility_signature",
    "governance_index",
    "release_readiness"
  ],
  "requireGovernanceIndexSync": true
}
<!-- RELEASE_READINESS_REQUIREMENTS_END -->
