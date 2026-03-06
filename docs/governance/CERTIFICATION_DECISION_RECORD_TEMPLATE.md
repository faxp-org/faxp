# Certification Decision Record Template

Use this template to produce deterministic, auditable certification decisions.

## How to Use
1. Copy this template for each certification intake decision.
2. Fill every required field.
3. Include evidence links that resolve to concrete artifacts.
4. Keep reason codes machine-readable and stable.

## Normative Requirements (Test-Enforced)

<!-- CERT_DECISION_TEMPLATE_REQUIREMENTS_BEGIN -->
{
  "requiredFields": [
    "decisionId",
    "decisionTimestamp",
    "adapterId",
    "requestedTier",
    "decisionOutcome",
    "decidedTier",
    "decisionReasonCodes",
    "registryVersionEvaluated",
    "conformanceRunId",
    "conformanceReportRef",
    "evidenceLinks",
    "approver",
    "notes"
  ],
  "allowedDecisionOutcomes": ["Approve", "Reject", "RequestChanges"],
  "reasonCodePattern": "^[A-Z][A-Z0-9_]{2,}$",
  "requiredEvidenceTypes": [
    "ConformanceSuiteReport",
    "SubmissionManifest",
    "AdapterProfile",
    "RegistrySnapshotBefore",
    "RegistrySnapshotAfter",
    "PolicyChecks"
  ],
  "evidenceRefPattern": "^(https?://\\S+|[A-Za-z0-9._/-]+)$"
}
<!-- CERT_DECISION_TEMPLATE_REQUIREMENTS_END -->

## Example Decision Record

<!-- CERT_DECISION_TEMPLATE_EXAMPLE_BEGIN -->
{
  "decisionId": "faxp-cert-decision-20260222-0001",
  "decisionTimestamp": "2026-02-22T19:30:00Z",
  "adapterId": "sample-compliance-adapter-us-prod",
  "requestedTier": "TrustedProduction",
  "decisionOutcome": "Approve",
  "decidedTier": "TrustedProduction",
  "decisionReasonCodes": [
    "CONFORMANCE_SUITE_PASS",
    "POLICY_PROFILE_SYNC_PASS",
    "REGISTRY_ADMISSION_POLICY_PASS"
  ],
  "registryVersionEvaluated": "1.0.0",
  "conformanceRunId": "sample-run-id-20260222-0001",
  "conformanceReportRef": "conformance/sample_conformance_report.json",
  "evidenceLinks": [
    {
      "type": "ConformanceSuiteReport",
      "ref": "conformance/sample_conformance_report.json"
    },
    {
      "type": "SubmissionManifest",
      "ref": "conformance/submission_manifest.sample.json"
    },
    {
      "type": "AdapterProfile",
      "ref": "conformance/adapter_profile.sample.json"
    },
    {
      "type": "RegistrySnapshotBefore",
      "ref": "conformance/certification_registry.sample.json"
    },
    {
      "type": "RegistrySnapshotAfter",
      "ref": "conformance/certification_registry.sample.after_update.json"
    },
    {
      "type": "PolicyChecks",
      "ref": "tests/run_policy_profile_sync.py"
    }
  ],
  "approver": {
    "organization": "FAXP Certification Committee",
    "approverRef": "review-ticket-20260222-011",
    "approvalMode": "CommitteePolicy"
  },
  "notes": "Approved after deterministic conformance and policy gates passed."
}
<!-- CERT_DECISION_TEMPLATE_EXAMPLE_END -->
