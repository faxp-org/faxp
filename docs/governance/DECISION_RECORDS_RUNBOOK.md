# Decision Records Runbook

This runbook defines how FAXP certification decision artifacts are created, reviewed, stored, and audited.

## Purpose
- Ensure every certification decision is reproducible and auditable.
- Keep decision rationale and evidence links machine-checkable.
- Prevent ambiguous approval/rejection outcomes.

## Source Contract
- Template: `/Users/zglitch009/projects/logistics-ai/FAXP/docs/governance/CERTIFICATION_DECISION_RECORD_TEMPLATE.md`
- Artifact check: `/Users/zglitch009/projects/logistics-ai/FAXP/tests/run_decision_record_artifacts.py`
- Template check: `/Users/zglitch009/projects/logistics-ai/FAXP/tests/run_decision_record_template.py`

## Artifact Location
- Store decision records in `conformance/`.
- Recommended file pattern:
  - `conformance/certification_decision_record.<decision-id>.json`
- Keep one sample artifact:
  - `conformance/certification_decision_record.sample.json`

## Creation Procedure
1. Copy the JSON example from the template.
2. Populate all required fields.
3. Add evidence links for required evidence types.
4. Confirm local evidence refs resolve to actual files.
5. Validate reason codes are machine-readable (`UPPER_SNAKE_CASE`).

## Review Procedure
1. Confirm decision outcome (`Approve`, `Reject`, or `RequestChanges`) is explicit.
2. Confirm `decisionReasonCodes` explain the outcome.
3. Confirm `adapterId`, `decidedTier`, and registry snapshot links are coherent.
4. Confirm conformance evidence reports pass for approvals.
5. Confirm approver metadata is complete.

## Validation Commands
```bash
python3 tests/run_decision_record_template.py
python3 tests/run_decision_record_artifacts.py
python3 conformance/run_all_checks.py --output /tmp/faxp_conformance_suite_report.json
```

## Retention and Audit
- Do not delete prior decision records.
- If a decision changes, create a new decision record with a new `decisionId`.
- Preserve links to both pre-change and post-change registry snapshots.
- Keep records in Git history for immutable audit traceability.

## Failure Handling
- If checks fail, mark decision as `RequestChanges` or `Reject`.
- Include blocking reason codes and required remediation in `notes`.
- Re-run checks only after evidence artifacts are updated.
